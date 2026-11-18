# Contributing

Thanks for helping improve the continuous valence and arousal demos. By taking part, you agree to
follow our [Code of Conduct](CODE_OF_CONDUCT.md).

This repo is a demo of the [Behavioral Signals API](https://behavioralsignals.readme.io/). For
changes to the API client itself, see the
[Python SDK](https://github.com/BehavioralSignalTechnologies/behavioralsignals-python).

## Report a bug or ask for a feature

Open an [issue](https://github.com/BehavioralSignalTechnologies/continuous-va-demo/issues/new/choose).
Never paste your API key or CID in an issue.

To report a security problem, follow [SECURITY.md](SECURITY.md) instead.

## Set up

Follow [Install](README.md#install) in the README, then install the dev tools:

```bash
uv sync --extra dev
```

CI uses the versions pinned in `uv.lock`. If you change `pyproject.toml`, run `uv lock` and commit
`uv.lock`, or CI may fail.

## Code style and tests

We use [ruff](https://docs.astral.sh/ruff/) with the settings in `ruff.toml` (line length 100).
The tests don't call the API and need no microphone, so they need no credentials. Before you open a
pull request, run:

```bash
uv run ruff check
uv run ruff format
uv run pytest
```

CI runs ruff, and runs the tests on Python 3.10 to 3.14 on Linux, and on Windows and macOS.

## Pull requests

1. Create a branch from `main`.
2. Keep each pull request to one change.
3. If you change how the demos are used, update `README.md`.
4. Open the pull request.
