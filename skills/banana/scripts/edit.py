#!/usr/bin/env python3
"""Edit an existing image with a text instruction.

    edit.py --image path/to/image.png --prompt "..." [--model ID] [--api-key KEY]

The source image is uploaded to Google alongside the instruction. Only real
image files are accepted — see encode_image in gemini_client.py.
"""

import argparse
import json
import sys

from gemini_client import (
    BananaError, call_gemini, encode_image, extract_image, fail, read_api_key,
    save_image,
)

DEFAULT_MODEL = "gemini-3.1-flash-image"


def main():
    parser = argparse.ArgumentParser(description="Edit an image via the Gemini API")
    parser.add_argument("--image", required=True, help="Path to the source image")
    parser.add_argument("--prompt", required=True, help="The enhanced edit instruction")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--api-key", default=None, help="Overrides GOOGLE_AI_API_KEY")
    args = parser.parse_args()

    if not args.prompt.strip():
        fail(BananaError("Prompt is empty."))

    try:
        api_key = read_api_key(args.api_key)
        image_b64, mime = encode_image(args.image)
        response = call_gemini(
            model=args.model,
            parts=[
                {"text": args.prompt},
                {"inlineData": {"mimeType": mime, "data": image_b64}},
            ],
            api_key=api_key,
        )
        result_b64, text = extract_image(response)
        path = save_image(result_b64, prefix="banana_edit")
    except BananaError as exc:
        fail(exc)

    print(json.dumps({
        "path": str(path),
        "source": args.image,
        "model": args.model,
        "text": text,
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
