#!/usr/bin/env python3
"""Lower validator-approved Marlowe JSON into Sui Move using local generator pipeline."""

from __future__ import annotations

import argparse
import io
import importlib.util
import json
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any


def load_py_module(name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(name, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import module {name} from {file_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_validator(contract_path: Path, validator_script: Path) -> tuple[bool, Any]:
    proc = subprocess.run(
        [sys.executable, str(validator_script), str(contract_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    payload: Any
    stdout = (proc.stdout or "").strip()
    if stdout:
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            payload = {"raw_output": stdout}
    else:
        payload = {"raw_output": ""}

    ok = proc.returncode == 0 and isinstance(payload, dict) and payload.get("status") == "valid"
    return ok, payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Lower Marlowe JSON to Move")
    parser.add_argument("contract", help="Path to Marlowe JSON")
    parser.add_argument("--module-name", default="generated_from_skill", help="Move module name")
    parser.add_argument("--out-move", default="", help="Output .move path (optional)")
    parser.add_argument(
        "--choice-policy",
        choices=["set_once", "overwrite"],
        default="set_once",
        help="Choice write policy in generated Move (default: set_once)",
    )
    parser.add_argument(
        "--no-emit-views",
        action="store_true",
        help="Disable generation of debug/view helper functions",
    )
    parser.add_argument(
        "--validator-script",
        default=str(Path(__file__).resolve().parents[2] / "marlowe-json-validator" / "scripts" / "validate_marlowe_json.py"),
        help="Path to validator script"
    )
    parser.add_argument(
        "--generator-dir",
        default=str(Path(__file__).resolve().parents[4] / "generator"),
        help="Path to repository generator directory"
    )
    args = parser.parse_args()

    contract_path = Path(args.contract).resolve()
    validator_script = Path(args.validator_script).resolve()
    generator_dir = Path(args.generator_dir).resolve()

    if not contract_path.exists():
        print(json.dumps({"status": "invalid_input", "message": f"Contract file not found: {contract_path}"}, ensure_ascii=False))
        return 1

    if not validator_script.exists():
        print(json.dumps({"status": "invalid_input", "message": f"Validator script not found: {validator_script}"}, ensure_ascii=False))
        return 1

    valid, validation_payload = run_validator(contract_path, validator_script)
    if not valid:
        print(
            json.dumps(
                {
                    "status": "invalid_input",
                    "message": "Input contract failed validation",
                    "validation": validation_payload,
                },
                ensure_ascii=False,
            )
        )
        return 1

    parser_py = generator_dir / "parser.py"
    fsm_py = generator_dir / "fsm_model.py"
    move_py = generator_dir / "move_generator.py"

    missing = [str(p) for p in (parser_py, fsm_py, move_py) if not p.exists()]
    if missing:
        print(json.dumps({"status": "lowering_error", "message": "Missing generator files", "missing": missing}, ensure_ascii=False))
        return 1

    try:
        # Ensure intra-generator imports (e.g. marlowe_types) resolve.
        generator_dir_str = str(generator_dir)
        if generator_dir_str not in sys.path:
            sys.path.insert(0, generator_dir_str)

        parser_mod = load_py_module("marlowe_parser", parser_py)
        fsm_mod = load_py_module("marlowe_fsm", fsm_py)
        move_mod = load_py_module("marlowe_movegen", move_py)

        contract_json = json.loads(contract_path.read_text(encoding="utf-8"))

        # Keep output channel pure JSON; capture generator stdout into metadata.
        capture = io.StringIO()
        with redirect_stdout(capture):
            ast = parser_mod.parse_contract(contract_json)
            infos, _ = fsm_mod.parse_contract_to_infos(ast, stage=0)
            stage_lookup = move_mod.build_stage_lookup(infos)
            options = move_mod.LoweringOptions(
                choice_write_policy=args.choice_policy,
                emit_debug_views=not args.no_emit_views,
            )
            move_code = move_mod.generate_module(
                infos,
                stage_lookup,
                module_name=args.module_name,
                options=options,
            )

        output_path = Path(args.out_move).resolve() if args.out_move else Path.cwd() / f"{args.module_name}.move"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(move_code, encoding="utf-8")

        stage_counts = {}
        for k, v in infos.items():
            stage_counts[k] = len(v)

        payload = {
            "status": "ok",
            "move_output": str(output_path),
            "metadata": {
                "module_name": args.module_name,
                "stage_counts": stage_counts,
                "validation": validation_payload,
                "generator_stdout": capture.getvalue().strip(),
                "lowering_options": {
                    "choice_policy": args.choice_policy,
                    "emit_debug_views": not args.no_emit_views,
                },
            },
        }
        print(json.dumps(payload, ensure_ascii=False))
        return 0

    except Exception as exc:
        print(json.dumps({"status": "lowering_error", "message": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
