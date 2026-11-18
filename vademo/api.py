"""The streaming call: PCM blocks in, continuous valence/arousal points out.

The API computes `continuous_valence` / `continuous_arousal` server-side. The
demos ask for SEGMENT level only: one value per segment (usually 2 s, sometimes
shorter) as soon as it ends, without waiting for an utterance to close. Nothing
here derives a value from posteriors: what is drawn is what the API returned.
"""

from __future__ import annotations

import shutil
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


def require_ffmpeg():
    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg is not on the PATH: install it (see Setup in the README)")


def decode(path: str | Path) -> bytes:
    """Any audio/video file -> 16 kHz mono int16 PCM."""
    require_ffmpeg()
    try:
        return run_ffmpeg_decode(path)
    except subprocess.CalledProcessError as e:
        reason = e.stderr.decode(errors="replace").strip().splitlines() or [str(e)]
        raise SystemExit(f"ffmpeg cannot decode {path}: {reason[-1]}") from None


def run_ffmpeg_decode(path: str | Path) -> bytes:
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
    Missing credentials and streaming errors end the program with a short message.
    """
    import grpc
    from behavioralsignals import StreamingOptions, BehavioralSignalsError

    client = make_client()
    opts = StreamingOptions(
        sample_rate=SAMPLE_RATE,
        encoding="LINEAR_PCM",
        level=level,
        continuous=["valence", "arousal"],
    )
    try:
        for resp in client.behavioral.stream_audio(audio_stream=blocks, options=opts):
            for point in points_of(resp):
                yield resp.pid, point
    except grpc.RpcError as e:
        raise SystemExit(
            f"streaming failed: {e.details() if isinstance(e, grpc.Call) else e}"
        ) from None
    except BehavioralSignalsError as e:
        raise SystemExit(f"streaming failed: {e}") from None


def make_client():
    from behavioralsignals import Client, BehavioralSignalsError

    try:
        return Client()  # signs in at once
    except ValueError as e:  # no CID or API key set
        raise SystemExit(f"{e} (see Setup in the README)") from None
    except BehavioralSignalsError as e:  # rejected, e.g. a wrong API key
        raise SystemExit(f"cannot sign in: {e}") from None


def points_of(resp) -> list[Point]:
    """The Points of one streaming response: units that carry both continuous values."""
    units: dict = {}
    for it in resp.results or []:
        if not it.task.startswith("continuous_"):
            continue
        key_ = (it.level, it.id, float(it.st), float(it.et))
        units.setdefault(key_, {})[it.task[len("continuous_") :]] = float(it.prediction[0].score)
    return [
        Point(str(lvl), st, et, v["valence"], v["arousal"])
        for (lvl, _id, st, et), v in units.items()
        if "valence" in v and "arousal" in v
    ]
