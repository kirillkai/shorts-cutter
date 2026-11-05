#!/usr/bin/env python3
"""Check that everything shorts-cutter needs is installed. Prints install hints for anything missing."""
import os as _os, sys as _sys
_VENV = _os.path.expanduser("~/.shorts-cutter-venv")
_PY = _os.path.join(_VENV, "bin", "python")
if _os.path.exists(_PY) and _os.path.realpath(_sys.prefix) != _os.path.realpath(_VENV):
    _os.execv(_PY, [_PY] + _sys.argv)  # always run inside the shorts-cutter venv once setup.sh has made it

import importlib.util
import platform
import shutil
import subprocess
import sys

ok = True
mac = platform.system() == "Darwin"


def report(name, good, hint, required=True):
    global ok
    tag = "ok" if good else ("MISSING" if required else "no")
    print(f"[{tag}] {name}" + ("" if good else f"  ->  {hint}"))
    if required:
        ok = ok and good


def reachable(url):
    import urllib.request
    try:
        urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=6)
        return True
    except Exception as ex:  # an HTTP error still means the host answered
        return hasattr(ex, "code") and ex.code not in (403, 407)


has = lambda m: importlib.util.find_spec(m) is not None

report("python 3.9+", sys.version_info >= (3, 9), "install Python 3.9 or newer")
report("ffmpeg", shutil.which("ffmpeg") is not None,
       "brew install ffmpeg" if mac else "sudo apt install ffmpeg  (Windows: winget install ffmpeg)")
if shutil.which("ffmpeg"):
    f = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True).stdout
    report("ffmpeg with libass (for captions)", " subtitles " in f or " ass " in f,
           "install a full ffmpeg build (brew install ffmpeg includes libass)")
cv = has("cv2")
report("opencv (face tracking)", cv, 'pip install "opencv-python-headless>=4.8,<5"')
if cv:
    import os
    import cv2
    try:
        hm = os.path.exists(os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml"))
    except AttributeError:
        hm = False
    report("opencv face model", hm, 'pip install "opencv-python-headless>=4.8,<5"  (OpenCV 5 dropped the bundled model)')

# transcription: Whisper needs Hugging Face for the model; the lite path downloads from GitHub
hf = reachable("https://huggingface.co")
gh = reachable("https://github.com")
fw = has("faster_whisper") and hf
lite = has("sherpa_onnx") and has("numpy") and gh
report("transcriber", fw or lite, "run scripts/setup.sh  (needs huggingface.co or github.com)")
if fw or lite:
    print(f"     use: {'transcribe.py (Whisper)' if fw else 'transcribe_lite.py (Parakeet, models from GitHub)'}")

yt = (shutil.which("yt-dlp") is not None or has("yt_dlp")) and reachable("https://www.youtube.com")
report("YouTube links", yt and shutil.which("deno") is not None,
       "not available here: ask the user for the video file instead" if not reachable("https://www.youtube.com")
       else ("brew install deno" if mac else "install deno (https://deno.com)"), required=False)

print(f"\nAll set. Python: {sys.executable}" if ok else "\nRun scripts/setup.sh to install the missing pieces, then run this again.")
sys.exit(0 if ok else 1)
