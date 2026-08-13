"""Filesystem bounds for image reads and event-file writes."""
from __future__ import annotations

import os
from pathlib import Path

DEFAULT_MAX_IMAGE_BYTES = 20 * 1024 * 1024


class UnsafePathError(ValueError):
    """Raised when a path escapes the allowed root or is otherwise unsafe."""


def data_root(explicit: str | os.PathLike[str] | None = None) -> Path:
    if explicit is not None:
        return Path(explicit).expanduser().resolve()
    env = os.environ.get("SMF_VISION_DATA_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return Path.cwd().resolve()


def resolve_readable_image(
    path: str | os.PathLike[str],
    *,
    max_bytes: int = DEFAULT_MAX_IMAGE_BYTES,
) -> Path:
    target = Path(path).expanduser().resolve()
    if not target.is_file():
        raise FileNotFoundError(f"image not found: {target}")
    size = target.stat().st_size
    if size > max_bytes:
        raise UnsafePathError(f"image exceeds {max_bytes} bytes: {target} ({size})")
    return target


def resolve_writable_path(
    path: str | os.PathLike[str],
    *,
    root: str | os.PathLike[str] | None = None,
) -> Path:
    base = data_root(root)
    target = Path(path).expanduser().resolve()
    try:
        target.relative_to(base)
    except ValueError as exc:
        raise UnsafePathError(f"path {target} is outside allowed root {base}") from exc
    return target
