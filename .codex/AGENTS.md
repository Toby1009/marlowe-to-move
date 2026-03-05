# AGENTS.md instructions for ./.codex

## Skills
A skill is a reusable folder bundle with `SKILL.md` as the entry point.

### Available skills
- marlowe-json-author: Convert natural-language contract requirements into constrained Marlowe Core JSON drafts, with ambiguity/missing-info reporting for downstream validation. (file: /Users/yangjunan/Documents/blockchain/專題/.codex/skills/marlowe-json-author/SKILL.md)
- marlowe-json-validator: Validate Marlowe Core JSON drafts for schema correctness, semantic consistency, and supported-subset compliance before lowering. (file: /Users/yangjunan/Documents/blockchain/專題/.codex/skills/marlowe-json-validator/SKILL.md)
- marlowe-to-sui-lowerer: Deterministically lower validator-approved Marlowe JSON into Sui Move artifacts using the local generator pipeline. (file: /Users/yangjunan/Documents/blockchain/專題/.codex/skills/marlowe-to-sui-lowerer/SKILL.md)

### How to use skills
- Discovery: Skills listed above are available in this repo context.
- Trigger rules:
  - If the user explicitly names a skill (for example `marlowe-json-author`), use it.
  - If the request clearly matches a skill description, use it even if the skill name is not mentioned.
- Multiple skills:
  - Prefer this order for generation pipeline:
    1. `marlowe-json-author`
    2. `marlowe-json-validator`
    3. `marlowe-to-sui-lowerer`
- Context hygiene:
  - Read `SKILL.md` first.
  - Load only necessary referenced files.
  - Prefer bundled `scripts/` over rewriting logic.
- Safety:
  - `marlowe-to-sui-lowerer` must only process validator-approved JSON.
  - If request exceeds supported subset, return structured unsupported/missing responses.

### Trigger examples
- "幫我把需求生出 Marlowe JSON" -> `marlowe-json-author`
- "幫我檢查這份 Marlowe JSON" -> `marlowe-json-validator`
- "把這份已驗證 JSON 轉成 Sui Move" -> `marlowe-to-sui-lowerer`
