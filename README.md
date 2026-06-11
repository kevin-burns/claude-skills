# claude-skills

A small collection of [Claude Code](https://claude.com/claude-code) skills I build and maintain, kept here so they can be versioned and shared openly. Each skill lives in its own directory with a `SKILL.md`; some bundle scripts or reference files.

All skills here are MIT licensed (see [`LICENSE`](./LICENSE)). Skills that wrap an external tool or service carry a **Provenance** note in their `SKILL.md` crediting the upstream project and its license — the MIT license covers the skill content, not the wrapped tools.

## Skills

| Skill | What it does | Wraps |
|---|---|---|
| [clear-and-human](./clear-and-human) | Construct, review, score, and rewrite prose so it reads human, not AI | — |
| [hook-and-human](./hook-and-human) | Write, punch up, and review persuasive marketing copy without fabricating | — |
| [c7search](./c7search) | Fetch up-to-date library docs via the `c7search` CLI | [Context7](https://context7.com) API |
| [markdown-converter](./markdown-converter) | Convert PDF/Office/HTML/media files to Markdown | [markitdown](https://github.com/microsoft/markitdown) (MS, MIT) |
| [nano-banana-pro-json](./nano-banana-pro-json) | Generate and edit images with structured JSON control | Google Gemini image API |
| [convert-to-webp](./convert-to-webp) | Convert images to WebP for web projects | [libwebp](https://developers.google.com/speed/webp) `cwebp` / macOS `sips` |
| [social-image-prep](./social-image-prep) | Resize and format images for social platforms | `sips` / [ImageMagick](https://imagemagick.org) / [Pillow](https://python-pillow.org) |
| [terragrunt-skill](./terragrunt-skill) | Generate, validate, review, and debug Terragrunt 1.x configs across AWS/Azure/GCP | — |

## Install

Symlink any skill into your personal skills directory:

```bash
ln -s "$(pwd)/clear-and-human" ~/.claude/skills/clear-and-human
```

Symlinking (rather than copying) keeps this repo the single source of truth — edits here are picked up immediately.

### Requirements per skill

- **c7search** — the `c7search` binary (`go install github.com/kevin-burns/c7search@latest`). A `CONTEXT7_API_KEY` is optional.
- **markdown-converter** — `uv` (uses `uvx markitdown`, no install needed).
- **nano-banana-pro-json** — `uv` and a `GEMINI_API_KEY` environment variable. No key is bundled.
- **convert-to-webp** — `cwebp` (`brew install webp`) or macOS `sips`. No install needed on macOS.
- **social-image-prep** — `sips` (macOS), ImageMagick, or `uv` (for the Pillow fallback). Uses whichever is present.
- **terragrunt-skill** — works as static review with no tooling; the bundled `scripts/validate.sh` uses `terragrunt` (1.0.x), plus optional `tflint` and `trivy` if present. `scripts/detect_custom_resources.py` runs on Python 3.
