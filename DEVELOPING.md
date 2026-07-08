# Development

## Setup

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev,hf]"
```

## Tests

```bash
pytest
```

## Lint

```bash
ruff check src tests
```

## Pre-commit checklist

- [ ] `pytest` passes
- [ ] `ruff check` is clean
- [ ] No model files committed (check `.gitignore`)
- [ ] No secrets/API keys in code or config