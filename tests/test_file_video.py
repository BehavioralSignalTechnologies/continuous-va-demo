"""file_video.py streams a file once and reuses the cached results after that."""

import json

import pytest

import file_video
from vademo.api import Point, cache_path


POINT = Point("segment", 0.0, 2.0, 0.1, -0.2)


@pytest.fixture
def calls(monkeypatch):
    """Fakes decoding and streaming; lists one entry per streaming pass."""
    calls = []

    def fake_stream(blocks):
        calls.append(1)
        list(blocks)
        yield 5, POINT

    monkeypatch.setattr(file_video, "decode", lambda _: b"\0\0" * 32000)  # 2 s
    monkeypatch.setattr(file_video, "stream", fake_stream)
    return calls


@pytest.fixture
def src(tmp_path):
    path = tmp_path / "call.wav"
    path.write_bytes(b"audio")
    return path


def test_second_run_uses_the_cache(src, calls, tmp_path):
    cache = cache_path(src, tmp_path)

    first = file_video.get_points(src, cache, restream=False)
    second = file_video.get_points(src, cache, restream=False)

    assert first == second == (5, 2.0, [POINT])
    assert len(calls) == 1


def test_restream_ignores_the_cache(src, calls, tmp_path):
    cache = cache_path(src, tmp_path)

    file_video.get_points(src, cache, restream=False)
    file_video.get_points(src, cache, restream=True)

    assert len(calls) == 2


def test_empty_result_is_cached(src, calls, tmp_path, monkeypatch):
    monkeypatch.setattr(file_video, "stream", lambda blocks: iter([]))
    cache = cache_path(src, tmp_path)

    assert file_video.get_points(src, cache, restream=False) == (None, 2.0, [])
    assert json.loads(cache.read_text())["points"] == []
