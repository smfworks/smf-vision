# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] — 2026-08-13

### Added
- `url_safety` and `path_safety` modules with tests
- GitHub Actions CI (pytest + ruff on Python 3.10 and 3.12)
- SECURITY.md, ARCHITECTURE.md, CONTRIBUTING.md
- `--version` on both CLIs; `smf_vision_version` on watcher events
- `SMF_VISION_DATA_DIR` root for `file:` dispatch and `--save-dir`
- `--allow-insecure-webhook` / `--allow-private-webhook`
- `CAMERA_HTTP_PASSWORD` env as the preferred camera password source
- llama-server binds `127.0.0.1` by default; `--listen-all` for 0.0.0.0

### Fixed
- Tests now collect on a clean clone (`pythonpath = ["src"]`)
- Package import no longer depends on a `sys.path` hack
- `start_server.sh` pointed at a nonexistent `download_models.sh`
- Unsafe env values for timeout / token / temperature now fail closed

### Security
- Reject `file://`, metadata IPs/hostnames, and non-http(s) camera network schemes
- Webhooks require public HTTPS unless explicitly opted in
- Writable paths cannot escape the data root

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