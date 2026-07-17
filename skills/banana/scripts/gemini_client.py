#!/usr/bin/env python3
"""Shared Gemini image API client.

One place where a network request is built, sent, and unpacked. Every other
script in this skill goes through here, so there is exactly one function in the
codebase that touches the network and exactly one that touches the API key.
That is deliberate: a reader who wants to know "where does my key go?" reads
this file and nothing else.

Standard library only. No third-party packages, at any depth.
"""

import base64
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

# The only host this skill ever contacts.
API_HOST = "generativelanguage.googleapis.com"
API_BASE = f"https://{API_HOST}/v1beta/models"

OUTPUT_DIR = Path.home() / "Documents" / "banana_images"

REQUEST_TIMEOUT = 180
MAX_RETRIES = 3

IMAGE_MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


class BananaError(Exception):
    """Any failure worth reporting to the caller as structured JSON."""

    def __init__(self, message, status=None, retryable=False):
        super().__init__(message)
        self.message = message
        self.status = status
        self.retryable = retryable

    def to_dict(self):
        out = {"error": True, "message": self.message}
        if self.status is not None:
            out["status"] = self.status
        return out


def read_api_key(explicit=None):
    """Resolve the API key. Never logged, never persisted, never echoed."""
    key = explicit or os.environ.get("GOOGLE_AI_API_KEY")
    if not key or not key.strip():
        raise BananaError(
            "No API key. Set GOOGLE_AI_API_KEY in your shell profile, or pass --api-key.\n"
            "Get one at https://aistudio.google.com/apikey"
        )
    return key.strip()


def encode_image(path):
    """Read a local image and return (base64_payload, mime_type).

    Rejects unknown extensions outright. Defaulting an unrecognised file to
    image/png would mean any file the user names gets uploaded, which is not a
    decision a helper function should make silently on their behalf.
    """
    path = Path(path).expanduser().resolve()
    if not path.exists():
        raise BananaError(f"Image not found: {path}")
    if not path.is_file():
        raise BananaError(f"Not a file: {path}")

    mime = IMAGE_MIME_TYPES.get(path.suffix.lower())
    if mime is None:
        supported = ", ".join(sorted(IMAGE_MIME_TYPES))
        raise BananaError(
            f"Unsupported file type '{path.suffix or '(none)'}'. Supported: {supported}"
        )

    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return payload, mime


def _explain_http_error(status, body):
    """Turn Google's error body into something a user can act on."""
    if status == 400 and "FAILED_PRECONDITION" in body:
        return BananaError(
            "Billing is not enabled on this Google project. Enable it at "
            "https://aistudio.google.com/apikey — this is not retryable.",
            status=status,
        )
    if status in (401, 403):
        return BananaError(
            "API key rejected. Check GOOGLE_AI_API_KEY, or issue a new key at "
            "https://aistudio.google.com/apikey",
            status=status,
        )
    if status == 429:
        return BananaError("Rate limited by Google.", status=status, retryable=True)
    if status >= 500:
        return BananaError(f"Google server error ({status}).", status=status, retryable=True)
    return BananaError(f"Request failed ({status}): {body[:400]}", status=status)


def call_gemini(model, parts, api_key, image_config=None, thinking_level=None,
                image_only=False):
    """POST one generateContent request and return the parsed response.

    `parts` is the content payload: text, or text plus an inline image.
    Retries only what is worth retrying (429 and 5xx), with exponential backoff.
    A 400 is a bug in our request or a billing problem; retrying it just burns
    the user's quota.
    """
    body = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "responseModalities": ["IMAGE"] if image_only else ["TEXT", "IMAGE"],
        },
    }
    if image_config:
        body["generationConfig"]["imageConfig"] = image_config
    if thinking_level:
        body["generationConfig"]["thinkingConfig"] = {"thinkingLevel": thinking_level}

    payload = json.dumps(body).encode("utf-8")
    url = f"{API_BASE}/{model}:generateContent"

    # Key travels in a header, not the query string. Google accepts both; the
    # header keeps it out of URLs that get written to proxy and server logs.
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }

    context = ssl.create_default_context()

    last_error = None
    for attempt in range(MAX_RETRIES):
        request = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT, context=context) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            error = _explain_http_error(exc.code, detail)
            if not error.retryable or attempt == MAX_RETRIES - 1:
                raise error
            last_error = error
        except urllib.error.URLError as exc:
            last_error = BananaError(f"Network error: {exc.reason}", retryable=True)
            if attempt == MAX_RETRIES - 1:
                raise last_error
        except json.JSONDecodeError:
            raise BananaError("Google returned a response that was not valid JSON.")

        wait = 2 ** (attempt + 1)
        print(
            json.dumps({"retry": True, "attempt": attempt + 1, "wait_seconds": wait,
                        "reason": last_error.message}),
            file=sys.stderr,
        )
        time.sleep(wait)

    raise last_error or BananaError("Exhausted retries with no response.")


def extract_image(response):
    """Pull the image bytes and any commentary out of a Gemini response.

    Google reports refusals in several different shapes depending on where the
    block happened, so each one gets its own message rather than a generic
    'no image returned'.
    """
    candidates = response.get("candidates") or []
    if not candidates:
        block = (response.get("promptFeedback") or {}).get("blockReason")
        if block:
            raise BananaError(
                f"Prompt blocked before generation ({block}). Rephrase and try again."
            )
        raise BananaError("Google returned no candidates and gave no reason.")

    candidate = candidates[0]
    finish = candidate.get("finishReason", "")
    parts = (candidate.get("content") or {}).get("parts") or []

    image_b64 = None
    text = ""
    for part in parts:
        if "inlineData" in part:
            image_b64 = part["inlineData"].get("data")
        elif "text" in part:
            text += part["text"]

    if image_b64:
        return image_b64, text.strip()

    if finish == "IMAGE_SAFETY":
        raise BananaError(
            "The generated image was blocked by Google's output filter (IMAGE_SAFETY). "
            "The prompt itself may be fine — the model's interpretation triggered it. "
            "Shift the visual concept further from the trigger and retry."
        )
    if finish == "PROHIBITED_CONTENT":
        raise BananaError(
            "Topic is prohibited (PROHIBITED_CONTENT). Not retryable — the concept "
            "needs to change, not the wording."
        )
    raise BananaError(f"No image in response (finishReason: {finish or 'unknown'}). {text[:200]}".strip())


def save_image(image_b64, prefix="banana"):
    """Decode and write the image. Returns the resolved path."""
    try:
        raw = base64.b64decode(image_b64)
    except Exception:
        raise BananaError("Google returned image data that could not be decoded.")

    if not raw:
        raise BananaError("Google returned an empty image.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = (OUTPUT_DIR / f"{prefix}_{stamp}.png").resolve()
    path.write_bytes(raw)
    return path


def fail(error):
    """Print a structured error and exit non-zero."""
    payload = error.to_dict() if isinstance(error, BananaError) else {
        "error": True, "message": str(error)
    }
    print(json.dumps(payload))
    sys.exit(1)
