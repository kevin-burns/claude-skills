# Logos & brand identity

A recipe for generating **logo and brand-identity marks** with `generate_image.py`. Logos are the
opposite of the skill's default photography style — flat, iconic, scalable — so the value here is a
brand brief and logo-appropriate prompting, not a camera profile. The generator does the image call;
this guide shapes what you ask it for.

**Read the boundary first (it's the point):** the output is a **raster** image (PNG/WebP), not
production vector art. It's for *concepting and direction* — pick a winner, then trace it to SVG
(Illustrator's Image Trace, Inkscape, or an auto-tracer) for real use. This does **not** do
trademark clearance, and text in generated logos can be imperfect — verify any wordmark's spelling
and expect to redo the typography properly.

## Step 1 — Take the brand brief

Ask for these (assume-and-state if the user wants a quick pass):

- **Brand name** — exact spelling and capitalization.
- **Industry / what it does** — one line (fintech, specialty coffee, cybersecurity, kids' app…). Anchors the visual language.
- **Personality** — 3-5 adjectives (e.g. "warm, trustworthy, modern" vs "bold, edgy, technical"). This drives the look more than anything.
- **Color leanings** — any must-have or must-avoid colors; else propose a small palette that fits the personality.
- **Logo type** — one of:
  - *wordmark* (the name styled, e.g. Google) — text-heavy, highest AI-text risk;
  - *lettermark* (initials/monogram, e.g. IBM);
  - *icon/symbol* (a mark, no text, e.g. Apple) — safest and most reliable to generate;
  - *combination* (icon + name).
- **Icon concept** *(optional)* — a specific symbol direction if they have one ("a stylized coffee bean", "an abstract upward arrow"). If not, propose 2-3 concepts before generating.
- **Where it'll live** — app icon, website header, print — affects how simple it must stay.

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
- For **wordmarks/combination marks**, keep the name short in the prompt and treat the text as
  provisional — call out that spelling/kerning will be finalized in real type.

A good skeleton:
> "Flat vector logo for **[name]**, a **[industry]** brand. Style: **[adjectives]**. **[icon concept]**.
> Minimal, clean, strong silhouette, generous negative space, scalable. Palette: **[colors]**. Solid
> flat shapes, no gradients, no 3D, no shadows, no photorealism. Centered on a plain white background."

## Step 3 — Generate a small set

- Use **`--aspect-ratio 1:1`** and **`--resolution 2K`**. Do **not** use a photographic
  `--style-preset` or `--photorealistic` — those fight the flat aesthetic.
- Generate **3-4 variants**, varying the *concept or style* between runs (a symbol option, a
  monogram option, a more geometric vs. more organic take) rather than re-rolling the same prompt.
  Name them so they're easy to compare.

```bash
UV="$(command -v uv || ls "$HOME/.local/bin/uv" /opt/homebrew/bin/uv 2>/dev/null | head -1)"
"$UV" run ~/.claude/skills/nano-banana-pro-json/scripts/generate_image.py \
  --prompt "Flat vector logo for Chaptr, a podcast-tools brand. Style: modern, friendly, technical. An abstract chapter-marker bookmark forming a play triangle. Minimal, clean, strong silhouette, generous negative space, scalable. Palette: deep indigo and warm coral. Solid flat shapes, no gradients, no 3D, no shadows, no photorealism. Centered on a plain white background." \
  --filename "logo-chaptr-v1-bookmark.png" --aspect-ratio 1:1 --resolution 2K
```

Repeat with varied concepts (`-v2-monogram`, `-v3-geometric`, …).

## Step 4 — Evaluate like a designer, then iterate

For each candidate, apply the tests that separate a logo from a picture:

- **Monochrome test** — would it survive in one flat color? Generate or imagine it in solid black.
  A mark that only reads because of color or shading is a weak logo.
- **Scalability** — is the silhouette still legible shrunk to a favicon? Kill anything fiddly.
- **Distinctiveness** — does it look like a generic template? Push for one memorable idea.
- **On-brief** — does it actually carry the personality adjectives?

Iterate on a winner with **image-to-image editing** (`--input-image logo-...png` + a change
instruction) rather than starting over — "simplify the mark", "make the negative space cleaner",
"try it in a single color". Then hand the chosen raster off to be traced to vector for production.
