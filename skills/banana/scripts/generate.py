#!/usr/bin/env python3
"""Generate an image from a prompt.

    generate.py --prompt "..." [--aspect-ratio 16:9] [--resolution 2K]
                [--model ID] [--thinking low|medium|high] [--image-only]
                [--api-key KEY]

Prints JSON with the saved path. The prompt is expected to be a fully
constructed creative brief — building it is Claude's job, not this script's.
"""

import argparse
import json
import sys

from gemini_client import (
    BananaError, call_gemini, extract_image, fail, read_api_key, save_image,
)

DEFAULT_MODEL = "gemini-3.1-flash-image"
DEFAULT_RESOLUTION = "2K"
DEFAULT_RATIO = "1:1"

# Google rejects lowercase resolution values silently, so the choice is
# constrained here rather than passed through and left to fail downstream.
VALID_RESOLUTIONS = ("512", "1K", "2K", "4K")
VALID_RATIOS = (
    "1:1", "16:9", "9:16", "4:3", "3:4", "2:3", "3:2",
    "4:5", "5:4", "1:4", "4:1", "1:8", "8:1", "21:9",
)


def main():
    parser = argparse.ArgumentParser(description="Generate an image via the Gemini API")
    parser.add_argument("--prompt", required=True, help="The full creative brief")
    parser.add_argument("--aspect-ratio", default=DEFAULT_RATIO, choices=VALID_RATIOS)
    parser.add_argument("--resolution", default=DEFAULT_RESOLUTION, choices=VALID_RESOLUTIONS)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--thinking", default=None, choices=["minimal", "low", "medium", "high"])
    parser.add_argument("--image-only", action="store_true", help="Skip the model's text commentary")
    parser.add_argument("--api-key", default=None, help="Overrides GOOGLE_AI_API_KEY")
    args = parser.parse_args()

    if not args.prompt.strip():
        fail(BananaError("Prompt is empty."))

    try:
        api_key = read_api_key(args.api_key)
        response = call_gemini(
            model=args.model,
            parts=[{"text": args.prompt}],
            api_key=api_key,
            image_config={"aspectRatio": args.aspect_ratio, "imageSize": args.resolution},
            thinking_level=args.thinking,
            image_only=args.image_only,
        )
        image_b64, text = extract_image(response)
        path = save_image(image_b64, prefix="banana")
    except BananaError as exc:
        fail(exc)

    print(json.dumps({
        "path": str(path),
        "model": args.model,
        "aspect_ratio": args.aspect_ratio,
        "resolution": args.resolution,
        "text": text,
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
