"""Release 2, steps 2–3: the Oracle stress scenario in the app, with editable assumptions and an Excel record.

The model is liquidity_simulation.py. This view shows the math model and the assumption basis before any result
(as in class), runs the four decisions side by side, tests month-end cash for the decision shown, measures the cash
uses the model leaves out, shows a stability check, and offers the scenario as its own workbook. It is kept out of the checked evidence workbooks on purpose:
assumptions are not filing facts. Results are shares of simulated trials, never probabilities of default.
"""
from __future__ import annotations

from dataclasses import replace

import liquidity_simulation as ls
import scenario_state

B = 1_000_000_000
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
SHARE = "Share of trials below zero"
USD = " (USD, displayed in millions)"   # stored in dollars, shown in $ millions


def heading(st, text, note=""):
    """A scenario section heading (ui.py .sim-h): one size above body text, with a rule, so each part is easy to find."""
    from ui import esc
    tail = f'<span class="sim-h-note"> · {esc(note)}</span>' if note else ""
    st.markdown(f'<div class="sim-h">{esc(text)}{tail}</div>', unsafe_allow_html=True)


def _billions(st, label, value, key, help=None, nonnegative=False):
    return st.number_input(label, value=round(value / B, 3), step=0.5, format="%.3f", key=key, help=help, min_value=0.0 if nonnegative else None,
                           persist_state="session") * B


def assumptions(st, inputs, decisions):
    """Editable inputs, defaulting to the checked basis. Returns (inputs, decisions, trials, seed) or None."""
    heading(st, "Assumptions", "USD billions · defaults are anchored to checked historical figures, which do not "
            "establish future values")
    c1, c2, c3 = st.columns(3)
    t = inputs.ocf_ex_prepayments
    low = _billions(c1, "OCF excl. prepayments, assumed low", t.low, "sim_ocf_low")
    mode = _billions(c2, "Assumed mode — not estimated from future outcomes", t.mode, "sim_ocf_mode")
    high = _billions(c3, "Assumed high", t.high, "sim_ocf_high")
    st.caption(t.basis)
    c4, c5 = st.columns(2)
    prepay = _billions(c4, "Prepayments, assumed high (low and most likely are $0)", inputs.prepayments.high,
                       "sim_prepay", nonnegative=True, help=inputs.prepayments.basis)
    dividends = _billions(c5, "Dividends over the year (a decision)", decisions[0].dividends, "sim_div", nonnegative=True,
                          help="Default: Jun–Aug 2026 dividends of $1.565B, times four.")
    c6, c7 = st.columns(2)
    capex_a = _billions(c6, "Capex, decision A", decisions[0].capex, "sim_capex_a", nonnegative=True, help="Default: TTM cash capex.")
    capex_b = _billions(c7, "Capex, decision B", decisions[2].capex, "sim_capex_b", nonnegative=True, help="Default: fiscal 2026 cash capex.")
    rho = st.slider("Correlation, OCF excl. prepayments and prepayments", -0.9, 0.9, inputs.correlation, 0.1,
                    format="%.1f", key="sim_rho", persist_state="session")
    st.caption(ls.CORRELATION_BASIS)
    c8, c9 = st.columns(2)
    trials = c8.selectbox("Trials", [10_000, 50_000], key="sim_trials", persist_state="session")
    seed = int(c9.number_input("Seed", value=ls.DEFAULT_SEED, min_value=0, step=1, key="sim_seed", persist_state="session"))
    try:
        edited = replace(inputs, ocf_ex_prepayments=ls.Triangular(low, mode, high, t.basis),
                         prepayments=ls.Triangular(0, 0, prepay, inputs.prepayments.basis),
                         correlation=float(rho))
        ls.validate_inputs(edited, seed)
    except ValueError as exc:
        st.warning("Invalid assumptions: low ≤ most likely ≤ high; cash uses must be non-negative. " + str(exc))
        return None
    choices = [ls.Decision(f"{name}{', revolver assumed usable' if rev else ''}", capex, dividends, rev)
               for name, capex in (("Decision A", capex_a), ("Decision B", capex_b)) for rev in (False, True)]
    return edited, choices, trials, seed


