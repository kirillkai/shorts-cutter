#!/usr/bin/env python3
"""Transcribe a video with word timestamps using sherpa-onnx + NVIDIA Parakeet TDT v3 (25 European languages,
including English and Russian). Everything it downloads comes from GitHub, so it also works where Hugging Face
is blocked (for example in Claude Cowork).

usage: python3 transcribe_lite.py VIDEO OUTDIR [--models DIR] [--threads 4] [--budget SECONDS]

--budget: stop after about this many seconds and exit with code 3 ("not finished, run the same command
again"). Progress is saved, so each run continues where the last one stopped. Use it where a command has a
time limit, such as Cowork.

Writes the same files as transcribe.py:
  words.json      [[word, start, end], ...]
  segments.json   [[start, end, text], ...]
  transcript.txt  one line per segment: [mm:ss.s - mm:ss.s] text
"""
import os as _os, sys as _sys
_VENV = _os.path.expanduser("~/.shorts-cutter-venv")
_PY = _os.path.join(_VENV, "bin", "python")
if _os.path.exists(_PY) and _os.path.realpath(_sys.prefix) != _os.path.realpath(_VENV):
    _os.execv(_PY, [_PY] + _sys.argv)  # always run inside the shorts-cutter venv once setup.sh has made it

import argparse
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import time
import wave

T0 = time.time()
BUDGET = 0


def left():
    return BUDGET - (time.time() - T0) if BUDGET else 1e9


def unfinished(msg):
    print(f"NOT FINISHED: {msg}. Run the same command again to continue.", flush=True)
    sys.exit(3)

REL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/"
MODEL = "sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8"


def ts(t):
    return f"{int(t // 60):02d}:{t % 60:04.1f}"


def fetch(url, dst):
    """Download with resume. curl copes better with slow proxies than urllib, so prefer it."""
    import shutil
    tmp = dst + ".part"
    have = os.path.getsize(tmp) // 1048576 if os.path.exists(tmp) else 0
    print(f"downloading {os.path.basename(dst)} (once; {have} MB so far) ...", flush=True)
    if shutil.which("curl"):
        while True:
            if left() < 15:
                unfinished("model download")
            cmd = ["curl", "-fL", "-sS", "-C", "-", "--speed-limit", "20000", "--speed-time", "30", "-o", tmp, url]
            if BUDGET:
                cmd[1:1] = ["--max-time", str(int(left() - 10))]
            r = subprocess.run(cmd)
            if r.returncode == 0:
                break
            if r.returncode not in (18, 28, 56, 92):  # partial, timeout, recv error, http2 stream
                sys.exit(f"download failed (curl {r.returncode}): {url}")
    else:
        urllib.request.urlretrieve(url, tmp)
    os.replace(tmp, dst)


def ensure_models(d):
    os.makedirs(d, exist_ok=True)
    m = os.path.join(d, MODEL)
    if not os.path.exists(os.path.join(m, "tokens.txt")):
        tb = os.path.join(d, MODEL + ".tar.bz2")
        if not os.path.exists(tb):
            fetch(REL + MODEL + ".tar.bz2", tb)  # about 490 MB
        if left() < 150:
            unfinished("model downloaded, unpacking is next")
        print("unpacking ...", flush=True)
        tmpd = os.path.join(d, ".unpack")
        import shutil
        shutil.rmtree(tmpd, ignore_errors=True)
        with tarfile.open(tb) as t:
            t.extractall(tmpd)
        os.replace(os.path.join(tmpd, MODEL), m)
        shutil.rmtree(tmpd, ignore_errors=True)
        os.remove(tb)
    vad = os.path.join(d, "silero_vad.onnx")
    if not os.path.exists(vad):
        fetch(REL + "silero_vad.onnx", vad)
    return m, vad


ap = argparse.ArgumentParser()
ap.add_argument("video")
ap.add_argument("outdir")
ap.add_argument("--models", default=os.path.expanduser("~/.shorts-cutter-models"))
ap.add_argument("--threads", type=int, default=max(1, min(8, os.cpu_count() or 4)))
ap.add_argument("--budget", type=float, default=0)
a = ap.parse_args()
BUDGET = a.budget
os.makedirs(a.outdir, exist_ok=True)

try:
    import numpy as np
    import sherpa_onnx
except ImportError:
    sys.exit("Missing packages. Run scripts/setup.sh once, then try again.")

