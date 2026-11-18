"""The valence/arousal plane, shared by the video and the live demo.

One figure, built once; `update(t, points)` moves the artists to time t.
A point is shown from the moment its segment has ended (plus an optional
latency), never before -- the picture is causal, as it would be live.
"""

from __future__ import annotations

import math

import numpy as np
import matplotlib
from matplotlib import pyplot as plt
from matplotlib.collections import LineCollection


BG = "#0f1724"
PANEL = "#162133"
GRID = "#2b3a52"
TEXT = "#e6edf7"
MUTED = "#8a9bb5"
VAL = "#4fc3f7"
ARO = "#ff8a65"
DOT = "#ffd54f"

QUADRANTS = [
    (0.55, 0.55, "positive\nactivated"),
    (-0.55, 0.55, "negative\nactivated"),
    (-0.55, -0.55, "negative\ncalm"),
    (0.55, -0.55, "positive\ncalm"),
]


class Plane:
    def __init__(
        self,
        title: str = "",
        trail: float = 12.0,
        window: float = 30.0,
        stale: float = 3.0,
        ease: float = 0.35,
        figsize=(12.8, 7.2),
        dpi=100,
    ):
        self.trail, self.window, self.stale, self.ease = trail, window, stale, ease
        self.pos = None
        self.last_t = None
        self.fig = plt.figure(figsize=figsize, dpi=dpi, facecolor=BG)
        f = self.fig
        f.text(0.035, 0.94, "Continuous valence & arousal", color=TEXT, fontsize=20, weight="bold")
        f.text(0.035, 0.905, title, color=MUTED, fontsize=11)
        self.status = f.text(0.965, 0.94, "", color=MUTED, fontsize=12, ha="right")
        f.text(
            0.035,
            0.018,
            "Estimated from the voice by the Behavioral Signals streaming API "
            "(continuous_valence / continuous_arousal), one value per segment, "
            "range −1 to 1.",
            color=MUTED,
            fontsize=9,
        )

        ax = self.ax = f.add_axes([0.065, 0.13, 0.40, 0.75])
        ax.set_facecolor(PANEL)
        ax.set_xlim(-1, 1)
        ax.set_ylim(-1, 1)
        ax.set_aspect("equal")
        for s in ax.spines.values():
            s.set_color(GRID)
        ax.tick_params(colors=MUTED, labelsize=9)
        ax.set_xticks([-1, -0.5, 0, 0.5, 1])
        ax.set_yticks([-1, -0.5, 0, 0.5, 1])
        ax.grid(color=GRID, lw=0.6, alpha=0.6)
        ax.axhline(0, color=MUTED, lw=1)
        ax.axvline(0, color=MUTED, lw=1)
        ax.set_xlabel("valence  →  more positive", color=TEXT, fontsize=11)
        ax.set_ylabel("arousal  →  more activated", color=TEXT, fontsize=11)
        for x, y, s in QUADRANTS:
            ax.text(x, y, s, color=MUTED, alpha=0.55, ha="center", va="center", fontsize=11)
        self.trail_lc = LineCollection([], linewidths=2, zorder=2)
        ax.add_collection(self.trail_lc)
        self.trail_sc = ax.scatter([], [], s=28, zorder=3)
        self.halo = ax.scatter([], [], s=900, color=DOT, alpha=0.18, zorder=5)
        self.dot = ax.scatter(
            [], [], s=170, color=DOT, edgecolors="white", linewidths=1.5, zorder=6
        )
        self.readout = ax.text(
            -0.97, -0.95, "", color=TEXT, fontsize=12, family="monospace", va="bottom", zorder=7
        )

        self.ts = []
        for i, (name, col) in enumerate([("valence", VAL), ("arousal", ARO)]):
            a = f.add_axes([0.545, 0.545 - i * 0.415, 0.42, 0.335])
            a.set_facecolor(PANEL)
            for s in a.spines.values():
                s.set_color(GRID)
            a.tick_params(colors=MUTED, labelsize=9)
            a.set_ylim(-1.05, 1.05)
            a.axhline(0, color=MUTED, lw=0.8)
            a.grid(color=GRID, lw=0.6, alpha=0.6)
            a.set_ylabel(name, color=col, fontsize=12)
            (seg,) = a.plot([], [], color=col, lw=2.2, drawstyle="steps-post")
            head = a.axvline(0, color=TEXT, lw=1, alpha=0.5)
            self.ts.append((a, seg, head, name))
        self.ts[1][0].set_xlabel("time (s)", color=MUTED, fontsize=10)

    # ------------------------------------------------------------------
    def update(self, t: float, points, latency: float = 0.0, label: str = ""):
        seen = [p for p in points if p.et + latency <= t]
        segs = [p for p in seen if p.level == "segment"]
        dt = 0.04 if self.last_t is None else max(0.0, t - self.last_t)
        self.last_t = t

        stale = True
        if segs:
            cur = segs[-1]
            target = np.array([cur.valence, cur.arousal])
            stale = t - (cur.et + latency) > self.stale
            if self.pos is None:
                self.pos = target.copy()
            else:
                k = 1 - math.exp(-dt / self.ease) if self.ease > 0 else 1.0
                self.pos = self.pos + k * (target - self.pos)
            self.dot.set_offsets([self.pos])
            self.halo.set_offsets([self.pos])
            c = MUTED if stale else DOT
            self.dot.set_color(c)
            self.dot.set_edgecolor("white")
            self.halo.set_alpha(0.0 if stale else 0.18)
            self.readout.set_text(f"V {cur.valence:+.2f}   A {cur.arousal:+.2f}")
        else:
            self.dot.set_offsets(np.empty((0, 2)))
            self.halo.set_offsets(np.empty((0, 2)))
            self.readout.set_text("")

        recent = [p for p in segs if t - (p.et + latency) <= self.trail]
        if recent:
            xy = np.array([[p.valence, p.arousal] for p in recent])
            age = np.array([t - (p.et + latency) for p in recent])
            alpha = np.clip(1 - age / self.trail, 0, 1) ** 1.6
            cols = np.zeros((len(recent), 4))
            cols[:, :3] = matplotlib.colors.to_rgb(DOT)
            cols[:, 3] = alpha * 0.8
            self.trail_sc.set_offsets(xy)
            self.trail_sc.set_color(cols)
            if len(xy) > 1:
                self.trail_lc.set_segments([xy[i : i + 2] for i in range(len(xy) - 1)])
                self.trail_lc.set_color(cols[1:] * [1, 1, 1, 0.7])
            else:
                self.trail_lc.set_segments([])
        else:
            self.trail_sc.set_offsets(np.empty((0, 2)))
            self.trail_lc.set_segments([])

        lo, hi = max(0.0, t - self.window), max(self.window, t)
        for a, seg_line, head, name in self.ts:
            a.set_xlim(lo, hi)
            xs, ys = [], []
            for p in segs:
                if xs and abs(xs[-1] - p.st) > 1e-6:  # gap = no speech: break the line
                    xs.append(xs[-1])
                    ys.append(np.nan)
                xs += [p.st, p.et]
                ys += [getattr(p, name)] * 2
            seg_line.set_data(xs, ys)
            head.set_xdata([t, t])

        state = (
            "no speech" if (stale and segs) else ("waiting for speech" if not segs else "speech")
        )
        self.status.set_text(f"{label}t = {t:6.1f} s   ·   {state}")