def results_table(st, results):
    import pandas as pd
    rows = [{"Decision": r["decision"], "Capex ($B)": round(d.capex / B, 2),
             "Mean ending cash ($B)": round(r["mean"] / B, 2), "10th percentile ($B)": round(r["p10"] / B, 2),
             SHARE: r["share_below_zero"] * 100,
             "Average shortfall in those trials ($B)": round(r["mean_shortfall"] / B, 2)}
            for r, d in results]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                 column_config={**{c: st.column_config.NumberColumn(format="%.2f") for c in rows[0] if c.endswith("($B)")}, SHARE: st.column_config.NumberColumn(format="%.1f%%")})
    st.caption("Shares are of simulated trials under the assumptions above. They are not probabilities of default "
               "or of a funding gap.")


def monthly_table(st, end, path):
    """The decision shown, tested once at the end of the window and again at every month end."""
    import pandas as pd
    rows = [{"Cash at": "Aug 31, 2027", SHARE: end["share_below_zero"] * 100,
             "Mean ($B)": round(end["mean"] / B, 2), "10th percentile ($B)": round(end["p10"] / B, 2)},
            {"Cash at": "Lowest month end", SHARE: path["share_below_zero_any_month"] * 100,
             "Mean ($B)": round(path["lowest_mean"] / B, 2), "10th percentile ($B)": round(path["lowest_p10"] / B, 2)}]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                 column_config={**{c: st.column_config.NumberColumn(format="%.2f") for c in rows[0] if c.endswith("($B)")}, SHARE: st.column_config.NumberColumn(format="%.1f%%")})
    dated = ", ".join(f"{m} ${a / B:.3f}B" for m, a in zip(ls.MONTHS, path["principal_by_month"]) if a)
    where = (f"The month with the lowest cash before any revolver draw is {path['lowest_month']} in "
             f"{path['lowest_month_share']:.1%} of trials.")
    if path["lowest_month"] == ls.MONTHS[-1] and path["lowest_month_share"] == 1:
        why = (" The year's flows are a net outflow in every trial, so cash falls every month, and the" if
               path["share_net_outflow"] == 1 else " The")
        where += f"{why} two tests agree on these assumptions."
    st.caption(f"Lowest month end: each trial's lowest of the twelve month ends, Sep 2026–Aug 2027; below zero means "
               f"below zero in any month. {where}")
    st.caption(_dollars(f"Dated principal by month: {dated}. {ls.MONTHLY_BASIS}"))


def correlation_table(st, comparison, revolver):
    """The same decision and seed at three correlations: each input keeps its triangle, so only the spread moves."""
    import pandas as pd
    rows = [{"Correlation setting": r["correlation"], "Realized correlation": r["realized_correlation"],
             "Mean ending cash ($B)": round(r["mean"] / B, 2), "Std dev ($B)": round(r["sd"] / B, 2),
             "10th percentile ($B)": round(r["p10"] / B, 2), SHARE: r["share_below_zero"] * 100}
            for r in comparison]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                 column_config={**{c: st.column_config.NumberColumn(format="%.2f") for c in rows[0] if c.endswith("($B)")}, "Correlation setting": st.column_config.NumberColumn(format="%.1f"),
                                "Realized correlation": st.column_config.NumberColumn(format="%+.2f"),
                                SHARE: st.column_config.NumberColumn(format="%.1f%%")})
    note = ("Without the revolver, ending cash is a sum of the inputs, so the mean stays put and only the spread "
            "changes.")
    if revolver:
        note = ("With the revolver, a draw fills only shortfalls and stops at \\$10B, so a wider spread can also move "
                "the mean.")
    st.caption(f"Same decision, seed and trials at each setting. {note}")


def outside_uses(st, effects, uses, decision):
    """The base result beside each use the model leaves out, then the uses excluded because they are inside OCF."""
    import pandas as pd
    rows = [{"Scenario": e["scenario"], "Sensitivity amount ($B)": round(e["added_uses"] / B, 3),
             "Mean ending cash ($B)": round(e["mean"] / B, 2), SHARE: e["share_below_zero"] * 100}
            for e in effects]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                 column_config={**{c: st.column_config.NumberColumn(format="%.2f") for c in rows[0] if c.endswith("($B)")}, SHARE: st.column_config.NumberColumn(format="%.1f%%")})
    measured = "\n".join(f"- **{u.name}.** {u.amount_basis} {u.why_outside}" for u in uses)
    excluded = "\n".join(f"- **{name}:** {status}. {proof}" for name, status, proof in ls.EXCLUDED)
    unmeasured = "\n".join(f"- **{name}:** {note}" for name, note in ls.UNQUANTIFIED)
    st.markdown(_dollars(f"{decision.name}, same seed and trials. {ls.SENSITIVITY_NOTE}\n\n" + measured))
    st.markdown(_dollars("**Left out because a filing shows they are inside a modelled line**\n\n" + excluded))
    st.markdown(_dollars("**Left out with no measurable amount**\n\n" + unmeasured))