mdir, vad_path = ensure_models(a.models)
rec = sherpa_onnx.OfflineRecognizer.from_transducer(
    encoder=os.path.join(mdir, "encoder.int8.onnx"), decoder=os.path.join(mdir, "decoder.int8.onnx"),
    joiner=os.path.join(mdir, "joiner.int8.onnx"), tokens=os.path.join(mdir, "tokens.txt"),
    model_type="nemo_transducer", num_threads=a.threads)

wav = os.path.join(a.outdir, ".audio16k.wav")
if not os.path.exists(wav):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.video, "-vn", "-ac", "1", "-ar", "16000",
                    "-f", "wav", wav + ".tmp"], check=True)
    os.replace(wav + ".tmp", wav)
w = wave.open(wav)
x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768
state_path = os.path.join(a.outdir, ".lite_state.json")
state = json.load(open(state_path)) if os.path.exists(state_path) else {}

if "chunks" not in state:
    # speech regions with silero VAD, merged into chunks of at most ~25 s
    cfg = sherpa_onnx.VadModelConfig()
    cfg.silero_vad.model = vad_path
    cfg.silero_vad.min_silence_duration = 0.35
    cfg.silero_vad.min_speech_duration = 0.2
    cfg.silero_vad.max_speech_duration = 25
    cfg.sample_rate = 16000
    vad = sherpa_onnx.VoiceActivityDetector(cfg, buffer_size_in_seconds=60)
    regions, win = [], cfg.silero_vad.window_size
    for i in range(0, len(x), win):
        vad.accept_waveform(x[i:i + win])
        while not vad.empty():
            s = vad.front.start / 16000
            regions.append([s, s + len(vad.front.samples) / 16000]); vad.pop()
    vad.flush()
    while not vad.empty():
        s = vad.front.start / 16000
        regions.append([s, s + len(vad.front.samples) / 16000]); vad.pop()

    chunks = []
    for s, e in regions:
        if chunks and s - chunks[-1][1] < 0.6 and e - chunks[-1][0] < 25:
            chunks[-1][1] = e
        else:
            chunks.append([s, e])

    state = {"chunks": chunks, "done": {}}
    json.dump(state, open(state_path, "w"))
chunks = state["chunks"]

done = state["done"]
for ci, (s, e) in enumerate(chunks):
    if str(ci) in done:
        continue
    if left() < 20:
        json.dump(state, open(state_path, "w"))
        unfinished(f"transcribed {len(done)} of {len(chunks)} parts")
    a0, a1 = max(0, s - 0.15), min(len(x) / 16000, e + 0.15)
    st = rec.create_stream()
    st.accept_waveform(16000, x[int(a0 * 16000):int(a1 * 16000)])
    rec.decode_stream(st)
    r = st.result
    toks, tims = list(r.tokens), list(r.timestamps)
    seg_words = []
    for k, (tok, t) in enumerate(zip(toks, tims)):
        t = a0 + t
        nxt = a0 + tims[k + 1] if k + 1 < len(tims) else a1
        if tok.startswith((" ", "▁")) or not seg_words:
            seg_words.append([tok.replace("▁", " ").strip(), t, nxt])
        else:
            seg_words[-1][0] += tok
            seg_words[-1][2] = nxt
    seg_words = [[w_, round(b, 2), round(min(c, b + 1.2), 2)] for w_, b, c in seg_words if w_]
    done[str(ci)] = seg_words
    if ci % 5 == 0:
        json.dump(state, open(state_path, "w"))
        print(f"  {len(done)}/{len(chunks)} parts", flush=True)
json.dump(state, open(state_path, "w"))

words, segments = [], []
for ci in range(len(chunks)):
    seg_words = done.get(str(ci)) or []
    words += seg_words
    # one transcript line per sentence, so clips can start and end on sentence boundaries
    cur = []
    for wd in seg_words:
        cur.append(wd)
        if wd[0][-1:] in ".?!\u2026" or wd is seg_words[-1]:
            segments.append([cur[0][1], cur[-1][2], " ".join(c[0] for c in cur)])
            cur = []

json.dump(words, open(os.path.join(a.outdir, "words.json"), "w"), ensure_ascii=False)
json.dump(segments, open(os.path.join(a.outdir, "segments.json"), "w"), ensure_ascii=False)
with open(os.path.join(a.outdir, "transcript.txt"), "w") as f:
    for s, e, t in segments:
        f.write(f"[{ts(s)} - {ts(e)}] {t}\n")
print(f"\nDONE. words: {len(words)}  segments: {len(segments)}  -> {a.outdir}")
