# SMF Vision

Remote camera frame ingestion + local VLM analysis pipeline.

Reads frames from RTSP/HTTP/local cameras, filters by motion detection, captions
selected frames with a local vision-language model (Qwen3.5-0.8B via llama.cpp),
and dispatches structured JSON events to stdout, file, or webhook.

## Quick start

### 1. Install

```bash
git clone https://github.com/smfworks/smf-vision.git
cd smf-vision
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev,hf]"
```

### 2. Build llama.cpp

CPU only:
```bash
git clone https://github.com/ggml-org/llama.cpp.git ../llama.cpp-build
cd ../llama.cpp-build && cmake -B build -DCMAKE_BUILD_TYPE=Release \
  && cmake --build build -j$(nproc) --target llama-server
```

AMD ROCm (gfx1151 / Radeon 8060S):
```bash
cmake -B build-rocm -DGGML_HIP=ON -DAMDGPU_TARGETS=gfx1151 -DCMAKE_BUILD_TYPE=Release \
  && cmake --build build-rocm -j$(nproc) --target llama-server
```

### 3. Download models

```bash
python scripts/download_models.py
```

### 4. Start the vision server

```bash
./scripts/start_server.sh          # auto-detect GPU/CPU
./scripts/start_server.sh --cpu    # force CPU
./scripts/start_server.sh --gpu    # force ROCm GPU
```

### 5. Caption an image

```bash
smf-vision-caption --selftest
smf-vision-caption --image photo.jpg
```

### 6. Watch a camera

```bash
# Local webcam
smf-vision-watch --source 0 --interval 5 --dispatch print

# HTTP snapshot camera
smf-vision-watch --source http://camera.local/snapshot.jpg \
  --interval 10 --username admin --password secret \
  --dispatch webhook:https://api.example.com/events

# RTSP stream with motion filter
smf-vision-watch --source rtsp://192.168.1.50/stream \
  --interval 3 --motion-only \
  --save-dir /tmp/camera_frames \
  --dispatch file:/tmp/camera_events.jsonl
```

## Event schema

```json
{
  "event_id": 1,
  "timestamp": "2026-07-08T01:18:21Z",
  "source": "rtsp://192.168.1.50/stream",
  "image_path": "/tmp/camera_frames/frame_20260707_211816.jpg",
  "caption": "A dark room with a computer monitor and a person sitting in front of it.",
  "objects": ["computer monitor", "person", "tripod"],
  "has_person": true,
  "inference_ms": 1855,
  "model": "Qwen3.5-0.8B-UD-Q4_K_XL"
}
```

## Configuration

Environment variables:

| Variable | Default | Description |
|---|---|---|
| `VISION_ENDPOINT` | `http://localhost:8081/v1/chat/completions` | OpenAI-compatible vision endpoint |
| `VISION_MODEL` | `Qwen3.5-0.8B-UD-Q4_K_XL` | Model name |
| `VISION_PROMPT` | strict JSON prompt | Caption prompt |
| `VISION_MAX_TOKENS` | `384` | Max generation tokens (auto-retries at 2x/4x on empty output) |
| `VISION_TEMPERATURE` | `0.0` | Sampling temperature |
| `CAMERA_MOTION_THRESHOLD` | `25` | Pixel diff threshold for motion |
| `CAMERA_MOTION_AREA` | `0.02` | Min fraction of frame area with motion |

## Tested hardware

| Platform | Backend | Latency |
|---|---|---|
| AMD Ryzen AI MAX+ 395 (CPU) | llama.cpp CPU | 3–5 s/frame |
| AMD Radeon 8060S (gfx1151, ROCm 7.2) | llama.cpp HIP | 0.7–2 s/frame |

## Architecture

```
camera feed → camera_watcher → motion filter → vision_bridge → structured event → dispatch
                                   |                |
                              frame buffer    local VLM (llama-server)
```

## License

MIT © SMF Works