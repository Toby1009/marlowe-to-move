---
name: marlowe-json-author
description: Convert natural-language contract requirements into constrained Marlowe Core JSON drafts for a Marlowe-to-Sui workflow. Use when users describe contract intent in prose (Chinese or English) and need structured Marlowe JSON, ambiguity reporting, unsupported-requirement detection, and draft output for downstream validation.
---

# Purpose

Convert user requirements into Marlowe Core JSON drafts that are suitable for downstream validation and safe lowering to Sui Move.

Do not output Sui Move.
Do not claim semantic safety.

# Workflow

1. Normalize user text with `scripts/normalize_input.py`.
2. If required fields are missing or ambiguous, ask clarification questions first (do not guess).
3. Map clarified fields into Marlowe constructors supported by this skill.
4. Validate JSON shape with `scripts/validate_json.py` and `schema/marlowe-core-contract.schema.json`.
5. Return exactly one JSON object:
- success: `{"status":"ok","contract":{...},"notes":[...],"assumptions":[...]}`
- missing info: `{"status":"missing_information","missing":[...],"questions":[...],"partial_contract":{...}}`
- unsupported: `{"status":"unsupported_requirement",...}`
- invalid request: `{"status":"invalid_request",...}`

# Supported Subset

- Parties: role-based parties only (`{"role_token":"..."}`)
- Token: one or more tokens (including maker/taker swap token pairs)
- Actions: `Deposit`, `Choice`, `Notify`
- Contracts: `Close`, `Pay`, `If`, `When`
- Timeout: explicit absolute UNIX timestamp only

# Hard Rules

- Use integer minor units for all monetary amounts.
- Never emit relative time text such as "3 days later".
- Never invent fields outside schema.
- Never hide ambiguity; list it in `missing` and `questions`.
- Every timeout must be explicit and absolute.
- Every choice must include non-empty bounds.
- Every payment must include source account, payee, token, and value.
- If requirement exceeds subset, return `unsupported_requirement`.
- If any key field is missing or ambiguous, return `missing_information` first and ask up to 3 concise questions.

# Resources

- Schema: `schema/marlowe-core-contract.schema.json`
- Domain hints schema: `schema/domain-hints.schema.json`
- Extraction checklist: `prompts/extraction-checklist.md`
- Unsupported patterns: `prompts/unsupported-patterns.md`
- Few-shots: `prompts/few-shots.md`
- Templates: `templates/*.json`
- Summary helper: `scripts/summarize_contract.py`
- Answer merge helper: `scripts/answer_merge.py`

# Output Discipline

Return JSON only. Do not wrap with markdown or prose.

# File Output Rule

- Write generated JSON files under `specs/`.
- If `specs/` does not exist, create it.
- For `scripts/answer_merge.py`, when `--output` is omitted, auto-save to `specs/<input_stem>.<contract_type>.json`.
