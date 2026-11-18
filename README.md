# Continuous valence and arousal demos

<div align="center">

[![CI](https://github.com/BehavioralSignalTechnologies/continuous-va-demo/actions/workflows/ci.yml/badge.svg)](https://github.com/BehavioralSignalTechnologies/continuous-va-demo/actions/workflows/ci.yml)
[![License](https://badgen.net/badge/license/Apache-2.0/blue)](LICENSE)
[![Python](https://badgen.net/badge/python/3.10+/blue)](pyproject.toml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![readme.io](https://badgen.net/badge/readme.io/Documentation/?color=black)](https://behavioralsignals.readme.io/)
[![Discord](https://badgen.net/discord/members/fxjRrbMH3Q/?color=8978cc&icon=discord)](https://discord.com/invite/fxjRrbMH3Q)

</div>

See how a voice moves on the valence/arousal plane, using the continuous
valence and arousal outputs of the
[Behavioral Signals streaming API](https://behavioralsignals.readme.io/) and its
[Python SDK](https://github.com/BehavioralSignalTechnologies/behavioralsignals-python).

- **File → video** (`file_video.py`): turns an audio or video file into an MP4 of
  the plane, with the file as its sound track.
- **Live microphone** (`mic_live.py`): the same picture in a window, while you speak.

![A frame of the video: the valence/arousal plane with a moving dot and its trail, and valence and arousal over time](assets/screenshot.png)

## Install

You need:

- Python 3.10 or later and [uv](https://docs.astral.sh/uv/)
- ffmpeg, to read the input file and write the video
- On Linux, PortAudio and tkinter for the live demo
- A client ID (CID) and API key from the
  [Behavioral Signals portal](https://portal.behavioralsignals.com/)

| OS | Command |
| --- | --- |
| macOS | `brew install ffmpeg` |
| Ubuntu/Debian | `sudo apt install ffmpeg libportaudio2 python3-tk` |
| Windows | `winget install ffmpeg`, then open a new terminal |

Then:

```bash
git clone https://github.com/BehavioralSignalTechnologies/continuous-va-demo.git
cd continuous-va-demo
uv sync
```

Set your CID and API key, as for the SDK:

```bash
export BEHAVIORALSIGNALS_CID="your_cid"            # macOS / Linux
export BEHAVIORALSIGNALS_API_KEY="your_api_key"
```

```powershell
$env:BEHAVIORALSIGNALS_CID = "your_cid"            # Windows (PowerShell)
$env:BEHAVIORALSIGNALS_API_KEY = "your_api_key"
```

**Both demos are billable** at the streaming rate per minute of audio.

## File → video

Try it with the 48 s sample in `examples/` (two short calls, an angry one and
then a happy one):

```bash
uv run file_video.py examples/sample.m4a
```

It prints each value as it arrives and writes `out/sample_va.mp4`. The picture
above is a frame of it.

Any speech file works (wav, mp3, mp4, ...):

```bash
uv run file_video.py recording.wav                 # -> out/recording_va.mp4
uv run file_video.py call.mp3 -o call.mp4          # choose the output file
uv run file_video.py call.mp3 --latency 0.5        # show values with the live delay
```

- The file is streamed as fast as the server accepts it. The server splits it
  into segments the same way as live, so the values are the same.
- The results are saved in `out/`, so rendering the same file again (other
  `--fps`, `--trail`, `--window` or `--latency`) costs nothing. Add
  `--restream` to stream it again.

## Live microphone

```bash
uv run mic_live.py                                 # default microphone
uv run mic_live.py --list                          # list audio devices
uv run mic_live.py --device 4                      # use device 4 from the list
uv run mic_live.py --simulate examples/sample.m4a  # play a file in real time, no microphone
```

- To stop, close the window or press Ctrl-C.
- The session is saved in `out/` as `mic_<time>.wav` with its results. Turn it
  into a video without streaming again with
  `uv run file_video.py out/mic_<time>.wav`. Add `--no-save` to save nothing.
- If the stream failed or did not finish, only the recording is saved, and
  rendering it streams it again.
- Where no window can open (for example over SSH), add `--seconds N` to run for
  N seconds without one.
- On macOS, give the terminal microphone access (System Settings → Privacy &
  Security → Microphone). Without it, the mic records silence and the window
  shows "NO INPUT SIGNAL".

## Reading the picture

- Each segment of speech (usually 2 s, sometimes shorter) gets one value from
  −1 to 1 for **valence** (how positive the voice sounds) and **arousal** (how
  activated).
- The dot shows the latest value and glides to each new one over about a
  second. The trail shows the last 12 s (`--trail`), the time panels the last
  30 s (`--window`).
- A value appears when its segment ends. Live, that is about 0.3–0.4 s after a
  2 s segment and about 1.3 s after a shorter one.
- The dot turns gray ("no speech") after 3 s without a segment. Silence gets no
  value.
- The values are the `continuous_valence` and `continuous_arousal` results of
  the API, as returned. Nothing is computed locally.
- They estimate what the voice expresses, not how the speaker feels. Use them
  to follow trends, not as exact measurements.

For the API side, see
[Continuous valence and arousal](https://github.com/BehavioralSignalTechnologies/behavioralsignals-python#continuous-valence-and-arousal)
in the SDK README.

## Help

- Each script lists all its options with `--help`.
- Ask questions on [Discord](https://discord.com/invite/fxjRrbMH3Q) or open an
  [issue](https://github.com/BehavioralSignalTechnologies/continuous-va-demo/issues).
- Report security problems as described in [SECURITY.md](SECURITY.md).

## Development

```bash
uv sync --extra dev
uv run ruff check && uv run ruff format --check
uv run pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE).
