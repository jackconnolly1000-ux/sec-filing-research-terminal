# General research Excel record

Roadmap item 18. The experimental general-research download now opens on a Research record
cover and retains all existing Market data, Findings, 8-K events, Evidence and Filing review
records. Data adds the retained SEC component facts; About explains units, colors and limits.
The individual LLY/ORCL/VST checked exports and optional summary are unchanged.

## Reading the record

- Dollar amounts are numeric whole USD displayed in millions. Share prices retain dollars
  per share. Fractions display as percentages and multiples as x. Units remain explicit.
- Yahoo data retains its field, retrieval time and period, including Period not stated.
  SEC calculations retain their TTM end, tags and filing versions. A Yahoo margin and a
  SEC margin are separate observations; they may use different periods and definitions.
- SEC results link to reported components in Data. TTM equals annual plus current YTD less
  prior YTD. Margin and FCF formulas use those same components. The cache must reconcile
  to the saved result before export. Old saved profiles without components retain an
  explicit formula-unavailable note. No missing input is replaced by zero.
- Findings preserve catalysts, risks, implications, source periods, excerpt checks and
  unsupported-figure flags. A source filing's period does not establish the period of every
  narrative number. This layout change does not complete roadmap item 17's narrative audit.
- Source URL cells have native links to the displayed URL. Missing URLs are explicitly
  identified. Source period dates are typed Excel dates. Narrative remains literal text,
  including text beginning with an equals sign.

## Layout and reproduction

The layout uses Arial 10, wrapped text, column widths appropriate to the field, frozen table
headers and light structural borders with faint vertical separators. Gridlines are hidden.
Blue numeric text marks retained inputs; formulas linking to Data are green. There are no
editable scenario assumptions in this record. Wide narrative tables retain one row per record
and require horizontal scrolling; the original source/detail fields are not discarded.

`research_export.py` assembles records and hydrates the checked template using standard-library
OpenXML. Streamlit does not require Node. The app reloads the module before use and keeps
the reviews accessible if the export layout or calculation inputs cannot be validated.

To rebuild, copy `tests/offline/build_research_template.mjs` and `workbook_style.mjs` to an OS
temporary directory with the bundled Artifact Tool runtime. Run the copied builder with the
repository path and an output directory. It writes `samples/research_template.xlsx` and its
manifest, then generates the archived AAPL/STRL record, recalculates it, changes/restores a
source input to verify dependency calculation, scans errors and renders all eight sheets.
Runtime hydration preserves the authored styles and attaches exact source hyperlinks.

Five new tests check preserved figures and headlines, formula/cache reconciliation, source
links and dates, missing versus zero, inconsistent-input refusal, legacy records, literal
narrative text and template fingerprint refusal. Desktop Excel is unavailable in the hosted
environment; native desktop recalculation is not claimed. No paid AI calls are required.
