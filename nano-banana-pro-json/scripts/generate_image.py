#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "google-genai>=1.0.0",
#     "pillow>=10.0.0",
# ]
# ///
"""
Generate images using Google's Nano Banana Pro (Gemini 3 Pro Image) API.

Supports simple prompts, JSON configuration, style presets, and photorealistic enhancement.

Usage:
    uv run generate_image.py --prompt "description" --filename "output.png"
    uv run generate_image.py --prompt "description" --filename "output.png" --style-preset cinematic
    uv run generate_image.py --prompt "description" --filename "output.png" --json-config config.json
    uv run generate_image.py --prompt "description" --filename "output.png" --photorealistic --aspect-ratio 16:9
"""

import argparse
import json
import os
import sys
from pathlib import Path

# --- Style Presets ---

STYLE_PRESETS = {
    "photorealistic-studio": {
        "camera": {
            "type": "DSLR",
            "model": "Sony A7III",
            "focal_length": "85mm",
            "aperture": "f/1.4",
            "shutter_speed": "1/200s",
            "iso": "100",
        },
        "lighting": {
            "type": "Studio",
            "setup": "Three-point lighting with key, fill, and rim lights",
            "direction": "Front-angled key light, soft fill",
            "color_temperature": "5500K neutral daylight",
        },
        "composition": {
            "framing": "Medium close-up",
            "perspective": "Eye-level",
            "depth_of_field": "Shallow, subject isolated from background",
        },
        "prompt_suffix": "professional studio photograph, clean background, crisp details",
    },
    "nostalgic-film": {
        "camera": {
            "type": "Film camera",
            "model": "35mm point-and-shoot",
            "focal_length": "35mm",
            "aperture": "f/2.8",
            "shutter_speed": "1/60s",
            "iso": "400",
        },
        "lighting": {
            "type": "Direct flash",
            "setup": "On-camera flash, harsh direct light",
            "direction": "Front-facing flash",
            "color_temperature": "Warm 3800K with flash highlight",
        },
        "composition": {
            "framing": "Casual snapshot framing",
            "perspective": "Slightly off-center, candid",
            "depth_of_field": "Medium, everything mostly in focus",
        },
        "prompt_suffix": "1990s film aesthetic, visible film grain, slight color shift, nostalgic warm tones, authentic snapshot feel",
    },
    "cinematic": {
        "camera": {
            "type": "Film camera",
            "model": "Shot on Kodak Portra 400",
            "focal_length": "50mm",
            "aperture": "f/1.8",
            "shutter_speed": "1/125s",
            "iso": "400",
        },
        "lighting": {
            "type": "Natural light",
            "setup": "Golden hour side lighting",
            "direction": "Side-lit with warm ambient fill",
            "color_temperature": "3200K warm golden hour",
        },
        "composition": {
            "framing": "Wide cinematic framing",
            "perspective": "Slightly low angle",
            "depth_of_field": "Shallow with beautiful bokeh",
        },
        "prompt_suffix": "cinematic film still, film grain, rich color grading, emotional atmosphere, bokeh background",
    },
    "high-fashion": {
        "camera": {
            "type": "DSLR",
            "model": "Professional DSLR",
            "focal_length": "85mm",
            "aperture": "f/2.0",
            "shutter_speed": "1/250s",
            "iso": "200",
        },
        "lighting": {
            "type": "Dramatic studio flash",
            "setup": "Hard key light with dramatic shadows",
            "direction": "High angle key light, minimal fill",
            "color_temperature": "5000K cool studio lighting",
        },
        "composition": {
            "framing": "Full body or three-quarter",
            "perspective": "Slightly low angle for power",
            "depth_of_field": "Medium-shallow, subject sharp",
        },
        "prompt_suffix": "high-fashion editorial photograph, Vogue magazine style, bold styling, dramatic contrast, professional retouching",
    },
    "anime-hyperrealistic": {
        "camera": {
            "type": "DSLR",
            "model": "Portrait lens DSLR",
            "focal_length": "85mm",
            "aperture": "f/1.4",
            "shutter_speed": "1/200s",
            "iso": "100",
        },
        "lighting": {
            "type": "Spotlight",
            "setup": "Single dramatic spotlight with ambient fill",
            "direction": "Top-down spotlight with cool ambient",
            "color_temperature": "Cool 6500K with color accents",
        },
        "composition": {
            "framing": "Portrait close-up",
            "perspective": "Slightly low angle",
            "depth_of_field": "Very shallow, dreamy background blur",
        },
        "prompt_suffix": "anime-inspired hyperrealistic portrait, large expressive eyes, high contrast, vibrant colors, smooth skin, dramatic lighting",
    },
}

