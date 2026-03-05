---
name: marlowe-to-sui-lowerer
description: Deterministically lower validator-approved Marlowe JSON into Sui Move artifacts using the local Marlowe-to-Move generator pipeline. Use when JSON has already passed validation and you need reproducible Move source output with explicit assumptions and failure on unsupported constructs.
---

# Purpose

Compile validated Marlowe JSON into Sui Move artifacts.

This skill does not author requirements and does not auto-fix invalid contracts.

# Preconditions

- Input must be validator-approved JSON.
- Input must conform to the supported subset used by this repository.

# Workflow

1. Run `scripts/lower_to_sui_move.py` with an input JSON file.
2. Script validates input with local validator skill checks.
3. Script invokes local generator pipeline (`generator/parser.py`, `generator/fsm_model.py`, `generator/move_generator.py`).
4. Script writes deterministic `.move` output and metadata report.

# Output

Return one JSON object:
- `{"status":"ok","move_output":"...","metadata":{...}}`
- `{"status":"invalid_input",...}`
- `{"status":"lowering_error",...}`

# Hard Rules

- Never bypass validator checks.
- Never insert custom control flow outside mapped Marlowe constructors.
- Fail closed on unsupported constructs.
- Keep output deterministic for same input.

# Resources

- Lowering rules: `references/lowering-rules.md`
- Script: `scripts/lower_to_sui_move.py`
- Output template: `templates/lowering-report.template.json`

Return JSON only.
