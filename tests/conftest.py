"""Draw without a window in every test, on every OS (macOS would pick its native one)."""

import os


os.environ.setdefault("MPLBACKEND", "Agg")
