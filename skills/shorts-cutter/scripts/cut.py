#!/usr/bin/env python3
"""Render vertical 9:16 clips with face tracking and word-by-word captions.

usage: python3 cut.py SOURCE CLIPS_JSON WORDS_JSON OUTDIR [--no-captions] [--no-track] [--budget SECONDS] [--fast]

Clips that are already rendered are skipped, so it is safe to run again. With --budget it stops before the
next clip when time runs low and exits with code 3 ("run the same command again").

CLIPS_JSON: [{"start": 12.3, "end": 48.0, "title": "...", "hook": "..."}, ...]   (seconds)
WORDS_JSON: [[word, start, end], ...]   (from transcribe.py)
"""
import os as _os, sys as _sys
_VENV = _os.path.expanduser("~/.shorts-cutter-venv")
_PY = _os.path.join(_VENV, "bin", "python")
if _os.path.exists(_PY) and _os.path.realpath(_sys.prefix) != _os.path.realpath(_VENV):
    _os.execv(_PY, [_PY] + _sys.argv)  # always run inside the shorts-cutter venv once setup.sh has made it

import argparse
import json
import os
import re
import subprocess
import tempfile

W_OUT, H_OUT = 1080, 1920
ap = argparse.ArgumentParser()
ap.add_argument("source")
ap.add_argument("clips")
ap.add_argument("words")
ap.add_argument("outdir")
ap.add_argument("--no-captions", action="store_true")
ap.add_argument("--no-track", action="store_true", help="center crop instead of following the face")
ap.add_argument("--font", default="Arial", help="caption font name installed on this computer")
ap.add_argument("--budget", type=float, default=0, help="stop before the next clip after about this many seconds")
ap.add_argument("--fast", action="store_true", help="faster x264 preset (slightly bigger files)")
a = ap.parse_args()
import time
T0 = time.time()
os.makedirs(a.outdir, exist_ok=True)


def probe(path):
    # -show_streams/-show_format work on old (4.x) and new ffprobe alike
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_streams", "-show_format",
                          "-of", "json", path], capture_output=True, text=True).stdout
    j = json.loads(out); st = j["streams"][0]
    w, h = st["width"], st["height"]
    rot = abs(int(float((st.get("tags") or {}).get("rotate", 0) or 0)))
    for sd in st.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = abs(int(float(sd["rotation"] or 0)))
    if rot in (90, 270): w, h = h, w
    return w, h, float(j["format"]["duration"])