def _dollars(text):
    """Streamlit's Markdown treats text between dollar signs as math."""
    return text.replace("$", "\\$")


def histogram_figure(result):
    """Ending cash across trials. Bars below zero are colored apart from the rest because that split is the result
    the panel reports (the share of trials below zero); height alone already shows the count, so color is not
    spent repeating it. Bins are aligned so zero is always a bin edge and no bar straddles it."""
    import math
    import numpy as np
    import plotly.graph_objects as go
    import theme as T
    cash = result["ending_cash"] / B
    lo, hi = float(cash.min()), float(cash.max())
    size = max((hi - lo) / 60, 1e-9)
    start = math.floor(min(lo, 0) / size) * size
    bins = dict(start=start, end=max(hi, 0) + size, size=size)
    trials, below = len(cash), cash < 0
    hover = "%{x:.2f}B: %{y} of " + f"{trials:,}" + " trials<extra></extra>"
    fig = go.Figure()
    for mask, color, name in ((below, T.CAUTION_SOLID, f"Below zero: {below.mean():.1%} of trials"),
                              (~below, T.SERIES_CASH, f"Zero or above: {(~below).mean():.1%}")):
        fig.add_trace(go.Histogram(x=cash[mask], xbins=bins, marker_color=color, name=name, hovertemplate=hover,
                                   showlegend=bool(np.any(mask))))
    fig.add_vline(x=0, line_color=T.TEXT_STRONG, line_width=1)
    fig.add_annotation(x=0, y=1, yref="paper", text="zero", showarrow=False, yanchor="bottom",
                       font=dict(color=T.TEXT_MUTED, size=11))
    fig.update_layout(height=330, margin=dict(l=64, r=12, t=24, b=80), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", bargap=0.04, barmode="stack", font=dict(color=T.TEXT, size=11),
                      legend=dict(orientation="h", y=-0.3, x=0, traceorder="normal"),
                      xaxis=dict(title="Ending cash · USD billions", gridcolor=T.BORDER,
                                 zerolinecolor=T.BORDER),
                      yaxis=dict(title=f"Simulated trials (of {trials:,})", gridcolor=T.BORDER))
    return fig, size


def histogram(st, result):
    from charts import CHART_CONFIG
    fig, size = histogram_figure(result)
    st.plotly_chart(fig, width="stretch", theme=None, config=CHART_CONFIG)
    st.caption(f"Ending cash is at August 31, 2027. Each bar counts the simulated trials whose ending cash fell in that \\${size:.2f}B range; the bars add "
               f"up to all {result['trials']:,} trials. The left axis is a count of trials, not dollars.")


TICKS = (0, 4, 8, 11)   # Sep 2026, Jan 2027, May 2027, Aug 2027: at least three months apart, so all fit at 390 px


