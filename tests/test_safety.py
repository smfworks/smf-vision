"""URL and path safety contracts."""
from __future__ import annotations

from pathlib import Path

import pytest

from smf_vision.path_safety import UnsafePathError, resolve_readable_image, resolve_writable_path
from smf_vision.url_safety import (
    UnsafeURLError,
    ValidatingRedirectHandler,
    validate_camera_source,
    validate_webhook_url,
)


def test_camera_http_private_allowed():
    assert validate_camera_source("http://192.168.1.50/snapshot.jpg").startswith("http://")


def test_camera_rejects_file_scheme():
    with pytest.raises(UnsafeURLError, match="unsupported camera source"):
        validate_camera_source("file:///etc/passwd")


def test_camera_rejects_metadata_ip():
    with pytest.raises(UnsafeURLError, match="metadata"):
        validate_camera_source("http://169.254.169.254/latest/meta-data")


def test_camera_index_passthrough():
    assert validate_camera_source("0") == "0"


def test_camera_rtsp_passthrough():
    assert validate_camera_source("rtsp://192.168.1.50/stream").startswith("rtsp://")


def test_webhook_requires_https():
    with pytest.raises(UnsafeURLError, match="https"):
        validate_webhook_url("http://example.com/hook")


def test_webhook_rejects_loopback_by_default():
    with pytest.raises(UnsafeURLError, match="non-public"):
        validate_webhook_url("https://127.0.0.1/hook", allow_insecure=True)


def test_webhook_allows_loopback_when_opted_in():
    url = validate_webhook_url(
        "http://127.0.0.1:9/hook",
        allow_insecure=True,
        allow_private=True,
    )
    assert url.startswith("http://127.0.0.1")


def test_writable_path_rejects_escape(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SMF_VISION_DATA_DIR", raising=False)
    with pytest.raises(UnsafePathError):
        resolve_writable_path("/etc/passwd")


def test_writable_path_allows_under_root(tmp_path, monkeypatch):
    monkeypatch.setenv("SMF_VISION_DATA_DIR", str(tmp_path))
    target = resolve_writable_path(tmp_path / "events.jsonl")
    assert target == (tmp_path / "events.jsonl").resolve()


def test_readable_image_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        resolve_readable_image(tmp_path / "missing.jpg")


def test_readable_image_size_cap(tmp_path):
    p = tmp_path / "big.bin"
    p.write_bytes(b"x" * 100)
    with pytest.raises(UnsafePathError, match="exceeds"):
        resolve_readable_image(p, max_bytes=10)


def test_camera_rejects_mapped_metadata_ipv6():
    with pytest.raises(UnsafeURLError, match="metadata"):
        validate_camera_source("http://[::ffff:169.254.169.254]/latest/meta-data")
    with pytest.raises(UnsafeURLError, match="metadata"):
        validate_camera_source("http://[::ffff:a9fe:a9fe]/x")


def test_camera_rejects_malformed_and_file_schemes():
    for source in ("file:/etc/passwd", "file:etc/passwd", "//169.254.169.254/x", "http:/169.254.169.254/x"):
        with pytest.raises(UnsafeURLError):
            validate_camera_source(source)


def test_rtsp_rejects_metadata():
    with pytest.raises(UnsafeURLError, match="metadata"):
        validate_camera_source("rtsp://169.254.169.254/stream")


def test_webhook_rejects_cgnat():
    with pytest.raises(UnsafeURLError, match="non-public"):
        validate_webhook_url("https://100.100.100.200/hook")


def test_redirect_to_metadata_is_rejected():
    handler = ValidatingRedirectHandler(role="webhook", allow_private=False, require_https=False)
    with pytest.raises(UnsafeURLError, match="metadata"):
        handler.redirect_request(
            None,
            None,
            302,
            "Found",
            {},
            "http://169.254.169.254/latest/meta-data",
        )


def test_start_server_defaults_to_localhost():
    text = Path("scripts/start_server.sh").read_text()
    assert 'HOST="${HOST:-127.0.0.1}"' in text
    assert "--host \"$HOST\"" in text
    assert "--host 0.0.0.0" not in text
