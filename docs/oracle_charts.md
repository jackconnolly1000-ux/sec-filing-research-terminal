# Oracle maturity and scenario charts

## Checked maturity ladder

The checked Oracle review shows the August 31, 2026 principal calendar on a zero-based scale.
It replaces the older May 31 bar presentation; the historical annual figures remain in a table.
FY2027 is only September 2026–May 2027. The last bar combines FY2032 onward and must not be read
as one year's repayment. Commercial paper, interest and leases are excluded. The contractual
term-loan date can be extended. This chart does not establish funding coverage.

**App layout (October 17 reader review).** The scale is set by the largest single fiscal year (FY2028, so $2B
gridlines to $12B) rather than by the combined FY2032-onward bucket. That bucket ($90.250B, FY2032 through FY2066)
is drawn cut at the edge, with a visible break and "bar cut" beside its value, so the nearer years stay
readable. Each row has a rule linking its label, bar and value, and a dollar scale runs under the bars. The note
reconciles the twelve-month figure: $7.317B due September 2026–August 2027 is Remainder FY2027 ($2.672B) plus
June–August 2027 ($4.645B of FY2028's $10.145B). The Excel native chart is unchanged (saved, fingerprinted workbook).

The individual Oracle workbook adds one native chart beside the existing calendar on Payment dates.
Its series links directly to C49:C54 and categories to A49:A54, with the same checked caches.
No original cell, formula, cached result or chart is replaced. Author the chart using
`tests/offline/build_oracle_ladder.mjs` in the Artifact Tool runtime, then attach it with
`tests/offline/add_oracle_ladder.py OUTPUT_DIRECTORY`. The workbook hash is rebound.

## Illustrative monthly cash

The distribution histogram colors trials below zero (caution amber) apart from those at or above zero
(cash blue), because that split is the reported result; its bins are aligned so zero is a bin edge. Height
already encodes the count, so a height gradient is not used. The y-axis reads "Simulated trials (of N)" and a
caption explains that each bar counts trials in its range. The decision shown is chosen with two switches, capex
(A or B) and the revolver hypothetical (not assumed or assumed usable), which together select one of the four.

The Oracle scenario view retains its distribution histogram and adds a monthly median line with
shading between the 10th and 90th percentiles. These are pointwise summaries across the simulated
trials at each month end, not one individual path, a forecast band or confidence intervals for Oracle.
The zero reference is explicit. The dated principal is allocated to its calendar month; other flows
are spread evenly by assumption. No payment-date liquidity conclusion follows.

The scenario workbook records median and 90th percentile alongside its existing monthly statistics.
Its native chart draws the p10, median and p90 bounds as lines, plus a dashed zero reference. The app
uses shading between the bounds; the workbook uses bound lines. The selected decision, correlation,
seed and trial count drive both outputs. Range references and point caches are updated to the selected
decision's twelve rows. Rebuild the scenario template with `SCENARIO_ONLY=1` and the A3 builder.

The model adds monthly percentile summaries only. Existing trial arrays, historical figures, funding
conclusions and ending-cash statistics are unchanged. No missing amount is converted to a chart zero.
Excel native recalculation and physical-phone interaction remain unverified in this environment.
