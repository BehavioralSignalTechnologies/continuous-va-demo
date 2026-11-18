#!/usr/bin/env python3
"""(a) File -> MP4: stream an audio file through the Behavioral Signals streaming API
with continuous valence/arousal at SEGMENT level (one value per segment, usually 2 s),
and render a video of the V/A plane whose sound track is the input file.

    uv run file_video.py recording.wav                  # -> out/recording_va.mp4
    uv run file_video.py call.mp3 -o demo.mp4 --latency 0.5

BILLABLE: one streaming pass over the file (streaming rate per minute). The
API results are cached in out/<stem>-<content hash>.points.json, so re-rendering (other fps,
latency, trail) costs nothing; --restream forces a new pass.

The audio is sent as fast as the server accepts it; segmentation is the
server's either way, so the values are those of a live pass. In the video a
segment appears when it ends (+ --latency, to mimic the live delay: about
0.3-0.5 s after a 2 s segment ends, about 1.3 s after a shorter one).
"""

from __future__ import annotations

import sys
import json
import argparse
import subprocess
from pathlib import Path

import matplotlib


matplotlib.use("Agg")

from vademo.api import SAMPLE_RATE, Point, decode, stream, cache_path, pcm_blocks
from vademo.plane import Plane


HERE = Path(__file__).resolve().parent


def get_points(src: Path, cache: Path, restream: bool):
    if cache.exists() and not restream:
        d = json.loads(cache.read_text())
        if d.get("level") == "segment":
            print(f"cached results: {cache}")
            return d["pid"], d["duration"], [Point(**p) for p in d["points"]]
        print("cache was made at another level; streaming again")
    pcm = decode(src)
    duration = len(pcm) / 2 / SAMPLE_RATE
    print(f"streaming {src.name} ({duration:.1f} s) ...", flush=True)
    pid, points = None, []
    for pid_, p in stream(pcm_blocks(pcm)):
        pid = pid or pid_
        points.append(p)
        print(
            f"  {p.level:9s} {p.st:6.1f}-{p.et:6.1f}s  V {p.valence:+.3f}  A {p.arousal:+.3f}",
            flush=True,
        )
    points.sort(key=lambda p: (p.et, p.level != "segment"))
    cache.write_text(
        json.dumps(
            {
                "source": str(src),
                "pid": pid,
                "level": "segment",
                "duration": duration,
                "points": [p.as_dict() for p in points],
            },
            indent=1,
        )
    )
    return pid, duration, points


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("input", help="audio or video file")
    ap.add_argument("-o", "--out", help="output mp4 (default out/<stem>_va.mp4)")
    ap.add_argument("--fps", type=int, default=25)
    ap.add_argument(
        "--latency",
        type=float,
        default=0.0,
        help="seconds after a segment ends before it is shown (live is about 0.5)",
    )
    ap.add_argument("--trail", type=float, default=12.0, help="seconds of fading trail")
    ap.add_argument("--window", type=float, default=30.0, help="seconds in the time panels")
    ap.add_argument("--restream", action="store_true", help="ignore the cached results")
    a = ap.parse_args()

    src = Path(a.input).expanduser().resolve()
    outdir = HERE / "out"
    outdir.mkdir(exist_ok=True)
    out = Path(a.out) if a.out else outdir / f"{src.stem}_va.mp4"
    pid, duration, points = get_points(src, cache_path(src, outdir), a.restream)
    nseg = sum(p.level == "segment" for p in points)
    print(f"pid {pid}: {nseg} segments")
    if not nseg:
        sys.exit("no segments came back (no speech found by the API's VAD?)")

    plane = Plane(title=f"{src.name}  ·  pid {pid}", trail=a.trail, window=a.window)
    w, h = plane.fig.canvas.get_width_height()
    ff = subprocess.Popen(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgba",
            "-s",
            f"{w}x{h}",
            "-r",
            str(a.fps),
            "-i",
            "-",
            "-i",
            str(src),
            "-map",
            "0:v",
            "-map",
            "1:a",
            "-c:v",
            "libx264",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-shortest",
            str(out),
        ],
        stdin=subprocess.PIPE,
    )
    n = int(duration * a.fps) + 1
    for i in range(n):
        plane.update(i / a.fps, points, latency=a.latency)
        plane.fig.canvas.draw()
        ff.stdin.write(plane.fig.canvas.buffer_rgba().tobytes())
        if i % (a.fps * 10) == 0:
            print(f"  render {i / a.fps:6.1f} / {duration:.1f} s", end="\r", flush=True)
    ff.stdin.close()
    if ff.wait() != 0:
        sys.exit(f"\nffmpeg failed (exit code {ff.returncode}); {out} is not complete")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
