# Nano Banana Pro JSON

Advanced image generation skill for Claude Code using Google's Gemini 3 Pro Image API. Extends the original `nano-banana-pro` skill with structured JSON configuration, style presets, photorealistic enhancement, and WebP output.

## Requirements

- Python 3.10+
- [UV](https://docs.astral.sh/uv/) package manager
- `GEMINI_API_KEY` environment variable (or pass via `--api-key`)

Dependencies (`google-genai`, `pillow`) are auto-installed by UV via inline script metadata.

## Quick Start

```bash
# Simple prompt (backward compatible with original skill)
uv run ~/.claude/skills/nano-banana-pro-json/scripts/generate_image.py \
  --prompt "A cat on a windowsill" --filename "cat.png"

# With a style preset
uv run ~/.claude/skills/nano-banana-pro-json/scripts/generate_image.py \
  --prompt "portrait of a musician" --filename "portrait.webp" \
  --style-preset cinematic --webp

# With JSON config
uv run ~/.claude/skills/nano-banana-pro-json/scripts/generate_image.py \
  --prompt "mountain landscape" --filename "landscape.webp" \
  --json-config '{"style_parameters":{"camera":{"focal_length":"24mm"}}}' --webp
```

## CLI Reference

| Flag | Short | Description |
|------|-------|-------------|
| `--prompt` | `-p` | Image description (required) |
| `--filename` | `-f` | Output filename (required) |
| `--input-image` | `-i` | Source image for editing mode |
| `--resolution` | `-r` | `1K` (default), `2K`, or `4K` |
| `--api-key` | `-k` | Gemini API key |
| `--json-config` | `-j` | JSON file path or inline `{...}` string |
| `--style-preset` | `-s` | Named style preset |
| `--aspect-ratio` | `-a` | `1:1`, `4:3`, `16:9`, `9:16`, `3:2`, `2:3` |
| `--photorealistic` | | Inject quality markers (8k, ultra-sharp, etc.) |
| `--webp` | | Force WebP output |
| `--quality` | | JPEG/WebP quality 1-100 (default 80) |

## Style Presets

| Preset | Camera | Lighting | Look |
|--------|--------|----------|------|
| `photorealistic-studio` | Sony A7III, 85mm f/1.4 | Studio three-point, 5500K | Professional headshot |
| `nostalgic-film` | Film 35mm f/2.8 | Direct flash, warm 3800K | 1990s snapshot aesthetic |
| `cinematic` | Kodak Portra 400, 50mm f/1.8 | Golden hour, 3200K | Film grain, bokeh |
| `high-fashion` | DSLR 85mm f/2.0 | Dramatic flash, cool 5000K | Editorial, bold |
| `anime-hyperrealistic` | Portrait 85mm f/1.4 | Spotlight, cool 6500K | Anime-inspired |

## JSON Configuration

All fields are optional. Provide only what you want to control.

```json
{
  "consistency_id": "character name",
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
    "format": "webp"
  }
}
```

When combined with a `--style-preset`, the preset provides defaults and JSON overrides specific fields via deep merge.

## How It Works

The JSON configuration and style presets are **prompt-engineering layers**, not native API features. The structured config is serialized into natural-language prompt text before being sent to the Gemini API. For example, camera settings become `"Shot on DSLR Sony A7III 85mm, f/1.4, ISO 100"` appended to your prompt.

WebP output is also a conversion layer -- the Gemini API returns PNG/JPEG, and PIL converts to WebP with configurable quality.

## Precedence Rules

1. **Prompt:** `--prompt` CLI always wins over JSON `prompt` field
2. **Format:** `--webp` > JSON `output_settings.format` > filename extension > PNG
3. **Aspect ratio:** `--aspect-ratio` CLI > JSON `output_settings.aspect_ratio`
4. **Style:** Preset defaults + JSON overrides (deep merge)
5. **Photorealistic:** Additive, appended regardless of other settings

## File Structure

```
nano-banana-pro-json/
  README.md          # This file
  SKILL.md           # Claude Code skill definition
  scripts/
    generate_image.py  # Main script
```

## Relationship to nano-banana-pro

This skill is a **superset** of the original `nano-banana-pro`. Simple prompt-only usage produces identical results. The original skill remains available separately for basic generation without the additional options.
