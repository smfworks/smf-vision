# Security Policy

SMF Vision is a **local-first** camera + VLM tool. It is not an internet-facing service.

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.2.x   | Yes       |
| < 0.2   | No        |

## Threat model

- Camera HTTP(S) sources may be RFC1918 (that is the product).
- Webhooks default to **public HTTPS only**. Loopback / RFC1918 / plaintext HTTP require explicit flags.
- `file:` dispatch and `--save-dir` are confined to `SMF_VISION_DATA_DIR` (or the current working directory).
- `file://`, metadata IPs (`169.254.169.254`, `169.254.170.2`), and metadata hostnames are rejected.
- The bundled `scripts/start_server.sh` binds llama-server to `127.0.0.1` by default. Use `--listen-all` only on a trusted network.

## Reporting

Email `dev@smfworks.com` or open a private GitHub security advisory on this repository. Do not file public issues for unreleased vulnerabilities.
