# Debt & Liquidity Research Terminal

**What does a company owe, what can fund it, and what do the filings leave unresolved?**

Trace SEC filing facts through reconciled calculations to dated funding and repayment conclusions for **Eli Lilly (LLY), Oracle (ORCL) and Vistra (VST)**. The app combines checked company reviews, source-linked Excel records and a separate illustrative Oracle stress scenario. Research, not investment advice.

[Open Debt & Liquidity Research Terminal](https://sec-filing-research-terminal.streamlit.app/)

The app and browser title use the current name. The hosting address and GitHub repository still use the original `sec-filing-research-terminal` slug; the address requires a separate Streamlit hosting change.

## Start here

1. **Choose a company.** Read its dated funding conclusion, usable resources, competing uses and decisive unknowns.
2. **Trace the conclusion.** Inspect borrowing and leases, cash generation, repayment dates, historical ratios and five completed fiscal years of checked history. Source dates and definitions stay visible.
3. **Download that company’s workbook.** It contains the review, calculations, charts and evidence. The optional combined export is a compact summary, not a peer ranking.
4. **Explore Oracle’s stress scenario separately.** Change stated assumptions and inspect simulated cash paths and the scenario download. These results do not alter the checked funding conclusion.

## Scope and evidence

| Review | Latest checked balance sheet | Main funding questions |
|---|---|---|
| Eli Lilly | June 30, 2026 | Borrowing, acquisition and manufacturing payments, cash generation and credit availability |
| Oracle | August 31, 2026 | Dated principal, capital spending, prepayments, leases and conditional revolver capacity |
| Vistra | June 30, 2026 | Debt and project recourse, restricted resources, credit support, Nuveen and Helix obligations |

Reviews are saved snapshots. Opening them makes no live SEC, Yahoo or AI request and needs no secrets. A newer filing is not incorporated until its evidence is reviewed and the saved outputs are rebuilt. Later financing events retain their own dates and do not silently update a balance sheet.

- Borrowing, lease liabilities and commitments for leases not yet commenced are separate.
- Cash, historical operating cash flow, customer prepayments, equity proceeds and credit commitments are not interchangeable funding resources.
- Current ratio, net debt, OCF/debt, FCF/debt and historical interest coverage reconcile to their inputs. Interest definitions and fiscal periods differ by company.
- Five-year history separates fiscal-year-end balances from annual flows; later TTM flows may overlap the last fiscal year.
- Unsupported timing, drawable credit and funding coverage remain **Unavailable**, with a reason. Missing values are never treated as zero.
- Source and workbook fingerprints block stale downloads. Each company’s workbook is the primary export.

## Limits that matter

**Future funding coverage remains Unavailable for all three companies.** The reviews explain the decisive gaps rather than inventing forecasts. Examples include incomplete payment calendars, drawable credit and covenant headroom, overlapping commitments and Vistra’s Parent-accessible resources.

Oracle’s dated note and term-loan calendar does not establish its commercial-paper balance or payment dates. Lilly and Vistra’s June lease balances are not established by the checked quarterly evidence; older lease figures keep their December dates.

Oracle’s stress scenario is conditional on stated assumptions. Simulated trial shares are not default probabilities. Monthly cash allocation does not establish liquidity on individual payment dates. Some obligations are tested only as sensitivities because their amounts, timing or overlap are unresolved. See [scenario method and limits](docs/liquidity_simulation.md).

This is a three-company research project, not an automated credit rating, investment recommendation or complete obligations analysis. Desktop output has been reviewed; static chart renders at phone width do not substitute for actual phone interaction testing.

## Supporting tool: general filing research

**General filing research — experimental** remains a separate secondary page. It compares 10-K risk-factor text, reads selected 10-Q/8-K and MD&A sections, and displays cited AI summaries, catalysts and market data. Its open ticker search does **not** create a checked Debt & Liquidity review for another company.

The archived AAPL/STRL example is dated October 10, 2026 and opens without live calls. Live research needs credentials and can incur Anthropic charges. It has known limits: some exhibits are not read, text matching does not verify an interpretation, and SEC/Yahoo/AI figures can use different or unstated periods. These outputs are not held out as equivalent to the checked pilot reviews.

The public AI budget is $0.25 per day per server process; cache hits cost nothing. The in-memory ledger resets on restart, so the provider’s account limit is the hard stop. An optional owner passcode bypasses the app limit but still records spend. Never put credentials in the public repository.

## Code and evidence map

| Area | Entry points |
|---|---|
| App and presentation | `app.py`, `ui.py`, `company_review.py`, `theme.py` |
| Filing facts and reconciled metrics | `xbrl.py`, `filing_xbrl.py`, `ratio_review.py`, `borrowing_leases.py` |
| Funding conclusions | `funding_conclusions.py`; company-specific liquidity, interest and repayment modules |
| Oracle scenario | `liquidity_simulation.py`, `simulation_view.py`, `scenario_export.py` |
| Saved evidence and downloads | `samples/`, `workbook_manifest.py`, `tests/offline/build_workbooks.py` |
| Experimental research | `sec_data.py`, `compare.py`, `analysis.py`, `market_data.py`, `research_export.py` |

- [Build plan](docs/debt_liquidity_plan.md) and [roadmap](docs/roadmap.md)
- [Lilly evidence](docs/pilot_evidence_lly.md), [Oracle evidence](docs/pilot_evidence_oracle.md), [Vistra evidence](docs/pilot_evidence_vistra.md)
- [Funding conclusions](docs/funding_conclusions.md), [ratio reconciliation](docs/ratio_reconciliation.md), [annual history](docs/annual_history_reconciliation.md)
- [Oracle case study and walkthrough](docs/oracle_case_study.md)
- [Export organization](docs/export_organization.md), [Excel parity](docs/excel_parity.md), [general research export](docs/general_research_export.md)
- [Release 1 reconciliation](docs/release1_reconciliation.md), [presentation acceptance](docs/presentation_acceptance.md), [October 18 audit](docs/audit_execution_2026-10-18.md)

Release 1’s three-company workflow is complete. Oracle’s illustrative scenario and checked five-year history are also built. Current work is presentation and evidence maintenance; new companies, automatic refresh and unsupported financing conclusions are outside the completed scope. Historical acceptance records describe the checks performed at their own checkpoints.

## Running it

```
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

On Windows, use `py -3.12 -m venv .venv` and `.venv\Scripts\` in place of `.venv/bin/`.

The Debt & Liquidity page needs no secrets. Live general research needs `ANTHROPIC_API_KEY` and `SEC_CONTACT_EMAIL` in Streamlit Secrets (`.streamlit/secrets.toml`; SEC EDGAR asks every automated request to name a contact), and optionally `OWNER_PASSCODE`.

## Tests

```
.venv/bin/python -m unittest discover -s tests -p "test_*.py"      # Mac/Linux
.venv\Scripts\python -m unittest discover -s tests -p "test_*.py"  # Windows
```

Unit tests import the production modules (`sec_data.py`, `compare.py`, `analysis.py`, `market_data.py`, `budget.py`, `xbrl.py`) and make no network calls. `tests/test_app_pages.py` runs the whole app in Streamlit's AppTest with no secrets and every outside connection refused: default page, company selection, navigation, kept selections, missing and stale reviews, the archived example and download bytes. `tests/offline/` runs the whole app on fake SEC, Yahoo and Anthropic responses; `tests/check_risk_extraction.py` checks section extraction against live EDGAR filings without calling Anthropic.
## Rebuilding exports

Run `python tests/offline/build_workbooks.py` in the documented Codex Artifact Tool environment. It builds the company exports and templates, checks source fingerprints and restores prior outputs if a build fails. Do not replay retired patch scripts. Deployment serves saved workbooks and does not require the build runtime.
