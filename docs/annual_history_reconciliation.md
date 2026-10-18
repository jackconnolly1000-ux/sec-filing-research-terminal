# Annual history: source reconciliation checkpoint

Checked through October 17, 2026. This checkpoint acquires and reconciles the sources before five-year tables or charts are added. The original source checkpoint precedes the app/workbook integration recorded below. Checked latest-date conclusions are unchanged.

## Coverage and selection

All 15 original annual filings are saved outside git with SHA-256 hashes, along with three captured SEC companyfacts datasets, submissions metadata, and five Vistra extension schemas and label files. The saved submissions screen found no 10-K/A for the selected periods. Fifteen selected company-years contain 75 reconciled measures. Original observations remain alongside selected observations, including two original Vistra borrowing gaps.

The grain is company, fiscal year, measure, and filing version. Facts must have the exact entity, USD unit, period, accession and undimensioned context. Full-year flows are separate from balance-sheet instants and from the app’s latest TTM window. Borrowing components and FCF inputs each use one filing version; independent stock and flow measures need not share a filing. Companyfacts is an independent cross-check, not an automatic latest-filed override. Later differing values are retained for review.

## Selected values

USD millions; negative amounts remain negative. Cash means cash and equivalents excluding restricted cash, not necessarily cash freely transferable to every obligation. Debt means baseline borrowing at carrying value, excluding lease liabilities. FCF = annual operating cash flow (OCF) less reported capital spending; it is not future funding coverage.

| Company | Fiscal year | Cash | Borrowing | OCF | Capital spending | FCF |
|---|---:|---:|---:|---:|---:|---:|
| LLY | 2021 | 3,818.5 | 16,884.7 | 7,365.9 | 1,309.8 | 6,056.1 |
| LLY | 2022 | 2,067 | 16,238.6 | 7,585.7 | 1,854.3 | 5,731.4 |
| LLY | 2023 | 2,818.6 | 25,225.3 | 4,240.1 | 3,447.6 | 792.5 |
| LLY | 2024 | 3,268.4 | 33,644.2 | 8,817.9 | 5,057.8 | 3,760.1 |
| LLY | 2025 | 7,268 | 42,503 | 16,813 | 7,841 | 8,972 |
| ORCL | 2022 | 21,383 | 75,859 | 9,539 | 4,511 | 5,028 |
| ORCL | 2023 | 9,765 | 90,481 | 17,165 | 8,695 | 8,470 |
| ORCL | 2024 | 10,454 | 86,869 | 18,673 | 6,866 | 11,807 |
| ORCL | 2025 | 10,786 | 92,568 | 20,821 | 21,215 | -394 |
| ORCL | 2026 | 31,289 | 129,541 | 31,977 | 55,663 | -23,686 |
| VST | 2021 | 1,325 | 10,731 | -206 | 1,033 | -1,239 |
| VST | 2022 | 455 | 13,046 | 485 | 1,301 | -816 |
| VST | 2023 | 3,485 | 14,402 | 5,453 | 1,676 | 3,777 |
| VST | 2024 | 1,188 | 17,048 | 4,563 | 2,078 | 2,485 |
| VST | 2025 | 785 | 20,068 | 4,070 | 2,752 | 1,318 |

Lilly and Vistra end December 31; Oracle ends May 31. Different fiscal calendars, business acquisitions and disposals, working capital and spending definitions limit comparability. No cross-company ranking or normalized growth claim is made.

## Presentation changes that matter

- **Lilly 2021–2022:** FY2023 Note 1, printed page 63, reclassifies development-milestone payments for externally developed IPR&D acquired outside business combinations from operating to investing activities. OCF rises by 105.2M in 2021 and 501.3M in 2022. Selected OCF/capex pairs both come from that FY2023 comparative presentation; cash and borrowing remain the original balance sheets. Original cash-flow values are retained. This is a classification change, not new cash generation. FCF here excludes purchases of IPR&D and acquisitions. Later small rounded differences are recorded rather than silently substituted.
- **Vistra 2021 and 2024:** the originals lack the exact consolidated short-term-borrowing fact. Their borrowing totals remain Unavailable in the original series. The selected series uses complete comparative snapshots from the following annual filing, including an explicitly reported zero short-term balance. It does not treat absence as zero or mix inputs across filings.
- **Vistra 2025:** 1,201M current long-term debt + 15,842M noncurrent long-term debt + 1,800M short-term borrowings + 1,225M accounts receivable financing = 20,068M. Count the face financing line once. Its assignment between the receivables and repurchase facilities is not explicit; do not add the separately disclosed 1,100M and 125M again. The separate Nuveen obligation is excluded from baseline borrowing, and project debt already within long-term debt is not added twice.
- **Vistra lease and capex scope:** annual lease policies place finance leases in other current/noncurrent liabilities; debt-note totals reconcile the two long-term borrowing lines despite their legacy tag names. The selected standard capex tag includes nuclear fuel and LTSA prepayments. A narrower custom nuclear-fuel/PP&E tag is not substituted.

