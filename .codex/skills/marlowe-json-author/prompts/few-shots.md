# Few-Shot Set

## 1) Single Disbursement
Input summary:
- Agency pays Applicant 5000000 USDC before `2026-06-30 23:59:59 UTC` if applicant deposited 1000000 USDC before `2026-05-31 23:59:59 UTC`.

Expected pattern:
- `When(Deposit)` -> `Pay` subsidy -> `Pay` refund -> `Close`

## 2) Two-Party Escrow
Input summary:
- Buyer deposits 1000000 USDC by date, Seller delivers by date, Buyer chooses release or refund.

Expected pattern:
- `When(Deposit)` -> `When(Choice)` -> `If` choice -> pay seller or refund buyer

## 3) Installment Payment
Input summary:
- Borrower deposits installment monthly; lender can confirm each installment.

Expected pattern:
- chained `When(Deposit/Choice)` blocks with explicit absolute timeouts

## 4) Overdue Refund / Timeout Close
Input summary:
- If deadline passes without deposit, contract closes; if rejected, deposit refunded.

Expected pattern:
- timeout branch to `Close`, rejection branch to refund `Pay`

## 5) Two-Token DEX Swap
Input summary:
- Maker deposits `maker_amount` of `maker_token`.
- Taker deposits `taker_amount` of `taker_token`.
- After both deposits, exchange both assets atomically.

Expected pattern:
- `When(maker deposit)` and `When(taker deposit)` symmetric branches
- both branches converge to `Pay(maker -> taker)` then `Pay(taker -> maker)` then `Close`
