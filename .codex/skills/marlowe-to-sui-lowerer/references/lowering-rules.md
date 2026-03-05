# Lowering Rules (Constrained)

- Input must pass `marlowe-json-validator` first.
- Lowering is deterministic for identical JSON input.
- Constructor mapping:
  - `close` -> terminal stage
  - `when` -> staged user entry functions
  - `deposit` -> `deposit_stage_*` Move entry
  - `choice` -> `choice_stage_*` Move entry
  - `notify` -> `notify_stage_*` Move entry
  - `pay/if` -> internal auto-transition logic
- Unsupported/invalid input returns `lowering_error` or `invalid_input`; never auto-repair.
