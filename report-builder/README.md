# report-builder

Data in, **one self-contained HTML file** out — rendered by a Jinja2 template, openable by
double-clicking, no server.

Part of [claude-skills](../README.md).

## What it does

Keeps the job in one shape, so it stays small and reproducible:

```
data (CSV / DataFrame / JSON)
   └─ your prep code (pandas, optional)  →  a plain JSON "context"
        └─ Jinja2 template (.html.j2)    →  scripts/render.py
             └─ one self-contained report.html
```

The separation is the point. **Prep** is project-specific and may use pandas. **Render**
is generic: `scripts/render.py` takes a template and a JSON context and emits HTML. Don't
rewrite it per project.

```bash
rbuild --template my_report.html.j2 --data context.json \
       --out report.html --title "Q2 Cost Report"
```

`assets/report-template.html.j2` is a working starter: Bootstrap 5 frame, KPI cards, a
Chart.js example wired correctly, a data table, and a provenance footer.

## The two failure modes it designs against

**Unsafe interpolation.** Autoescape stays **on**, with `StrictUndefined` — so a typo'd
variable fails loudly instead of rendering blank, and text values cannot inject markup.
Reach for `| safe` only on content *you* generated and trust; never on data from a user, a
file or an API. To hand a dataset to a chart library, serialise it in the template:

```html
<script>const chartData = {{ data | tojson }};</script>
```

That escapes `</script>`, quotes and unicode correctly. Building JS by concatenating
values is the classic injection hole.

**Non-determinism.** Pass any "generated at" timestamp *in* via the context rather than
calling `datetime.now()` inside the template. Re-rendering the same inputs is then
byte-stable, and tests can assert on the output. Record provenance in a footer — data
source, render command, library versions and whether you used CDN or vendored assets. A
report a reader cannot trace is a report they cannot trust.

## Choosing a chart library

| Chart.js | Plotly |
|---|---|
| Bar, line, pie, doughnut, radar | Zoom, pan, rich hover, selection |
| Small, fast, dashboard-y | Statistical and scientific: box, violin, heatmap, 3D |
| Hundreds to a few thousand points | Large datasets, or readers who will drill in |

Default to Chart.js for status and metrics dashboards; reach for Plotly when the reader
needs to *interrogate* the data rather than read it. Don't load both unless a report truly
needs each.

**CDN or vendored** is a per-report decision. CDN gives the smallest file but needs network
at view time. Vendor and inline the libraries when the report must open air-gapped, or look
identical years from now. State which you chose in the provenance footer.

## What it does NOT do

- **It does not analyse your data.** It renders what you give it. Deciding what the numbers
  mean is prep work, and prep is yours.
- **It does not build multi-page sites or apps.** One page, one file, no server, no router.
- **It does not fetch anything at view time by default** — and where a report does (CDN
  assets), that is a deliberate, recorded choice.
- **It does not assert library versions from memory.** Bootstrap, Chart.js and Plotly
  versions and option names drift. Verify before pinning; leave a clearly-marked
  placeholder rather than inventing a number.

## Requirements

`uv` is **required**, not optional — `render.py` has PEP 723 inline dependencies (jinja2),
so a bare `python` will fail on the missing package. Run it by **absolute path**; a
relative `report-builder/scripts/render.py` will not resolve from another repo.
[`SKILL.md`](./SKILL.md) has the `rbuild` function recipe and explains why it is a function
rather than a variable.

## A note on `evals/`

`evals/grade.py` here is **not** an offline behavioural eval — it scores generated
skill-creator eval runs, reading a `report-builder-workspace/iteration-N/` directory that
is gitignored. It is skipped in CI by an explicit marker for exactly that reason. Don't
expect `uv run evals/grade.py` to verify the skill.