def monthly_figure(path):
    """Pointwise simulated percentiles, not a predicted cash path or a confidence interval."""
    import plotly.graph_objects as go
    import theme as T
    fig = go.Figure()
    rgb = tuple(int(T.SERIES_CASH[k:k+2],16) for k in (1,3,5))
    fig.add_trace(go.Scatter(x=ls.MONTH_ENDS, y=path["month_p90"] / B, mode="lines", line=dict(width=0),
                             showlegend=False, name="90th percentile", customdata=ls.MONTHS, hovertemplate="%{customdata}: %{y:.2f}B<extra>90th percentile</extra>"))
    fig.add_trace(go.Scatter(x=ls.MONTH_ENDS, y=path["month_p10"] / B, mode="lines", line=dict(width=0),
                             fill="tonexty", fillcolor=f"rgba({rgb[0]},{rgb[1]},{rgb[2]},0.22)", name="Simulated 10th–90th percentiles",
                             customdata=ls.MONTHS, hovertemplate="%{customdata}: %{y:.2f}B<extra>10th percentile</extra>"))
    fig.add_trace(go.Scatter(x=ls.MONTH_ENDS, y=path["month_p50"] / B, mode="lines+markers",
                             line=dict(color=T.SERIES_CASH, width=2), marker=dict(size=4), name="Simulated median",
                             customdata=ls.MONTHS, hovertemplate="%{customdata}: %{y:.2f}B<extra>Median</extra>"))
    fig.add_hline(y=0, line_color=T.TEXT_MUTED, line_width=1, line_dash="dash")
    fig.update_layout(height=330, margin=dict(l=52,r=8,t=12,b=50), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(color=T.TEXT,size=11),
                      legend=dict(orientation="h",y=-.22,x=0),
                      # Points sit at month ends; date ticks fell on the 1st and read "Oct 26". Label the month-end points
                      # themselves, every fourth month plus the last, as "Sep 2026"
                      xaxis=dict(type="date",tickmode="array",tickvals=[ls.MONTH_ENDS[k] for k in TICKS],
                                 ticktext=[ls.MONTHS[k] for k in TICKS],tickangle=0,gridcolor=T.BORDER),
                      yaxis=dict(title="Cash, USD billions",rangemode="tozero",gridcolor=T.BORDER))
    return fig


def workbook(inputs, results, trials, seed, comparison=None, outside=None, uses=None, monthly=None) -> bytes:
    """Record the current run with the source documentation and layout authored offline."""
    import scenario_export
    return scenario_export.workbook(inputs, results, trials, seed, comparison, outside, uses, monthly)


CAPEX_CHOICES = ("Decision A", "Decision B")
REVOLVER_CHOICES = ("Not assumed usable", "Assumed usable")


def decision_picker(st, decisions):
    """The four decisions as a 2 x 2: capex level (A or B) beside the revolver hypothetical (off or on).
    Returns the chosen decision's name, matching the results table."""
    capex = {d.name: d.capex for d in decisions}
    c1, c2 = st.columns(2)
    level = c1.segmented_control("Capex decision", CAPEX_CHOICES, default=CAPEX_CHOICES[0], required=True,
                                 key="sim_pick_capex", persist_state="session",
                                 format_func=lambda o: f"{o} · \\${capex[o] / B:.2f}B")
    revolver = c2.segmented_control("Revolver (hypothetical)", REVOLVER_CHOICES, default=REVOLVER_CHOICES[0],
                                    required=True, key="sim_pick_revolver", persist_state="session")
    return f"{level}{', revolver assumed usable' if revolver == REVOLVER_CHOICES[1] else ''}"


VIEWS = ("Checked review", "Stress scenario (illustrative)")


def available(snapshot) -> bool:
    """Oracle only: Lilly and Vistra have no dated principal calendar, so their obligations side would be invented."""
    return snapshot.get("ticker") == "ORCL"


