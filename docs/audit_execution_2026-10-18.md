# Audit execution — October 18, 2026

## Status

Implemented on `audit-execution`, starting from merged PR #86 (`98faf56`). No paid AI calls. No push, merge or deployment is claimed. The cloud browser could not reach the workspace Streamlit server (`ERR_CONNECTION_REFUSED`); physical desktop/390px interaction and deployed download verification remain unverified.

## Completed stages

1. Scenario validation, explicit-submit form, retained completed runs/exports, evidence-version reset, per-request concurrency coordination and bounded response cache. 539 tests passed. `budget.py` is unchanged.
2. Checked current-funding detail and total-liability extraction, stable source registry, cell aliases/migration maps, and a single workbook build. 544 tests passed.
3. Separate liability stacks; annual Oracle maturity wall; optional maturity heatmap, fixed-coupon distribution and instrument composition; annual OCF/year-end borrowing panels. 550 tests passed.
4. Authored-template programmatic export, shared OpenXML utilities and manifest gates, retired legacy style/annual patch paths, palette consolidation and documentation corrections. **554 tests passed** in the final full suite. The original 532 cases remain; assertions for intentional forms, chart counts, sheet organization and explicit Unavailable cells were migrated without dropping their financial checks.

## Financial reconciliation

- LLY: 5,284M carrying-value CP in c-295 plus derived 1,766M current long-term borrowing reconciles to the existing 7,050M current line. Fair-value c-296 at 5,280M is refused. June liabilities: 47,741M current / 60,663M noncurrent.
- ORCL: 7,625M current carrying borrowing remains combined. August CP and drawable revolver remain Unavailable; May CP, May revolver and September–August principal are separately dated. Current/noncurrent liabilities: 47,514M / 188,549M. Known principal: 125,567M; term-loan payment events sum to 5,067M once. The 53 fixed coupons were checked against the full saved annual filing and retain exact contexts in Data.
- VST: 1,876M current LTD + reported 0 short-term borrowing + 300M receivables financing = 2,176M current baseline borrowing. Noncurrent liabilities = 37,109M total less 10,557M current = 26,552M, explicitly derived. Reported availability already deducts letters of credit.

Baseline borrowing, cash, historical ratios, catalysts and funding conclusions are preserved. Missing latest lease figures never become zero. Unknown funding coverage remains Unavailable. Cash bridges are not debt roll-forwards. Debt-movement and principal/interest trajectories remain deferred.

## Verification

- Final full suite: 554 passing tests using the repository's unittest runner. `pytest` is not installed in the available runtimes; no pytest pass is claimed.
- Offline app check passed with all network calls disabled. Saved-source audit reread available full annual filings and cash-flow sources.
- Company workbook sheets and new chart areas were rendered and inspected. Formula previews use reconciled caches in memory where the rendering importer cannot evaluate SUMIFS; published workbook formulas remain intact.
- LibreOffice recalculated disposable copies of the three company workbooks plus programmatic, research and full scenario examples: **53 sheets, 1378 matching formula caches, zero formula errors**. The shipped files were not overwritten by LibreOffice.
- Native chart ranges/caches, hyperlinks and interpretation/source gates pass the tests. Dynamic export examples live under `verification/examples` in the package.
- `git diff --check` passes. `budget.py`, checked pilot snapshots and original archived sample data are preserved.

## Reproduce

From the repository root, with pinned Python dependencies:

```bash
python -m unittest discover -s tests -p 'test_*.py'
python tests/offline/audit_release1.py
python tests/offline/check_liquidity_app.py
```

The source-based build requires the Codex Artifact Tool runtime environment variables:

```bash
python tests/offline/build_workbooks.py
```

It builds the three company workbooks and programmatic template, annual tables, principal block and charts, applies links and chart caches, validates gates, and restores prior outputs on failure. It makes no network or AI request. Full raw-source tests require the separately saved public filings; committed checkpoints/fixtures support offline tests. Do not replay retired hash-specific patch scripts.

## Next step

Review this branch, then use a browser-capable local environment to check desktop/390px interactions and each actual download before publishing. The cloud browser access failure is the remaining acceptance boundary, not a claim that the app failed.