PHOTOREALISM_MARKERS = [
    "8k resolution",
    "ultra-sharp",
    "hyperrealistic",
    "visible skin pores",
    "natural skin texture",
    "subsurface scattering",
    "micro-details",
    "photorealistic",
    "RAW photo",
    "professional color grading",
]

ASPECT_RATIO_PROMPT = {
    "1:1": "square aspect ratio composition",
    "4:3": "4:3 aspect ratio, standard photo composition",
    "16:9": "wide 16:9 cinematic aspect ratio",
    "9:16": "tall 9:16 vertical portrait aspect ratio",
    "3:2": "3:2 classic 35mm film aspect ratio",
    "2:3": "2:3 tall portrait aspect ratio",
}

OUTPUT_FORMAT_MAP = {
    "png": ("PNG", ".png"),
    "jpg": ("JPEG", ".jpg"),
    "jpeg": ("JPEG", ".jpg"),
    "webp": ("WEBP", ".webp"),
}


def load_json_config(json_input: str) -> dict:
    """Parse JSON from inline string or file path."""
    json_input = json_input.strip()
    if json_input.startswith("{"):
        return json.loads(json_input)
    path = Path(json_input)
    if not path.exists():
        print(f"Error: JSON config file not found: {json_input}", file=sys.stderr)
        sys.exit(1)
    return json.loads(path.read_text())


