---
name: nano-banana-pro-json
description: Generate and edit images using Google's Nano Banana Pro (Gemini 3 Pro Image) API. Use when the user asks to generate, create, edit, modify, change, alter, or update images. Also use when user references an existing image file and asks to modify it in any way (e.g., "modify this image", "change the background", "replace X with Y"). Supports simple prompts, style presets (cinematic, film, fashion, studio), JSON-configured camera/lighting/composition parameters, photorealistic enhancement, aspect ratios, and WebP output. This is the default image generation skill. DO NOT read image files first - use --input-image parameter directly.
license: MIT
---

# Nano Banana Pro JSON - Advanced Image Generation

Generate and edit images using Google's Nano Banana Pro API with structured JSON control, style presets, and photorealistic enhancement.

## Usage

Run the script using absolute path (do NOT cd to skill directory first):

```bash
uv run ~/.claude/skills/nano-banana-pro-json/scripts/generate_image.py --prompt "description" --filename "output.png" [options]
```

**Important:** Always run from the user's current working directory so images save where the user is working.

**If `uv` isn't found** (`uv: command not found` — non-interactive shells often drop `~/.local/bin` or the Homebrew bin from PATH), resolve it and call it explicitly rather than giving up. This script needs uv (third-party deps: `google-genai`, `pillow`), so plain `python3` is not a fallback here:

```bash
UV="$(command -v uv || ls "$HOME/.local/bin/uv" "$HOME/.cargo/bin/uv" /opt/homebrew/bin/uv /usr/local/bin/uv 2>/dev/null | head -1)"
"$UV" run ~/.claude/skills/nano-banana-pro-json/scripts/generate_image.py --prompt "..." --filename "..."
```

## Simple Mode

Works identically to the original nano-banana-pro skill:

```bash
uv run ~/.claude/skills/nano-banana-pro-json/scripts/generate_image.py --prompt "A serene Japanese garden" --filename "2025-11-23-14-23-05-japanese-garden.png"
```

## Style Presets

Use `--style-preset NAME` to apply a curated camera/lighting/composition profile:

| Preset | Camera | Lighting | Look |
|--------|--------|----------|------|
| `photorealistic-studio` | Sony A7III, 85mm f/1.4 | Studio three-point, 5500K | Professional headshot, clean |
| `nostalgic-film` | Film 35mm f/2.8 | Direct flash, warm 3800K | 1990s aesthetic, grain |
| `cinematic` | Kodak Portra 400, 50mm f/1.8 | Golden hour side light, 3200K | Film grain, bokeh, emotional |
| `high-fashion` | DSLR 85mm f/2.0 | Dramatic flash, cool 5000K | Editorial, bold styling |
| `anime-hyperrealistic` | Portrait lens 85mm f/1.4 | Spotlight, cool 6500K | Anime-inspired, high contrast |

Example:
```bash
uv run ~/.claude/skills/nano-banana-pro-json/scripts/generate_image.py \
  --prompt "portrait of a woman in a garden" \
  --filename "2025-11-23-14-23-05-studio-portrait.png" \
  --style-preset photorealistic-studio
```

## JSON Configuration

Use `--json-config` with a file path or inline JSON string:

```bash
# Inline JSON
uv run ~/.claude/skills/nano-banana-pro-json/scripts/generate_image.py \
  --prompt "mountain landscape" \
  --filename "output.png" \
  --json-config '{"style_parameters":{"camera":{"focal_length":"24mm","aperture":"f/8"}}}'

# File path
uv run ~/.claude/skills/nano-banana-pro-json/scripts/generate_image.py \
  --prompt "mountain landscape" \
  --filename "output.png" \
  --json-config config.json
```

### Full JSON Schema

```json
{
  "prompt": "optional - CLI --prompt always takes precedence",
  "consistency_id": "character name for consistency across generations",
  "style_parameters": {
    "camera": {
      "type": "DSLR",
      "model": "Sony A7III",
      "focal_length": "85mm",
      "aperture": "f/1.4",
      "shutter_speed": "1/200s",
      "iso": "100"
    },
    "lighting": {
      "type": "Studio",
      "setup": "Three-point lighting",
      "direction": "Front-angled key light",
      "color_temperature": "5500K"
    },
    "composition": {
      "framing": "Medium close-up",
      "perspective": "Eye-level",
      "depth_of_field": "Shallow"
    }
  },
  "output_settings": {
    "aspect_ratio": "16:9",
    "format": "png"
  }
}
```

All fields are optional. Only include what you want to control.

## Aspect Ratio

Use `--aspect-ratio` to guide composition (applied as prompt text, not API parameter):

Choices: `1:1`, `4:3`, `16:9`, `9:16`, `3:2`, `2:3`

```bash
uv run ~/.claude/skills/nano-banana-pro-json/scripts/generate_image.py \
  --prompt "cityscape at dusk" \
  --filename "output.png" \
  --aspect-ratio 16:9
```

Can also be set via JSON `output_settings.aspect_ratio`. CLI flag takes precedence.

## Photorealistic Enhancement

Use `--photorealistic` to auto-inject quality markers (8k, ultra-sharp, hyperrealistic, visible pores, natural skin texture, etc.):

```bash
uv run ~/.claude/skills/nano-banana-pro-json/scripts/generate_image.py \
  --prompt "portrait of an elderly fisherman" \
  --filename "output.png" \
  --photorealistic
```

## Combining Options

All options can be combined. Precedence rules:

1. **Prompt:** CLI `--prompt` always wins over JSON `prompt` field
2. **Aspect ratio:** CLI `--aspect-ratio` wins over JSON `output_settings.aspect_ratio`
3. **Style:** Preset provides base defaults, JSON config overrides specific fields via deep merge
4. **Photorealistic:** Additive -- markers are appended regardless of other settings

