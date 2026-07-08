"""Tests for vision_bridge JSON extraction and camera_watcher dispatch."""
from smf_vision.vision_bridge import _extract_json


def test_extract_json_plain():
    result = _extract_json('{"caption":"a cat","objects":["cat"],"has_person":false}')
    assert result is not None
    assert result["caption"] == "a cat"
    assert result["objects"] == ["cat"]
    assert result["has_person"] is False


def test_extract_json_markdown_fenced():
    text = '```json\n{"caption":"a dog","objects":["dog"],"has_person":false}\n```'
    result = _extract_json(text)
    assert result is not None
    assert result["caption"] == "a dog"


def test_extract_json_with_prefix():
    text = 'Here is the result:\n{"caption":"a car","objects":["car"],"has_person":false}'
    result = _extract_json(text)
    assert result is not None
    assert result["caption"] == "a car"


def test_extract_json_empty():
    assert _extract_json("") is None
    assert _extract_json("no json here") is None


def test_extract_json_malformed():
    assert _extract_json('{"caption": broken') is None


def test_extract_json_nested_objects():
    text = '{"caption":"scene","objects":["a","b"],"has_person":true}'
    result = _extract_json(text)
    assert result is not None
    assert result["objects"] == ["a", "b"]
    assert result["has_person"] is True
