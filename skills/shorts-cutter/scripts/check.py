#!/usr/bin/env python3
"""Check that everything shorts-cutter needs is installed. Prints install hints for anything missing."""
import importlib.util
import platform
import shutil
import subprocess
import sys

ok = True
mac = platform.system() == "Darwin"


def report(name, good, hint):
    global ok
    print(f"[{'ok' if good else 'MISSING'}] {name}" + ("" if good else f"  ->  {hint}"))
    ok = ok and good


report("python 3.9+", sys.version_info >= (3, 9), "install Python 3.9 or newer")
report("ffmpeg", shutil.which("ffmpeg") is not None,
       "brew install ffmpeg" if mac else "sudo apt install ffmpeg  (Windows: winget install ffmpeg)")
if shutil.which("ffmpeg"):
    f = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True).stdout
    report("ffmpeg with libass (for captions)", " subtitles " in f or " ass " in f,
           "install a full ffmpeg build (brew install ffmpeg includes libass)")
report("yt-dlp (only for links)", shutil.which("yt-dlp") is not None,
       "brew install yt-dlp" if mac else "pip install yt-dlp")
report("faster-whisper", importlib.util.find_spec("faster_whisper") is not None, "pip install faster-whisper")
cv = importlib.util.find_spec("cv2") is not None
report("opencv (face tracking)", cv, 'pip install "opencv-python-headless>=4.8,<5"')
if cv:
    import os
    import cv2
    try:
        has = os.path.exists(os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml"))
    except AttributeError:
        has = False
    report("opencv face model", has, 'pip install "opencv-python-headless>=4.8,<5"  (OpenCV 5 dropped the bundled model)')
print("\nAll set." if ok else "\nInstall the missing pieces, then run this again.")
sys.exit(0 if ok else 1)
