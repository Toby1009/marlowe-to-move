#!/usr/bin/env python3
"""Validate Marlowe JSON for schema + semantic checks."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

ABSOLUTE_TIME_MIN = 946684800  # 2000-01-01T00:00:00Z


def unwrap_contract(payload: Any) -> Any:
    if isinstance(payload, dict) and "status" in payload and "contract" in payload:
        return payload["contract"]
    return payload


def maybe_schema_errors(instance: Any, schema: dict) -> tuple[list[dict], list[dict]]:
    try:
        import jsonschema  # type: ignore
    except Exception:
        return [], [{"path": "$", "message": "jsonschema package not installed; schema validation skipped"}]

    errors = []
    validator = jsonschema.Draft202012Validator(schema)
    for err in validator.iter_errors(instance):
        path = "$" if not err.path else "$." + ".".join(str(p) for p in err.path)
        errors.append({"path": path, "message": err.message})
    return errors, []


def role_name(party: dict) -> str | None:
    if isinstance(party, dict) and isinstance(party.get("role_token"), str):
        return party["role_token"]
    return None


def check_value(node: Any, path: str, warnings: list[dict], errors: list[dict]) -> None:
    if isinstance(node, int):
        return
    if isinstance(node, str):
        if node in {"time_interval_start", "time_interval_end"}:
            return
        errors.append({"path": path, "message": f"Unsupported value string: {node}"})
        return
    if not isinstance(node, dict):
        errors.append({"path": path, "message": "Value must be integer/string/dict"})
        return

    if "constant" in node:
        c = node.get("constant")
        if not isinstance(c, int):
            errors.append({"path": f"{path}.constant", "message": "constant must be integer"})
        return

    if "value_of_choice" in node:
        return
    if "amount_of_token" in node and "in_account" in node:
        return
    if "use_value" in node:
        return
    if "negate" in node:
        check_value(node["negate"], f"{path}.negate", warnings, errors)
        return
    if "add" in node and "and" in node:
        check_value(node["add"], f"{path}.add", warnings, errors)
        check_value(node["and"], f"{path}.and", warnings, errors)
        return
    if "value" in node and "minus" in node:
        check_value(node["value"], f"{path}.value", warnings, errors)
        check_value(node["minus"], f"{path}.minus", warnings, errors)
        return
    if "multiply" in node and "times" in node:
        check_value(node["multiply"], f"{path}.multiply", warnings, errors)
        check_value(node["times"], f"{path}.times", warnings, errors)
        return
    if "divide" in node and "by" in node:
        check_value(node["divide"], f"{path}.divide", warnings, errors)
        check_value(node["by"], f"{path}.by", warnings, errors)
        return
    if "if" in node and "then" in node and "else" in node:
        check_observation(node["if"], f"{path}.if", warnings, errors)
        check_value(node["then"], f"{path}.then", warnings, errors)
        check_value(node["else"], f"{path}.else", warnings, errors)
        return

    errors.append({"path": path, "message": "Unsupported Value node"})


def check_observation(node: Any, path: str, warnings: list[dict], errors: list[dict]) -> None:
    if isinstance(node, bool):
        return
    if not isinstance(node, dict):
        errors.append({"path": path, "message": "Observation must be bool/object"})
        return

    if "both" in node and "and" in node:
        check_observation(node["both"], f"{path}.both", warnings, errors)
        check_observation(node["and"], f"{path}.and", warnings, errors)
        return
    if "either" in node and "or" in node:
        check_observation(node["either"], f"{path}.either", warnings, errors)
        check_observation(node["or"], f"{path}.or", warnings, errors)
        return
    if "not" in node:
        check_observation(node["not"], f"{path}.not", warnings, errors)
        return
    if "chose_something_for" in node:
        return

    for cmp_key in ("ge_than", "gt", "lt", "le_than", "equal_to"):
        if "value" in node and cmp_key in node:
            check_value(node["value"], f"{path}.value", warnings, errors)
            check_value(node[cmp_key], f"{path}.{cmp_key}", warnings, errors)
            return

    errors.append({"path": path, "message": "Unsupported Observation node"})


def numeric_constant(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, dict) and isinstance(value.get("constant"), int):
        return value["constant"]
    return None


def check_contract(
    node: Any,
    path: str,
    errors: list[dict],
    warnings: list[dict],
    tokens: set[str],
    choices_seen: set[tuple[str, str]],
) -> None:
    now = int(time.time())

    if isinstance(node, str):
        if node != "close":
            errors.append({"path": path, "message": f"Unsupported shorthand contract: {node}"})
        return

    if not isinstance(node, dict):
        errors.append({"path": path, "message": "Contract must be object or 'close'"})
        return

    if "let" in node or "assert" in node:
        errors.append({"path": path, "message": "let/assert not in current supported subset"})
        return

    if "pay" in node:
        c = numeric_constant(node.get("pay"))
        if c is not None and c <= 0:
            warnings.append({"path": f"{path}.pay", "message": "Non-positive payment constant may create useless transaction"})
        check_value(node.get("pay"), f"{path}.pay", warnings, errors)

        token = node.get("token", {}).get("token_name")
        if isinstance(token, str) and token:
            tokens.add(token)

        check_contract(node.get("then"), f"{path}.then", errors, warnings, tokens, choices_seen)
        return

    if "if" in node and "then" in node and "else" in node:
        check_observation(node.get("if"), f"{path}.if", warnings, errors)
        check_contract(node.get("then"), f"{path}.then", errors, warnings, tokens, choices_seen)
        check_contract(node.get("else"), f"{path}.else", errors, warnings, tokens, choices_seen)
        return

    if "when" in node and "timeout" in node and "timeout_continuation" in node:
        timeout = node.get("timeout")
        if not isinstance(timeout, int):
            errors.append({"path": f"{path}.timeout", "message": "timeout must be integer UNIX timestamp"})
        elif timeout < ABSOLUTE_TIME_MIN:
            errors.append({"path": f"{path}.timeout", "message": "timeout is not absolute UNIX time"})
        elif timeout < now + 3600:
            warnings.append({"path": f"{path}.timeout", "message": "timeout is within one hour from current time"})

        cases = node.get("when", [])
        if not isinstance(cases, list) or len(cases) == 0:
            errors.append({"path": f"{path}.when", "message": "when must contain at least one case"})
        else:
            for i, case in enumerate(cases):
                cpath = f"{path}.when[{i}]"
                action = case.get("case") if isinstance(case, dict) else None
                if not isinstance(action, dict):
                    errors.append({"path": f"{cpath}.case", "message": "case must be object"})
                    continue

                if "deposits" in action:
                    dval = numeric_constant(action.get("deposits"))
                    if dval is not None and dval <= 0:
                        warnings.append({"path": f"{cpath}.case.deposits", "message": "Non-positive deposit may be useless"})
                    check_value(action.get("deposits"), f"{cpath}.case.deposits", warnings, errors)
                    token_name = action.get("of_token", {}).get("token_name")
                    if isinstance(token_name, str) and token_name:
                        tokens.add(token_name)
                elif "for_choice" in action:
                    cid = action.get("for_choice", {})
                    cname = cid.get("choice_name") if isinstance(cid, dict) else None
                    cowner = role_name(cid.get("choice_owner", {})) if isinstance(cid, dict) else None
                    if isinstance(cname, str) and isinstance(cowner, str):
                        k = (cname, cowner)
                        if k in choices_seen:
                            warnings.append({"path": f"{cpath}.case.for_choice", "message": "Duplicate choice_name by same owner"})
                        choices_seen.add(k)

                    bounds = action.get("choose_between")
                    if not isinstance(bounds, list) or not bounds:
                        errors.append({"path": f"{cpath}.case.choose_between", "message": "choose_between must be non-empty"})
                    else:
                        for j, b in enumerate(bounds):
                            bpath = f"{cpath}.case.choose_between[{j}]"
                            if not isinstance(b, dict):
                                errors.append({"path": bpath, "message": "bound must be object"})
                                continue
                            low = b.get("from")
                            high = b.get("to")
                            if not isinstance(low, int) or not isinstance(high, int):
                                errors.append({"path": bpath, "message": "bound values must be integers"})
                            elif low > high:
                                errors.append({"path": bpath, "message": "bound.from must be <= bound.to"})
                elif "notify_if" in action:
                    check_observation(action.get("notify_if"), f"{cpath}.case.notify_if", warnings, errors)
                else:
                    errors.append({"path": f"{cpath}.case", "message": "Unsupported action type"})

                if not isinstance(case, dict) or "then" not in case:
                    errors.append({"path": cpath, "message": "case must include then continuation"})
                else:
                    check_contract(case["then"], f"{cpath}.then", errors, warnings, tokens, choices_seen)

        check_contract(node.get("timeout_continuation"), f"{path}.timeout_continuation", errors, warnings, tokens, choices_seen)
        return

    errors.append({"path": path, "message": "Unsupported contract constructor"})


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Marlowe JSON for supported subset")
    parser.add_argument("contract", help="Path to Marlowe JSON contract")
    parser.add_argument(
        "--schema",
        default=str(Path(__file__).resolve().parents[1] / "schema" / "marlowe-supported-subset.schema.json"),
        help="Path to schema"
    )
    args = parser.parse_args()

    contract_payload = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    contract = unwrap_contract(contract_payload)
    schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))

    schema_errors, schema_warnings = maybe_schema_errors(contract, schema)
    errors = list(schema_errors)
    warnings = list(schema_warnings)

    tokens: set[str] = set()
    choices_seen: set[tuple[str, str]] = set()

    check_contract(contract, "$", errors, warnings, tokens, choices_seen)

    if len(tokens) > 2:
        warnings.append({"path": "$", "message": f"High token count detected ({sorted(tokens)}); review settlement design carefully"})

    if errors:
        print(json.dumps({"status": "invalid", "errors": errors, "warnings": warnings}, indent=2, ensure_ascii=False))
        return 1

    payload = {
        "status": "valid",
        "warnings": warnings,
        "metadata": {
            "token_count": len(tokens),
            "tokens": sorted(tokens),
            "choice_count": len(choices_seen)
        }
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
