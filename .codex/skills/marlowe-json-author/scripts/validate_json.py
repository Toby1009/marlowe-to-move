#!/usr/bin/env python3
"""Validate Marlowe JSON draft against local schema and parser compatibility."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


def maybe_schema_validate(instance: Any, schema: dict) -> tuple[list[str], list[str]]:
    try:
        import jsonschema  # type: ignore
    except Exception:
        return [], ["jsonschema package not installed; schema validation skipped"]

    errors = []
    validator = jsonschema.Draft202012Validator(schema)
    for err in validator.iter_errors(instance):
        path = "/".join(str(p) for p in err.path)
        errors.append(f"schema:{path or '$'}: {err.message}")
    return errors, []


def maybe_parse_contract(instance: Any, parser_file: Path) -> str | None:
    if not parser_file.exists():
        return None

    import sys
    parser_dir = str(parser_file.parent)
    if parser_dir not in sys.path:
        sys.path.insert(0, parser_dir)

    spec = importlib.util.spec_from_file_location("marlowe_parser", parser_file)
    if spec is None or spec.loader is None:
        return "Could not load parser module"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        module.parse_contract(instance)
        return None
    except Exception as exc:  # pragma: no cover
        return str(exc)


def unwrap_contract(payload: Any) -> Any:
    if isinstance(payload, dict) and "contract" in payload and "status" in payload:
        return payload["contract"]
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate draft JSON")
    parser.add_argument("contract", help="Path to contract JSON")
    parser.add_argument(
        "--schema",
        default=str(Path(__file__).resolve().parents[1] / "schema" / "marlowe-core-contract.schema.json"),
        help="Schema path"
    )
    parser.add_argument(
        "--parser-file",
        default=str(Path(__file__).resolve().parents[3] / "generator" / "parser.py"),
        help="Local parser.py path"
    )
    args = parser.parse_args()

    payload = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    contract = unwrap_contract(payload)
    schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))

    errors, warnings = maybe_schema_validate(contract, schema)

    parse_error = maybe_parse_contract(contract, Path(args.parser_file))
    if parse_error:
        errors.append(f"parser:$: {parse_error}")

    if errors:
        print(json.dumps({"status": "invalid", "errors": errors, "warnings": warnings}, indent=2, ensure_ascii=False))
        return 1

    print(json.dumps({"status": "valid", "warnings": warnings}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
