"""The streaming call: PCM blocks in, continuous valence/arousal points out.

The API computes `continuous_valence` / `continuous_arousal` server-side. The
demos ask for SEGMENT level only: one value per segment (usually 2 s, sometimes
shorter) as soon as it ends, without waiting for an utterance to close. Nothing
here derives a value from posteriors: what is drawn is what the API returned.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from dataclasses import dataclass


SAMPLE_RATE = 16000
BLOCK_BYTES = SAMPLE_RATE // 4 * 2  # 0.25 s of int16 mono


@dataclass
class Point:
    level: str  # "segment" or "utterance"
    st: float
    et: float
    valence: float
    arousal: float

    def as_dict(self):
        return self.__dict__.copy()


def cache_path(src: str | Path, outdir: Path) -> Path:
    """Cached results are keyed by the file's CONTENT, not its name: two
    different recordings both called take1.wav must not share results."""
    h = hashlib.sha256(Path(src).read_bytes()).hexdigest()[:12]
    return outdir / f"{Path(src).stem}-{h}.points.json"


def decode(path: str | Path) -> bytes:
    """Any audio/video file -> 16 kHz mono int16 PCM."""
    return subprocess.run(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-vn",
            "-ar",
            str(SAMPLE_RATE),
            "-ac",
            "1",
            "-f",
            "s16le",
            "-",
        ],
        check=True,
        capture_output=True,
    ).stdout


def pcm_blocks(pcm: bytes):
    for i in range(0, len(pcm), BLOCK_BYTES):
        yield pcm[i : i + BLOCK_BYTES]


def stream(blocks, level: str = "segment"):
    """Yield (pid, Point) for every unit that carries both continuous values.

    Credentials come from BEHAVIORALSIGNALS_CID / BEHAVIORALSIGNALS_API_KEY, read by the SDK.
    """
    from behavioralsignals import Client, StreamingOptions

    client = Client()
    opts = StreamingOptions(
        sample_rate=SAMPLE_RATE,
        encoding="LINEAR_PCM",
        level=level,
        continuous=["valence", "arousal"],
    )
    for resp in client.behavioral.stream_audio(audio_stream=blocks, options=opts):
        units: dict = {}
        for it in resp.results or []:
            if not it.task.startswith("continuous_"):
                continue
            key_ = (it.level, it.id, float(it.st), float(it.et))
            units.setdefault(key_, {})[it.task[len("continuous_") :]] = float(
                it.prediction[0].score
            )
        for (lvl, _id, st, et), v in units.items():
            if "valence" in v and "arousal" in v:
                yield resp.pid, Point(str(lvl), st, et, v["valence"], v["arousal"])
