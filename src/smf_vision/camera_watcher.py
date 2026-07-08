#!/usr/bin/env python3
"""camera_watcher.py — minimal remote camera frame ingestion + analysis.

Reads frames from an RTSP/HTTP(S) stream or local camera, runs a simple motion
filter, and sends selected frames to a local vision endpoint. Results are emitted
as structured JSON events.

Examples:
    python3 camera_watcher.py --source 0 --interval 5
    python3 camera_watcher.py --source rtsp://192.168.1.50/stream --interval 5
    python3 camera_watcher.py --source http://camera.local/snapshot.jpg --interval 10 --dispatch webhook:https://api.example.com/events

Env vars:
    VISION_ENDPOINT, VISION_MODEL, VISION_PROMPT, VISION_MAX_TOKENS
    CAMERA_MOTION_THRESHOLD (0-255, default 25)
    CAMERA_MOTION_AREA (0-1, default 0.02)
"""
from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import sys
import time
import urllib.request
from typing import Any, Callable

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vision_bridge import describe_image  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("camera_watcher")

MOTION_THRESHOLD = int(os.environ.get("CAMERA_MOTION_THRESHOLD", "25"))
MOTION_AREA = float(os.environ.get("CAMERA_MOTION_AREA", "0.02"))


def _open_source(source: str) -> cv2.VideoCapture:
    """Open a camera index, local path, or network stream."""
    try:
        idx = int(source)
        cap = cv2.VideoCapture(idx)
    except ValueError:
        cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"could not open camera source: {source}")
    return cap


def _fetch_http_frame(source: str, username: str | None, password: str | None) -> np.ndarray | None:
    """Fetch a single JPEG snapshot from an HTTP(S) URL."""
    req = urllib.request.Request(source)
    if username and password:
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        req.add_header("Authorization", f"Basic {credentials}")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        arr = np.frombuffer(data, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return frame
    except Exception as e:
        logger.warning("HTTP frame fetch failed: %s", e)
        return None


def _detect_motion(frame: np.ndarray, prev: np.ndarray | None, threshold: int, min_area: float) -> tuple[bool, np.ndarray]:
    """Return (motion_detected, current_gray_for_next_call)."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)
    if prev is None:
        return False, gray
    diff = cv2.absdiff(prev, gray)
    _, thresh = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    dilated = cv2.dilate(thresh, kernel, iterations=2)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    motion_area = sum(cv2.contourArea(c) for c in contours)
    total_area = frame.shape[0] * frame.shape[1]
    return (motion_area / total_area) > min_area, gray


def _build_dispatch(dispatch: str) -> Callable[[dict[str, Any]], None]:
    if dispatch.startswith("webhook:"):
        url = dispatch.split(":", 1)[1]

        def _send(event: dict[str, Any]) -> None:
            try:
                data = json.dumps(event).encode()
                req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    logger.info("webhook %s HTTP %s", url, r.status)
            except Exception as e:
                logger.warning("webhook dispatch failed: %s", e)

        return _send
    if dispatch.startswith("file:"):
        path = dispatch.split(":", 1)[1]

        def _append(event: dict[str, Any]) -> None:
            with open(path, "a") as f:
                f.write(json.dumps(event) + "\n")

        return _append
    if dispatch == "print":
        return lambda event: print(json.dumps(event))
    raise ValueError(f"unknown dispatch: {dispatch}")


def _resize_if_large(frame: np.ndarray, max_dim: int = 1280) -> np.ndarray:
    h, w = frame.shape[:2]
    if max(h, w) <= max_dim:
        return frame
    scale = max_dim / max(h, w)
    return cv2.resize(frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)


def watch(
    source: str,
    interval: float,
    dispatch: str = "print",
    motion_only: bool = True,
    save_dir: str | None = None,
    max_dim: int = 1280,
    username: str | None = None,
    password: str | None = None,
) -> None:
    """Main loop: grab frames, filter by motion, caption selected frames, dispatch events."""
    dispatcher = _build_dispatch(dispatch)
    is_http = source.startswith("http://") or source.startswith("https://")

    cap: cv2.VideoCapture | None = None
    if not is_http:
        cap = _open_source(source)

    prev_gray: np.ndarray | None = None
    last_caption_time = 0.0
    frame_counter = 0
    event_counter = 0

    try:
        while True:
            t_loop = time.time()
            if is_http:
                frame = _fetch_http_frame(source, username, password)
                if frame is None:
                    time.sleep(max(1.0, interval / 2))
                    continue
            else:
                assert cap is not None
                ok, frame = cap.read()
                if not ok:
                    logger.warning("stream read failed, reconnecting...")
                    if cap:
                        cap.release()
                    cap = _open_source(source)
                    continue

            frame_counter += 1
            frame = _resize_if_large(frame, max_dim)

            if motion_only:
                has_motion, prev_gray = _detect_motion(frame, prev_gray, MOTION_THRESHOLD, MOTION_AREA)
                if not has_motion:
                    time.sleep(0.1)
                    continue

            if t_loop - last_caption_time < interval:
                time.sleep(0.1)
                continue
            last_caption_time = t_loop

            ts = time.strftime("%Y%m%d_%H%M%S")
            image_path = f"/tmp/camera_watcher_{ts}.jpg"
            if save_dir:
                os.makedirs(save_dir, exist_ok=True)
                image_path = os.path.join(save_dir, f"frame_{ts}.jpg")
            cv2.imwrite(image_path, frame)

            try:
                result = describe_image(image_path)
            except Exception as e:
                logger.error("vision inference failed: %s", e)
                continue

            event_counter += 1
            event = {
                "event_id": event_counter,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "source": source,
                "image_path": image_path,
                "caption": result.get("caption", ""),
                "objects": result.get("objects", []),
                "has_person": bool(result.get("has_person")),
                "inference_ms": result.get("elapsed_ms", 0),
                "model": result.get("model", ""),
            }
            dispatcher(event)
    except KeyboardInterrupt:
        logger.info("stopped by user")
    finally:
        if cap:
            cap.release()


def main() -> None:
    ap = argparse.ArgumentParser(description="Remote camera frame ingestion + analysis")
    ap.add_argument("--source", required=True, help="camera index, rtsp://..., http://...")
    ap.add_argument("--interval", type=float, default=5.0, help="minimum seconds between captions")
    ap.add_argument("--motion-only", action="store_true", default=True, help="only caption when motion detected")
    ap.add_argument("--no-motion-only", dest="motion_only", action="store_false", help="caption on interval regardless of motion")
    ap.add_argument("--dispatch", default="print", help="print | file:path | webhook:url")
    ap.add_argument("--save-dir", help="directory to keep analyzed frames")
    ap.add_argument("--max-dim", type=int, default=1280, help="resize largest dimension before inference")
    ap.add_argument("--username", help="HTTP basic auth username")
    ap.add_argument("--password", help="HTTP basic auth password")
    args = ap.parse_args()

    watch(
        source=args.source,
        interval=args.interval,
        dispatch=args.dispatch,
        motion_only=args.motion_only,
        save_dir=args.save_dir,
        max_dim=args.max_dim,
        username=args.username,
        password=args.password,
    )


if __name__ == "__main__":
    main()
