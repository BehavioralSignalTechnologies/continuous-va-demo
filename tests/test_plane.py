"""The picture is causal: a value shows only once its segment has ended (plus latency)."""

from matplotlib.colors import to_hex

from vademo.api import Point
from vademo.plane import DOT, MUTED, Plane


POINTS = [Point("segment", 0.0, 2.0, 0.5, -0.25)]


def test_value_is_hidden_until_its_segment_ends_plus_latency():
    plane = Plane()

    plane.update(2.4, POINTS, latency=0.5)
    assert plane.readout.get_text() == ""
    assert len(plane.dot.get_offsets()) == 0

    plane.update(2.5, POINTS, latency=0.5)
    assert plane.readout.get_text() == "V +0.50   A -0.25"
    assert to_hex(plane.dot.get_facecolor()[0]) == DOT


def test_dot_turns_gray_after_3_s_without_speech():
    plane = Plane()

    plane.update(4.9, POINTS)
    assert plane.status.get_text().endswith("·   speech")

    plane.update(5.1, POINTS)
    assert plane.status.get_text().endswith("no speech")
    assert to_hex(plane.dot.get_facecolor()[0]) == MUTED
