"""Checked calendar cell specification used by principal_records.py; no workbook mutation path."""
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import oracle_principal as op  # noqa: E402

# Semantic cell roles in this specification; the authoring tool assigns actual workbook styles.
TITLE, BOLD, HEAD, TEXT, WRAP, NOTE = 70, 77, 182, 40, 74, 72
BLUE, BLACK, DATE = 29, 57, 31
FIRST = 35
M = 1_000_000


class Sheet:
    def __init__(self):
        self.rows = {}

    def put(self, ref_col, row, xml):
        self.rows.setdefault(row, []).append((ref_col, xml))

    def text(self, col, row, value, style=TEXT):
        self.put(col, row, f'<x:c r="{col}{row}" s="{style}" t="str"><x:v>{escape(value)}</x:v></x:c>')

    def number(self, col, row, value, style=BLUE):
        self.put(col, row, f'<x:c r="{col}{row}" s="{style}" t="n"><x:v>{value}</x:v></x:c>')

    def day(self, col, row, value):
        self.put(col, row, f'<x:c r="{col}{row}" s="{DATE}" t="d"><x:v>{value}T00:00:00.000Z</x:v></x:c>')

    def formula(self, col, row, expr, cached, style=BLACK):
        self.put(col, row, f'<x:c r="{col}{row}" s="{style}" t="n"><x:f>{escape(expr)}</x:f><x:v>{cached}</x:v></x:c>')

    def xml(self, heights):
        out = ""
        for row in sorted(self.rows):
            cells = "".join(x for _, x in sorted(self.rows[row], key=lambda c: c[0]))
            height = heights.get(row, 18)
            out += f'<x:row r="{row}" ht="{height}" customHeight="1">{cells}</x:row>'
        return out