Example combining everything:
```bash
uv run ~/.claude/skills/nano-banana-pro-json/scripts/generate_image.py \
  --prompt "portrait of a woman on a rooftop at sunset" \
  --filename "2025-11-23-14-23-05-rooftop-portrait.png" \
  --style-preset cinematic \
  --json-config '{"style_parameters":{"camera":{"focal_length":"35mm"}},"consistency_id":"Elena"}' \
  --photorealistic \
  --aspect-ratio 16:9 \
  --resolution 4K
```

## Resolution

The Gemini 3 Pro Image API supports three resolutions (uppercase K required):

- **1K** (default) - ~1024px resolution
- **2K** - ~2048px resolution
- **4K** - ~4096px resolution

Map user requests:
- No mention of resolution -> `1K`
- "low resolution", "1080", "1080p", "1K" -> `1K`
- "2K", "2048", "normal", "medium resolution" -> `2K`
- "high resolution", "high-res", "hi-res", "4K", "ultra" -> `4K`

## API Key

Checked in order:
1. `--api-key` argument
2. `GEMINI_API_KEY` environment variable

## Filename Generation

Generate filenames with the pattern: `yyyy-mm-dd-hh-mm-ss-name.ext`

- Timestamp: Current date/time in `yyyy-mm-dd-hh-mm-ss` (24-hour format)
- Name: Descriptive lowercase text with hyphens
- Extension: `.png` (default), `.jpg`, or `.webp` based on JSON config `output_settings.format`

Examples:
- `2025-11-23-14-23-05-japanese-garden.png`
- `2025-11-23-15-30-12-sunset-mountains.jpg`

## Image Editing

When modifying an existing image:
1. Use `--input-image` with the path to the source image
2. `--prompt` contains editing instructions
3. All style/preset/photorealistic options work with editing too

```bash
uv run ~/.claude/skills/nano-banana-pro-json/scripts/generate_image.py \
  --prompt "make it look like a cinematic film still" \
  --filename "2025-11-23-14-25-30-cinematic-edit.png" \
  --input-image "original-photo.jpg" \
  --style-preset cinematic
```

## Output Formats

Set via JSON config `output_settings.format`, filename extension, or `--webp` flag:

- **png** (default) - Lossless
- **jpg/jpeg** - JPEG (lossy, configurable quality)
- **webp** - WebP (lossy, configurable quality) - converted from Gemini's native PNG/JPEG output via PIL

**WebP notes:** The Gemini API does not natively export WebP. The script receives the image as PNG/JPEG from the API and converts it to WebP using PIL. This adds a negligible conversion step but produces smaller files with good quality.

### WebP convenience flag

Use `--webp` to force WebP output regardless of filename extension:

```bash
uv run ~/.claude/skills/nano-banana-pro-json/scripts/generate_image.py \
  --prompt "sunset over ocean" \
  --filename "2025-11-23-14-23-05-sunset.png" \
  --webp
```

This saves as `2025-11-23-14-23-05-sunset.webp` (extension auto-corrected).

### Quality control

Use `--quality` (1-100, default 80) to control JPEG/WebP compression:

```bash
# High quality WebP
uv run ~/.claude/skills/nano-banana-pro-json/scripts/generate_image.py \
  --prompt "detailed macro photo" \
  --filename "output.webp" \
  --quality 95

# Smaller file size
uv run ~/.claude/skills/nano-banana-pro-json/scripts/generate_image.py \
  --prompt "web thumbnail" \
  --filename "output.webp" \
  --quality 60
```

Quality has no effect on PNG output (always lossless).

### Format precedence

1. `--webp` flag (highest)
2. JSON config `output_settings.format`
3. Filename extension
4. Default: PNG

## Examples

**Simple generation:**
```bash
uv run ~/.claude/skills/nano-banana-pro-json/scripts/generate_image.py \
  --prompt "A cat wearing a tiny hat" \
  --filename "2025-11-23-14-23-05-cat-hat.png"
```

**Studio portrait with preset:**
```bash
uv run ~/.claude/skills/nano-banana-pro-json/scripts/generate_image.py \
  --prompt "professional headshot of a young CEO" \
  --filename "2025-11-23-14-23-05-ceo-headshot.png" \
  --style-preset photorealistic-studio \
  --photorealistic \
  --resolution 4K
```

**Cinematic landscape with custom JSON:**
```bash
uv run ~/.claude/skills/nano-banana-pro-json/scripts/generate_image.py \
  --prompt "misty mountain valley at dawn" \
  --filename "2025-11-23-14-23-05-mountain-dawn.png" \
  --json-config '{"style_parameters":{"camera":{"focal_length":"24mm","aperture":"f/11"},"lighting":{"setup":"Soft diffused dawn light","color_temperature":"4000K warm"}}}' \
  --aspect-ratio 16:9 \
  --resolution 4K
```

**Nostalgic film edit:**
```bash
uv run ~/.claude/skills/nano-banana-pro-json/scripts/generate_image.py \
  --prompt "add warm film grain and a slight vignette" \
  --filename "2025-11-23-14-23-05-nostalgic-edit.png" \
  --input-image "modern-photo.jpg" \
  --style-preset nostalgic-film
```

## Provenance

This skill calls **Google's Gemini image API** ("Nano Banana Pro" / Gemini 3 Pro Image) via the official `google-genai` SDK, and converts output formats with Pillow (PIL). It requires your own `GEMINI_API_KEY` — no key is bundled or stored in the skill. Not affiliated with or endorsed by Google; Google's API terms, pricing, and content policies apply.
