# Five-year history: source and implementation plan

Roadmap items 12–13. Source reconciliation completed October 17, 2026. Existing app/workbook
values and review dates are unchanged; annual history is not displayed yet.

## Periods and definitions

| Company | Five completed fiscal years | Year end |
|---|---|---|
| Lilly | 2021–2025 | December 31 |
| Oracle | 2022–2026 | May 31 |
| Vistra | 2021–2025 | December 31 |

Keep this annual history separate from the latest TTM window. Do not splice overlapping
TTM observations into an annual trend. Use cash excluding restricted cash, borrowing
excluding leases, reported annual operating cash flow and company-specific reported
capital spending. Free cash flow equals that year's OCF less that year's capital spending.
It is not cash available to repay debt. No independent-period growth rate across FY/TTM.

## Available evidence and gates

All 15 original annual filings and captured companyfacts are now acquired and checked.
The source checkpoint contains 75 selected measures and retains original observations.
See [annual_history_reconciliation.md](annual_history_reconciliation.md) for values,
printed locations, source choices, tests and remaining limits.

Cash must reconcile to the exact annual date, USD unit and accession used. OCF and capex
must span the exact fiscal year, with reported scale and sign checked against the filing.
Each borrowing mapping must be checked for that year; today's tags are not automatically
valid historically. Vistra's financing line is counted once; its facility split remains unresolved. Never
replace a missing extension component with zero. A comparative may differ from an original
filing; retain both and disclose which version is used rather than silently mixing versions.

Before displaying each observation, retain form, filing date, accession, period, source URL,
tag, unit, context/dimensions, raw-file hash, printed location and independent expected value.
Keep missing or non-reconciling cells Unavailable with a specific reason. Do not interpolate
or chart them as zero. Validate fiscal-year changes and presentation changes explicitly.

## Build order

1. Inventory and retrieve missing annual sources and original tagged data. Build an explicit
   checklist of 15 company-years and five requested measures per year. A source gap is a
   missing review task, not evidence that a company did not report a figure.
2. Reconcile source observations and borrowing scope, preserving the existing checked
   latest/FY values as regression cases. Store only independently checked history records.
3. Add the annual table to each company review and individual workbook from one shared
   dataset. Derived FCF must be an Excel formula linked to that year's inputs.
4. Add trend charts only after the table reconciles. Display dates, definitions and visible
   gaps; avoid ranking companies with different fiscal calendars and capex definitions.
5. Test source refusal, conflicting filings, missing components and formula parity. Inspect
   desktop/narrow layouts and changed workbook sheets, then verify deployed downloads.

Build steps 1–2 are complete. Lilly 2021/2022 flows use its disclosed FY2023
reclassification, while the balance sheets remain original. Vistra 2021/2024 use complete
comparative snapshots to establish reported zero short-term borrowing. Each calculation
retains one filing version, and original gaps remain visible in the audit.

Roadmap item 12 still needs the app/workbook annual table (step 3); item 13 charts
remain not started. Correct the legacy Lilly FY2025 printed-page references during
integration. No unsupported history should be published merely to fill five columns.
