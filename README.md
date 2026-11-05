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

Then install the tools once (Mac):
```
brew install ffmpeg yt-dlp
pip install faster-whisper "opencv-python-headless>=4.8,<5"
```
If pip says "externally-managed-environment", ask Claude to set up a venv. The skill knows how.

On Windows, use `winget install ffmpeg` and `pip install yt-dlp`. On Linux, use `sudo apt install ffmpeg` and `pip install yt-dlp`.

## Use

Just ask:
```
cut this into 5 shorts: https://www.youtube.com/watch?v=...
```
Claude checks your setup, downloads and transcribes the video, shows you the clips it picked, and renders them to `shorts/out/`.

## Good to know
- Clip only videos you own, have permission to use, or that a creator's clipping program allows.
- The first run downloads the speech model once. That takes a few minutes. After that it runs offline.
- If captions are missing, your ffmpeg has no libass. Run `brew reinstall ffmpeg`.

MIT license.
