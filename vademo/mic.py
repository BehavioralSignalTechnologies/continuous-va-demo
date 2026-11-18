"""Microphone capture as a blocking iterator of 16 kHz int16 PCM.

The input stream is opened AT 16 kHz, so Core Audio does the rate conversion
once, continuously. Resampling each callback block on its own (the first
version did) restarts the filter at every block edge and shifts the values
noticeably. The callback only converts and queues; the generator drains the
queue for the streaming SDK. Every block is kept, so the session can be saved.
"""

from __future__ import annotations

import sys
import queue
import threading

import numpy as np
import sounddevice as sd

from .api import SAMPLE_RATE


class Mic:
    def __init__(self, device=None, rate: int = SAMPLE_RATE):
        self.device, self.rate = device, rate
        self.device_rate = rate  # open the device at the API's rate
        self._q: queue.Queue[bytes] = queue.Queue(maxsize=256)
        self._closed = threading.Event()
        self.recorded: list[bytes] = []
        self.level = 0.0
        self.dropped = 0
        self._stream = None

    def _callback(self, indata, frames, time_info, status):
        if status:
            print(status, file=sys.stderr)
        x = indata[:, 0].astype(np.float32)
        self.level = float(np.sqrt(np.mean(x**2)) + 1e-9)
        pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes()
        self.recorded.append(pcm)
        try:
            self._q.put_nowait(pcm)
        except queue.Full:
            self.dropped += 1  # uplink behind: drop rather than drift from wall-clock

    def __enter__(self):
        try:
            self._stream = sd.InputStream(
                device=self.device,
                channels=1,
                samplerate=self.rate,
                dtype="float32",
                blocksize=0,
                callback=self._callback,
            )
        except sd.PortAudioError as e:
            raise SystemExit(f"cannot open the input device at {self.rate} Hz: {e}")
        self._stream.start()
        return self

    def __exit__(self, *exc):
        self._closed.set()
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()

    def blocks(self):
        while not self._closed.is_set():
            try:
                yield self._q.get(timeout=0.5)
            except queue.Empty:
                continue
        while True:  # flush what was captured before the close
            try:
                yield self._q.get_nowait()
            except queue.Empty:
                return

    def name(self) -> str:
        d = sd.query_devices(self.device, "input")
        return f"{d['name']} (opened at {self.rate} Hz)"
