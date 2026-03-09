---
name: marlowe-json-author
description: Convert natural-language contract requirements into constrained Marlowe Core JSON drafts for a Marlowe-to-Sui workflow. Use when users describe contract intent in prose (Chinese or English) and need structured Marlowe JSON, ambiguity reporting, unsupported-requirement detection, and draft output for downstream validation.
---

# Purpose

Convert user requirements into Marlowe Core JSON drafts that are suitable for downstream validation and safe lowering to Sui Move.
When users mention Oracle, zero-knowledge proof, external attestations, signed data, or off-chain verification, keep Marlowe Core JSON pure and express those requirements under a sibling `extensions` object.

Do not output Sui Move.
Do not claim semantic safety.

# Workflow

1. Normalize user text with `scripts/normalize_input.py`.
2. If required fields are missing or ambiguous, ask clarification questions first in plain text (do not guess) and wait for user answers.
3. Merge user answers with normalized hints (optionally with `scripts/answer_merge.py`).
4. Map clarified fields into Marlowe constructors supported by this skill.
5. If Oracle or ZKP requirements are present, write them under `extensions` using `schema/platform-extensions.schema.json` and `references/oracle-zkp-extensions.md`.
6. Validate JSON shape with `scripts/validate_json.py`, `schema/marlowe-core-contract.schema.json`, and `schema/platform-extensions.schema.json` when `extensions` are present.
7. Return exactly one JSON object after required information is complete:
- success: `{"status":"ok","contract":{...},"extensions":{...},"notes":[...],"assumptions":[...]}`
- missing info: `{"status":"missing_information","missing":[...],"questions":[...],"partial_contract":{...}}`
- unsupported: `{"status":"unsupported_requirement",...}`
- invalid request: `{"status":"invalid_request",...}`

# Supported Subset

- Parties: role-based parties only (`{"role_token":"..."}`)
- Token: one or more tokens (including maker/taker swap token pairs)
- Actions: `Deposit`, `Choice`, `Notify`
- Contracts: `Close`, `Pay`, `If`, `When`
- Timeout: explicit absolute UNIX timestamp only
- External dependency declarations: sibling `extensions.oracles[]` and `extensions.zkp[]`

# Hard Rules

- Use integer minor units for all monetary amounts.
- Never emit relative time text such as "3 days later".
- Never invent fields outside schema.
- Never hide ambiguity; list it in `missing` and `questions`.
- Every timeout must be explicit and absolute.
- Every choice must include non-empty bounds.
- Every payment must include source account, payee, token, and value.
- If requirement exceeds subset, return `unsupported_requirement`.
- If any key field is missing or ambiguous, ask up to 3 concise clarification questions first and wait for answers.
- Do not end the turn with `missing_information` JSON unless the user explicitly asks for machine-readable interim output.
- Keep `contract` pure Marlowe Core JSON; never inject Oracle/ZKP pseudo-syntax into Marlowe expressions.
- Put platform-specific Oracle/ZKP requirements only under `extensions`.
- Every Oracle or ZKP requirement must include an explicit `bind_to` target that names the contract-facing hook.

# Resources

- Schema: `schema/marlowe-core-contract.schema.json`
- Platform extensions schema: `schema/platform-extensions.schema.json`
- Domain hints schema: `schema/domain-hints.schema.json`
- Extraction checklist: `prompts/extraction-checklist.md`
- Unsupported patterns: `prompts/unsupported-patterns.md`
- Oracle/ZKP extension rules: `references/oracle-zkp-extensions.md`
- Few-shots: `prompts/few-shots.md`
- Templates: `templates/*.json`
- Summary helper: `scripts/summarize_contract.py`
- Answer merge helper: `scripts/answer_merge.py`

# Output Discipline

- Clarification stage: ask concise plain-text questions (no JSON wrapper).
- Final stage (after clarification): return JSON only. Do not wrap with markdown or prose.

# File Output Rule

- Write generated JSON files under `specs/`.
- If `specs/` does not exist, create it.
- For `scripts/answer_merge.py`, when `--output` is omitted, auto-save to `specs/<input_stem>.<contract_type>.json`.
