# Architecture

```
camera / snapshot  -->  camera_watcher  -->  motion filter
                              |                    |
                         frame buffer         vision_bridge
                                                   |
                                          local OpenAI-compatible
                                          VLM (llama-server)
                                                   |
                                            JSON event
                                                   |
                                    print | file: | webhook:
```

## Modules

| Module | Role |
|--------|------|
| `smf_vision.vision_bridge` | Caption a local image via `VISION_ENDPOINT` |
| `smf_vision.camera_watcher` | Ingest RTSP / HTTP / device index, motion filter, dispatch |
| `smf_vision.url_safety` | Scheme / metadata / private-address policy |
| `smf_vision.path_safety` | Image size cap and writable-path root |

## Trust boundaries

- **Vision endpoint** must be http(s). Private/loopback is allowed (local llama-server).
- **Camera HTTP source** may be private http(s). Non-http(s) network schemes except `rtsp://` are rejected.
- **Webhook** is public HTTPS unless `--allow-insecure-webhook` / `--allow-private-webhook`.
- **File outputs** must resolve under `SMF_VISION_DATA_DIR` or cwd.

There is no SQLite, no multi-tenant auth, and no remote control plane. A future Hermes adapter should sit *in front of* these functions rather than replacing them.
