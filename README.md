# Shorts Cutter for Claude Code

Give Claude a long video, get back vertical clips that are ready to post.

- **Link or file in, 9:16 clips out.** Works with YouTube links (via yt-dlp) or any video on your computer.
- **Claude picks the moments.** It reads the full transcript and chooses clips that open with a hook and end on the payoff.
- **Face tracking.** Landscape videos are cropped to vertical around the speaker's face, with smooth glides when they move.
- **Word-by-word captions,** burned in.
- **Audio at −14 LUFS,** the loudness Reels, Shorts and TikTok expect.
- **Runs locally.** It transcribes with faster-whisper on your machine. No paid API.

## Install

In Claude Code:
```
/plugin marketplace add kirillkai/shorts-cutter
/plugin install shorts-cutter@shorts-cutter
```
Or copy `skills/shorts-cutter` into `~/.claude/skills/`.

In Claude Cowork or the Claude app: download [`shorts-cutter-skill.zip`](shorts-cutter-skill.zip) and upload it under Skills in Claude's settings. Then connect the folder with your video.

On the first run Claude sets up the tools for you: ffmpeg, deno and a private Python environment in `~/.shorts-cutter-venv`. That takes about 5 minutes, once. On a Mac you only need [Homebrew](https://brew.sh). To do it yourself instead, run `bash skills/shorts-cutter/scripts/setup.sh`.

Where it works:
- **Claude Code**: everything, including YouTube links.
- **Claude Cowork** (desktop app, with a folder connected): put the video file in that folder. Links work only if your network settings allow YouTube. The first run downloads a speech model (about 490 MB) into `shorts/.models` in that folder, once.
- **A plain web chat**: not supported. The video is processed on your computer.

## Use

Just ask:
```
cut this into 5 shorts: https://www.youtube.com/watch?v=...
```
Claude checks your setup, downloads and transcribes the video, shows you the clips it picked, and renders them to `shorts/out/`.

## Good to know
- Clip only videos you own, have permission to use, or that a creator's clipping program allows.
- The first run downloads the speech model once. That takes a few minutes. After that it works offline.
- If captions are missing, your ffmpeg has no libass. Run `brew reinstall ffmpeg`.

MIT license.
