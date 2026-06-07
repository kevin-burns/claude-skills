---
name: social-image-prep
description: Resize and format images for social media platforms. Use when the user needs to prepare an image for LinkedIn, Bluesky, Reddit, Hacker News, or other social platforms. Triggers on "resize for linkedin", "image for social", "prepare image for posting", "social media image", "resize for bluesky", or any request to optimize an image for a specific social platform.
license: MIT
---

# Social image prep

Resize and format images for social media posting. One source image, multiple platform-ready outputs.

## Platform specs

| Platform | Post image size | Aspect ratio | Max file size | Formats | Notes |
|----------|----------------|--------------|---------------|---------|-------|
| LinkedIn | 1200 x 627 | 1.91:1 | 5 MB | JPG, PNG | No WebP. Links in post body kill reach. |
| Bluesky | 1000 x 563 | 16:9 | 1 MB | JPG, PNG | Longest side compressed to 1000px. No animated GIFs. Up to 4 images/post. |
| Bluesky (square) | 1000 x 1000 | 1:1 | 1 MB | JPG, PNG | Alternative for square crops. |
| Bluesky (portrait) | 800 x 1000 | 4:5 | 1 MB | JPG, PNG | For vertical images. |
| Reddit | 1200 x 628 | 1.91:1 | 20 MB | JPG, PNG, GIF | Preview thumbnail crops to center. |
| HN | N/A | N/A | N/A | N/A | Text only. Use og:image on linked page. |
| YouTube thumbnail | 1280 x 720 | 16:9 | 2 MB | JPG, PNG | Min width 640px. |
| og:image (generic) | 1200 x 630 | 1.91:1 | -- | JPG, PNG | For link previews across platforms. |

## Tool detection

Check which image tool is available (run once per session):

1. **`sips`** -- macOS built-in. No install needed.
2. **`magick`** (ImageMagick 7+) -- Linux, Windows, macOS. Install: `brew install imagemagick`, `apt install imagemagick`, `choco install imagemagick`.
3. **`convert`** (ImageMagick 6) -- legacy Linux installs.
4. **Python PIL** -- fallback. `uv run --with Pillow python3 script.py`

Pick the first one available. Prefer `sips` on macOS, `magick` elsewhere.

## Resize commands by tool

### sips (macOS)

```bash
# Check dimensions
sips -g pixelWidth -g pixelHeight -g format INPUT

# Resize (stretches to exact dimensions)
sips -z HEIGHT WIDTH INPUT --out OUTPUT.jpg -s format jpeg -s formatOptions 90

# Aspect-ratio-safe: resize width, then crop height
sips --resampleWidth 1200 INPUT --out /tmp/resized.jpg -s format jpeg
sips --cropToHeightWidth 627 1200 /tmp/resized.jpg --out OUTPUT.jpg
```

Note: `sips -z` takes **height then width** (not width then height).

### ImageMagick (magick / convert)

```bash
# Check dimensions
magick identify INPUT

# Resize and crop to exact dimensions (gravity center)
magick INPUT -resize 1200x627^ -gravity center -extent 1200x627 -quality 90 OUTPUT.jpg

# Simple resize (may distort)
magick INPUT -resize 1200x627! -quality 90 OUTPUT.jpg
```

The `^` suffix fills the target area (may overshoot one dimension), then `-extent` crops to exact size. This is aspect-ratio-safe in one command.

For ImageMagick 6, replace `magick` with `convert`.

### Python PIL (fallback)

```python
# uv run --with Pillow python3 script.py
from PIL import Image

img = Image.open("INPUT")

# Aspect-ratio-safe resize + crop
target = (1200, 627)
ratio = max(target[0] / img.width, target[1] / img.height)
resized = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
left = (resized.width - target[0]) // 2
top = (resized.height - target[1]) // 2
cropped = resized.crop((left, top, left + target[0], top + target[1]))
cropped.save("OUTPUT.jpg", "JPEG", quality=90)
```

## Platform presets

| Preset name | Width | Height | Quality | Notes |
|-------------|-------|--------|---------|-------|
| linkedin | 1200 | 627 | 90 | |
| bluesky | 1000 | 563 | 85 | Keep under 1MB |
| bluesky-square | 1000 | 1000 | 85 | |
| bluesky-portrait | 800 | 1000 | 85 | |
| reddit | 1200 | 628 | 90 | |
| youtube | 1280 | 720 | 90 | |
| og | 1200 | 630 | 90 | |

## Workflow

1. Check source dimensions and format
2. Detect available image tool
3. Ask which platforms (or do all if user says "all")
4. Resize for each target using aspect-ratio-safe crop
5. Verify file size (especially Bluesky 1MB limit -- lower quality to 80 if needed)
6. Report output paths and file sizes
7. Name outputs with platform suffix: `image-linkedin.jpg`, `image-bluesky.jpg`

## Batch mode

If the user says "prep for all platforms", generate all applicable presets. Output to the same directory as the source, or to a user-specified directory.

## Notes

- Always output JPEG for social posts (smaller files, universal support). PNG only if transparency is needed.
- WebP is not accepted by LinkedIn or most social platforms. Always convert to JPG or PNG.
- Bluesky has a 1MB hard limit. If output exceeds 1MB, reduce quality to 80, then 75.
- HN is text-only. If you need an image for HN, set it as og:image in the linked page's meta tags.
- LinkedIn penalizes posts edited within the first hour. Get the image right before posting.
- Verify file size after conversion with `ls -lh` (or `dir` on Windows).

## Provenance

This skill drives whichever image tool is already installed and bundles none of them:

- **`sips`** — Apple's Scriptable Image Processing System, built into macOS.
- **[ImageMagick](https://imagemagick.org)** (`magick` / `convert`) — © ImageMagick Studio LLC, [ImageMagick License](https://imagemagick.org/script/license.php) (Apache-2.0-compatible). Installed separately via `brew`/`apt`/`choco`.
- **[Pillow](https://python-pillow.org) (PIL)** — © Jeffrey A. Clark and contributors, [MIT-CMU license](https://github.com/python-pillow/Pillow/blob/main/LICENSE). Run on demand via `uv run --with Pillow`.

The platform specs and presets are compiled from each platform's public guidance and may change over time. The skill is not affiliated with or endorsed by any of the platforms or tools above. The MIT license covers this skill's content, not the wrapped tools.
