# Contributing

1. Create a branch from `main`.
2. Install: `python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev,hf]"`
3. `pytest` and `ruff check src tests` must pass.
4. Do not commit GGUF/weights, `.venv`, or credentials.
5. Public API changes (CLI flags, event schema) need a CHANGELOG entry.

See `DEVELOPING.md` and `SECURITY.md`.
