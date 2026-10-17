# Roadmap

**As of October 17, 2026.** What comes after Release 1 (the three checked company reviews) and Release 2 (Oracle's illustrative stress scenario). Each numbered item is one pull request on its own branch, merged once CI passes and followed by a check of the live site. The status column is updated as items merge.

Rules for every item: no invented metrics. Anything a filing does not establish stays Unavailable; it is never estimated and never plotted as zero. Shares of simulated trials are not probabilities. Checked figures, funding conclusions and source gates change only when an item says so. A saved workbook changes only through a byte-preserving patch script in `tests/offline` that rebinds its manifest fingerprints.

## A. Safety net and housekeeping

| # | Item | Status |
|---|---|---|
| 1 | GitHub Actions CI: pinned requirements on Python 3.12; unit tests, release audit and offline app check on every pull request. Tests that need saved filings skip. | Merged, PR #69 |
| 2 | Single-process `unittest discover` run. It wasn't hanging: it took about 2 minutes, mostly repeated filing parses. Parsed filings are now cached and CI runs one process. | Merged, PR #70 |
| 3 | Remove local paths from `docs/debt_liquidity_plan.md`. | Merged, PR #71 |
| 4 | Update the stale status lines in `CLAUDE.md` (Release 1 step 8, test count, Release 2 and presentation pass). | Merged, PR #78 |
| 5 | This roadmap. | Merged, PR #72 |
| 6 | Install Node (LTS) so the `tests/offline/*.mjs` workbook builders can run, then run each once. | Node is available in the hosted execution environment. Lenovo installation and running every legacy builder remain unverified; do not rebuild checked exports just to test installation. |

## B. Remaining reader fixes

From the first-time-reader obstacles in [`presentation_acceptance.md`](presentation_acceptance.md).

| # | Item | Status |
|---|---|---|
| 7 | Plain answer first: "Future funding coverage: Unavailable" with a one-line reason near the top of each review, plus short definitions of TTM, OCF, FCF, H1, PP&E and IPR&D. Rebinds all three company manifests and keeps the shared interpretation fingerprint consistent. | Merged, PR #73 |
| 8 | Scenario workbook: the Results sheet says at the top that it is an illustrative scenario from stated assumptions, not a forecast, and points to About. | Merged, PR #74 |
| 9 | Monthly scenario chart: month labels read "Sep 2026", not "Oct 26". | Merged, PR #75 |
| 10 | Move each company's primary download, with its caption, below the review header and conclusion. | Merged, PR #76 |
| 11 | Oracle's long-dated principal by decade (FY2032–36, FY2037–46, FY2047–56, FY2057–66) from `samples/oracle_principal.json`, under the ladder in the app and on the workbook's Payment dates sheet as formulas over the existing instrument rows. | Merged, PR #77 |

## C. More checked data and charts

| # | Item | Status |
|---|---|---|
| 12 | Five fiscal years of annual cash, gross debt, OCF, capex and FCF per company from SEC companyfacts (fixtures in `tests/fixtures`), each reconciled to the filing figures. A year that doesn't reconcile is Unavailable with its reason. Planned and agreed before it's built. | Source preflight complete; see five_year_history_plan.md. Full five-year source set missing. |
| 13 | Trend charts from item 12 in the app and the workbooks, with gaps for Unavailable years. | Depends on item 12; not started |
| 14 | Oracle sources-and-uses chart from checked figures only (starting cash, OCF, capex, dividends, dated principal), labelled historical, not a forecast. | Existing quarterly bridge covers the checked quarter. Inspect before adding a distinct view; not started. |

## D. Stress scenario additions

| # | Item | Status |
|---|---|---|
| 15 | Sensitivity (tornado) chart: for each input (OCF low and high, capex, dividends, correlation, each outside-use sensitivity amount), the change in the share of trials below zero, with the same seed. In the scenario view and workbook, with tests. | Not started; define perturbations explicitly before implementation |
| 16 | On the live site, run the scenario with changed inputs and confirm the charts, tables and downloaded workbook follow. | Live changed-capex/seed run and actual download verified October 17; see presentation_acceptance.md |

## E. General research page (experimental)

Offline tests only; any paid Claude run needs the owner's OK first.

| # | Item | Status |
|---|---|---|
| 17 | Label every AI-written figure with its period and source, and stop unlabeled SEC versus Yahoo margin conflicts on the page and in Excel. | Not started |
| 18 | Make the general research Excel a research record: cover sheet, units in headers, wrapped text, set widths. | Next implementation: general-research export layout |
| 19 | Read risk factors incorporated by reference from an annual-report exhibit; JPM is the test case. | Not started; required JPM exhibit not saved here |
| 20 | Profile the 108-second first run, report where the time goes and fix the biggest piece. | Not started; no paid calls authorized |

## Gated items (not before their date or condition)

| Item | Gate | Why |
|---|---|---|
| Compare the stress scenario with the course's simulation method | After the simulation classes on October 19 and 21, 2026 | The scenario applies the simulation material covered so far. The remaining classes may change how inputs, distributions or results should be presented. |
| Refresh the reviews with newer 10-Qs | When each company files its next 10-Q | The reviews are frozen at June 30 (LLY, VST) and August 31 (ORCL). A newer filing isn't read until the review is rebuilt and checked by hand. Oracle's next 10-Q (quarter ending November 30) is likely mid-December. |
| CAPM regression (beta and alpha against SPY) | After the regression classes on November 11 and 13, 2026 | Not yet covered in the course. |
| LP allocation | When the course notes show LP covered, and after the simulation work | The course notes mark linear programming covered (checked October 9). It still needs a framing that can't be read as allocation advice: a max-return portfolio would be illustrative only. |

## Not planned

- Grades, default probabilities, ratings or recommendations, at any point.
- Estimated funding capacity, drawable credit or covenant headroom where the filings don't establish them.
- Deferred from the debt and liquidity plan until their evidence exists: full financing terms and covenants, recalculating debt and cash from later financing events, a complete obligations analysis, industry peers and category assessments.
