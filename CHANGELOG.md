# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project structure (`src/smf_vision/`, `tests/`, `scripts/`, `docs/`)
- `vision_bridge.py` — OpenAI-compatible vision client with structured JSON output
  - `/no_think` prompt prefix to suppress Qwen3.5 reasoning tokens
  - Auto-retry with larger token budget on empty responses (dark/ambiguous frames)
  - Markdown fence stripping for robust JSON extraction
- `camera_watcher.py` — frame ingestion from RTSP/HTTP/local cameras
  - Motion detection filter (frame differencing + contour area)
  - Dispatch to stdout, JSONL file, or webhook
  - HTTP basic auth support for IP cameras
  - Automatic stream reconnection
- `scripts/start_server.sh` — auto-detects AMD ROCm vs CPU, launches llama-server
- `scripts/download_models.py` — fetches Qwen3.5-0.8B GGUF + mmproj from HuggingFace
- Test suite for JSON extraction, dispatch routing, and motion detection
- Tested on AMD Ryzen AI MAX+ 395 (CPU: 3–5 s/frame, ROCm gfx1151: 0.7–2 s/frame)