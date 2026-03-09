#!/usr/bin/env python3
"""Render BPMN XML and SVG from a Marlowe JSON payload passed on stdin."""

import json
import sys

from parser import parse_contract
from bpmn_generator import generate_bpmn_xml, generate_bpmn_svg
from bpmn_validate import validate_bpmn_xml


def unwrap_marlowe_payload(payload):
    if isinstance(payload, dict) and "contract" in payload and isinstance(payload["contract"], (dict, str)):
        return payload["contract"]
    return payload


def main() -> int:
    try:
        request = json.load(sys.stdin)
        payload = request.get("content", request)
        process_name = request.get("process_name") or "Marlowe Contract"

        contract_json = unwrap_marlowe_payload(payload)
        contract_ast = parse_contract(contract_json)

        bpmn_xml = generate_bpmn_xml(contract_ast, process_name=process_name)
        svg = generate_bpmn_svg(contract_ast, process_name=process_name)
        errors, warnings = validate_bpmn_xml(bpmn_xml)

        json.dump(
            {
                "ok": True,
                "bpmn_xml": bpmn_xml,
                "svg": svg,
                "warnings": warnings,
                "errors": errors,
                "valid": len(errors) == 0,
            },
            sys.stdout,
        )
        return 0
    except Exception as exc:
        json.dump(
            {
                "ok": False,
                "error": str(exc),
            },
            sys.stdout,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