## Original sources

Printed pages below are the consolidated balance sheet / cash-flow statement. Every checkpoint input also records its tag, context, unit, scale, decimals, accession and row text. FY2023 Lilly reclassification is separately located at page 63.

| Company | Fiscal year | Filed | Accession and original 10-K | Printed pages BS / CF |
|---|---:|---|---|---|
| LLY | 2021 | 2022-02-23 | [0000059478-22-000068](https://www.sec.gov/Archives/edgar/data/59478/000005947822000068/lly-20211231.htm) | 57 / 59 |
| LLY | 2022 | 2023-02-22 | [0000059478-23-000082](https://www.sec.gov/Archives/edgar/data/59478/000005947823000082/lly-20221231.htm) | 58 / 60 |
| LLY | 2023 | 2024-02-21 | [0000059478-24-000065](https://www.sec.gov/Archives/edgar/data/59478/000005947824000065/lly-20231231.htm) | 59 / 61 |
| LLY | 2024 | 2025-02-19 | [0000059478-25-000067](https://www.sec.gov/Archives/edgar/data/59478/000005947825000067/lly-20241231.htm) | 60 / 62 |
| LLY | 2025 | 2026-02-12 | [0000059478-26-000013](https://www.sec.gov/Archives/edgar/data/59478/000005947826000013/lly-20251231.htm) | 59 / 61 |
| ORCL | 2022 | 2022-06-21 | [0001564590-22-023675](https://www.sec.gov/Archives/edgar/data/1341439/000156459022023675/orcl-10k_20220531.htm) | 66 / 70 |
| ORCL | 2023 | 2023-06-20 | [0000950170-23-028914](https://www.sec.gov/Archives/edgar/data/1341439/000095017023028914/orcl-20230531.htm) | 64 / 68 |
| ORCL | 2024 | 2024-06-20 | [0000950170-24-075605](https://www.sec.gov/Archives/edgar/data/1341439/000095017024075605/orcl-20240531.htm) | 65 / 69 |
| ORCL | 2025 | 2025-06-18 | [0000950170-25-087926](https://www.sec.gov/Archives/edgar/data/1341439/000095017025087926/orcl-20250531.htm) | 64 / 68 |
| ORCL | 2026 | 2026-06-22 | [0001193125-26-277521](https://www.sec.gov/Archives/edgar/data/1341439/000119312526277521/orcl-20260531.htm) | 64 / 68 |
| VST | 2021 | 2022-02-25 | [0001692819-22-000005](https://www.sec.gov/Archives/edgar/data/1692819/000169281922000005/vistra-20211231.htm) | 92 / 90 |
| VST | 2022 | 2023-03-01 | [0001692819-23-000005](https://www.sec.gov/Archives/edgar/data/1692819/000169281923000005/vistra-20221231.htm) | 96 / 94 |
| VST | 2023 | 2024-02-29 | [0001692819-24-000012](https://www.sec.gov/Archives/edgar/data/1692819/000169281924000012/vistra-20231231.htm) | 82 / 80 |
| VST | 2024 | 2025-02-28 | [0001692819-25-000013](https://www.sec.gov/Archives/edgar/data/1692819/000169281925000013/vistra-20241231.htm) | 79 / 81 |
| VST | 2025 | 2026-02-27 | [0001692819-26-000006](https://www.sec.gov/Archives/edgar/data/1692819/000169281926000006/vistra-20251231.htm) | 80 / 82 |

## Reproduction and limits

- `samples/annual_source_inventory.json`: original URLs, hashes, capture metadata and extension definitions. `samples/annual_history_reconciliation.json`: original and selected observations with full source provenance and explicit selection rules.
- `annual_history.py`: source-specific controls, strict selection and refusal rules. `tests/fixtures/annual_history/`: unchanged tagged fact/context subsets and captured companyfacts rows for offline replay; these are not substitutes for reviewing the complete notes.
- `python tests/offline/acquire_annual_history.py --raw <raw-directory>` acquires missing reviewed sources with `SEC_CONTACT_EMAIL` or an identifying `--user-agent`. It refuses changed hashes and never overwrites a reviewed capture. Live companyfacts/submissions endpoints change, so an older snapshot may no longer be downloadable; committed subsets preserve offline replay.
- `python tests/offline/build_annual_history.py --raw <raw-directory> --check` reproduces the checkpoint against full saved documents and captured companyfacts. `build_annual_history_fixtures.py` rebuilds the fact subsets. `python -m unittest discover -s tests` includes regression and refusal tests; the full-document replay skips if the raw sources are absent.
- The source checkpoint itself changed no app/workbook figures. The integration below adds the sourced annual tables; five-year charts follow only after table parity passes.
- Lilly FY2025 uses printed balance-sheet/cash-flow pages 59/61. The legacy history references that used 56/58 are corrected during integration.
- No usable credit capacity, repayment forecast, quarterly seasonality, restricted-cash availability or new funding conclusion is inferred from these annual totals.

## App and individual workbook integration

The annual table is now served by `annual_history_view.py` in each checked review and
in each individual workbook's **Annual history** tab. Its 75 values come from the
checkpoint above. The app retains the exact fiscal year-end dates and presentation notes;
Excel retains full-dollar inputs on Data, native source hyperlinks, filing metadata and
formula-linked totals. FCF is a same-year OCF-minus-capex formula. Annual data is separate
from the latest TTM and the existing annual-versus-latest comparison.

The FY2025 Vistra audit also resolves its earlier two-date borrowing gap: 20,068M of
borrowing, 19,283M of net debt, 20.3% annual OCF/debt and 6.6% annual FCF/debt. The
financing balance-sheet line is counted once; its facility split remains unresolved.
Latest-quarter figures, funding conclusions, catalysts and scenario assumptions do not change.
Lilly's legacy balance-sheet/cash-flow references are corrected to printed pages 59/61 in
the saved history sources, their builder and workbook source cells.

Rebuild in an OS temporary directory with the Codex primary runtime:

1. Copy `tests/offline/integrate_annual_history.mjs` and `workbook_style.mjs` there and link
   the runtime's `node_modules` into that temporary directory.
2. Run the script with repository root and output-directory arguments. It authors the
   annual tab and explicit changes, tests FCF recalculation, and renders affected views.
3. Run `python tests/offline/apply_annual_history.py <output-directory>` from the repo.
   This installs authored cells, styles, source links and affected native chart parts,
   checks unrelated ZIP parts remain byte-identical, and rebinds manifests.
4. Run unit tests, the release saved-source audit and the offline app check.

The disposable authoring import uses cached original cells to avoid the spreadsheet
runtime's mis-typing of unrelated Oracle formulas containing dates. Original formulas,
chart parts and caches are retained in the final workbook unless explicitly changed.
Desktop Excel recalculation itself is not available in this environment; new formulas
are recalculated and mutation-tested in Artifact Tool and independently checked in the
saved files. The optional combined summary and separate scenario workbook stay unchanged.

## Five-year charts (October 17, 2026)

Each review and individual workbook adds two charts under the five-year table, from the same checked rows
(`annual_history_view.build`). In the app both are Plotly grouped-column charts with fiscal years left to right
(`annual_history_view.figures`, rebuilt Oct 17 after the first stacked-row version read poorly); a caption under each
names any Unavailable year:

1. **Fiscal-year-end cash and baseline borrowing**: balances at each fiscal year end, one scale for both.
2. **Annual OCF, capital spending and FCF**: capital spending is drawn below zero as a use of cash, as in the
   latest-TTM chart; FCF is the result, not another flow.

Annual periods stay separate from the TTM: the charts show completed fiscal years only, with their own dates. The
Lilly reclassification and Vistra comparative-source notes still follow the table and charts. Negative values keep
their sign (Vistra FY2021 OCF −$206M; FCF negative in FY2021–22). A missing value draws no bar and reads
Unavailable; in Excel the series cells return `NA()`, which plots as a gap, never zero.

Excel: `tests/offline/add_annual_history_charts.py` adds native clustered-column charts to the Annual history sheet
(rows 24–40 and 42–58), bound to the table rows and to one helper row (61: `=IF(ISNUMBER(B9),-B9,NA())`, capital
spending as a use). Chart caches are seeded from the table's cached values. Only that sheet, its new relationships,
one drawing, two charts and `[Content_Types].xml` change; every other part is byte-identical. Manifests rebind the
workbook SHA-256 and the annual-history, history and core-chart fingerprints (`--rebind` after a later code edit).
The `--charts` branch in `integrate_annual_history.mjs` was not used: it needs Node and the Artifact Tool runtime,
and its plain `=B7` chart links would plot a missing value as zero.

Checked in desktop Excel (PowerShell COM): full recalculation with 0 error cells; every formula's cached value
equals Excel's recalculation (LLY 200, Oracle 309, Vistra 242); all pre-existing formulas and native charts unchanged;
both charts exported and inspected.