def block(review):
    s, heights, r = Sheet(), {}, FIRST
    rec, tl = review["reconciliation"], review["term_loan"]
    s.text("A", r, "August 31, 2026 borrowing principal by instrument", TITLE); heights[r] = 24
    r += 1
    s.text("A", r, ("Principal, excluding interest. Senior notes and the term loan come from the 10-K debt table at "
                    "May 31, 2026, carried forward to August 31. Commercial paper is Unavailable. Each instrument's "
                    "tag, context and source are in its row below. Not funding coverage or drawable credit."), WRAP)
    heights[r] = 54
    # Row positions of the supporting blocks, fixed before the formulas that reference them
    near_top = r + 3
    near_rows = review["next_twelve_months"]["rows"]
    near_total = near_top + len(near_rows) + 1
    fy_top = near_total + 3
    fy_total = fy_top + len(review["calendar"])
    rec_top = fy_total + 3
    tl_top = rec_top + 18
    inst_top = tl_top + len(tl["installments"]) + 6
    instruments = review["matured"] + review["remaining"]
    inst_first, inst_last = inst_top + 1, inst_top + len(instruments)
    rows_of = {i["member"]: inst_first + k for k, i in enumerate(instruments)}
    tl_borrowed = tl_top + 1
    inst_first_row = tl_top + 2
    inst_last_row = inst_first_row + len(tl["installments"]) - 1
    tl_final, tl_aug = inst_last_row + 1, inst_last_row + 2
    notes = f"$E${inst_first}:$E${inst_last}"
    dates = f"$B${inst_first}:$B${inst_last}"
    kinds = f"$F${inst_first}:$F${inst_last}"
    tl_amounts = f"$C${inst_first_row}:$C${tl_final}"
    tl_dates = f"$B${inst_first_row}:$B${tl_final}"

    def in_window(start, end):
        notes_sum = sum(i["principal_aug_31"] or 0 for i in review["remaining"]
                        if i["kind"] in ("Fixed-rate senior notes", "Floating-rate senior notes")
                        and start <= i["maturity"] <= (end or "9999"))
        steps = tl["installments"] + [tl["final"]]
        tl_sum = sum(x["amount"] for x in steps if op.ANCHOR < x["date"] and start <= x["date"] <= (end or "9999"))
        return notes_sum + tl_sum

    def window_formula(start_ref, end_ref):
        end = f',{dates},"<="&{end_ref}' if end_ref else ""
        tl_end = f',{tl_dates},"<="&{end_ref}' if end_ref else ""
        return (f'SUMIFS({notes},{dates},">="&{start_ref}{end},{kinds},"<>Term loan")'
                f'+SUMIFS({tl_amounts},{tl_dates},">="&{start_ref}{tl_end})')

    # 1. Next twelve months
    r = near_top - 1
    for col, head in zip("ABCD", ("Due September 2026–August 2027", "Due date", "Principal (USD millions)", "Basis")):
        s.text(col, r, head, HEAD)
    heights[r] = 30
    tl_steps = {x["date"]: inst_first_row + k for k, x in enumerate(tl["installments"])}
    for k, row in enumerate(near_rows):
        rr = near_top + k
        s.text("A", rr, row["label"])
        s.day("B", rr, row["date"])
        if row["label"].startswith("Term loan, scheduled"):
            s.formula("C", rr, f"C{tl_steps[row['date']]}", row["amount"])
            s.text("D", rr, "Contract installment, calculated; not separately reported.", WRAP)
        elif row["label"] == "Term loan, remaining principal":
            s.formula("C", rr, f"C{tl_final}", row["amount"])
            s.text("D", rr, "Calculated remainder. Oracle may extend the date by up to 2 years.", WRAP)
        else:
            member = next(i["member"] for i in review["remaining"] if i["label"] == row["label"])
            s.formula("C", rr, f"E{rows_of[member]}", row["amount"])
            s.text("D", rr, "Senior note at its stated maturity.", WRAP)
    rr = near_top + len(near_rows)
    s.text("A", rr, "Commercial paper")
    s.text("D", rr, "Unavailable: August 31 balance and maturity dates are not reported.", WRAP)
    s.text("A", near_total, "Next twelve months, excluding commercial paper", BOLD)
    s.formula("C", near_total, f"SUM(C{near_top}:C{near_top + len(near_rows) - 1})",
              review["next_twelve_months"]["principal"], BOLD)

    # 2. By fiscal year (Oracle's year ends May 31)
    r = fy_top - 1
    for col, head in zip("ABCD", ("Fiscal year", "From", "Principal (USD millions)", "Through")):
        s.text(col, r, head, HEAD)
    heights[r] = 30
    for k, bucket in enumerate(review["calendar"]):
        rr = fy_top + k
        s.text("A", rr, bucket["label"])
        s.day("B", rr, bucket["start"])
        if bucket["end"]:
            s.day("D", rr, bucket["end"])
        else:
            s.text("D", rr, "Final maturity")
        expr = window_formula(f"B{rr}", f"D{rr}" if bucket["end"] else None)
        cached = in_window(bucket["start"], bucket["end"])
        assert cached == bucket["principal"], bucket["label"]
        s.formula("C", rr, expr, cached)
    s.text("A", fy_total, "Total, excluding commercial paper", BOLD)
    s.formula("C", fy_total, f"SUM(C{fy_top}:C{fy_total - 1})", rec["known_principal_excluding_cp"], BOLD)

    # 3. Reconciliation to reported borrowing
    r = rec_top - 1
    for col, head in zip("ACD", ("Principal versus carrying value", "USD millions", "Basis")):
        s.text(col, r, head, HEAD)
    heights[r] = 30
    lt, lt_r = rec["long_term_carrying_reported"], rec_top + 1
    rows = [
        ("Senior-note and term-loan principal at August 31", ("f", f"C{fy_total}", rec["known_principal_excluding_cp"]),
         "Sum of the calendar above."),
        ("Long-term borrowing at carrying value, as tagged", ("n", lt),
         "10-Q Note 2, p. 9: $125.0B, decimals -8 (nearest $100M). us-gaap:DebtInstrumentCarryingAmount, senior notes and other long-term borrowings."),
        ("Implied unamortized discount and issuance costs, low", ("f", f"C{rec_top}-(C{lt_r}+50000000)", rec["implied_discount_range"][0]),
         "Not reported at August 31. Rounding of the tagged figure gives a range."),
        ("Implied unamortized discount and issuance costs, high", ("f", f"C{rec_top}-(C{lt_r}-50000000)", rec["implied_discount_range"][1]), ""),
        ("Unamortized discount and issuance costs at May 31", ("n", 564 * M),
         "10-K Note 6, p. 84. It falls as costs amortize; no new issuance in the quarter."),
        ("Current borrowing at carrying value", ("n", rec["current_reported"]), "10-Q balance sheet, p. 1."),
        ("Noncurrent borrowing at carrying value", ("n", rec["noncurrent_reported"]), "10-Q balance sheet, p. 1."),
        ("Total borrowing at carrying value", ("f", f"C{rec_top + 5}+C{rec_top + 6}", rec["carrying_reported"]), ""),
        ("Commercial paper implied, low", ("f", f"C{rec_top + 7}-(C{lt_r}+50000000)", rec["commercial_paper_range"][0]),
         "Total carrying less the rounded long-term figure. A range, so the balance stays Unavailable."),
        ("Commercial paper implied, high", ("f", f"C{rec_top + 7}-(C{lt_r}-50000000)", rec["commercial_paper_range"][1]), ""),
        ("Grouped June–August repayments", ("n", rec["repayments_quarter"]),
         "10-Q cash flows, p. 5: senior notes, term loan and other borrowings. Not assigned to instruments."),
        ("Scheduled principal due June–August", ("f", f"C{rows_of[review['matured'][0]['member']]}+C{tl_steps['2026-06-30']}",
                                                 rec["scheduled_principal_quarter"]),
         "July 15, 2026 notes plus the June 30 term-loan installment. MD&A: about $3.1B of scheduled repayments."),
        ("Grouped repayments less scheduled principal", ("f", f"C{rec_top + 10}-C{rec_top + 11}",
                                                          rec["repayments_quarter"] - rec["scheduled_principal_quarter"]),
         "MD&A describes about $1.1B of commercial-paper repayment; the commercial-paper row is zero. Not subtracted."),
        ("Instrument principal at May 31", ("f", f"SUM(C{inst_first}:C{inst_last})", 130_105 * M), "Sum of the instrument table."),
        ("Reported principal total at May 31", ("n", 130_105 * M), "10-K Note 6, p. 84; us-gaap:DebtInstrumentCarryingAmount, undimensioned."),
    ]
    for k, (label, value, basis) in enumerate(rows):
        rr = rec_top + k
        s.text("A", rr, label)
        if value[0] == "n":
            s.number("C", rr, value[1])
        else:
            s.formula("C", rr, value[1], value[2])
        if basis:
            s.text("D", rr, basis, WRAP)
            heights[rr] = 30
    s.text("A", rec_top + len(rows), "Difference", BOLD)
    s.formula("C", rec_top + len(rows), f"C{rec_top + 13}-C{rec_top + 14}", 0, BOLD)

    # 4. Term-loan amortization from its stated terms
    s.text("A", tl_top, "Term loan: amortization from the stated terms (10-K Note 6, pp. 85–86)", HEAD)
    for col in "BCD":
        s.text(col, tl_top, {"B": "Date", "C": "USD millions", "D": "Basis"}[col], HEAD)
    s.text("A", tl_borrowed, "Amount borrowed")
    s.number("C", tl_borrowed, tl["borrowed"])
    s.text("D", tl_borrowed, "us-gaap:DebtInstrumentFaceAmount, term loan member, May 31, 2026. Assumes no prepayment.", WRAP)
    for k, step in enumerate(tl["installments"]):
        rr = inst_first_row + k
        rate = 0.0125 if step["basis"].startswith("1.25") else 0.025
        s.text("A", rr, "Installment, paid" if step["date"] <= op.AS_OF else
               "Installment, June–August" if step["date"] <= op.ANCHOR else "Installment, scheduled")
        s.day("B", rr, step["date"])
        s.formula("C", rr, f"ROUND($C${tl_borrowed}*{rate},0)", step["amount"])
        s.text("D", rr, step["basis"], WRAP)
    s.text("A", tl_final, "Remaining principal")
    s.day("B", tl_final, tl["final"]["date"])
    s.formula("C", tl_final, f"C{tl_borrowed}-SUM(C{inst_first_row}:C{inst_last_row})", tl["final"]["amount"])
    s.text("D", tl_final, "Due August 16, 2027 unless Oracle extends it (up to 2 years at its option).", WRAP)
    s.text("A", tl_aug, "Principal outstanding at August 31, 2026", BOLD)
    s.formula("C", tl_aug, f'C{tl_borrowed}-SUMIFS(C{inst_first_row}:C{inst_last_row},B{inst_first_row}:B{inst_last_row},"<="&DATE(2026,8,31))',
              tl["balance_aug_31_2026"], BOLD)
    s.text("A", tl_aug + 1, "Check: calculated May 31, 2026 balance less reported 5,137M")
    s.formula("C", tl_aug + 1, f'C{tl_borrowed}-SUMIFS(C{inst_first_row}:C{inst_last_row},B{inst_first_row}:B{inst_last_row},"<="&DATE(2026,5,31))-5137000000',
              tl["balance_may_31_2026"] - 5_137 * M)
    s.text("D", tl_aug + 1, "Reported to the nearest million; a difference under 0.5M agrees.", WRAP)

    # 5. Instrument table
    for col, head in zip("ABCDEF", ("Instrument (10-K debt table)", "Maturity", "May 31, 2026 principal (USD millions)",
                                    "Status and source", "August 31, 2026 principal (USD millions)", "Kind")):
        s.text(col, inst_top, head, HEAD)
    heights[inst_top] = 42
    for k, row in enumerate(instruments):
        rr = inst_first + k
        s.text("A", rr, row["label"])
        if row["maturity"]:
            s.day("B", rr, row["maturity"])
        s.number("C", rr, row["principal_may_31"])
        source = (f"{row['status']}. {row['principal_tag']} context {row['principal_context']}"
                  + (f"; maturity context {row['maturity_context']}" if row["maturity_context"] else "")
                  + f"; {op.ANNUAL['accession']}.")
        if row["member"] == op.COMMERCIAL_PAPER:
            source = "Unavailable at August 31: no balance or maturity dates reported. " + source
        s.text("D", rr, source, WRAP)
        heights[rr] = 42
        if row["member"] == op.TERM_LOAN:
            s.formula("E", rr, f"C{tl_aug}", row["principal_aug_31"])
        elif row["status"] == "Carried forward":
            s.formula("E", rr, f"C{rr}", row["principal_aug_31"])
        elif row["status"] == "Matured":
            s.formula("E", rr, f"C{rr}-C{rr}", 0)
        s.text("F", rr, row["kind"].replace("Fixed-rate senior notes", "Senior notes").replace("Floating-rate senior notes", "Senior notes"))
    s.text("A", inst_last + 1, "Source: " + op.ANNUAL["source_url"], NOTE)
    return s.xml(heights), inst_last + 1


if __name__=="__main__":
    raise SystemExit("Use python tests/offline/build_workbooks.py; principal cells are part of that build.")
