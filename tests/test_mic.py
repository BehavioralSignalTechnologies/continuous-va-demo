"""Microphone and session saving, with a fake sounddevice: no audio device needed."""

import sys
import json
import queue
from types import SimpleNamespace

import numpy as np


def fake_mic_class(monkeypatch):
    fake_sd = SimpleNamespace(query_devices=lambda *_: {"name": "fake"}, PortAudioError=OSError)
    monkeypatch.setitem(sys.modules, "sounddevice", fake_sd)
    monkeypatch.delitem(sys.modules, "vademo.mic", raising=False)
    from vademo.mic import Mic

    return Mic


def test_dropped_blocks_are_not_in_the_recording(monkeypatch):
    mic = fake_mic_class(monkeypatch)()
    mic._q = queue.Queue(maxsize=1)
    block = np.zeros((4000, 1), np.float32)

    mic._callback(block, 4000, None, None)
    mic._callback(block, 4000, None, None)  # queue full: dropped

    assert mic.dropped == 1
    assert len(mic.recorded) == 1


def test_incomplete_session_saves_audio_but_no_results(tmp_path):
    import mic_live
    from vademo.api import cache_path

    wav = mic_live.save_session(tmp_path, [b"\0\0" * 100], 1, [], complete=False)

    assert wav.exists()
    assert not cache_path(wav, tmp_path).exists()


def test_complete_session_saves_results_file_video_can_read(tmp_path):
    import mic_live
    from vademo.api import Point, cache_path

    point = Point("segment", 0.0, 2.0, 0.1, -0.2)
    wav = mic_live.save_session(tmp_path, [b"\0\0" * 100], 9, [point], complete=True)

    saved = json.loads(cache_path(wav, tmp_path).read_text())
    assert saved["pid"] == 9
    assert saved["level"] == "segment"
    assert [Point(**p) for p in saved["points"]] == [point]
