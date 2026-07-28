# Logos & brand identity

A recipe for generating **logo and brand-identity marks** with `generate_image.py`. Logos are the
opposite of the skill's default photography style — flat, iconic, scalable — so the value here is a
brand brief and logo-appropriate prompting, not a camera profile. The generator does the image call;
this guide shapes what you ask it for.

**Read the boundary first (it's the point):** the generator outputs a **raster** image (PNG/WebP),
not production vector art. It's for *concepting and direction*. But you don't have to stop at raster
— **Step 5 traces the winner to a real SVG for free**, which is exactly the step every paid logo
tool (Looka, Tailor Brands, Brandmark, Banana2) charges for. This does **not** do trademark
clearance or confirm font licensing — run an originality/trademark check and verify any font's
license before shipping. And text in generated logos can be imperfect: verify a wordmark's spelling
and expect to finalize the typography in real type.

## Step 1 — Take the brand brief

Ask for these (assume-and-state if the user wants a quick pass):

- **Brand name** — exact spelling and capitalization.
- **Industry / what it does** — one line (fintech, specialty coffee, cybersecurity, kids' app…). Anchors the visual language.
- **Personality** — 3-5 adjectives (e.g. "warm, trustworthy, modern" vs "bold, edgy, technical"). This drives the look more than anything.
- **Color leanings** — any must-have or must-avoid colors; else propose a small palette that fits the personality.
- **Logo type** — one of:
  - *wordmark* (the name styled, e.g. Google) — text-heavy, highest AI-text risk;
  - *lettermark / monogram* (initials, e.g. IBM);
  - *icon/symbol* (a mark, no text, e.g. Apple) — safest and most reliable to generate;
  - *combination* (icon + name); *badge/emblem*; *mascot*; *app icon*.
- **Icon concept** *(optional)* — a specific symbol direction if they have one ("a stylized coffee bean", "an abstract upward arrow"). If not, propose 2-3 concepts before generating.
- **Typography feel** *(for word/combination marks)* — geometric, humanist, rounded, techy, serif/classic — so the letterforms match the personality.
- **One-color requirement** — confirm it must also work in a single flat color (it should); this shapes the prompt away from color-dependent tricks.
- **Where it'll live** — app icon, website header, print, favicon — affects how simple it must stay.

## Step 2 — Construct a logo-appropriate prompt

Translate the brief into a prompt that pushes *toward* logo qualities and *away* from the skill's
default photorealism:

- **Steer toward:** "flat vector logo", "minimal", "clean", "simple geometric shapes", "strong
  silhouette", "generous negative space", "scalable", "solid fills", a **limited palette** (name the
  1-3 colors), "on a plain white background".
- **Steer away from (state these explicitly):** photorealism, 3D rendering, gradients (unless the
  brand wants them), drop shadows, glossy/bevel effects, fine intricate detail, busy backgrounds,
  and literal-cliché objects (a lightbulb for "ideas", a globe for "global"). Depth and detail are
  what make a mark fail when it's shrunk to a favicon.
- **Integrate the symbol, don't just place it.** The biggest quality jump comes from telling the
  model *how* two elements combine, not just that they co-exist. "Add a lightning bolt to a bike"
  floats a disconnected bolt; "**integrate a lightning bolt into the bicycle's frame structure**"
  makes it read as one mark. Name the relationship (negative-space cut-out, formed-from, wraps-around).
- **State the technical specs the model drops if you don't** — "consistent thick outlines" (else it
  renders spindly), "high contrast", "recognizable at 32px", "no small interior details" — these are
  what keep it a *logo* rather than an illustration.
- For **icon-only marks, end the prompt with "Render just the logo symbol. No text."** — this both
  gives a clean symbol and sidesteps the AI-text-garbling problem. For **wordmarks/combination
  marks**, keep the name short and treat the text as provisional — spelling/kerning gets finalized in
  real type.

A good skeleton:
> "Flat vector logo for **[name]**, a **[industry]** brand. Style: **[adjectives]**, **[minimalist
> line-art / bold geometric / hand-drawn]**. Main element: **[element]**; integrate **[symbolic
> element]** *into* it to mean **[what it says about the brand]**. Palette: **[1-3 colors + why]**.
> Consistent thick outlines, high contrast, no gradients/3D/shadows, recognizable at 32px. Centered
> on a plain white background. [Render just the logo symbol. No text.]"

## Step 3 — Generate a small set

