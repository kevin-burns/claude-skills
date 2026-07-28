# Infographics & explanatory diagrams

A recipe for **infographics and explanatory diagrams** — process flows, comparisons, concept
explainers, "anatomy of X" posters — with `generate_image.py`. Like logos, this is a flat/graphic
mode (not photographic), so the camera presets don't apply. Unlike logos, the hard part isn't brand
personality — it's **structure, correct labels, and legibility**. The single biggest risk is the one
this recipe exists to manage: **the model will garble text and invent numbers.** Read the boundary
before you rely on anything it renders.

## The honest scope (decide this first)

- **Great for:** *conceptual/visual* infographics — a process, a comparison, a hierarchy, an
  "anatomy of," a cycle — where **you supply the exact labels** and there's little or no precise data.
- **Wrong tool for:** anything **data-accurate** (real statistics, exact bar/line values, tables). An
  image model can't be trusted with numbers — it will produce plausible-looking wrong ones. For real
  data visualization use the **`report-builder`** skill (real charts from real data). Use this recipe
  for the *look and structure*, not as a source of truth.

## Step 1 — Brief

- **Topic** — the one idea the graphic explains.
- **Audience** — drives complexity and tone (kids vs. execs vs. engineers).
- **Title** — exact words, in quotes, and where it sits.
- **The content that MUST appear, verbatim** — list every label, step name, and number you need,
  spelled exactly. This is the list you'll verify against the output. **Supply real data yourself;
  never let the model invent it.**
- **Visual style** and **layout** — see Steps 2-3.
- **Format** — aspect ratio: `4:5` or `9:16` for a shareable/social infographic, `16:9` for a slide,
  `1:1` for feed.

## Step 2 — Pick a layout that matches the content's shape

The layout should mirror the structure of the idea — this is what makes an infographic *read*:

- **Sequence/process** → horizontal or vertical **timeline / numbered steps**
- **Hierarchy / priorities** → **pyramid** or **iceberg** (visible vs. hidden)
- **One center, many parts** → **hub-and-spoke**
- **A vs. B** → **side-by-side comparison** (two columns) or a **comparison matrix**
- **Narrowing** → **funnel**
- **Parts of a whole / "anatomy of"** → **labeled cross-section / exploded diagram**

## Step 3 — Pick a visual style

Name a concrete style (this is where the aesthetic lives):

- **corporate flat** (clean, minimal, brand colors) — safest for business
- **isometric 3D** (depth, techy)
- **blueprint / schematic** (technical, white-on-blue)
- **paper cut-out** or **hand-drawn** (friendly, editorial)
- **vintage science poster** (detailed, characterful)

## Step 4 — Construct the prompt

Combine topic + layout + style + **exact labels in quotes** + aspect ratio. Put every word you need
rendered in quotes, and state legibility requirements:

```bash
UV="$(command -v uv || ls "$HOME/.local/bin/uv" /opt/homebrew/bin/uv 2>/dev/null | head -1)"
"$UV" run ~/.claude/skills/nano-banana-pro-json/scripts/generate_image.py \
  --prompt "A clean corporate-flat infographic titled \"How Composting Works\", vertical 4-step numbered timeline top to bottom. Steps, in order, with these exact labels: \"1. Collect scraps\", \"2. Layer greens and browns\", \"3. Turn and aerate\", \"4. Harvest compost\". Each step a simple flat icon plus its label. Muted green and earth palette, generous spacing, large legible sans-serif text, plenty of negative space." \
  --filename "composting-infographic.png" --aspect-ratio 4:5 --resolution 2K
```

Tips that materially improve legibility: fewer elements, larger type, one clear reading direction,
and *"large legible text, no tiny labels"* stated explicitly.

## Step 5 — Evaluate (accuracy first, aesthetics second)

- **Proofread every word** against your Step-1 list — the model routinely misspells, drops, or
  duplicates labels. This check is not optional.
- **Verify every number** — if any data appears, confirm it's the real value you supplied, not a
  hallucination. If you didn't supply it, don't trust it.
- **Legibility** — readable at the size it'll be shown? Kill clutter.
- **Structure** — does the layout actually match the idea's shape?

Fix wording/labels by iterating with `--input-image` and masking language ("keep the layout and
icons; correct the label to read exactly 'Turn and aerate'"). Persistent text errors are common — for
a final asset, it's often faster to generate the graphic *without* text and set the type in a real
editor.

## What it does NOT do

- **It is not a data-accurate chart.** It renders the *appearance* of an infographic; it cannot be
  trusted to plot real values or do arithmetic. Supply exact labels/numbers and verify them, and for
  genuine data viz use **`report-builder`** (or a real charting tool), not this.
- **It invents facts if you let it.** Never ask it to "add relevant statistics" — it will fabricate
  convincing ones. Provide the facts; it only lays them out.
- **Text can be imperfect** — always proofread; consider setting final type in an editor.

---

*Infographic style/layout patterns adapted from [controlaltachieve.com — The Ultimate Guide to AI Infographics](https://www.controlaltachieve.com/2025/11/infographics.html)
and Google's [Nano Banana prompting guide](https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-nano-banana).*
