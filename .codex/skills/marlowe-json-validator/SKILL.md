---
name: marlowe-json-validator
description: Validate Marlowe Core JSON drafts for schema correctness, semantic consistency, and supported-subset compliance before lowering to Sui Move. Use when JSON is authored by humans or agents and must be checked for explicit timeouts, party/token references, bounded choices, completeness, and unsupported constructs.
---

# Purpose

Validate Marlowe JSON before lowering.
When a payload includes a sibling `extensions` object for Oracle or ZKP requirements, validate Marlowe Core JSON separately from those platform extensions.

Accept JSON input and return one JSON object:
- `{"status":"valid",...}`
- `{"status":"invalid","errors":[...],"warnings":[...]}`

# Validation Pipeline

1. Run schema validation against `schema/marlowe-supported-subset.schema.json` for the `contract` portion.
2. If `extensions` are present, validate them against `../marlowe-json-author/schema/platform-extensions.schema.json`.
3. Run semantic checks with `scripts/validate_marlowe_json.py`.
4. Return structured errors and warnings with JSON paths.

# Mandatory Checks

- Contract uses supported constructors only.
- All timeouts are explicit absolute UNIX timestamps.
- Monetary values are integers.
- Party/Token/Payee/Choice references are structurally valid.
- Multi-token contracts are allowed; check consistency and emit warnings when risky.
- Choice bounds are non-empty and ordered.
- Continuations are complete and reachable.
- Obvious unsupported requirements are flagged.

# Warning Policy

Emit warnings for patterns that are legal JSON but high-risk design:
- timeout too near current time
- empty `when` cases
- zero or negative payment constants
- duplicated choice names by same role

# Resources

- Schema: `schema/marlowe-supported-subset.schema.json`
- Platform extensions schema: `../marlowe-json-author/schema/platform-extensions.schema.json`
- Semantic checks: `references/semantic-checks.md`
- Runner: `scripts/validate_marlowe_json.py`

Return JSON only.
