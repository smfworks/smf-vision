#!/usr/bin/env python3
"""vision_bridge.py — reliable local VLM captioning.

Unlike llm-eyes/bridge/see.py, this client:
- asks the model to answer in a strict format and omits reasoning tokens,
- returns structured JSON as well as plain text,
- supports arbitrary OpenAI-compatible vision endpoints via env vars,
- retries on transient failures.

Library use:
    from vision_bridge import describe_image
    result = describe_image("frame.jpg")
    print(result["caption"])

CLI use:
    python3 vision_bridge.py --image frame.jpg
    python3 vision_bridge.py --image frame.jpg --format json
    python3 vision_bridge.py --prompt "List all people and vehicles."
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any

ENDPOINT = os.environ.get("VISION_ENDPOINT", "http://localhost:8081/v1/chat/completions")
MODEL = os.environ.get("VISION_MODEL", "Qwen3.5-0.8B-UD-Q4_K_XL")
DEFAULT_PROMPT = os.environ.get(
    "VISION_PROMPT",
    '/no_think\nOutput a JSON object {"caption":"...","objects":["..."],"has_person":true/false}. No markdown, no explanation.',
)
TIMEOUT = int(os.environ.get("VISION_TIMEOUT", "120"))
MAX_TOKENS = int(os.environ.get("VISION_MAX_TOKENS", "384"))
TEMPERATURE = float(os.environ.get("VISION_TEMPERATURE", "0.0"))


def _encode_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def _post(payload: dict[str, Any], retries: int = 2) -> dict[str, Any]:
    data = json.dumps(payload).encode()
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(
            ENDPOINT,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            last_err = RuntimeError(f"HTTP {e.code}: {body[:500]}")
        except Exception as e:
            last_err = e
        if attempt < retries:
            time.sleep(1)
    raise last_err or RuntimeError("unknown error")


def _extract_json(text: str) -> dict[str, Any] | None:
    """Grab the first JSON object from a string that may have markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        # Strip markdown fences
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    # Find first { ... } object
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def describe_image(image_path: str, prompt: str = DEFAULT_PROMPT) -> dict[str, Any]:
    """Return a structured description of the image.

    Returns a dict with at least:
        caption (str), objects (list[str]), has_person (bool), raw (str), elapsed_ms (int)
    """
    t0 = time.time()
    b64 = _encode_image(image_path)

    # First attempt with default max_tokens. If the model burns the budget on
    # reasoning and returns empty content (common on dark/ambiguous frames with
    # Qwen3.5's reasoning mode), retry with a larger budget so it can finish.
    for max_tokens in (MAX_TOKENS, MAX_TOKENS * 2, MAX_TOKENS * 4):
        payload = {
            "model": MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                        },
                    ],
                }
            ],
            "max_tokens": max_tokens,
            "temperature": TEMPERATURE,
        }
        resp = _post(payload)
        content = resp["choices"][0]["message"].get("content", "").strip()
        if content:
            break

    parsed = _extract_json(content) or {}

    return {
        "caption": parsed.get("caption") or content or "(no caption)",
        "objects": parsed.get("objects") or [],
        "has_person": bool(parsed.get("has_person")),
        "raw": content,
        "elapsed_ms": int((time.time() - t0) * 1000),
        "model": resp.get("model", MODEL),
        "usage": resp.get("usage", {}),
    }


def _selftest() -> None:
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        sys.exit("selftest needs Pillow: pip install pillow")
    img = "/tmp/_vision_bridge_selftest.jpg"
    im = Image.new("RGB", (320, 160), (28, 28, 60))
    ImageDraw.Draw(im).text((24, 66), "vision bridge OK", fill=(255, 255, 255))
    im.save(img)
    print(json.dumps(describe_image(img), indent=2))


def main() -> None:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description="Reliable local vision captioning")
    ap.add_argument("--image", help="path to image to describe")
    ap.add_argument("--prompt", default=DEFAULT_PROMPT, help="custom prompt")
    ap.add_argument("--format", choices=["text", "json"], default="json", help="output format")
    ap.add_argument("--selftest", action="store_true", help="use a generated test image")
    args = ap.parse_args()

    if args.selftest:
        _selftest()
        return
    if not args.image:
        ap.print_help()
        sys.exit(1)

    result = describe_image(args.image, prompt=args.prompt)
    if args.format == "text":
        print(result["caption"])
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
