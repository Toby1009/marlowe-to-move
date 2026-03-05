# Unsupported Patterns (MVP)

- Dynamic participant creation after deployment.
- Relative timeout output without concrete timestamp.
- Decimal money values in final JSON.
- Loops, recursion, or arbitrary external callbacks.
- Unbounded or missing choice bounds.
- Oracle-dependent logic not represented as explicit `Choice`/`Notify` input.
- Deep arithmetic expressions beyond practical review depth.
