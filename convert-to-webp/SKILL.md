---
name: convert-to-webp
description: Convert images (PNG, JPG, etc.) to WebP format. Use when saving screenshots or images for web projects, Hugo sites, or any context where WebP is preferred.
license: MIT
---

# Convert to WebP

Convert one or more images to WebP format.

## Usage

Arguments: one or more file paths, optionally followed by `--dest <directory>` and/or `--quality <number>`.

Examples:
- `/convert-to-webp /tmp/screenshot.png`
- `/convert-to-webp /tmp/a.png /tmp/b.jpg --dest /path/to/site/static/images`
- `/convert-to-webp /tmp/photo.jpg --quality 90`

## Instructions

First, check which tool is available (run once per session):

1. **`cwebp`** -- best quality control. Install via `brew install webp`
2. **`sips`** -- built into macOS (Monterey+), no install needed. No quality flag for WebP output.

Pick whichever is available. Prefer `cwebp` if both exist.

For each input file:

1. Skip if the file is already `.webp`
2. Determine the output path:
   - If `--dest` is provided, output to that directory with the same filename but `.webp` extension
   - Otherwise, output to the same directory as the input with `.webp` extension
3. Convert:
   - **cwebp**: `cwebp -q <quality> <input> -o <output>` (default quality: 85)
   - **sips**: `sips -s format webp <input> --out <output>`
4. Report the output path and file size

## Provenance

This skill drives two interchangeable command-line tools and bundles neither:

- **[`cwebp`](https://developers.google.com/speed/webp/docs/cwebp)** — part of Google's **libwebp** (© Google, [BSD-3-Clause](https://chromium.googlesource.com/webm/libwebp/+/refs/heads/main/COPYING)), installed separately via `brew install webp`.
- **`sips`** — Apple's Scriptable Image Processing System, built into macOS.

The skill documents the conversion workflow; it is not affiliated with or endorsed by Google or Apple. The MIT license covers this skill's content, not the wrapped tools.
