"""The two scripts start and print their help without an API key or a microphone."""

import sys
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).parent.parent


@pytest.mark.parametrize("script", ["file_video.py", "mic_live.py"])
def test_help(script):
    out = subprocess.run(
        [sys.executable, str(ROOT / script), "--help"], capture_output=True, text=True, check=False
    )

    assert out.returncode == 0, out.stderr
    assert "usage:" in out.stdout


@pytest.mark.parametrize("args", [["file_video.py", "x.wav"], ["mic_live.py"]])
def test_fps_zero_is_refused(args, tmp_path):
    out = subprocess.run(
        [sys.executable, str(ROOT / args[0]), *args[1:], "--fps", "0"],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )

    assert out.returncode == 2, out.stderr
    assert "--fps must be 1 or more" in out.stderr
