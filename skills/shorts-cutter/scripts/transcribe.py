#!/usr/bin/env python3
"""Transcribe a video with word timestamps (faster-whisper, runs locally).

usage: python3 transcribe.py VIDEO OUTDIR [--model small] [--language en]

Writes to OUTDIR:
  words.json      [[word, start, end], ...]
  segments.json   [[start, end, text], ...]
  transcript.txt  one line per segment: [mm:ss.s - mm:ss.s] text   (this is what Claude reads to pick clips)
"""
import argparse
import json
import os
import subprocess
import tempfile


def ts(t):
    return f"{int(t // 60):02d}:{t % 60:04.1f}"


ap = argparse.ArgumentParser()
ap.add_argument("video")
ap.add_argument("outdir")
ap.add_argument("--model", default="small", help="tiny, base, small, medium, large-v3 (bigger = better, slower)")
ap.add_argument("--language", default=None, help="e.g. en, ru. Default: auto-detect")
a = ap.parse_args()
os.makedirs(a.outdir, exist_ok=True)

from faster_whisper import WhisperModel

with tempfile.TemporaryDirectory() as tmp:
    wav = os.path.join(tmp, "a.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.video, "-vn", "-ac", "1", "-ar", "16000", wav], check=True)
    model = WhisperModel(a.model, device="auto", compute_type="int8")
    segs, info = model.transcribe(wav, language=a.language, word_timestamps=True, vad_filter=True)
    words, segments = [], []
    for s in segs:
        segments.append([round(s.start, 2), round(s.end, 2), s.text.strip()])
        for w in (s.words or []):
            words.append([w.word.strip(), round(w.start, 2), round(w.end, 2)])
        print(f"[{ts(s.start)} - {ts(s.end)}] {s.text.strip()}", flush=True)

json.dump(words, open(os.path.join(a.outdir, "words.json"), "w"), ensure_ascii=False)
json.dump(segments, open(os.path.join(a.outdir, "segments.json"), "w"), ensure_ascii=False)
with open(os.path.join(a.outdir, "transcript.txt"), "w") as f:
    for s, e, t in segments:
        f.write(f"[{ts(s)} - {ts(e)}] {t}\n")
print(f"\nlanguage: {info.language}  words: {len(words)}  segments: {len(segments)}  -> {a.outdir}")
