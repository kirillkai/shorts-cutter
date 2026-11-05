#!/usr/bin/env bash
# One-time setup for shorts-cutter. Safe to run again: it skips what is already installed.
# Installs ffmpeg + deno (Homebrew on Mac) and a private Python venv with yt-dlp, faster-whisper and OpenCV.
# deno is the JavaScript runtime yt-dlp needs for YouTube downloads.
# --lite: skip faster-whisper (Whisper needs huggingface.co anyway). Use it in Cowork, where commands have a
#         short time limit. If a run is cut off, run it again: pip keeps what it already downloaded.
set -e
VENV="$HOME/.shorts-cutter-venv"
LITE=0; [ "$1" = "--lite" ] && LITE=1

have() { command -v "$1" >/dev/null 2>&1; }

if [ "$(uname)" = "Darwin" ]; then
  if ! have brew; then
    echo "Homebrew is missing. Install it first (one line from https://brew.sh), then run this again."
    exit 1
  fi
  have ffmpeg || brew install ffmpeg
  have deno || brew install deno
else
  if ! have ffmpeg; then
    echo "ffmpeg is missing. Linux: sudo apt install ffmpeg   Windows: winget install ffmpeg"
    exit 1
  fi
  have deno || echo "Note: for YouTube links also install deno (https://deno.com). Local files work without it."
fi

PY=python3
have python3 || { echo "Python 3 is missing. Mac: brew install python"; exit 1; }

if [ ! -x "$VENV/bin/python" ]; then
  echo "Creating $VENV ..."
  $PY -m venv "$VENV"
fi
PKGS='sherpa-onnx numpy opencv-python-headless>=4.8,<5 yt-dlp[default]'
[ $LITE = 1 ] || PKGS="faster-whisper $PKGS"
set -f  # no globbing of yt-dlp[default]
"$VENV/bin/pip" install -q $PKGS

echo
"$VENV/bin/python" "$(dirname "$0")/check.py"
