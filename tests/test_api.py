"""Tests for vademo.api, with a fake SDK client: no network, no credentials."""

from types import SimpleNamespace
from typing import ClassVar

import pytest
import behavioralsignals
from behavioralsignals.models import StreamingResultResponse

from vademo import api


def row(task, level, start, end, score):
    return {
        "id": "1",
        "task": task,
        "level": level,
        "startTime": start,
        "endTime": end,
        "prediction": [{"score": score}],
    }


class FakeClient:
    """Stands in for behavioralsignals.Client and returns fixed streaming responses."""

    responses: ClassVar[list] = []
    options: ClassVar[list] = []

    def __init__(self):
        self.behavioral = SimpleNamespace(stream_audio=self.stream_audio)

    def stream_audio(self, audio_stream, options):
        FakeClient.options.append(options)
        list(audio_stream)
        return iter(self.responses)


def test_stream_pairs_valence_and_arousal_per_segment(monkeypatch):
    FakeClient.responses = [
        StreamingResultResponse(
            pid=7,
            result=[
                row("emotion", "segment", "0.0", "2.0", "0.9"),
                row("continuous_valence", "segment", "0.0", "2.0", "0.25"),
                row("continuous_arousal", "segment", "0.0", "2.0", "-0.5"),
                # Only one of the two values: not drawn.
                row("continuous_valence", "segment", "2.0", "3.0", "0.1"),
            ],
        )
    ]
    monkeypatch.setattr(behavioralsignals, "Client", FakeClient)

    points = list(api.stream(iter([b"\0\0"])))

    assert points == [(7, api.Point("segment", 0.0, 2.0, 0.25, -0.5))]


def test_stream_asks_for_segment_level_continuous_values(monkeypatch):
    FakeClient.responses, FakeClient.options = [], []
    monkeypatch.setattr(behavioralsignals, "Client", FakeClient)

    list(api.stream(iter([b"\0\0"])))

    (opts,) = FakeClient.options
    assert opts.sample_rate == api.SAMPLE_RATE == 16000
    assert opts.encoding == "LINEAR_PCM"
    assert opts.level == "segment"
    assert opts.continuous == ["valence", "arousal"]


def test_missing_credentials_end_with_a_message(monkeypatch):
    monkeypatch.delenv("BEHAVIORALSIGNALS_CID", raising=False)
    monkeypatch.delenv("BEHAVIORALSIGNALS_API_KEY", raising=False)

    with pytest.raises(SystemExit, match="BEHAVIORALSIGNALS_CID"):
        list(api.stream(iter([])))


def test_missing_ffmpeg_ends_with_a_message(monkeypatch, tmp_path):
    monkeypatch.setattr(api.shutil, "which", lambda _: None)

    with pytest.raises(SystemExit, match="ffmpeg is not on the PATH"):
        api.decode(tmp_path / "x.wav")


def test_pcm_blocks_are_quarter_seconds():
    pcm = b"\0" * (api.BLOCK_BYTES * 2 + 10)

    sizes = [len(b) for b in api.pcm_blocks(pcm)]

    assert sizes == [api.BLOCK_BYTES, api.BLOCK_BYTES, 10]
    assert api.BLOCK_BYTES == api.SAMPLE_RATE // 4 * 2


def test_cache_path_is_keyed_by_content(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(), b.mkdir()
    (a / "take1.wav").write_bytes(b"one")
    (b / "take1.wav").write_bytes(b"two")
    (b / "copy.wav").write_bytes(b"one")

    first = api.cache_path(a / "take1.wav", tmp_path)
    second = api.cache_path(b / "take1.wav", tmp_path)

    assert first != second
    assert first.name.startswith("take1-")
    assert api.cache_path(b / "copy.wav", tmp_path).name.split("-")[1] == first.name.split("-")[1]
