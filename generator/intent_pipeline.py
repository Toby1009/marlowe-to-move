#!/usr/bin/env python3
"""Template-first Marlowe authoring pipeline with fallback composition."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
SPECS_DIR = ROOT_DIR / "specs"
CONTRACT_SOURCES_DIR = ROOT_DIR / "contract" / "sources"

NORMALIZE_SCRIPT = ROOT_DIR / ".codex" / "skills" / "marlowe-json-author" / "scripts" / "normalize_input.py"
ANSWER_MERGE_SCRIPT = ROOT_DIR / ".codex" / "skills" / "marlowe-json-author" / "scripts" / "answer_merge.py"
VALIDATOR_SCRIPT = ROOT_DIR / ".codex" / "skills" / "marlowe-json-validator" / "scripts" / "validate_marlowe_json.py"
LOWERER_SCRIPT = ROOT_DIR / ".codex" / "skills" / "marlowe-to-sui-lowerer" / "scripts" / "lower_to_sui_move.py"

CHOICE_HINTS = ("vote", "voting", "approve", "reject", "decision", "投票", "表決", "同意", "不同意", "審核", "核准")
SWAP_HINTS = ("swap", "dex", "exchange", "兌換", "交換", "換幣")
GRANT_REVIEW_HINTS = ("grant", "review", "approve", "reject", "補助", "審核", "核准", "撥款")


def to_role(role_name: str) -> dict[str, str]:
    return {"role_token": role_name}


def run_json_command(cmd: list[str]) -> tuple[int, Any, str, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    parsed: Any = None
    if stdout:
        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError:
            parsed = None
    if stdout and parsed is None:
        for line in reversed([ln for ln in stdout.splitlines() if ln.strip()]):
            try:
                parsed = json.loads(line)
                break
            except json.JSONDecodeError:
                continue
    if stdout and parsed is None:
        parsed = {"raw_stdout": stdout}
    return proc.returncode, parsed, stdout, stderr


def sanitize_module_name(name: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    if not sanitized:
        sanitized = "generated_marlowe"
    if not sanitized[0].isalpha():
        sanitized = f"m_{sanitized}"
    return sanitized


def extract_roles(hints: dict[str, Any]) -> list[str]:
    parties = hints.get("parties")
    if not isinstance(parties, list):
        return []
    out: list[str] = []
    for role in parties:
        if isinstance(role, str) and role and role not in out:
            out.append(role)
    return out


def extract_tokens(hints: dict[str, Any]) -> list[dict[str, str]]:
    tokens = hints.get("tokens")
    if not isinstance(tokens, list):
        return []
    out: list[dict[str, str]] = []
    for tok in tokens:
        if not isinstance(tok, dict):
            continue
        token_name = tok.get("token_name")
        if not isinstance(token_name, str) or not token_name:
            continue
        symbol = tok.get("currency_symbol", "")
        out.append(
            {
                "currency_symbol": symbol if isinstance(symbol, str) else "",
                "token_name": token_name,
            }
        )
    return out


def extract_deadlines(hints: dict[str, Any]) -> list[int]:
    deadlines = hints.get("deadlines")
    if not isinstance(deadlines, list):
        return []
    out: list[int] = []
    for d in deadlines:
        if not isinstance(d, dict):
            continue
        unix = d.get("unix")
        if isinstance(unix, int) and unix > 0:
            out.append(unix)
    out = sorted(set(out))
    return out


def extract_amounts(hints: dict[str, Any]) -> list[int]:
    mentions = hints.get("money_mentions")
    if not isinstance(mentions, list):
        return []
    out: list[int] = []
    for m in mentions:
        if not isinstance(m, dict):
            continue
        val = m.get("minor_units")
        if isinstance(val, int) and val > 0:
            out.append(val)
    return sorted(set(out))


def detect_template_type(hints: dict[str, Any]) -> str | None:
    raw = hints.get("raw_text", "")
    text = raw.lower() if isinstance(raw, str) else ""
    if any(k in text for k in SWAP_HINTS):
        return "dex_swap"
    if any(k in text for k in GRANT_REVIEW_HINTS):
        return "grant_review"
    return None


def synthesize_answers(contract_type: str, hints: dict[str, Any]) -> dict[str, Any]:
    roles = extract_roles(hints)
    tokens = extract_tokens(hints)
    deadlines = extract_deadlines(hints)
    amounts = extract_amounts(hints)
    raw_text = hints.get("raw_text", "")
    lower_text = raw_text.lower() if isinstance(raw_text, str) else ""

    if contract_type == "dex_swap":
        payload: dict[str, Any] = {}
        if len(roles) >= 2:
            payload["roles"] = {"maker": roles[0], "taker": roles[1]}
        if len(tokens) >= 2:
            payload["token_mapping"] = {"maker_token": tokens[0], "taker_token": tokens[1]}
        if len(deadlines) >= 2:
            payload["timeout_mapping"] = {"maker_deadline": deadlines[0], "taker_deadline": deadlines[1]}
        if len(amounts) >= 2:
            payload["amount_mapping"] = {"maker_deposit": amounts[0], "taker_deposit": amounts[1]}
        return payload

    payload = {}
    if len(roles) >= 2:
        payload["roles"] = {"applicant": roles[0], "reviewer": roles[1]}
    if tokens:
        payload["single_token"] = tokens[0]
    if len(deadlines) >= 2:
        payload["timeout_mapping"] = {"deposit_deadline": deadlines[0], "review_deadline": deadlines[1]}
    if amounts:
        deposit = amounts[0]
        payout = amounts[-1] if len(amounts) >= 2 else amounts[0]
        payload["amount_mapping"] = {"deposit": deposit, "payout": payout, "refund": deposit}
    if any(k in lower_text for k in ("vote", "voting", "投票", "表決")):
        payload["choice"] = {"name": "vote_result", "approve_value": 1, "reject_value": 0}
    return payload


def merge_answers(hints: dict[str, Any], answers: dict[str, Any], contract_type: str) -> tuple[int, Any, str, str]:
    with tempfile.TemporaryDirectory(prefix="intent-pipeline-") as tmp:
        tmp_dir = Path(tmp)
        hints_path = tmp_dir / "normalized_hints.json"
        answers_path = tmp_dir / "answers.json"
        hints_path.write_text(json.dumps(hints, ensure_ascii=False, indent=2), encoding="utf-8")
        answers_path.write_text(json.dumps(answers, ensure_ascii=False, indent=2), encoding="utf-8")
        cmd = [
            sys.executable,
            str(ANSWER_MERGE_SCRIPT),
            str(hints_path),
            str(answers_path),
            "--contract-type",
            contract_type,
            "--output",
            "intent_pipeline.generated.json",
        ]
        return run_json_command(cmd)


def build_fallback_questions(missing_fields: list[dict[str, str]]) -> list[dict[str, str]]:
    questions: list[dict[str, str]] = []
    for item in missing_fields:
        field = item["field"]
        if field == "roles":
            questions.append(
                {
                    "id": "roles",
                    "question": "請至少提供兩個 role_token 角色名稱。",
                    "reason": item["reason"],
                }
            )
        elif field == "token":
            questions.append(
                {
                    "id": "token",
                    "question": "請指定至少一個 token（token_name 與可選 currency_symbol）。",
                    "reason": item["reason"],
                }
            )
        elif field == "amount":
            questions.append(
                {
                    "id": "amount",
                    "question": "請提供至少一個整數最小單位金額。",
                    "reason": item["reason"],
                }
            )
        elif field == "timeout":
            questions.append(
                {
                    "id": "timeout",
                    "question": "請提供至少一個絕對 UNIX timestamp timeout。",
                    "reason": item["reason"],
                }
            )
        elif field == "timeout_pair":
            questions.append(
                {
                    "id": "timeout_pair",
                    "question": "Choice 型流程請提供兩個 timeout（外層和內層）。",
                    "reason": item["reason"],
                }
            )
        if len(questions) >= 3:
            break
    return questions


def build_fallback_contract(hints: dict[str, Any]) -> dict[str, Any]:
    roles = extract_roles(hints)
    tokens = extract_tokens(hints)
    deadlines = extract_deadlines(hints)
    amounts = extract_amounts(hints)
    raw = hints.get("raw_text", "")
    text = raw.lower() if isinstance(raw, str) else ""
    needs_choice = any(k in text for k in CHOICE_HINTS)

    missing: list[dict[str, str]] = []
    if len(roles) < 2:
        missing.append({"field": "roles", "reason": "Need at least two roles for payment flow."})
    if not tokens:
        missing.append({"field": "token", "reason": "Need at least one token."})
    if not amounts:
        missing.append({"field": "amount", "reason": "Need at least one positive amount."})
    if not deadlines:
        missing.append({"field": "timeout", "reason": "Need at least one absolute timeout."})
    if needs_choice and len(deadlines) < 2:
        missing.append({"field": "timeout_pair", "reason": "Choice branch needs two timeouts."})

    if missing:
        return {
            "status": "missing_information",
            "missing": missing,
            "questions": build_fallback_questions(missing),
            "partial_contract": "close",
            "profile": "fallback",
        }

    actor = roles[0]
    counterparty = roles[1]
    token = tokens[0]
    deposit_amount = amounts[0]
    payout_amount = amounts[-1] if len(amounts) >= 2 else amounts[0]
    outer_timeout = deadlines[0]

    if needs_choice:
        inner_timeout = deadlines[1]
        choice_name = "vote_result" if any(k in text for k in ("vote", "voting", "投票", "表決")) else "decision"
        contract = {
            "when": [
                {
                    "case": {
                        "deposits": deposit_amount,
                        "party": to_role(actor),
                        "into_account": to_role(actor),
                        "of_token": token,
                    },
                    "then": {
                        "when": [
                            {
                                "case": {
                                    "for_choice": {
                                        "choice_name": choice_name,
                                        "choice_owner": to_role(counterparty),
                                    },
                                    "choose_between": [{"from": 0, "to": 1}],
                                },
                                "then": {
                                    "if": {
                                        "value": {
                                            "value_of_choice": {
                                                "choice_name": choice_name,
                                                "choice_owner": to_role(counterparty),
                                            }
                                        },
                                        "equal_to": 1,
                                    },
                                    "then": {
                                        "pay": payout_amount,
                                        "from_account": to_role(actor),
                                        "to": {"party": to_role(counterparty)},
                                        "token": token,
                                        "then": "close",
                                    },
                                    "else": {
                                        "pay": deposit_amount,
                                        "from_account": to_role(actor),
                                        "to": {"party": to_role(actor)},
                                        "token": token,
                                        "then": "close",
                                    },
                                },
                            }
                        ],
                        "timeout": inner_timeout,
                        "timeout_continuation": "close",
                    },
                }
            ],
            "timeout": outer_timeout,
            "timeout_continuation": "close",
        }
        return {
            "status": "ok",
            "contract": contract,
            "profile": "fallback.choice_gated_settlement",
            "notes": [
                "No template matched; composed from Marlowe primitives (When/Choice/If/Pay/Close).",
                "Choice owner is the second detected role.",
            ],
            "assumptions": [
                f"{actor} is the depositor and {counterparty} is the decision owner.",
            ],
        }

    contract = {
        "when": [
            {
                "case": {
                    "deposits": deposit_amount,
                    "party": to_role(actor),
                    "into_account": to_role(actor),
                    "of_token": token,
                },
                "then": {
                    "pay": payout_amount,
                    "from_account": to_role(actor),
                    "to": {"party": to_role(counterparty)},
                    "token": token,
                    "then": "close",
                },
            }
        ],
        "timeout": outer_timeout,
        "timeout_continuation": "close",
    }
    return {
        "status": "ok",
        "contract": contract,
        "profile": "fallback.deposit_then_pay",
        "notes": [
            "No template matched; composed a minimal deposit-then-pay contract.",
        ],
        "assumptions": [
            f"{actor} deposits before timeout; payout goes to {counterparty}.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Intent -> Marlowe JSON -> validation -> Move lowering")
    parser.add_argument("input", help="Path to natural-language requirement (md/txt)")
    parser.add_argument("--answers", default="", help="Optional answers JSON to override auto-filled template slots")
    parser.add_argument("--spec-name", default="", help="Output spec filename under specs/")
    parser.add_argument("--module-name", default="", help="Override Move module name for lowering")
    parser.add_argument("--force-fallback", action="store_true", help="Skip template matching and use fallback composer")
    parser.add_argument("--skip-lower", action="store_true", help="Skip Marlowe -> Move lowering step")
    parser.add_argument("--choice-policy", choices=["set_once", "overwrite"], default="set_once")
    parser.add_argument("--no-emit-views", action="store_true")
    args = parser.parse_args()

    rc, hints_payload, _, hints_stderr = run_json_command([sys.executable, str(NORMALIZE_SCRIPT), args.input])
    if rc != 0 or not isinstance(hints_payload, dict):
        print(
            json.dumps(
                {
                    "status": "authoring_error",
                    "message": "normalize_input failed",
                    "stderr": hints_stderr,
                    "payload": hints_payload,
                },
                ensure_ascii=False,
            )
        )
        return 1

    selected_template: str | None = None
    mode = "fallback"
    answers_used: dict[str, Any] | None = None

    if not args.force_fallback:
        selected_template = detect_template_type(hints_payload)

    if selected_template is not None:
        mode = "template"
        if args.answers:
            answers_used = json.loads(Path(args.answers).read_text(encoding="utf-8"))
        else:
            answers_used = synthesize_answers(selected_template, hints_payload)
        author_rc, author_payload, _, author_stderr = merge_answers(hints_payload, answers_used, selected_template)
        if author_rc != 0 and (not isinstance(author_payload, dict) or author_payload.get("status") == "ok"):
            author_payload = {
                "status": "authoring_error",
                "message": "answer_merge failed",
                "stderr": author_stderr,
                "payload": author_payload,
            }
    else:
        author_payload = build_fallback_contract(hints_payload)

    if not isinstance(author_payload, dict):
        print(json.dumps({"status": "authoring_error", "message": "Invalid author payload"}, ensure_ascii=False))
        return 1

    if author_payload.get("status") != "ok":
        print(
            json.dumps(
                {
                    "status": author_payload.get("status", "authoring_error"),
                    "mode": mode,
                    "selected_template": selected_template,
                    "normalized_hints": hints_payload,
                    "authoring": author_payload,
                    "answers_used": answers_used,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    contract = author_payload.get("contract")
    if not isinstance(contract, (dict, str)):
        print(json.dumps({"status": "authoring_error", "message": "Author output missing contract"}, ensure_ascii=False))
        return 1

    SPECS_DIR.mkdir(parents=True, exist_ok=True)
    spec_filename = args.spec_name if args.spec_name else f"{Path(args.input).stem}.auto.marlowe.json"
    spec_path = SPECS_DIR / Path(spec_filename).name
    spec_path.write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")

    val_rc, validation_payload, _, validation_stderr = run_json_command([sys.executable, str(VALIDATOR_SCRIPT), str(spec_path)])
    if not isinstance(validation_payload, dict):
        validation_payload = {"status": "invalid", "errors": [{"path": "$", "message": "Validator produced invalid output"}]}

    if val_rc != 0 or validation_payload.get("status") != "valid":
        print(
            json.dumps(
                {
                    "status": "invalid_contract",
                    "mode": mode,
                    "selected_template": selected_template,
                    "spec_output": str(spec_path),
                    "normalized_hints": hints_payload,
                    "authoring": author_payload,
                    "answers_used": answers_used,
                    "validation": validation_payload,
                    "validator_stderr": validation_stderr,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    lowering_payload: dict[str, Any] | None = None
    if not args.skip_lower:
        CONTRACT_SOURCES_DIR.mkdir(parents=True, exist_ok=True)
        module_name_raw = args.module_name if args.module_name else Path(spec_path).stem
        module_name = sanitize_module_name(module_name_raw)
        out_move = CONTRACT_SOURCES_DIR / f"{Path(spec_path).stem}.move"
        cmd = [
            sys.executable,
            str(LOWERER_SCRIPT),
            str(spec_path),
            "--module-name",
            module_name,
            "--out-move",
            str(out_move),
            "--choice-policy",
            args.choice_policy,
        ]
        if args.no_emit_views:
            cmd.append("--no-emit-views")
        _, lowering_payload_raw, _, lower_stderr = run_json_command(cmd)
        if isinstance(lowering_payload_raw, dict):
            lowering_payload = lowering_payload_raw
        else:
            lowering_payload = {"status": "lowering_error", "message": "Lowerer produced invalid output"}
        if lowering_payload.get("status") != "ok":
            guidance: list[str] = []
            msg = lowering_payload.get("message")
            if isinstance(msg, str) and "Could not map Marlowe token to Move type" in msg:
                guidance.append(
                    "Set MARLOWE_TOKEN_MAP_JSON before running. "
                    'Example: export MARLOWE_TOKEN_MAP_JSON=\'{":USDC":"test::mock_usdc::USDC",":SUI":"sui::sui::SUI"}\'.'
                )
            print(
                json.dumps(
                    {
                        "status": "lowering_error",
                        "mode": mode,
                        "selected_template": selected_template,
                        "spec_output": str(spec_path),
                        "normalized_hints": hints_payload,
                        "authoring": author_payload,
                        "answers_used": answers_used,
                        "validation": validation_payload,
                        "lowering": lowering_payload,
                        "guidance": guidance,
                        "lowerer_stderr": lower_stderr,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 1

    print(
        json.dumps(
            {
                "status": "ok",
                "mode": mode,
                "selected_template": selected_template,
                "spec_output": str(spec_path),
                "normalized_hints": hints_payload,
                "authoring": author_payload,
                "answers_used": answers_used,
                "validation": validation_payload,
                "lowering": lowering_payload,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
