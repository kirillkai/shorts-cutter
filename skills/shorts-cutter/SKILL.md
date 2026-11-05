---
name: shorts-cutter
description: Turn a long video (YouTube link or local file) into vertical 9:16 short clips with face tracking and word-by-word captions. Use when the user asks to clip, cut, or make shorts/reels/TikToks from a long video, podcast, stream or interview.
---

# Shorts Cutter

Turns one long video into ready-to-post vertical clips:
1. downloads the video (if it's a link),
2. transcribes it locally with word timestamps,
3. you (Claude) pick the strongest moments,
4. the script crops to 9:16 following the speaker's face, burns word-by-word captions and normalizes loudness.

Everything runs on the user's computer. No paid API is needed.

## Before you start
Ask only what you need, in one message, with sensible defaults:
- The source: a link or a file path.
- How many clips. Default 5.
- Clip length. Default 20 to 60 seconds.
- Captions on or off. Default on.

If the user says "just do it", use the defaults.

Remind the user once, briefly: only clip videos they own, have permission to use, or that a creator's clipping program allows.

`SKILL_DIR` below means this skill's folder (the base directory shown when the skill loads).

Work in a folder next to the video, e.g. `shorts/`, with `work/` for intermediate files and `out/` for the clips.

## Step 1. Check the setup
```bash
python3 SKILL_DIR/scripts/check.py
```
If something is missing, show the user the install command the script prints and wait. Typical setup on a Mac:
```bash
brew install ffmpeg yt-dlp
pip install faster-whisper "opencv-python-headless>=4.8,<5"
```
If pip refuses with "externally-managed-environment" (Homebrew Python), use a private venv and run every script with its python:
```bash
python3 -m venv ~/.shorts-cutter-venv
~/.shorts-cutter-venv/bin/pip install faster-whisper "opencv-python-headless>=4.8,<5"
# then use ~/.shorts-cutter-venv/bin/python instead of python3 below
```

## Step 2. Get the video
For a link:
```bash
yt-dlp -f "bv*[height<=1080]+ba/b[height<=1080]" --merge-output-format mp4 -o "work/source.%(ext)s" "URL"
```
For a file, use it as is.

## Step 3. Transcribe
```bash
python3 SKILL_DIR/scripts/transcribe.py work/source.mp4 work --model small
```
- Use `--language en` (or `ru`, etc.) if you know the language.
- `small` is a good default on a laptop. Use `medium` or `large-v3` for better accuracy if the user has time.
- The first run downloads the model once.

The script writes `work/transcript.txt`, with one line per segment and timestamps, plus `words.json` and `segments.json`.

## Step 4. Pick the clips (your job)
Read `work/transcript.txt` in full. Choose the clips by these rules:
- **Hook first.** The first sentence of the clip must work on a stranger with no context: a bold claim, a number, a conflict, a surprising answer, or a question that the clip answers. Never start mid-thought ("and so...", "but yeah").
- **One idea, with a payoff.** The clip ends right after the point lands: the answer, the punchline, the result. Don't trail off.
- **Self-contained.** It makes sense without the rest of the video. Cut out references like "as I said before".
- **Length.** Stay within the user's range, default 20–60 s. Shorter is better if the idea is complete.
- **Cut on sentence boundaries.** Use segment start and end times. Start 0.1 s before the first word and end 0.3 s after the last word.
- **Skip** intros, sponsor reads, "like and subscribe", and dead air.
- **Variety.** Don't pick two clips that make the same point.
- **Ranking.** Rank by how likely a stranger is to keep watching past 3 seconds.

Write `work/clips.json`:
```json
[
  {"start": 312.4, "end": 351.0, "title": "Why most startups die in year two", "hook": "Most startups don't die from competition."}
]
```
- `title`: 8 words or fewer, honest, usable as the post caption's first line.
- `hook`: the clip's first sentence as spoken.

Show the user the list (title, time range, length, hook) and offer to swap any clip before rendering. If they said "just do it", render right away.

## Step 5. Render
```bash
python3 SKILL_DIR/scripts/cut.py work/source.mp4 work/clips.json work/words.json out
```
What the script does:
- Landscape sources are cropped to 9:16 around the largest face, re-checked every 0.5 s, with smooth glides when the speaker moves. If no face is found, it center-crops.
- Vertical sources are kept as they are.
- Captions are burned in word by word, white with a black outline, in the lower middle of the frame.
- Audio is normalized to −14 LUFS.

Options:
- `--no-captions` turns captions off.
- `--no-track` uses a center crop instead of following the face.
- `--font "Montserrat"` sets the caption font. Any font installed on the computer works.

## Step 6. Report
Tell the user:
- where the clips are (`out/`);
- the list from `out/clips.md`;
- one line per clip on why it should work.

Suggest posting the strongest one first.

## Troubleshooting
- **No captions in the output.** The user's ffmpeg was built without libass. On a Mac, `brew reinstall ffmpeg`.
- **The crop follows the wrong person.** Re-run that clip with `--no-track`, or move its start or end to a moment where one person is on screen.
- **yt-dlp fails.** Update it (`brew upgrade yt-dlp` or `pip install -U yt-dlp`), or ask the user to download the file and give you the path.
- **Transcription is slow.** Use `--model base`, or transcribe only the part they care about. Cut it first with `ffmpeg -ss START -to END -i in.mp4 -c copy part.mp4`.
