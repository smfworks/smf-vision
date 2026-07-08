"""SMF Vision — remote camera frame ingestion + local VLM analysis.

A lightweight pipeline for reading remote camera feeds (RTSP/HTTP/local),
selecting frames by motion detection, captioning them with a local
vision-language model, and dispatching structured JSON events.

Modules:
    vision_bridge  — OpenAI-compatible vision client with structured JSON output.
    camera_watcher — frame ingestion, motion filter, event dispatch.
"""

__version__ = "0.1.0"