def deep_merge(base: dict, override: dict) -> dict:
    """Deep merge override into base, returning new dict."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def merge_config(json_config: dict, preset_name: str | None) -> dict:
    """Merge preset defaults with user JSON overrides."""
    if preset_name and preset_name in STYLE_PRESETS:
        preset = STYLE_PRESETS[preset_name]
        base = {
            "style_parameters": {
                "camera": dict(preset["camera"]),
                "lighting": dict(preset["lighting"]),
                "composition": dict(preset["composition"]),
            },
            "prompt_suffix": preset["prompt_suffix"],
        }
    else:
        base = {}

    if json_config:
        return deep_merge(base, json_config)
    return base


def _format_camera(camera: dict) -> str:
    parts = []
    if camera.get("type"):
        parts.append(camera["type"])
    if camera.get("model"):
        parts.append(camera["model"])
    specs = []
    if camera.get("focal_length"):
        specs.append(camera["focal_length"])
    if camera.get("aperture"):
        specs.append(camera["aperture"])
    if camera.get("shutter_speed"):
        specs.append(camera["shutter_speed"])
    if camera.get("iso"):
        specs.append(f"ISO {camera['iso']}")
    if specs:
        parts.append(", ".join(specs))
    return f"Shot on {' '.join(parts)}" if parts else ""


def _format_lighting(lighting: dict) -> str:
    parts = []
    if lighting.get("setup"):
        parts.append(lighting["setup"])
    elif lighting.get("type"):
        parts.append(f"{lighting['type']} lighting")
    if lighting.get("direction"):
        parts.append(lighting["direction"])
    if lighting.get("color_temperature"):
        parts.append(lighting["color_temperature"])
    return ", ".join(parts)


def _format_composition(composition: dict) -> str:
    parts = []
    if composition.get("framing"):
        parts.append(composition["framing"])
    if composition.get("perspective"):
        parts.append(f"{composition['perspective']} perspective")
    if composition.get("depth_of_field"):
        parts.append(composition["depth_of_field"])
    return ", ".join(parts)


def build_enhanced_prompt(
    base_prompt: str,
    config: dict,
    aspect_ratio: str | None,
    photorealistic: bool,
) -> str:
    """Assemble final prompt from base prompt, config, aspect ratio, and photorealism flag."""
    segments = [base_prompt]

    style = config.get("style_parameters", {})

    # Camera
    camera = style.get("camera", {})
    if camera:
        camera_text = _format_camera(camera)
        if camera_text:
            segments.append(camera_text)

    # Lighting
    lighting = style.get("lighting", {})
    if lighting:
        lighting_text = _format_lighting(lighting)
        if lighting_text:
            segments.append(lighting_text)

    # Composition
    composition = style.get("composition", {})
    if composition:
        comp_text = _format_composition(composition)
        if comp_text:
            segments.append(comp_text)

    # Preset prompt suffix
    if config.get("prompt_suffix"):
        segments.append(config["prompt_suffix"])

    # Consistency ID
    consistency_id = config.get("consistency_id")
    if consistency_id:
        segments.insert(0, f"[Character: {consistency_id}]")

    # Aspect ratio
    if aspect_ratio and aspect_ratio in ASPECT_RATIO_PROMPT:
        segments.append(ASPECT_RATIO_PROMPT[aspect_ratio])

    # Photorealism markers
    if photorealistic:
        segments.append(", ".join(PHOTOREALISM_MARKERS))

    return ". ".join(segments)


def get_api_key(provided_key: str | None) -> str | None:
    """Get API key from argument first, then environment."""
    if provided_key:
        return provided_key
    return os.environ.get("GEMINI_API_KEY")


def determine_output_format(config: dict, filename: str, force_webp: bool = False) -> tuple[str, str]:
    """Determine PIL format and extension from config or filename.

    Returns (pil_format, extension) e.g. ("PNG", ".png").
    """
    # --webp flag takes highest precedence
    if force_webp:
        return ("WEBP", ".webp")

    # Check JSON config output_settings
    fmt = config.get("output_settings", {}).get("format", "").lower()
    if fmt and fmt in OUTPUT_FORMAT_MAP:
        return OUTPUT_FORMAT_MAP[fmt]

    # Fall back to filename extension
    ext = Path(filename).suffix.lower().lstrip(".")
    if ext in OUTPUT_FORMAT_MAP:
        return OUTPUT_FORMAT_MAP[ext]

    # Default to PNG
    return ("PNG", ".png")


def main():
    parser = argparse.ArgumentParser(
        description="Generate images using Nano Banana Pro (Gemini 3 Pro Image) with JSON control"
    )
    parser.add_argument(
        "--prompt", "-p",
        required=True,
        help="Image description/prompt (always takes precedence over JSON config prompt)",
    )
    parser.add_argument(
        "--filename", "-f",
        required=True,
        help="Output filename (e.g., sunset-mountains.png)",
    )
    parser.add_argument(
        "--input-image", "-i",
        help="Optional input image path for editing/modification",
    )
    parser.add_argument(
        "--resolution", "-r",
        choices=["1K", "2K", "4K"],
        default="1K",
        help="Output resolution: 1K (default), 2K, or 4K",
    )
    parser.add_argument(
        "--api-key", "-k",
        help="Gemini API key (overrides GEMINI_API_KEY env var)",
    )
    parser.add_argument(
        "--json-config", "-j",
        help='JSON config: file path or inline JSON string (detected by "{" prefix)',
    )
    parser.add_argument(
        "--style-preset", "-s",
        choices=list(STYLE_PRESETS.keys()),
        help="Style preset to apply",
    )
    parser.add_argument(
        "--aspect-ratio", "-a",
        choices=list(ASPECT_RATIO_PROMPT.keys()),
        help="Aspect ratio (applied as prompt guidance)",
    )
    parser.add_argument(
        "--photorealistic",
        action="store_true",
        help="Inject photorealism quality markers into prompt",
    )
    parser.add_argument(
        "--webp",
        action="store_true",
        help="Save output as WebP (convenience flag, same as naming file .webp)",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=80,
        help="Output quality for JPEG/WebP (1-100, default 80)",
    )

    args = parser.parse_args()

    # Get API key
    api_key = get_api_key(args.api_key)
    if not api_key:
        print("Error: No API key provided.", file=sys.stderr)
        print("Please either:", file=sys.stderr)
        print("  1. Provide --api-key argument", file=sys.stderr)
        print("  2. Set GEMINI_API_KEY environment variable", file=sys.stderr)
        sys.exit(1)

    # Import here after checking API key to avoid slow import on error
    from google import genai
    from google.genai import types
    from PIL import Image as PILImage

    # Load and merge JSON config with preset
    json_config = {}
    if args.json_config:
        json_config = load_json_config(args.json_config)

    config = merge_config(json_config, args.style_preset)

    # Resolve aspect ratio: CLI > JSON config > None
    aspect_ratio = args.aspect_ratio
    if not aspect_ratio:
        aspect_ratio = config.get("output_settings", {}).get("aspect_ratio")

    # Build enhanced prompt (CLI --prompt always wins over config prompt)
    base_prompt = args.prompt
    enhanced_prompt = build_enhanced_prompt(base_prompt, config, aspect_ratio, args.photorealistic)

    # Determine output format
    pil_format, format_ext = determine_output_format(config, args.filename, force_webp=args.webp)

    # Ensure filename has correct extension for chosen format
    output_path = Path(args.filename)
    if output_path.suffix.lower() != format_ext:
        output_path = output_path.with_suffix(format_ext)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Initialise client
    client = genai.Client(api_key=api_key)

    # Load input image if provided
    input_image = None
    output_resolution = args.resolution
    if args.input_image:
        try:
            input_image = PILImage.open(args.input_image)
            print(f"Loaded input image: {args.input_image}")

            # Auto-detect resolution if not explicitly set by user
            if args.resolution == "1K":  # Default value
                width, height = input_image.size
                max_dim = max(width, height)
                if max_dim >= 3000:
                    output_resolution = "4K"
                elif max_dim >= 1500:
                    output_resolution = "2K"
                else:
                    output_resolution = "1K"
                print(f"Auto-detected resolution: {output_resolution} (from input {width}x{height})")
        except Exception as e:
            print(f"Error loading input image: {e}", file=sys.stderr)
            sys.exit(1)

    # Build contents (image first if editing, prompt only if generating)
    if input_image:
        contents = [input_image, enhanced_prompt]
        print(f"Editing image with resolution {output_resolution}...")
    else:
        contents = enhanced_prompt
        print(f"Generating image with resolution {output_resolution}...")

    if enhanced_prompt != base_prompt:
        print(f"Enhanced prompt: {enhanced_prompt[:200]}{'...' if len(enhanced_prompt) > 200 else ''}")

    try:
        response = client.models.generate_content(
            model="gemini-3-pro-image-preview",
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
                image_config=types.ImageConfig(
                    image_size=output_resolution
                ),
            ),
        )

        # Process response and save image
        image_saved = False
        for part in response.parts:
            if part.text is not None:
                print(f"Model response: {part.text}")
            elif part.inline_data is not None:
                from io import BytesIO

                image_data = part.inline_data.data
                if isinstance(image_data, str):
                    import base64
                    image_data = base64.b64decode(image_data)

                image = PILImage.open(BytesIO(image_data))

                # Flatten alpha to white background for formats that need RGB
                def to_rgb(img):
                    if img.mode == "RGBA":
                        bg = PILImage.new("RGB", img.size, (255, 255, 255))
                        bg.paste(img, mask=img.split()[3])
                        return bg
                    if img.mode != "RGB":
                        return img.convert("RGB")
                    return img

                quality = args.quality

                # Save in requested format
                if pil_format == "PNG":
                    to_rgb(image).save(str(output_path), "PNG")
                elif pil_format == "JPEG":
                    to_rgb(image).save(str(output_path), "JPEG", quality=quality)
                elif pil_format == "WEBP":
                    # Gemini API returns PNG/JPEG -- convert to WebP via PIL
                    print(f"Converting to WebP (quality={quality})...")
                    image.save(str(output_path), "WEBP", quality=quality, method=4)
                else:
                    to_rgb(image).save(str(output_path), pil_format)

                image_saved = True

        if image_saved:
            full_path = output_path.resolve()
            print(f"\nImage saved: {full_path}")
        else:
            print("Error: No image was generated in the response.", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"Error generating image: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