- Use **`--aspect-ratio 1:1`** and **`--resolution 2K`**. Do **not** use a photographic
  `--style-preset` or `--photorealistic` — those fight the flat aesthetic.
- Generate **3-4 variants**, varying the *concept or style* between runs (a symbol option, a
  monogram option, a more geometric vs. more organic take) rather than re-rolling the same prompt.
  Name them so they're easy to compare.
- **Be generous with volume — it's the user's own API key, so there's no per-logo fee.** Keepers are
  rare (expect ~1-2 you like per 8-10 generated), so batch freely. A high-leverage move: ask the
  model to expand "name + what it does + personality" into **5 distinct logo prompts** first, then
  generate from all five — cheap here, metered/paywalled on commercial tools.

```bash
UV="$(command -v uv || ls "$HOME/.local/bin/uv" /opt/homebrew/bin/uv 2>/dev/null | head -1)"
"$UV" run ~/.claude/skills/nano-banana-pro-json/scripts/generate_image.py \
  --prompt "Flat vector logo for Chaptr, a podcast-tools brand. Style: modern, friendly, technical. An abstract chapter-marker bookmark forming a play triangle. Minimal, clean, strong silhouette, generous negative space, scalable. Palette: deep indigo and warm coral. Solid flat shapes, no gradients, no 3D, no shadows, no photorealism. Centered on a plain white background." \
  --filename "logo-chaptr-v1-bookmark.png" --aspect-ratio 1:1 --resolution 2K
```

Repeat with varied concepts (`-v2-monogram`, `-v3-geometric`, …).

## Step 4 — Evaluate like a designer, then iterate

Run each candidate through the proof checklist that separates a logo from a picture:

- **Monochrome test** — would it survive in one flat color? A mark that only reads because of color
  or shading is a weak logo.
- **Small-size / favicon test** — still legible at ~16-32px? Kill anything fiddly.
- **Spelling** — on word/combination marks, confirm the text is exactly right (AI text slips).
- **Originality** — does it accidentally resemble a well-known logo or look like a generic template?
  Push for one memorable, distinct idea.
- **On-brief** — does it actually carry the personality adjectives?
- **Context test** — this skill's photorealistic side is perfect for it: feed the finalist back in
  (`--input-image logo-winner.png` + a scene prompt) and mock it up on a storefront sign, a phone
  app icon, a business card, a night billboard. If a mockup ignores your mark and renders a
  placeholder, tell it explicitly to *"use the uploaded logo exactly."* A logo that holds up across
  these scenes is a real logo.

Iterate on a winner with **image-to-image editing** (`--input-image logo-...png` + a change
instruction) — **one change at a time**, and use masking language to protect what works
("keep the symbol exactly; only adjust the wordmark spacing"). If the model stops cooperating after
~3 edits, start fresh: re-run with the latest image as the new `--input-image`. Then vectorize it
(Step 5).

## Step 5 — Vectorize the winner (this is the wedge)

The generator gives you a raster. Production logos need **vector (SVG)** — infinitely scalable, tiny
files, editable paths. Every paid logo tool charges for this exact step; here it's free and local.
Flat, high-contrast logo art traces cleanly:

```bash
# Color logos — vtracer handles multi-color flat art (brew install vtracer, or cargo install vtracer)
vtracer --input logo-chaptr-v1-icon.png --output logo-chaptr-v1-icon.svg --mode polygon

# One-color / monochrome marks — potrace (brew install potrace imagemagick):
magick logo-mono.png -threshold 55% logo-mono.pbm      # bitmap
potrace logo-mono.pbm -s -o logo-mono.svg              # -s = SVG output
```

Open the SVG, sanity-check the paths (simplify stray nodes, re-set exact brand colors, and rebuild
any text as real type rather than traced outlines — traced letters aren't editable text). That's a
production-ready logo, from a free recipe.

## A note on reference images

It's tempting to feed an existing logo you admire and ask for "something like it." Don't copy —
most logos are trademarked, and generating a lookalike is a legal and ethical problem. Use
references only for *style/geometry inspiration* and only public-domain / CC0-licensed material.
And a logo generated here is a starting point, not a cleared brand asset: it is **not** a substitute
for a professional designer or for trademark clearance.

---

*Prompting techniques here draw on practitioner write-ups by [theusableai.com](https://www.theusableai.com/mastai-generated-logo-design/)
and [yingtu.ai](https://yingtu.ai/en/blog/nano-banana-logo-generator), adapted to this skill's CLI workflow.*
