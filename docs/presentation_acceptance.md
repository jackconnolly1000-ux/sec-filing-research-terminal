# Presentation pass: acceptance record

Reviewed October 17, 2026 against `main` at `485c019` (merge of PR #65). Live app: https://sec-filing-research-terminal.streamlit.app/.

This records what the presentation pass changed, what was checked and how, what was not checked, and the obstacles a first-time reader still meets. It adds no features. Financial figures, funding conclusions, source gates and saved-workbook fingerprints are those already on `main`.

## What the presentation pass changed

| PR | Change |
|---|---|
| #60 | Oracle's illustrative stress scenario moved out of a collapsed section at the bottom of the review into its own view, chosen by a **View** switch. It's framed so it can't be read as checked filing facts. |
| #61 | Each company review reads in financial order, with labelled groups: What it owes → Cash generation and liquidity → Funding and repayment → Interest coverage → Change over time → What remains unresolved. |
| #62 | The scenario's three cash uses outside the model are labelled **sensitivity amounts**, not balances or payments due. The timing text says evenly spread monthly flows do not establish liquidity on actual payment dates. |
| #63 | Exports organized: individual company workbooks, a three-sheet optional summary, and a nine-sheet scenario workbook with Data and About sheets. |
| #64 | The optional download is labelled as a three-company metric summary. |
| #65 | Oracle's checked principal ladder, and a separate chart of the simulated monthly median with its 10th–90th percentile band (also as native Excel charts). |

## Checked on the live app (October 17, 2026)

| Check | Result |
|---|---|
| Each company (LLY, ORCL, VST) loads with no error and offers its primary download | Pass |
| Downloaded checked workbooks match the saved repository files byte for byte (SHA-256 of the served bytes): LLY 57,096 bytes, ORCL 74,831, VST 64,427, three-company summary 13,817 | Pass |
| Only Oracle shows the View switch; Checked review opens first; the scenario view shows none of the checked review or its download | Pass |
| Every review shows the five labelled groups in order, then What remains unresolved | Pass |
| After the reorder, every "above" or "below" cross-reference in the rendered reviews still points the right way | Pass |
| The scenario workbook downloads with nine sheets (Results, Monthly path, Monthly path by month, Correlation, Outside-use effects, Scenario, Uses not modelled, Data, About) and a native chart; numbers are stored as numbers | Pass |
| The simulated monthly median and percentile band render with their labels | Pass |

The offline suite (unit tests, the saved-source audit, and the offline app and archived-example checks) passed for each merged PR. The workbook checks hash the bytes the live download buttons serve; they do not depend on a local build.

## Not checked

- Interaction on a physical phone (layouts were checked at 390 px in a browser).
- Recalculation in desktop Excel after editing a workbook.
- A run with changed scenario assumptions in the live browser. Automated tests cover the chart bindings for the other decisions.

## Boundaries that still apply

- **Future funding coverage is Unavailable** for all three companies. A credit commitment is not drawable cash, and historical cash flows are not forecasts.
- Oracle's commercial-paper balance and timing are unresolved.
- Lilly's and Vistra's June 30 lease liabilities are Unavailable; their December 31 amounts keep their own date.
- **Scenario results are conditional on stated assumptions.** Shares of trials below zero are not probabilities of default. The monthly percentile band summarizes trials at each month end; it is not a confidence interval or a single cash path.
- Evenly spread monthly flows do not establish liquidity on actual payment dates.
- The three outside uses are sensitivity amounts, not balances due:
  - Finance-lease payments include interest.
  - The capex-financing figure is cumulative proceeds, not an outstanding balance.
  - Purchase obligations may overlap capex.
  - Combined, the three may overlap each other.
- Editing a downloaded scenario workbook does not rerun the simulation. Change the assumptions in the app and download again.

## Five-minute first-time-reader walkthrough

The route a new reader was walked through on the live app, with what each stop should leave them knowing:

1. **Company, date and conclusion (1 min).** Pick a company. The header gives the balance-sheet date and source filing. The funding conclusion gives near-term obligations, resources, competing uses and the decisive unknowns.
2. **Oracle's checked ladder and revolver (1 min).** Under *Funding and repayment*, the principal ladder dates note and term-loan principal; commercial paper is excluded as Unavailable. *How much financing capacity is established?* shows that the $10B revolver commitment is not established drawable capacity.
3. **Illustrative scenario (1.5 min).** Switch View to *Stress scenario (illustrative)*. Read the question, the model and which inputs are filing facts, assumptions or decisions. Then read the results by decision and the monthly median and percentile band.
4. **Scenario Data and About (1 min).** Download the scenario. About explains the meaning, units, reproduction, timing and sensitivity limits; Data separates reported facts from assumptions.
5. **Vistra's limits and the summary (0.5 min).** On Vistra, *What remains unresolved?* lists what is Unavailable. The optional three-company metric summary is a side-by-side record, not a peer ranking.

## First-time-reader obstacles found

Recorded for a later presentation fix. None is a figure error, and none is fixed in this change.

1. **The plain answer is buried under a favorable-sounding headline.** The header sentence leads with a historical comparison (Lilly: "TTM operating cash flow exceeded reported capital spending by $18.19B."). The release's actual answer, "Future funding coverage: Unavailable", first appears at the end of the funding conclusion's fourth row, *Decisive unknowns*. The rows above it lean on unexplained abbreviations (H1, PP&E, IPR&D, OCF, TTM). *Location:* each company review, header answer line and *Funding conclusion → Decisive unknowns*.
   *Status:* fixed October 17 (PR #73). Each review opens with "Future funding coverage: Unavailable" and a one-line reason, then the historical comparison, then a Terms used line.
2. **The scenario workbook opens on a results sheet with no illustrative label.** The first sheet, *Results*, shows figures such as a mean ending cash of −$11,233M with no statement that they are simulated under assumptions. The label and meaning are on *Scenario* (sixth sheet) and *About* (ninth, last). *Location:* the scenario Excel download, sheet order and the *Results* sheet.
3. **Oracle's twelve-month principal figure doesn't appear on its ladder.** The text and the scenario use $7.317B due September 2026–August 2027, but the ladder is bucketed by fiscal year (May year end). Its first bar, *Remainder FY2027*, is $2.672B and runs through May 2027; the remaining $4.645B due June–August 2027 is inside *FY2028* ($10.145B). A reader comparing the two can't find $7.317B on the chart. *Location:* Oracle review, *Funding and repayment → Which borrowing principal is due after August 31?*, principal maturity ladder.

Smaller notes, not counted above:
- The scenario's monthly chart labels ticks "Oct 26", "Jan 27", which can read as days of the month rather than October 2026. *Fixed October 17 (PR #75):* ticks sit on the month-end points and read "Sep 2026", "Jan 2027", "May 2027", "Aug 2027", all visible at 390 px.
- On every company page, the download button and its caption ("editing inputs does not update the checked narrative") sit above the review, before the reader knows what the workbook contains.
