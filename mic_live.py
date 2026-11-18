#!/usr/bin/env python3
"""(b) Live microphone: stream the mic through the Behavioral Signals streaming API
with continuous valence/arousal and draw the same V/A plane as the video demo.

    uv run mic_live.py                 # default input device
    uv run mic_live.py --list          # list devices
    uv run mic_live.py --device 2

BILLABLE while it runs (streaming rate per minute). Close the window or press
Ctrl-C to stop. The session is saved as out/mic_<time>.wav plus its results
(out/mic_<time>-<hash>.points.json), so

    uv run file_video.py out/mic_<time>.wav

renders it to an MP4 without streaming again.
"""

from __future__ import annotations

import os
import sys
import json
import time
import wave
import signal
import argparse
import threading
from pathlib import Path
from datetime import datetime

import matplotlib


# Some Python builds on macOS (e.g. Homebrew's) have no tkinter, so TkAgg fails.
# On macOS use the native backend unless MPLBACKEND says otherwise.
if sys.platform == "darwin" and not os.environ.get("MPLBACKEND"):
    matplotlib.use("macosx")
from matplotlib import pyplot as plt
from matplotlib.animation import FuncAnimation

from vademo.api import BLOCK_BYTES, SAMPLE_RATE, decode, stream, cache_path
from vademo.plane import Plane


HERE = Path(__file__).resolve().parent


class FileAsMic:
    """Same interface as Mic, fed from a file at wall-clock pace (for testing without a mic)."""

    def __init__(self, path):
        self.path, self.pcm = Path(path), decode(path)
        self.recorded, self.level, self.dropped = [], 0.0, 0
        self._closed = threading.Event()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self._closed.set()

    def blocks(self):
        t0 = time.monotonic()
        for i in range(0, len(self.pcm), BLOCK_BYTES):
            if self._closed.is_set():
                return
            b = self.pcm[i : i + BLOCK_BYTES]
            self.recorded.append(b)
            self.level = 0.02
            delay = t0 + (i + len(b)) / 2 / SAMPLE_RATE - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            yield b

    def name(self):
        return f"simulated from {self.path.name}"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument(
        "--device",
        type=lambda s: int(s) if s.isdigit() else s,
        default=None,
        help="input device number or name (see --list)",
    )
    ap.add_argument("--list", action="store_true", help="list audio devices and exit")
    ap.add_argument("--trail", type=float, default=12.0, help="seconds of fading trail")
    ap.add_argument("--window", type=float, default=30.0, help="seconds in the time panels")
    ap.add_argument("--fps", type=int, default=20, help="window redraws per second")
    ap.add_argument(
        "--simulate",
        metavar="FILE",
        help="play a file into the live loop at real-time pace instead of the mic",
    )
    ap.add_argument(
        "--seconds",
        type=float,
        default=0,
        help="stop after this many seconds (0 = until the window is closed; "
        "required where no window can open)",
    )
    ap.add_argument("--no-save", action="store_true", help="do not save wav + results")
    a = ap.parse_args()

    if a.list:
        import sounddevice as sd

        print(sd.query_devices())
        return

    headless = matplotlib.get_backend().lower() == "agg"
    if headless and not a.seconds:
        sys.exit("no window can open here (no display?): pass --seconds N to run without one")

    points, state = [], {"pid": None, "error": None, "stop": False}
    mic = FileAsMic(a.simulate) if a.simulate else open_mic(a.device)
    print(f"input: {mic.name()}", flush=True)
    plane = Plane(title=f"live microphone · {mic.name()}", trail=a.trail, window=a.window)

    def worker():
        try:
            for pid, p in stream(mic.blocks()):
                state["pid"] = state["pid"] or pid
                points.append(p)
                print(
                    f"  {p.level:9s} {p.st:6.1f}-{p.et:6.1f}s  V {p.valence:+.3f}  A {p.arousal:+.3f}",
                    flush=True,
                )
        except BaseException as e:  # noqa: BLE001 -- surfaced in the window and on exit
            state["error"] = e

    # Ctrl-C asks the window to close, on every backend (Tk would otherwise
    # swallow it and keep streaming); a second Ctrl-C cannot lose the session.
    signal.signal(signal.SIGINT, lambda *_: state.update(stop=True))

    with mic:
        t0 = time.monotonic()
        th = threading.Thread(target=worker, daemon=True)
        th.start()

        def tick(_):
            if state["stop"]:
                plt.close(plane.fig)
            t = time.monotonic() - t0
            label = "● REC  " if mic.level > 0.01 else "○ REC  "
            state["peak"] = max(state.get("peak", 0.0), mic.level)
            if t > 4 and state["peak"] < 1e-4:
                label = "NO INPUT SIGNAL (device / mic permission?)  "
                if not state.get("warned"):
                    state["warned"] = True
                    print(
                        "warning: the input device delivers pure silence. Pick another "
                        "--device (see --list) or grant the terminal microphone access "
                        "(on macOS: System Settings > Privacy & Security > Microphone).",
                        flush=True,
                    )
            if state["error"]:
                label = f"ERROR: {state['error']}  "
            plane.update(t, sorted(points, key=lambda p: p.et), label=label)
            return []

        anim = (
            None
            if headless
            else FuncAnimation(plane.fig, tick, interval=1000 // a.fps, cache_frame_data=False)
        )
        if headless:  # timed run, no window
            while time.monotonic() - t0 < a.seconds and not state["stop"]:
                time.sleep(1 / a.fps)
                tick(0)
        else:
            if a.seconds:
                timer = plane.fig.canvas.new_timer(interval=int(a.seconds * 1000))
                timer.add_callback(plt.close, plane.fig)
                timer.start()
            plt.show()
        duration = time.monotonic() - t0
    del anim
    # Closing the mic ends the upload; the server still owes the results for
    # the last seconds of audio. Wait for the stream to finish before saving.
    print("stopping: waiting for the last results ...", flush=True)
    th.join(timeout=15)
    if th.is_alive():
        print("warning: the stream did not close within 15 s; the last values may be missing")

    if state["error"]:
        print(f"stream error: {state['error']}")
    print(
        f"pid {state['pid']}: {len(points)} values over {duration:.0f} s; "
        f"dropped {mic.dropped * 0.25:.2f} s of audio"
    )
    if a.no_save or not mic.recorded:
        return
    complete = not state["error"] and not th.is_alive()
    save_session(HERE / "out", mic.recorded, state["pid"], points, complete)


def open_mic(device):
    from vademo.mic import Mic  # needs PortAudio, so only imported for a real mic

    return Mic(device)


def save_session(out: Path, recorded: list[bytes], pid, points, complete: bool) -> Path:
    """Save the recording; save its results only if the stream ended cleanly, so a
    partial session is never mistaken for a complete one."""
    out.mkdir(exist_ok=True)
    wav = out / datetime.now().strftime("mic_%Y%m%d-%H%M%S.wav")
    pcm = b"".join(recorded)
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm)
    render = f"uv run file_video.py out/{wav.name}"
    if not complete:
        print(f"saved {wav}, without results (incomplete) -> {render} streams it again (billable)")
        return wav
    cache_path(wav, out).write_text(
        json.dumps(
            {
                "source": str(wav),
                "pid": pid,
                "level": "segment",
                "duration": len(pcm) / 2 / SAMPLE_RATE,
                "points": [
                    p.as_dict() for p in sorted(points, key=lambda p: (p.et, p.level != "segment"))
                ],
            },
            indent=1,
        )
    )
    print(f"saved {wav} (+ its results) -> render with: {render}")
    return wav


if __name__ == "__main__":
    main()
