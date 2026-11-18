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
