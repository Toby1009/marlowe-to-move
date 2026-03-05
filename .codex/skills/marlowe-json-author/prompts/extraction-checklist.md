# Extraction Checklist

- Identify role parties and normalize names (`Applicant`, `Agency`, `Seller`, `Buyer`).
- Identify one or more tokens. If multiple tokens exist, ask for explicit role/token mapping.
- Identify all deadlines and convert to absolute UNIX timestamps.
- Identify user choices and bounds (`approve/reject` -> `[0,0]` and `[1,1]`).
- Identify deposits and payment flows:
  - `from_account`
  - `to` (party/account)
  - `token`
  - `pay` value (integer minor units)
- Map branches into `When` + continuation contracts.
- If any required field is missing or ambiguous, output `missing_information` with:
  - `missing`
  - `questions` (max 3 concise user-facing questions)
  - `partial_contract` (if possible)
- Do not silently guess token/deadline/party mappings.
