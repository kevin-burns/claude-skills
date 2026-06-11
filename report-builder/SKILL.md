---
name: report-builder
description: Build self-contained, single-page HTML reports and dashboards from data using Python + Jinja2 + Bootstrap 5 with Chart.js or Plotly. Use whenever the task is to produce an HTML report, data dashboard, metrics page, status page, or any single-file web artifact rendered from data — even if the user only says "report", "dashboard", "summary page", "visualize this", or hands you a CSV/DataFrame/JSON and wants it shown. Covers the render harness (Jinja2 autoescape discipline, passing data to JS safely with tojson), the Chart.js-vs-Plotly decision, Bootstrap 5 layout, and producing a portable single file. Pairs with markdown-converter (to ingest source docs) and is read by code-builder when it implements front-end report work.
license: MIT
---

# Report Builder

The job is almost always the same shape: **data in → one HTML file out**, rendered by a
template, viewable by double-clicking with no server. Keep that shape and the work stays
small and reproducible. The two failure modes to design against are (1) non-determinism
(charts that fetch live, timestamps that drift) and (2) unsafe data interpolation (raw
values dropped into HTML or `<script>`). Both are solved below.

## The pattern

```
data (CSV / DataFrame / JSON)
   └─ your prep code (pandas, optional)  →  a plain JSON "context"
        └─ Jinja2 template (.html.j2)    →  scripts/render.py
             └─ one self-contained report.html
```

Separate **prep** (project-specific, may use pandas) from **render** (generic, reusable).
`scripts/render.py` is the generic half — point it at a template and a JSON context file
and it emits HTML. Don't rewrite it per project.

```bash
uv run report-builder/scripts/render.py \
  --template my_report.html.j2 \
  --data context.json \
  --out report.html --title "Q2 Cost Report"
```

Use `uv run` (PEP 723 inline deps live in `render.py`) — never bare `python`.

## Two rules that prevent the common bugs

1. **Autoescape stays ON.** `render.py` enables it and uses `StrictUndefined`, so a typo'd
   variable fails loudly instead of rendering blank, and text values can't inject markup.
   Only reach for `| safe` on content **you** generated and trust (e.g. a Markdown→HTML
   block you produced). Never `| safe` on data that originated from a user, a file, or an
   API.
2. **Pass data to JavaScript with `| tojson`, never string-building.** To hand a dataset to
   Chart.js/Plotly, serialize it in the template:
   ```html
   <script>
     const chartData = {{ data | tojson }};   {# safe: escapes </script>, quotes, unicode #}
   </script>
   ```
   This is correct *and* XSS-safe. Building JS by concatenating values is the classic
   injection hole — don't.

## Chart.js or Plotly — pick per report

| Use **Chart.js** when | Use **Plotly** when |
|---|---|
| Standard charts: bar, line, pie, doughnut, radar | Interactive exploration: zoom, pan, rich hover, selection |
| Small bundle, fast, dashboard-y look | Statistical/scientific: box, violin, heatmap, 3D, contour |
| Few hundred → few thousand points | Large datasets, or users will drill into the data |
| You want a clean default aesthetic with little config | You need subplots, dual axes, or precise scientific layout |

Default to **Chart.js** for status/metrics dashboards; reach for **Plotly** when the reader
needs to *interrogate* the data, not just read it. Don't load both unless a report truly
needs each.

## Self-contained vs. CDN

- **CDN** (default for internal/online reports): Bootstrap 5, Chart.js, Plotly via
  `<script src="https://cdn...">`. Smallest file, but needs network at view time.
- **Vendored / inline** (for portable, air-gapped, or archived reports): download the libs
  and inline them, or commit them next to the report. Choose this when the report must open
  with no network, or must look identical years later. State which mode you chose in the
  report's provenance footer.

The starter template (`assets/report-template.html.j2`) uses CDN with the swap point
marked. Pin a major version in the URL; **verify the current version** rather than guessing
a patch number (see Fact-discipline).

## Layout with Bootstrap 5

Lean on the grid and components instead of hand-rolling CSS:
- Page frame: a `container`/`container-fluid`, a header row, then `row`/`col-*` for content.
- KPIs: `card` components in a responsive `row-cols-1 row-cols-md-3` grid.
- Tables: `<table class="table table-sm table-striped">`; for long tables, wrap in
  `table-responsive`.
- Keep custom CSS to a small `<style>` block for things Bootstrap doesn't cover (chart
  container heights, print tweaks). Don't fight the framework.

## Reproducibility (so the same data gives the same report)

- Pass any "generated at" timestamp **in** via the context (`--data`), don't call
  `datetime.now()` inside the template — that way a re-render of the same inputs is
  byte-stable, and tests can assert on output.
- Record provenance in a footer: source of the data, the render command, lib versions/mode
  (CDN vs vendored). A report a reader can't trace is a report they can't trust.

## Fact-discipline (library versions & APIs)

Don't assert a current Bootstrap/Chart.js/Plotly version or a chart-config field from
memory — these drift. Confirm the version and the option name before pinning:

```bash
# resolve then fetch — see the c7search skill (avoid `ask`)
LIB=$(c7search resolve --library-name "chart.js" "bar chart options" --json --limit 1 | jq -r '.[0].id')
c7search docs "$LIB" --topic "bar chart options" --tokens 3000
```

Or check the official docs/CDN. If you can't verify, leave the version as a clearly-marked
placeholder rather than inventing a number. (Defer to the `fact-verifier` agent when a
version gates the build.)

## Files in this skill

- `scripts/render.py` — generic Jinja2 renderer (autoescape + StrictUndefined; PEP 723
  inline deps; `uv run`-ready). Reuse it; don't reinvent it.
- `assets/report-template.html.j2` — starter: Bootstrap 5 frame, KPI cards, a Chart.js
  example wired through `| tojson`, a data table, and a provenance footer. Copy and adapt.

## Quick start

1. Copy `assets/report-template.html.j2` into the project; adapt the markup.
2. Write a small prep step that produces a JSON context (`{"title": ..., "kpis": [...],
   "chart": {...}, "rows": [...], "generated_at": "...", "provenance": {...}}`).
3. `uv run report-builder/scripts/render.py --template <tpl> --data <ctx.json> --out report.html`.
4. Open `report.html`. Verify chart renders, table populates, no `Undefined` errors.
