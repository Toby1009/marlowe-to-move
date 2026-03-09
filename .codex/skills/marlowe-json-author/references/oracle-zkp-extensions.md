# Oracle And ZKP Extensions

Use `extensions` as a sibling of `contract`, not as a modification of Marlowe
Core JSON.

## Output Shape

Successful payloads may include:

```json
{
  "status": "ok",
  "contract": { "...pure marlowe core json..." },
  "extensions": {
    "oracles": [],
    "zkp": []
  },
  "notes": [],
  "assumptions": []
}
```

## Binding Rules

- Keep `contract` pure Marlowe.
- Express Oracle and ZKP dependencies only under `extensions`.
- Use `bind_to` to point at the contract-facing hook name.
- Prefer `bind_to.kind = "choice"` when the dependency becomes a numeric or
  boolean-like input.
- Use `bind_to.kind = "observation"` only when the requirement is reported as a
  named condition and later lowering will translate it into contract wiring.
- Use `bind_to.kind = "choice_or_notify"` only when the requirement may lower
  into either a choice result or a notify gate.

## Authoring Rules

- Oracle requirements:
  - Include `id`, `type`, `description`, `inputs`, `integrity`, `bind_to`.
  - Include freshness constraints with `max_staleness_sec` when the user
    implies recency.
  - Include signer model with `signed_by`, `signature_scheme`,
    `required_quorum`.
- ZKP requirements:
  - Include `id`, `statement`, `public_inputs`, `proof_system`, `verifier`,
    `bind_to`, `privacy`.
  - Describe only public inputs; never invent private witness fields.
  - Keep privacy declarations explicit with `reveals` and `hides`.

## Do Not

- Do not inject `oracle(...)` or `zkp(...)` syntax into Marlowe expressions.
- Do not claim chain integration exists unless the user asked for a design-only
  draft and you mark assumptions.
- Do not move extension requirements into `contract`.