def face_track(path, s, e, w, h, cw):
    """Return [(t, x_left)] keyframes relative to clip start. Falls back to center."""
    center = (w - cw) / 2
    try:
        import cv2
        casc = cv2.CascadeClassifier(os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml"))
        if casc.empty(): raise RuntimeError("no face model")
    except Exception as ex:
        print(f"  face tracking off ({ex}); using center crop")
        return [(0.0, center)]
    cap = cv2.VideoCapture(path)
    samples, t = [], s
    while t < e:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, fr = cap.read()
        if ok:
            fh, fw = fr.shape[:2]
            # frames come unrotated from OpenCV only if rotation metadata exists; handle portrait-in-landscape
            if (fw > fh) != (w > h):
                fr = cv2.rotate(fr, cv2.ROTATE_90_CLOCKWISE); fh, fw = fr.shape[:2]
            k = 640 / fw
            g = cv2.cvtColor(cv2.resize(fr, (640, int(fh * k))), cv2.COLOR_BGR2GRAY)
            faces = casc.detectMultiScale(g, 1.1, 5, minSize=(int(40), int(40)))
            if len(faces):
                x, y, fw2, fh2 = max(faces, key=lambda r: r[2] * r[3])
                samples.append((t - s, (x + fw2 / 2) / k / fw))
        t += 0.5
    cap.release()
    if not samples:
        print("  no face found; using center crop")
        return [(0.0, center)]
    # median smoothing, then hold the frame steady unless the face really moves
    xs = [c for _, c in samples]
    sm = [sorted(xs[max(0, i - 2):i + 3])[len(xs[max(0, i - 2):i + 3]) // 2] for i in range(len(xs))]
    keys, cur = [], None
    for (tt, _), c in zip(samples, sm):
        if cur is None or abs(c - cur) * w > cw * 0.12:
            cur = c; keys.append((tt, cur))
    out = []
    for tt, c in keys:
        x = min(max(c * w - cw / 2, 0), w - cw)
        out.append((round(tt, 2), round(x, 1)))
    return out


def crop_expr(keys):
    """Piecewise-linear x(t) for the ffmpeg crop filter, with 0.4 s glides between keyframes."""
    if len(keys) == 1:
        return str(keys[0][1])
    expr = str(keys[-1][1])
    for (t0, x0), (t1, x1) in reversed(list(zip(keys, keys[1:]))):
        g0 = max(t0, t1 - 0.4)
        seg = f"if(lt(t,{g0}),{x0},if(lt(t,{t1}),{x0}+({x1}-{x0})*(t-{g0})/{t1 - g0:.3f},{expr}))"
        expr = seg
    return expr


def ass_file(path, words, s, e, font):
    def at(t):
        t = max(0, t); return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"
    ws = [(w, ws_ - s, we - s) for w, ws_, we in words if ws_ >= s - 0.05 and we <= e + 0.05 and w.strip()]
    lines = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W_OUT}", f"PlayResY: {H_OUT}", "WrapStyle: 2", "",
             "[V4+ Styles]",
             "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
             f"Style: W,{font},96,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,7,2,2,60,60,640,1",
             "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    for i, (w, ws_, we) in enumerate(ws):
        end = ws[i + 1][1] if i + 1 < len(ws) else we + 0.3
        end = min(end, ws_ + 0.9)
        txt = re.sub(r"[{}\\]", "", w)
        lines.append(f"Dialogue: 0,{at(ws_)},{at(end)},W,,0,0,0,,{{\\fscx88\\fscy88\\t(0,80,\\fscx100\\fscy100)}}{txt}")
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    return len(ws)


def slug(t):
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:40] or "clip"


w, h, dur = probe(a.source)
clips = json.load(open(a.clips))
words = json.load(open(a.words))
vertical = w / h <= 0.6
cw = int(h * 9 / 16) // 2 * 2
report = ["# Clips", ""]
for i, c in enumerate(clips, 1):
    s, e = max(0.0, float(c["start"])), min(dur, float(c["end"]))
    title = c.get("title", f"clip {i}")
    name = f"{i:02d}_{slug(title)}.mp4"
    report += [f"## {i}. {title}", f"- file: {name}", f"- source: {s:.1f}s to {e:.1f}s ({e - s:.0f}s)",
               f"- hook: {c.get('hook', '')}", ""]
    final = os.path.join(a.outdir, name)
    if os.path.exists(final):
        print(f"[{i}/{len(clips)}] {title}  already rendered")
        continue
    # a clip takes roughly 1.5-3x its length to render on a laptop; stop early rather than get cut off
    if a.budget and time.time() - T0 + (e - s) * (1.5 if a.fast else 3) > a.budget:
        open(os.path.join(a.outdir, "clips.md"), "w").write("\n".join(report))
        print(f"NOT FINISHED: {i - 1} of {len(clips)} clips done. Run the same command again to continue.")
        raise SystemExit(3)
    print(f"[{i}/{len(clips)}] {title}  {s:.1f}-{e:.1f}s", flush=True)
    with tempfile.TemporaryDirectory() as tmp:
        if vertical:
            vf = f"scale={W_OUT}:{H_OUT}:force_original_aspect_ratio=decrease,pad={W_OUT}:{H_OUT}:(ow-iw)/2:(oh-ih)/2,setsar=1"
        else:
            keys = [(0.0, (w - cw) / 2)] if a.no_track else face_track(a.source, s, e, w, h, cw)
            vf = f"crop={cw}:{h}:'{crop_expr(keys)}':0,scale={W_OUT}:{H_OUT},setsar=1"
        if not a.no_captions:
            ass = os.path.join(tmp, "c.ass")
            if ass_file(ass, words, s, e, a.font):
                vf += f",subtitles={ass}"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{s:.3f}", "-to", f"{e:.3f}", "-i", a.source,
                        "-vf", vf, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-r", "30",
                        "-c:v", "libx264", "-crf", "20", "-preset", "veryfast" if a.fast else "medium",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                        "-f", "mp4", final + ".part"], check=True)
        os.replace(final + ".part", final)
open(os.path.join(a.outdir, "clips.md"), "w").write("\n".join(report))
print(f"\nDONE: {len(clips)} clips in {a.outdir}")
