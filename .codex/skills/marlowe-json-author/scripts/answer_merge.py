#!/usr/bin/env python3
"""Merge clarification answers into a final Marlowe JSON draft."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


def as_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def normalize_token(raw: Any) -> dict[str, str] | None:
    if isinstance(raw, str) and raw:
        return {"currency_symbol": "", "token_name": raw}
    if isinstance(raw, dict):
        token_name = raw.get("token_name")
        if isinstance(token_name, str) and token_name:
            symbol = raw.get("currency_symbol", "")
            return {"currency_symbol": symbol if isinstance(symbol, str) else "", "token_name": token_name}
    return None


def normalize_roles(hints: dict[str, Any], answers: dict[str, Any]) -> tuple[str | None, str | None]:
    roles = answers.get("roles")
    if isinstance(roles, dict):
        applicant = roles.get("applicant")
        reviewer = roles.get("reviewer")
        if isinstance(applicant, str) and isinstance(reviewer, str) and applicant and reviewer:
            return applicant, reviewer

    party_mapping = answers.get("party_mapping")
    if isinstance(party_mapping, dict):
        uniq = []
        for role in party_mapping.values():
            if isinstance(role, str) and role and role not in uniq:
                uniq.append(role)
        if len(uniq) >= 2:
            return uniq[0], uniq[1]

    hint_roles = hints.get("parties")
    if isinstance(hint_roles, list):
        uniq = [x for x in hint_roles if isinstance(x, str) and x]
        if len(uniq) >= 2:
            return uniq[0], uniq[1]

    return None, None


def normalize_role_pair(
    hints: dict[str, Any],
    answers: dict[str, Any],
    left_key: str,
    right_key: str,
) -> tuple[str | None, str | None]:
    roles = answers.get("roles")
    if isinstance(roles, dict):
        left = roles.get(left_key)
        right = roles.get(right_key)
        if isinstance(left, str) and isinstance(right, str) and left and right:
            return left, right

    pair = answers.get("party_pair")
    if isinstance(pair, dict):
        left = pair.get(left_key)
        right = pair.get(right_key)
        if isinstance(left, str) and isinstance(right, str) and left and right:
            return left, right

    mapped = answers.get("party_mapping")
    if isinstance(mapped, dict):
        uniq = []
        for role in mapped.values():
            if isinstance(role, str) and role and role not in uniq:
                uniq.append(role)
        if len(uniq) >= 2:
            return uniq[0], uniq[1]

    hint_roles = hints.get("parties")
    if isinstance(hint_roles, list):
        uniq = [x for x in hint_roles if isinstance(x, str) and x]
        if len(uniq) >= 2:
            return uniq[0], uniq[1]
    return None, None


def normalize_timeouts(hints: dict[str, Any], answers: dict[str, Any]) -> tuple[int | None, int | None]:
    mapping = answers.get("timeout_mapping", {})
    if isinstance(mapping, dict):
        d = as_int(mapping.get("deposit_deadline"))
        r = as_int(mapping.get("review_deadline"))
        if d is not None and r is not None:
            return d, r

    hint_deadlines = hints.get("deadlines")
    if isinstance(hint_deadlines, list):
        unix_times = [as_int(x.get("unix")) for x in hint_deadlines if isinstance(x, dict)]
        unix_times = [x for x in unix_times if x is not None]
        unix_times.sort()
        if len(unix_times) >= 2:
            return unix_times[0], unix_times[1]
    return None, None


def normalize_timeouts_dex(hints: dict[str, Any], answers: dict[str, Any]) -> tuple[int | None, int | None]:
    mapping = answers.get("timeout_mapping", {})
    if isinstance(mapping, dict):
        maker_deadline = as_int(mapping.get("maker_deadline"))
        taker_deadline = as_int(mapping.get("taker_deadline"))
        if maker_deadline is not None and taker_deadline is not None:
            return maker_deadline, taker_deadline

    hint_deadlines = hints.get("deadlines")
    if isinstance(hint_deadlines, list):
        unix_times = [as_int(x.get("unix")) for x in hint_deadlines if isinstance(x, dict)]
        unix_times = [x for x in unix_times if x is not None]
        unix_times.sort()
        if len(unix_times) >= 2:
            return unix_times[0], unix_times[1]
    return None, None


def normalize_amounts(hints: dict[str, Any], answers: dict[str, Any]) -> tuple[int | None, int | None, int | None]:
    mapping = answers.get("amount_mapping", {})
    if isinstance(mapping, dict):
        dep = as_int(mapping.get("deposit"))
        payout = as_int(mapping.get("payout"))
        refund = as_int(mapping.get("refund")) if mapping.get("refund") is not None else dep
        if dep is not None and payout is not None:
            return dep, payout, refund

    hint_amounts = hints.get("money_mentions")
    if isinstance(hint_amounts, list):
        vals = [as_int(x.get("minor_units")) for x in hint_amounts if isinstance(x, dict)]
        vals = [v for v in vals if v is not None and v > 0]
        vals = sorted(set(vals))
        if len(vals) >= 2:
            dep = vals[0]
            payout = vals[-1]
            return dep, payout, dep
    return None, None, None


def normalize_amounts_dex(hints: dict[str, Any], answers: dict[str, Any]) -> tuple[int | None, int | None]:
    mapping = answers.get("amount_mapping", {})
    if isinstance(mapping, dict):
        maker_amount = as_int(mapping.get("maker_deposit"))
        taker_amount = as_int(mapping.get("taker_deposit"))
        if maker_amount is not None and taker_amount is not None:
            return maker_amount, taker_amount

    hint_amounts = hints.get("money_mentions")
    if isinstance(hint_amounts, list):
        vals = [as_int(x.get("minor_units")) for x in hint_amounts if isinstance(x, dict)]
        vals = [v for v in vals if v is not None and v > 0]
        uniq = sorted(set(vals))
        if len(uniq) == 2:
            return uniq[0], uniq[1]
    return None, None


def normalize_token_pair(hints: dict[str, Any], answers: dict[str, Any]) -> tuple[dict[str, str] | None, dict[str, str] | None]:
    mapping = answers.get("token_mapping")
    if isinstance(mapping, dict):
        maker_token = normalize_token(mapping.get("maker_token"))
        taker_token = normalize_token(mapping.get("taker_token"))
        if maker_token and taker_token:
            return maker_token, taker_token

    hint_tokens = hints.get("tokens")
    if isinstance(hint_tokens, list) and len(hint_tokens) >= 2:
        a = normalize_token(hint_tokens[0])
        b = normalize_token(hint_tokens[1])
        if a and b:
            return a, b
    return None, None


def to_role(role_name: str) -> dict[str, str]:
    return {"role_token": role_name}


def build_grant_review_contract(
    applicant: str,
    reviewer: str,
    token: dict[str, str],
    deposit_deadline: int,
    review_deadline: int,
    deposit_amount: int,
    payout_amount: int,
    refund_amount: int,
    choice_name: str,
    approve_value: int,
    reject_value: int,
) -> dict[str, Any]:
    choice_id = {"choice_name": choice_name, "choice_owner": to_role(reviewer)}
    choice_value = {"value_of_choice": choice_id}

    return {
        "when": [
            {
                "case": {
                    "deposits": deposit_amount,
                    "party": to_role(applicant),
                    "into_account": to_role(applicant),
                    "of_token": token,
                },
                "then": {
                    "when": [
                        {
                            "case": {
                                "for_choice": choice_id,
                                "choose_between": [{"from": min(approve_value, reject_value), "to": max(approve_value, reject_value)}],
                            },
                            "then": {
                                "if": {"value": choice_value, "equal_to": approve_value},
                                "then": {
                                    "pay": payout_amount,
                                    "from_account": to_role(reviewer),
                                    "to": {"party": to_role(applicant)},
                                    "token": token,
                                    "then": {
                                        "pay": refund_amount,
                                        "from_account": to_role(applicant),
                                        "to": {"party": to_role(applicant)},
                                        "token": token,
                                        "then": "close",
                                    },
                                },
                                "else": {
                                    "if": {"value": choice_value, "equal_to": reject_value},
                                    "then": {
                                        "pay": refund_amount,
                                        "from_account": to_role(applicant),
                                        "to": {"party": to_role(applicant)},
                                        "token": token,
                                        "then": "close",
                                    },
                                    "else": "close",
                                },
                            },
                        }
                    ],
                    "timeout": review_deadline,
                    "timeout_continuation": "close",
                },
            }
        ],
        "timeout": deposit_deadline,
        "timeout_continuation": "close",
    }


def build_dex_swap_contract(
    maker: str,
    taker: str,
    maker_token: dict[str, str],
    taker_token: dict[str, str],
    maker_amount: int,
    taker_amount: int,
    maker_deadline: int,
    taker_deadline: int,
) -> dict[str, Any]:
    outer_timeout = min(maker_deadline, taker_deadline)
    inner_timeout = max(maker_deadline, taker_deadline)

    settle_then = {
        "pay": maker_amount,
        "from_account": to_role(maker),
        "to": {"party": to_role(taker)},
        "token": maker_token,
        "then": {
            "pay": taker_amount,
            "from_account": to_role(taker),
            "to": {"party": to_role(maker)},
            "token": taker_token,
            "then": "close",
        },
    }

    maker_deposit_case = {
        "case": {
            "deposits": maker_amount,
            "party": to_role(maker),
            "into_account": to_role(maker),
            "of_token": maker_token,
        },
        "then": {
            "when": [
                {
                    "case": {
                        "deposits": taker_amount,
                        "party": to_role(taker),
                        "into_account": to_role(taker),
                        "of_token": taker_token,
                    },
                    "then": settle_then,
                }
            ],
            "timeout": inner_timeout,
            "timeout_continuation": "close",
        },
    }

    taker_deposit_case = {
        "case": {
            "deposits": taker_amount,
            "party": to_role(taker),
            "into_account": to_role(taker),
            "of_token": taker_token,
        },
        "then": {
            "when": [
                {
                    "case": {
                        "deposits": maker_amount,
                        "party": to_role(maker),
                        "into_account": to_role(maker),
                        "of_token": maker_token,
                    },
                    "then": settle_then,
                }
            ],
            "timeout": inner_timeout,
            "timeout_continuation": "close",
        },
    }

    return {
        "when": [maker_deposit_case, taker_deposit_case],
        "timeout": outer_timeout,
        "timeout_continuation": "close",
    }


def find_parser_file(start: Path) -> Path | None:
    for parent in [start] + list(start.parents):
        candidate = parent / "generator" / "parser.py"
        if candidate.exists():
            return candidate
    return None


def validate_contract(contract: dict[str, Any], schema_path: Path, parser_file: Path | None) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        import jsonschema  # type: ignore

        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        validator = jsonschema.Draft202012Validator(schema)
        for err in validator.iter_errors(contract):
            path = "/".join(str(p) for p in err.path)
            errors.append(f"schema:{path or '$'}: {err.message}")
    except Exception:
        warnings.append("jsonschema package not installed; schema validation skipped")

    if parser_file is not None:
        import sys

        parser_dir = str(parser_file.parent)
        if parser_dir not in sys.path:
            sys.path.insert(0, parser_dir)
        spec = importlib.util.spec_from_file_location("marlowe_parser", parser_file)
        if spec is None or spec.loader is None:
            warnings.append("parser import skipped")
        else:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            try:
                module.parse_contract(contract)
            except Exception as exc:  # pragma: no cover
                errors.append(f"parser:$: {exc}")

    return errors, warnings


def resolve_output_path(output_arg: str, normalized_hints_path: str, contract_type: str) -> Path:
    specs_dir = Path.cwd() / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)

    if output_arg:
        # Enforce specs/ as the output root for all generated files.
        name = Path(output_arg).name
        return specs_dir / name

    stem = Path(normalized_hints_path).stem
    if stem.endswith("_hints"):
        stem = stem[: -len("_hints")]
    return specs_dir / f"{stem}.{contract_type}.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge answers into a final Marlowe JSON draft")
    parser.add_argument("normalized_hints", help="Path to JSON output from normalize_input.py")
    parser.add_argument("answers", help="Path to JSON answers file")
    parser.add_argument("--output", default="", help="Output path; default prints JSON")
    parser.add_argument(
        "--contract-type",
        default="grant_review",
        choices=["grant_review", "dex_swap"],
        help="Contract builder profile"
    )
    args = parser.parse_args()

    hints = json.loads(Path(args.normalized_hints).read_text(encoding="utf-8"))
    answers = json.loads(Path(args.answers).read_text(encoding="utf-8"))
    ambiguity_fields = {
        x.get("field")
        for x in hints.get("ambiguities", [])
        if isinstance(x, dict) and isinstance(x.get("field"), str)
    }

    missing: list[dict[str, str]] = []
    questions: list[dict[str, str]] = []

    if args.contract_type == "grant_review":
        has_roles_answer = (
            isinstance(answers.get("roles"), dict)
            and isinstance(answers["roles"].get("applicant"), str)
            and isinstance(answers["roles"].get("reviewer"), str)
        ) or isinstance(answers.get("party_mapping"), dict)
        has_token_answer = normalize_token(answers.get("single_token")) is not None
        tm = answers.get("timeout_mapping")
        has_timeout_answer = isinstance(tm, dict) and as_int(tm.get("deposit_deadline")) is not None and as_int(tm.get("review_deadline")) is not None
        am = answers.get("amount_mapping")
        has_amount_answer = isinstance(am, dict) and as_int(am.get("deposit")) is not None and as_int(am.get("payout")) is not None

        applicant, reviewer = normalize_role_pair(hints, answers, "applicant", "reviewer")
        token = normalize_token(answers.get("single_token"))
        if token is None:
            hint_tokens = hints.get("tokens")
            if isinstance(hint_tokens, list) and len(hint_tokens) == 1:
                token = normalize_token(hint_tokens[0])

        deposit_deadline, review_deadline = normalize_timeouts(hints, answers)
        deposit_amount, payout_amount, refund_amount = normalize_amounts(hints, answers)

        if ("parties.mapping" in ambiguity_fields and not has_roles_answer) or applicant is None or reviewer is None:
            missing.append({"field": "roles", "reason": "Need two role_token parties (applicant/reviewer)."})
            questions.append(
                {
                    "id": "party_mapping",
                    "question": "請提供兩個角色名稱並映射（例如 applicant=Applicant, reviewer=Agency）。",
                    "reason": "Cannot safely infer final role mapping.",
                }
            )

        if token is None:
            missing.append({"field": "single_token", "reason": "Need one token for grant_review profile."})
            questions.append(
                {
                    "id": "single_token",
                    "question": "請指定單一 token（token_name 與可選 currency_symbol）。",
                    "reason": "Token choice is required and cannot be guessed.",
                }
            )
        elif ("token.mapping" in ambiguity_fields and not has_token_answer):
            questions.append(
                {
                    "id": "single_token_confirm",
                    "question": "偵測到多 token，grant_review 只用一種 token。請確認要用哪一種。",
                    "reason": "Token mapping is ambiguous.",
                }
            )

        if ("timeout.mapping" in ambiguity_fields and not has_timeout_answer) or deposit_deadline is None or review_deadline is None:
            missing.append({"field": "timeout_mapping", "reason": "Need deposit and review absolute UNIX deadlines."})
            questions.append(
                {
                    "id": "timeout_mapping",
                    "question": "請提供 deposit_deadline 與 review_deadline（UNIX timestamp, UTC）。",
                    "reason": "Timeout mapping is required.",
                }
            )

        if ("money.mapping" in ambiguity_fields and not has_amount_answer) or deposit_amount is None or payout_amount is None:
            missing.append({"field": "amount_mapping", "reason": "Need deposit and payout amounts in integer minor units."})
            questions.append(
                {
                    "id": "amount_mapping",
                    "question": "請提供 deposit、payout（以及可選 refund）整數金額。",
                    "reason": "Amount mapping is required.",
                }
            )

        if missing:
            payload = {
                "status": "missing_information",
                "missing": missing,
                "questions": questions[:3],
                "partial_contract": "close",
            }
        else:
            choice_cfg = answers.get("choice", {})
            choice_name = choice_cfg.get("name") if isinstance(choice_cfg, dict) else None
            approve_value = choice_cfg.get("approve_value") if isinstance(choice_cfg, dict) else None
            reject_value = choice_cfg.get("reject_value") if isinstance(choice_cfg, dict) else None
            choice_name = choice_name if isinstance(choice_name, str) and choice_name else "review_result"
            approve_value = as_int(approve_value) if approve_value is not None else 1
            reject_value = as_int(reject_value) if reject_value is not None else 0
            if approve_value is None:
                approve_value = 1
            if reject_value is None:
                reject_value = 0

            contract = build_grant_review_contract(
                applicant=applicant,  # type: ignore[arg-type]
                reviewer=reviewer,  # type: ignore[arg-type]
                token=token,  # type: ignore[arg-type]
                deposit_deadline=deposit_deadline,  # type: ignore[arg-type]
                review_deadline=review_deadline,  # type: ignore[arg-type]
                deposit_amount=deposit_amount,  # type: ignore[arg-type]
                payout_amount=payout_amount,  # type: ignore[arg-type]
                refund_amount=refund_amount if refund_amount is not None else deposit_amount,  # type: ignore[arg-type]
                choice_name=choice_name,
                approve_value=approve_value,
                reject_value=reject_value,
            )

            schema_path = Path(__file__).resolve().parents[1] / "schema" / "marlowe-core-contract.schema.json"
            parser_file = find_parser_file(Path.cwd())
            errors, warnings = validate_contract(contract, schema_path, parser_file)
            if errors:
                payload = {"status": "invalid_request", "errors": errors, "warnings": warnings}
            else:
                payload = {
                    "status": "ok",
                    "contract": contract,
                    "notes": [
                        "Merged from normalize_input output and explicit user answers.",
                        "Amounts use integer minor units.",
                    ],
                    "assumptions": [
                        f"{reviewer} has sufficient treasury balance for payout.",
                    ],
                    "warnings": warnings,
                }
    else:
        has_roles_answer = (
            isinstance(answers.get("roles"), dict)
            and isinstance(answers["roles"].get("maker"), str)
            and isinstance(answers["roles"].get("taker"), str)
        ) or isinstance(answers.get("party_mapping"), dict)
        tm = answers.get("timeout_mapping")
        has_timeout_answer = isinstance(tm, dict) and as_int(tm.get("maker_deadline")) is not None and as_int(tm.get("taker_deadline")) is not None
        am = answers.get("amount_mapping")
        has_amount_answer = isinstance(am, dict) and as_int(am.get("maker_deposit")) is not None and as_int(am.get("taker_deposit")) is not None
        token_map = answers.get("token_mapping")
        has_token_pair_answer = (
            isinstance(token_map, dict)
            and normalize_token(token_map.get("maker_token")) is not None
            and normalize_token(token_map.get("taker_token")) is not None
        )

        maker, taker = normalize_role_pair(hints, answers, "maker", "taker")
        maker_token, taker_token = normalize_token_pair(hints, answers)
        maker_deadline, taker_deadline = normalize_timeouts_dex(hints, answers)
        maker_amount, taker_amount = normalize_amounts_dex(hints, answers)

        if ("parties.mapping" in ambiguity_fields and not has_roles_answer) or maker is None or taker is None:
            missing.append({"field": "roles", "reason": "Need maker/taker role_token mapping."})
            questions.append(
                {
                    "id": "party_mapping",
                    "question": "請提供 maker 與 taker 的 role_token（例如 maker=Maker, taker=Taker）。",
                    "reason": "Cannot safely infer role mapping for dex_swap.",
                }
            )

        if ("token.mapping" in ambiguity_fields and not has_token_pair_answer) or maker_token is None or taker_token is None:
            missing.append({"field": "token_mapping", "reason": "Need maker_token and taker_token mapping."})
            questions.append(
                {
                    "id": "token_mapping",
                    "question": "請提供 maker_token 與 taker_token（含 token_name 與可選 currency_symbol）。",
                    "reason": "Cannot safely infer token pair mapping for dex_swap.",
                }
            )

        if ("timeout.mapping" in ambiguity_fields and not has_timeout_answer) or maker_deadline is None or taker_deadline is None:
            missing.append({"field": "timeout_mapping", "reason": "Need maker and taker absolute UNIX deadlines."})
            questions.append(
                {
                    "id": "timeout_mapping",
                    "question": "請提供 maker_deadline 與 taker_deadline（UNIX timestamp, UTC）。",
                    "reason": "Timeout mapping is required for dex_swap.",
                }
            )

        if ("money.mapping" in ambiguity_fields and not has_amount_answer) or maker_amount is None or taker_amount is None:
            missing.append({"field": "amount_mapping", "reason": "Need maker_deposit and taker_deposit amounts."})
            questions.append(
                {
                    "id": "amount_mapping",
                    "question": "請提供 maker_deposit 與 taker_deposit 整數金額（最小單位）。",
                    "reason": "Amount mapping is required for dex_swap.",
                }
            )

        if missing:
            payload = {
                "status": "missing_information",
                "missing": missing,
                "questions": questions[:3],
                "partial_contract": "close",
            }
        else:
            contract = build_dex_swap_contract(
                maker=maker,  # type: ignore[arg-type]
                taker=taker,  # type: ignore[arg-type]
                maker_token=maker_token,  # type: ignore[arg-type]
                taker_token=taker_token,  # type: ignore[arg-type]
                maker_amount=maker_amount,  # type: ignore[arg-type]
                taker_amount=taker_amount,  # type: ignore[arg-type]
                maker_deadline=maker_deadline,  # type: ignore[arg-type]
                taker_deadline=taker_deadline,  # type: ignore[arg-type]
            )

            schema_path = Path(__file__).resolve().parents[1] / "schema" / "marlowe-core-contract.schema.json"
            parser_file = find_parser_file(Path.cwd())
            errors, warnings = validate_contract(contract, schema_path, parser_file)
            if errors:
                payload = {"status": "invalid_request", "errors": errors, "warnings": warnings}
            else:
                payload = {
                    "status": "ok",
                    "contract": contract,
                    "notes": [
                        "Built dex_swap contract with two-token atomic settlement.",
                        "Amounts use integer minor units.",
                    ],
                    "assumptions": [
                        f"{maker} and {taker} complete deposits before deadline.",
                    ],
                    "warnings": warnings,
                }

    output_path = resolve_output_path(args.output, args.normalized_hints, args.contract_type)
    file_payload: Any = payload
    if payload.get("status") == "ok" and isinstance(payload.get("contract"), (dict, str)):
        # Persist pure Marlowe JSON in specs/ for downstream tools.
        file_payload = payload["contract"]
    output_path.write_text(json.dumps(file_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
