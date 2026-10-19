# Product revisions: October 19, 2026

## Decisions and resulting behavior

- **Name:** Debt & Liquidity Research. The shorter title describes the actual product without suggesting a full trading terminal. App/browser title and README agree. The verified public address is https://debt-liquidity-research.streamlit.app/; the repository name is unchanged.
- **Company-aware stress entry:** the View selector is available below the company selector for all three companies. Its selection survives a company change. The chosen company's model, periods and controls are displayed; Oracle assumptions/results are never applied to another company.
- **Different supported model scopes:** Oracle retains its twelve-month cash-path Monte Carlo and Excel record. Lilly and Vistra have a deterministic historical cash-generation sensitivity. Zero shocks reproduce checked TTM OCF less the checked capex line. User-selected OCF declines and capex changes are assumptions, with no calibrated distribution or implied likelihood. Company-specific inputs and interpretation limits come from the checked ratio model. The six underlying flow inputs, TTM coefficients, dates, accessions, source URLs, assumptions and result are downloadable as CSV.
- **No invented repayment model:** the Lilly/Vistra sensitivity does not calculate ending cash or funding coverage, add cash or credit capacity, or subtract an invented principal schedule. Acquisition payments, shareholder distributions, debt principal, capital calls and other cash uses remain outside the result and are stated beside it. The missing prerequisites for a full repayment cash path are named for each company.
- **Less repetition:** Oracle's repeated short-term instrument gaps are grouped into one explanation, with the original details retained. The dated funding conclusion stays visible; its four supporting rows sit in a disclosure. Detailed revolver-date conditions, resource mapping and interest composition remain accessible. A single evidence-gap section describes the finding, its consequence, the evidence needed and checked source links. Disclosure gaps are distinguished from inherently uncertain future outcomes.

## Why “Unavailable” was frequent

The original Oracle rendered review contained 62 case-insensitive occurrences before the separate evidence/filing disclosures. The same commercial-paper, revolver, interest and timing limitations were repeated in several views; some occurred in closed detail sections. This was not evidence of 62 different missing facts.

No unknown is filled with zero or made reliable by changing its label. The revised primary reading path (closed detail bodies excluded, summaries retained) has 9 occurrences, compared with 36 before the revision. Counts refer to generated review HTML, not a browser search across every expanded disclosure. The checked conclusion still states that future funding coverage is Unavailable. Failure messages for missing/stale evidence remain visible.

## Weaknesses and next work

1. **Independent interpretation:** the product needs a concise current Oracle credit memo that the author can defend. The existing case study contains historical updates and should be consolidated after the author's own argument is developed. Do not manufacture personal authorship by generating the argument for them.
2. **Repayment-model completeness:** Lilly needs a reconciled current principal calendar, post-expiry credit evidence and acquisition/manufacturing payment timing. Vistra needs a borrower-level service calendar, accessible cash, transfer restrictions and dated borrowing-base/draw evidence. Existing selected obligations remain useful; they are not a complete service schedule.
3. **Uncertainty:** Oracle's scenario distributions are assumptions anchored to history, not calibrated forecasts. The monthly allocation does not test payment-date liquidity. A deterministic break-even view may be useful after the memo's analytical question is agreed; do not add it automatically in this presentation pass.
4. **Reproduction:** full-filing checks depending on local raw files remain a separate gate from portable fixture tests. The next evidence improvement should make one complete source-to-conclusion example independently reproducible.

## Tools and access

The existing GitHub connector, PDF inspection, workbook tooling and browser verification cover this revision. No additional paid service or plugin is required. A market-data feed would not establish undisclosed payment dates or draw conditions. Access to the exact saved SEC exhibits and reproducible source checks is more useful for those gaps than adding another summarizer.

The PDF skill was used to read both text comments and the embedded screenshot. Existing individual and Oracle scenario Excel exports are retained. No workbook was reauthored: all three checked company workbook hashes are identical to the starting commit, and their manifest gates continue to pass.

## Verification

- Full local suite: 563 tests passed. New checks cover independent stress arithmetic, zero/invalid boundaries, source preservation, changed-evidence refusal, company-state isolation and progressive disclosure.
- The existing no-network app check passes; checked review downloads match the saved workbooks in AppTest.
- Visual and deployed verification is recorded after publication in the PR. Automated HTML checks and AppTest do not by themselves establish desktop/phone visual acceptance.
- No SEC/Yahoo/paid AI requests are needed for these saved review and stress views.

The next step is the author's independent Oracle memo, followed by an evidence-grounded review of its argument.
