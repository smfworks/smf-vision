"""Tests for camera_watcher dispatch routing and motion detection."""
import numpy as np

from smf_vision.camera_watcher import _build_dispatch, _detect_motion


def test_dispatch_print(capsys):
    dispatcher = _build_dispatch("print")
    dispatcher({"event_id": 1, "caption": "test"})
    captured = capsys.readouterr()
    assert '"event_id": 1' in captured.out


def test_dispatch_file(tmp_path):
    log = tmp_path / "events.jsonl"
    dispatcher = _build_dispatch(f"file:{log}")
    dispatcher({"event_id": 1, "caption": "first"})
    dispatcher({"event_id": 2, "caption": "second"})
    lines = log.read_text().strip().split("\n")
    assert len(lines) == 2
    assert '"event_id": 1' in lines[0]
    assert '"event_id": 2' in lines[1]


def test_dispatch_webhook_invalid_url():
    # Should not raise, just log a warning on failure
    dispatcher = _build_dispatch("webhook:http://127.0.0.1:1/events")
    dispatcher({"event_id": 1})  # no crash


def test_motion_detection_no_motion():
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    prev = np.zeros((480, 640), dtype=np.uint8)
    has_motion, _ = _detect_motion(frame, prev, threshold=25, min_area=0.02)
    assert has_motion is False


def test_motion_detection_with_motion():
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[100:300, 100:300] = 255  # big white block = motion
    prev_gray = np.zeros((480, 640), dtype=np.uint8)
    has_motion, _ = _detect_motion(frame, prev_gray, threshold=25, min_area=0.02)
    assert has_motion is True


def test_motion_detection_first_frame():
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    has_motion, _ = _detect_motion(frame, None, threshold=25, min_area=0.02)
    assert has_motion is False  # first frame never reports motion
