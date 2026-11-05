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

Everything runs on the user's own computer. No paid API is needed.

## Before you start
Ask only what you need, in one message, with sensible defaults:
- The source: a link or a file. In Cowork, the file goes in a connected folder.
- How many clips. Default 5.
- Clip length. Default 20 to 60 seconds.
- Captions on or off. Default on.

If the user says "just do it", use the defaults.

Remind the user once, briefly: only clip videos they own, have permission to use, or that a creator's clipping program allows.

`SKILL_DIR` below means this skill's folder (the base directory shown when the skill loads). Always use its full path in commands.

**Run every command yourself with your shell tool.** Don't paste commands for the user to type. The only thing the user may need to do by hand is install Homebrew on a Mac, if it's missing.

## Where it runs
- **Claude Code** (terminal or the Code tab of the desktop app): everything works, including YouTube links.
- **Claude Cowork** (desktop app) with a folder connected: works with video files in that folder. YouTube links work only if the organization's network settings allow youtube.com. If they don't, ask the user to put the video file in the connected folder.
- **A plain chat with no shell and no folder:** say it needs Claude Code or Cowork with a folder connected, and stop.

In Cowork, run the commands in the shell that sees the connected folder (`$HOME/mnt/<folder>`). If that shell can't see `SKILL_DIR` (the skill is loaded somewhere else), copy the `scripts/` folder over first, for example as a tar archive in base64, and use that copy as `SKILL_DIR`. Cowork commands have a time limit of a few minutes, and background jobs stop when the command ends, so don't use `nohup` or `&`. Pass `--budget 150` to the long steps instead (below): they stop safely, keep their progress, and exit with code 3 until they're finished, so you just run the same command again.

Work in a `shorts/` folder next to the video, or in `~/Movies/shorts/` in Claude Code. Use `work/` for intermediate files and `out/` for the clips. In Cowork, `out/` must be inside the connected folder so the user can see the clips.

## Step 1. Setup (one time, about 5 minutes)
```bash
python3 "SKILL_DIR/scripts/check.py"
```
If anything required is missing, tell the user in one line that you'll install the tools into a private Python environment (`~/.shorts-cutter-venv`), plus ffmpeg and deno with Homebrew on a Mac. Then run:
```bash
bash "SKILL_DIR/scripts/setup.sh"
```
In Cowork, run `bash "SKILL_DIR/scripts/setup.sh" --lite` instead (it skips Whisper, whose model host is usually blocked there). If it is cut off by the time limit, run it again.

It is safe to run again. After setup, the scripts switch to that environment by themselves, so plain `python3` works in every step below. `check.py` also says which transcriber to use and whether YouTube links work here.

## Step 2. Get the video
For a link, if `check.py` says YouTube links work:
```bash
~/.shorts-cutter-venv/bin/python -m yt_dlp -f "bv*[height<=1080]+ba/b[height<=1080]" --merge-output-format mp4 -o "work/source.%(ext)s" "URL"
```
Otherwise, ask for the file. For a file, use it as is.

## Step 3. Transcribe
Use the transcriber that `check.py` names.

Whisper (best quality; it needs huggingface.co for the model):
```bash
python3 "SKILL_DIR/scripts/transcribe.py" work/source.mp4 work --model small
```
- Use `--language en` (or `ru`, etc.) if you know the language.
- `small` is a good default on a laptop. Use `medium` or `large-v3` for better accuracy if the user has time.

Lite (NVIDIA Parakeet; it downloads from GitHub, so it works in Cowork; English, Russian and 23 other European languages; the language is detected by itself):
```bash
python3 "SKILL_DIR/scripts/transcribe_lite.py" work/source.mp4 work --models "<folder>/shorts/.models" --budget 150
```
- In Cowork, keep `--models` inside the connected folder so the model (about 490 MB) is downloaded only once, not every session. Tell the user the first download can take 5 to 15 minutes.
- `--budget 150` makes it stop safely before the command time limit. Exit code 3 means "not finished": run the same command again until it prints `DONE`. Progress is kept between runs.

Both transcribers download their model on the first run. Transcription takes a while on long videos, so run it in the background and tell the user it can take a few minutes.

The script writes `work/transcript.txt`, with one line per segment and timestamps, plus `words.json` and `segments.json`.

## Step 4. Pick the clips (your job)
Read `work/transcript.txt` in full. Speech recognition often mishears names (for example "Claude Code" heard as something else). Fix those words in `work/words.json` before rendering, because the captions come from it.

Choose the clips by these rules:
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
python3 "SKILL_DIR/scripts/cut.py" work/source.mp4 work/clips.json work/words.json out
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
- `--fast --budget 150` is for Cowork: a faster encoder preset, and it stops before the time limit. Exit code 3 means "run the same command again". Clips that are already rendered are skipped.

## Step 6. Report
Tell the user:
- where the clips are (`out/`);
- the list from `out/clips.md`;
- one line per clip on why it should work.

Suggest posting the strongest one first.

## Troubleshooting
- **No captions in the output.** The user's ffmpeg was built without libass. On a Mac, `brew reinstall ffmpeg`.
- **The crop follows the wrong person.** Re-run that clip with `--no-track`, or move its start or end to a moment where one person is on screen.
- **yt-dlp fails.** Update it with `~/.shorts-cutter-venv/bin/pip install -U "yt-dlp[default]"`, and check that deno is installed. If it still fails, ask the user to download the file and give you the path.
- **Transcription is slow.** Use `--model base`, or transcribe only the part they care about. Cut it first with `ffmpeg -ss START -to END -i in.mp4 -c copy part.mp4`.
