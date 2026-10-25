---
name: douyin-video-transcribe
description: Transcribe Douyin videos via browser session.
version: 0.1.0
author: Eden Lane, Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [Douyin, Video, Transcription, Whisper, Browser]
    related_skills: [video-to-subtitle-summary]
---

# Douyin Video Transcribe

Use the live browser session to read a Douyin page after the user logs in, extract the playable video URL, download it locally, extract audio, transcribe with `faster-whisper`, then summarize from the transcript. This skill is for personal analysis of user-provided videos, not bulk scraping or bypassing access controls.

## When to Use

- User provides a `v.douyin.com` or `douyin.com/video/...` link and asks what the video says.
- User asks to turn a Douyin video into subtitles, transcript, or a summary.
- `yt-dlp` reports fresh cookies are needed, but the user can log in through the browser.

Don't use for: private/unauthorized videos, bulk downloading, credential handling, or reposting downloaded media.

## Prerequisites

- User must complete any Douyin login / CAPTCHA themselves in the browser. Never ask for or accept passwords, SMS codes, 2FA codes, or cookies in chat.
- `ffmpeg` must be available. In Hermes on this Mac, prefer `/Users/eden/.hermes/tools/ffmpeg-9.0.1-darwin-arm64/ffmpeg` when `ffmpeg` is not on `PATH`.
- `video-to-subtitle-summary` skill should be installed so its helper can install/use `faster-whisper`:
  - installer: `~/.hermes/skills/media/video-to-subtitle-summary/scripts/install_faster_whisper.py`
  - transcriber: `~/.hermes/skills/media/video-to-subtitle-summary/scripts/transcribe_faster_whisper.py`
- Default Whisper Python after installation: `~/.cache/video-to-subtitle-summary/faster-whisper-venv/bin/python`.

## Procedure

1. **Open the Douyin page in the browser.**
   Use `browser_exec` to navigate to the original URL and wait for load. If the page is a CAPTCHA/login page, tell the user to complete it locally and say when done. Completion criterion: `page_info()` shows a `douyin.com/video/<id>` page or useful title text.

2. **Extract metadata and playable video URL.**
   Use `browser_exec` with JavaScript:
   ```javascript
   (() => {
     const videos = [...document.querySelectorAll('video')]
       .map(v => ({src: v.currentSrc || v.src, duration: v.duration, poster: v.poster}))
       .filter(v => v.src);
     const src = videos.find(v => v.src.includes('douyinvod'))?.src || videos[0]?.src || '';
     const metas = [...document.querySelectorAll('meta')]
       .map(m => ({name:m.getAttribute('name'), property:m.getAttribute('property'), content:m.getAttribute('content')}))
       .filter(x => x.content);
     return JSON.stringify({url: location.href, title: document.title, text: document.body.innerText.slice(0, 5000), videos, src, metas}, null, 2);
   })()
   ```
   Ignore ad/placeholder clips such as `uuu_265.mp4`; select the `douyinvod` URL with the real duration. Completion criterion: a non-empty `douyinvod` URL and title/ID are captured.

3. **Create a run folder and save the direct URL.**
   Use a deterministic scratch folder such as `~/.hermes/cache/scratch/douyin_video_<video_id>/`. Write the extracted URL to `video_src.txt` and metadata to `metadata.json` or note it in the run log. Completion criterion: the run folder contains the URL needed to redownload without reopening the page while it remains valid.

4. **Download the video.**
   Use `terminal`:
   ```bash
   RUN="$HOME/.hermes/cache/scratch/douyin_video_<video_id>"
   VIDEO_URL="$(cat "$RUN/video_src.txt")"
   curl -L --fail --retry 2 --connect-timeout 15 --max-time 180 \
     -H 'Referer: https://www.douyin.com/' \
     -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36' \
     "$VIDEO_URL" -o "$RUN/video.mp4"
   ```
   Completion criterion: `video.mp4` exists and is non-empty.

5. **Extract audio.**
   Use `terminal`:
   ```bash
   RUN="$HOME/.hermes/cache/scratch/douyin_video_<video_id>"
   FFMPEG="/Users/eden/.hermes/tools/ffmpeg-9.0.1-darwin-arm64/ffmpeg"
   "$FFMPEG" -y -i "$RUN/video.mp4" -vn -acodec mp3 "$RUN/audio.mp3"
   ```
   Completion criterion: `audio.mp3` exists and is non-empty.

6. **Install `faster-whisper` if needed.**
   If `~/.cache/video-to-subtitle-summary/faster-whisper-venv/bin/python` does not import `faster_whisper`, run:
   ```bash
   python3 "$HOME/.hermes/skills/media/video-to-subtitle-summary/scripts/install_faster_whisper.py"
   ```
   Completion criterion: the venv Python can import `faster_whisper` and `ctranslate2`.

7. **Transcribe.**
   Use `terminal`; if this exceeds the foreground cap it may become a tracked background process — do not rerun; wait for completion.
   ```bash
   RUN="$HOME/.hermes/cache/scratch/douyin_video_<video_id>"
   SKILL_DIR="$HOME/.hermes/skills/media/video-to-subtitle-summary"
   FW="$HOME/.cache/video-to-subtitle-summary/faster-whisper-venv/bin/python"
   FW_MODEL_SIZE=small FW_DEVICE=auto "$FW" "$SKILL_DIR/scripts/transcribe_faster_whisper.py" \
     "$RUN/audio.mp3" --output-dir "$RUN"
   ```
   Completion criterion: `text.txt` and `subtitle.srt` are written.

8. **Summarize from transcript only.**
   Read `text.txt` and optionally `subtitle.srt`. Produce:
   - concise summary;
   - key points;
   - named tools/products mentioned;
   - transcript file paths.
   Correct obvious ASR errors only when the video title or context makes the correction clear; mention uncertain corrections explicitly.

## Pitfalls

- `yt-dlp` may identify the Douyin video but fail with “Fresh cookies are needed.” Browser extraction after user login is the preferred fallback.
- The page may include multiple `<video>` tags, including short UI/login clips. Pick the `douyinvod` URL with the real video duration.
- Douyin direct URLs are time-limited. Download immediately after extraction.
- The downloaded file may be enough even if `ffprobe` is unavailable; use `ffmpeg` directly for audio extraction.
- Whisper warnings about unauthenticated Hugging Face requests or mel-spec runtime warnings can appear while transcription still succeeds; verify output files instead of assuming failure.
- Do not expose or forward cookies, browser profile data, passwords, SMS codes, or 2FA codes.

## Verification

- Browser metadata includes the expected Douyin title and video ID.
- `video.mp4`, `audio.mp3`, `subtitle.srt`, and `text.txt` all exist in the run folder.
- Transcript language/probability from the transcriber output is plausible.
- Final answer states any ASR uncertainties and links only local output paths, not expiring `douyinvod` URLs unless the user explicitly asks.
