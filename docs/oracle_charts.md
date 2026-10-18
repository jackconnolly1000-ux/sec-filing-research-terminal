# Oracle principal and scenario charts

The checked review shows one column for every fiscal year from the remainder of FY2027 through FY2066. `oracle_principal_view.ladder_years()` supplies both the app and the workbook calendar. Excel `Payment dates!H61:I101` contains the formula-based annual series; the chart is beside it. There is no clipped Thereafter column. FY2027 covers September 2026–May 2027; next-twelve-month principal also includes June–August 2027.

Known principal is $125.567B at August 31, 2026, excluding unknown commercial paper, interest and leases. The term loan uses its contractual installments and remainder, not both those events and the aggregate. Its optional extension remains a caveat.

The optional Debt detail views share `debt_detail.py`: maturity concentration by instrument/year, principal in explicit fixed-coupon buckets, and known-principal composition. The Excel Debt detail sheet uses the same bins, event dates and classifications. Coupons are stored as fractions, with exact source contexts in Data; floating-rate spreads and amortization rates are excluded. Color measures principal magnitude or weighted fixed coupon, never a risk score.

The scenario view remains separate. Its monthly percentile bands are conditional on assumptions and do not establish payment-date liquidity. The existing operating cash waterfalls remain cash bridges, not borrowing roll-forwards. A principal-and-interest trajectory is deferred until a complete cash-interest schedule exists.

Rebuild all exports with `python tests/offline/build_workbooks.py` in the Artifact Tool runtime. Old chart-only and style-only migrations are retired.
