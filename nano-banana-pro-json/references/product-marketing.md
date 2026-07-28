# Product & marketing images

A recipe for **product and marketing imagery** — hero shots, e-commerce catalog images, lifestyle
scenes, and ad creative — with `generate_image.py`. This is photographic (unlike the logo recipe),
so the camera/lighting presets *help* here. What the presets don't carry, and what this recipe adds,
is the product-specific discipline: e-commerce technical specs, **consistency across a shot set**,
on-image text, and — the load-bearing part — **honesty about a real product's appearance**.

## Two paths — pick first

- **Create from a description** *(the common case)* — you're generating a product/scene from scratch
  (a concept product, a generic hero, an ad background). Full creative freedom; accuracy only has to
  satisfy *you*.
- **Preserve an existing product** *(you have a real photo)* — pass the real product with
  `--input-image` and hold its exact appearance while you change the scene. Accuracy must satisfy
  *reality* — see the boundary at the bottom.

## Step 1 — Brief

- **Product** — what it is, and the **key visual attributes that must be depicted accurately**
  (shape, color, material, label text, distinctive features). This list is what you'll protect.
- **Shot type** — *hero* (product isolated, aspirational), *catalog* (clean, spec-accurate),
  *lifestyle* (product in a real use context), or *ad creative* (product + message + space for copy).
- **Scene & mood** — background (seamless studio sweep vs. a real environment), surface, props,
  season/time-of-day, and the feeling (premium, warm, clinical, energetic).
- **Lighting** — reuse a style preset (`photorealistic-studio` for clean catalog, `cinematic` /
  `high-fashion` for hero/lifestyle) or specify it; **note the direction and color temperature so a
  set stays consistent**.
- **Platform** — drives the spec (see Step 2). Amazon main, Shopify PDP, Instagram feed, a banner ad.
- **On-image text** *(if any)* — brand, tagline, price, legal/weight — captured **exactly**, in
  quotes (Step 4).

## Step 2 — Platform specs (e-commerce is stricter than it looks)

Marketplaces reject images that miss these — bake them into the prompt:

- **Catalog / main image:** **pure white `#FFFFFF` background**, product **filling ~70-90% of the
  frame**, centered, no props, soft even lighting, a subtle grounding shadow. Square `1:1`.
- **Detail / PDP:** `3:4` or `4:5`; props and context allowed.
- **Social:** `1:1` (feed) or `9:16` (stories/reels); lifestyle framing, room for text overlay.
- **Ad creative:** leave **negative space** for the headline/CTA; specify where.

```bash
UV="$(command -v uv || ls "$HOME/.local/bin/uv" /opt/homebrew/bin/uv 2>/dev/null | head -1)"
"$UV" run ~/.claude/skills/nano-banana-pro-json/scripts/generate_image.py \
  --prompt "E-commerce catalog hero of a matte-black insulated water bottle, centered, filling ~80% of the frame on a pure white #FFFFFF seamless background, soft even studio lighting with a subtle grounding shadow, crisp product focus, no props." \
  --filename "bottle-catalog-main.png" --style-preset photorealistic-studio --aspect-ratio 1:1 --resolution 2K
```

## Step 3 — Preserve a real product (identity-lock)

When you supply a real product photo, the single most important phrase is an **identity-preservation
anchor** — repeat it in every prompt of the set:

> "**Preserve the product's exact appearance — same shape, proportions, colors, materials, and label
> text. Do not redesign or reinterpret it.** Change only the scene/background as described."

```bash
"$UV" run ~/.claude/skills/nano-banana-pro-json/scripts/generate_image.py \
  --prompt "Place this exact product on a sunlit kitchen counter beside fresh citrus, morning light from the left. Preserve the product's exact appearance — same shape, colors, materials, and label text; do not redesign it." \
  --filename "bottle-lifestyle-kitchen.png" --input-image real-bottle.jpg --aspect-ratio 4:5 --resolution 2K
```

## Step 4 — A consistent shot SET (the thing presets alone can't do)

A product line needs images that look like *one* shoot. The formula: **lock the fixed elements, vary
only one thing.**

- **Fixed across the set:** lighting direction + color temperature, camera angle + lens, background
  treatment, product framing/scale. State them identically each run (or in a shared `--json-config`).
- **Variable:** the background/scene (Step 3), OR a **single controlled element** — "change **only**
  the bottle color to sage green; keep the shape, label, lighting, angle, and framing identical."
- Generate the set, then lay them side by side and cull anything that drifted in light or scale.

## Step 5 — On-image text

Nano Banana Pro renders text well, but only what you pin down:

- Put exact copy **in quotes**: brand `"Aventer"`, tagline `"carry less, drink more"`, price `"$34"`.
- Name where it sits and keep it short. **Verify spelling** in the output — and never put a
  **fabricated** price, spec, or claim on a real product's image.

## Step 6 — Evaluate

- **Accuracy** — for a real product, does the render match reality (no invented details, no altered
  label)? For a concept, is it internally consistent?
- **Appeal & platform fit** — does it meet the platform spec (white bg / aspect / product scale)?
- **Text** — spelling correct, nothing fabricated.
- **Set consistency** — do the variants read as one shoot?

Iterate with `--input-image` one change at a time (same discipline as the logo recipe).

## What it does NOT do (read this for real products)

- **It is not a photograph of your actual product.** In create-mode it invents a plausible product;
  in preserve-mode it can still subtly alter details. **For a real SKU you're selling, verify the
  render against the physical product** and don't ship a marketing image that misrepresents it.
- **No fabricated claims.** Don't render invented prices, ingredients, certifications, "clinically
  proven," or regulatory/label text onto a real product — that's deceptive, and often illegal
  (food, cosmetics, supplements have strict labeling rules). Where accuracy is legally required, use
  real product photography.
- **No counterfeit or brand-impersonation imagery** — don't reproduce another company's product,
  logo, or trade dress.

---

*Product-photography prompting patterns adapted from [sureprompts.com](https://sureprompts.com/blog/nano-banana-product-photography-prompts),
[apiyi.com](https://help.apiyi.com/en/ecommerce-product-photo-prompt-templates-nano-banana-en.html),
and Google's [Nano Banana prompting guide](https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-nano-banana).*
