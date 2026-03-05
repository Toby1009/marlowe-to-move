# Semantic Checks

- Timeout must be integer UNIX timestamp and treated as absolute time.
- `when` must have at least one case.
- `choose_between` must be non-empty and each bound must satisfy `from <= to`.
- Payment/deposit constants should be positive (warning if non-positive).
- Contracts should stay within configured subset (`close/pay/if/when` and `deposit/choice/notify`).
- Multi-token contracts are allowed; emit warnings only when token usage seems inconsistent.
- Duplicate `(choice_name, choice_owner)` pairs are warned.
- Unknown fields are rejected by schema and treated as invalid.