def render(st, snapshot) -> None:
    """The scenario as its own view, framed (ui.py, .st-key-scenario_view) so it never reads as checked facts."""
    from ui import notice
    if not available(snapshot):
        return
    inputs = ls.oracle_inputs()
    uses = ls.oracle_uses_outside_model()
    if inputs is None or uses is None:
        st.markdown(notice("Stress scenario Unavailable", "The checked Oracle evidence it reads did not load. "
                           "No assumed figures are substituted.", "caution"), unsafe_allow_html=True)
        return
    version = scenario_state.evidence_version()
    scenario_state.reset_for_version(st.session_state, version)
    with st.container(key="scenario_view"):
        st.button("Reset assumptions", key="scenario_reset", on_click=scenario_state.clear_scenario, args=(st.session_state,))
        st.markdown(notice(ls.LABEL, "Oracle, September 2026 to August 2027. The figures below come from simulated "
                           "trials, not from checked filing facts. The checked review's funding conclusion is "
                           "unchanged: future funding coverage remains Unavailable.", "caution"), unsafe_allow_html=True)
        heading(st, "How the scenario works")
        st.markdown(_dollars(
            "**Question:** if operating cash flow fell anywhere in the assumed range below, in what share of "
            "simulated trials would August 31 cash plus that cash flow end the twelve months below the cash uses "
            "the model subtracts, or go below zero at a month end on the way?"))
        st.markdown(
            '<div class="sim-formula"><b>Model, per trial:</b> ending cash = '
            f'<b>&#36;{inputs.starting_cash / B:.3f}B</b> cash + OCF excluding prepayments + prepayments − capex − '
            f'dividends − <b>&#36;{inputs.principal_due / B:.3f}B</b> dated debt principal − commercial paper due '
            '(+ a revolver draw up to &#36;10B, only where the decision assumes it is usable; drawable credit is '
            'Unavailable in the filings). The month-end path subtracts each dated principal payment in its calendar '
            'month and spreads the other flows evenly.</div>', unsafe_allow_html=True)
        st.markdown(_dollars(
            "- **Checked inputs:** reported starting cash (10-Q balance sheet, August 31, 2026) and derived note and "
            "term-loan principal due in the window (Oracle's August 31 principal calendar).\n"
            "- **Assumptions:** the OCF, prepayment and commercial-paper triangles and the correlation; their defaults "
            "are anchored to checked history, which does not set future bounds.\n"
            "- **Decisions:** capex, dividends and the revolver."))
        st.caption(ls.TIMING_LIMIT)
        with st.form("scenario_assumptions"):
            chosen = assumptions(st, inputs, ls.oracle_decisions())
            submitted = st.form_submit_button("Run scenario", key="sim_submit")
        if chosen is None:
            return
        candidate_key = scenario_state.input_key(chosen, version)
        completed = st.session_state.get("sim_completed")
        if submitted or completed is None:
            completed = scenario_state.calculate(chosen, uses, version)
            st.session_state["sim_completed"] = completed
        elif candidate_key != completed["key"]:
            st.info("Results and download retain the last completed run. Submit Run scenario to apply edited assumptions.")
        edited, decisions, trials, seed = completed["chosen"]
        results = completed["results"]
        heading(st, "Results by decision")
        results_table(st, results)
        pick = decision_picker(st, decisions)
        shown = next(d for d in decisions if d.name == pick)
        heading(st, "Distribution of ending cash", shown.name)
        histogram(st, next(r for r, d in results if d.name == pick))
        monthly = completed["monthly"]
        heading(st, "Cash at each month end", shown.name)
        monthly_table(st, *next((r, m) for d, r, m in monthly if d.name == pick))
        from charts import CHART_CONFIG
        path = next(m for d, _, m in monthly if d.name == pick)
        st.plotly_chart(monthly_figure(path), width="stretch", theme=None, config=CHART_CONFIG)
        st.caption("Shading shows the 10th–90th percentiles at each month end; the line is the simulated median. "
                   "These are pointwise summaries of assumed trials, not a forecast band or one individual path. "
                   "The dashed line is zero. Even monthly allocation does not establish payment-date liquidity.")
        if shown.name not in completed["comparisons"]:
            completed["comparisons"][shown.name] = ls.compare_correlations(edited, shown, trials, seed)
        comparison = completed["comparisons"][shown.name]
        heading(st, "How correlation changes the spread", shown.name)
        correlation_table(st, comparison, shown.revolver)
        outside = completed["outside"]
        heading(st, "Sensitivity: cash uses outside the model", shown.name)
        outside_uses(st, next(e for d, e in outside if d.name == pick), uses, shown)
        check = completed["stability"]
        drift = abs(check["share_below_zero"] - results[0][0]["share_below_zero"])
        st.caption(f"Stability check: rerunning decision A with {trials * 5:,} trials and a new seed changes the "
                   f"share of trials below zero by {drift:.1%}. A separate seed and larger trial count test whether "
                   "the reported result is sensitive to simulation noise.")
        st.caption("Also not modelled: new borrowing or equity.")
        try:
            if pick not in completed["exports"]:
                completed["exports"][pick] = workbook(edited, results, trials, seed, comparison, outside, uses, monthly)
            content = completed["exports"][pick]
        except (OSError, ValueError, KeyError):
            st.caption("Scenario workbook Unavailable: its verified layout could not be loaded.")
        else:
            st.download_button("Download this scenario (Excel)", content,
                               file_name=f"Oracle_Stress_Scenario_seed{seed}.xlsx", mime=XLSX, key="sim_download", on_click="ignore")
