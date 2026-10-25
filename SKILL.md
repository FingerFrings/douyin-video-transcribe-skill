---
name: douyin-video-transcribe
description: Transcribe Douyin videos via browser session.
version: 0.3.0
author: Eden Lane, Hermes Agent
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [Douyin, Video, Transcription, Whisper, Browser]
    related_skills: []
---

# Douyin Video Transcribe

Use a live browser session to open a user-provided Douyin page, let the user complete login/CAPTCHA, extract the playable video URL, download it locally, extract audio, transcribe with bundled `faster-whisper` helpers, and summarize from the transcript. This skill is for personal analysis of videos the user is allowed to access, not bulk scraping or bypassing access controls.

## When to Use

- User provides a `v.douyin.com` or `douyin.com/video/...` link and asks what the video says.
- User asks to turn a Douyin video into subtitles, transcript, or a summary.
- `yt-dlp` reports fresh cookies are needed, but the user can log in through the browser.

Don't use for: private/unauthorized videos, bulk downloading, credential handling, reposting media, or circumventing platform restrictions.

## Prerequisites

- A browser tool/session that can open Douyin. The user must complete any Douyin login or CAPTCHA themselves. Never ask for or accept passwords, SMS codes, 2FA codes, cookies, or browser profile data in chat.
- `curl`, `python3`, and `ffmpeg` must be available. If `ffmpeg` is missing, stop and tell the user to install it (`brew install ffmpeg` on macOS, `sudo apt install ffmpeg` on Debian/Ubuntu) or provide its absolute path.
- This repository bundles two helper scripts:
  - `scripts/install_faster_whisper.py` creates a dedicated venv and installs `faster-whisper`.
  - `scripts/transcribe_faster_whisper.py` runs transcription and writes `subtitle.srt` and `text.txt`.
- Default Whisper Python after installation: `~/.cache/douyin-video-transcribe/faster-whisper-venv/bin/python`.

## Helper Scripts

`install_faster_whisper.py` is an installer, not a transcriber. It probes several PyPI mirrors, selects the fastest reachable one, creates an isolated virtual environment, installs/upgrades `pip` and `faster-whisper`, verifies imports for `faster_whisper` and `ctranslate2`, then prints a JSON payload with the venv Python path and versions. Use it when the venv is missing or cannot import the transcription dependencies.

`transcribe_faster_whisper.py` is the transcription runner. It accepts an audio file and output directory, chooses device/compute settings from arguments or environment (`FW_MODEL_SIZE`, `FW_DEVICE`, `FW_COMPUTE_TYPE`), loads `faster-whisper`, transcribes with VAD, and writes:

- `subtitle.srt` — timestamped subtitles;
- `text.txt` — plain transcript;
- JSON on stdout with language, language probability, segment count, and output paths.

## Procedure

1. **Preflight local tools.**
   Use `terminal` from the skill repository root:
   ```bash
   python3 --version
   command -v curl
   command -v ffmpeg
   test -f scripts/install_faster_whisper.py
   test -f scripts/transcribe_faster_whisper.py
   ```
   Completion criterion: all commands succeed. If `ffmpeg` is not found, ask the user to install it or provide a path; do not continue to transcription without audio extraction capability.

2. **Open the Douyin page in the browser.**
   Use `browser_exec` to navigate to the original URL and wait for load. If the page is a CAPTCHA/login page, tell the user to complete it locally and say when done. Completion criterion: `page_info()` shows a `douyin.com/video/<id>` page or useful title text.

3. **Extract metadata and playable video URL.**
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

4. **Create a run folder and save metadata.**
   Use a deterministic scratch folder such as `~/.hermes/cache/scratch/douyin_video_<video_id>/`. Write the extracted URL to `video_src.txt` and metadata to `metadata.json` or `metadata.txt`. Completion criterion: the run folder contains the URL and title/ID needed to proceed.

5. **Download the video immediately.**
   Douyin direct URLs are time-limited. Use `terminal`:
   ```bash
   RUN="$HOME/.hermes/cache/scratch/douyin_video_<video_id>"
   VIDEO_URL="$(cat "$RUN/video_src.txt")"
   curl -L --fail --retry 2 --connect-timeout 15 --max-time 180 \
     -H 'Referer: https://www.douyin.com/' \
     -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36' \
     "$VIDEO_URL" -o "$RUN/video.mp4"
   ```
   Completion criterion: `video.mp4` exists and is non-empty.

6. **Extract audio.**
   Use `terminal`:
   ```bash
   RUN="$HOME/.hermes/cache/scratch/douyin_video_<video_id>"
   ffmpeg -y -i "$RUN/video.mp4" -vn -acodec mp3 "$RUN/audio.mp3"
   ```
   Completion criterion: `audio.mp3` exists and is non-empty.

7. **Install `faster-whisper` if needed.**
   Use the bundled installer only when the venv Python is missing or imports fail:
   ```bash
   FW="$HOME/.cache/douyin-video-transcribe/faster-whisper-venv/bin/python"
   if [ ! -x "$FW" ] || ! "$FW" - <<'PY'
import faster_whisper, ctranslate2
PY
   then
     python3 scripts/install_faster_whisper.py --venv-dir "$HOME/.cache/douyin-video-transcribe/faster-whisper-venv"
   fi
   ```
   Completion criterion: the venv Python can import `faster_whisper` and `ctranslate2`.

8. **Transcribe.**
   Use `terminal`; if the command becomes a tracked background process, do not rerun it—wait for completion.
   ```bash
   RUN="$HOME/.hermes/cache/scratch/douyin_video_<video_id>"
   FW="$HOME/.cache/douyin-video-transcribe/faster-whisper-venv/bin/python"
   FW_MODEL_SIZE=small FW_DEVICE=auto "$FW" scripts/transcribe_faster_whisper.py \
     "$RUN/audio.mp3" --output-dir "$RUN"
   ```
   Completion criterion: `text.txt` and `subtitle.srt` are written.

9. **Summarize from the transcript only.**
   Read `text.txt` first; use `subtitle.srt` only to disambiguate names and to locate timestamps. Never summarize from the video title alone, and never add facts that are not in the transcript.

   Output exactly these sections, in this order, in the user's language:

   ```markdown
   ### 视频内容总结
   2–4 sentences describing what the video is about. Prose, no bullets.

   ### 核心要点
   - 3–6 bullets. Each bullet states one claim the video explicitly makes.

   ### 提到的工具/产品
   - `名称` — 一句话说明用途

   ### 操作步骤
   1. Ordered steps — only when the video is a tutorial/walkthrough.

   ### 识别不确定处
   - `转写原文` → `推测为 …`（依据：标题/上下文）

   ### 生成文件
   - 视频：`…/video.mp4`
   - 音频：`…/audio.mp3`
   - 字幕：`…/subtitle.srt`
   - 文本：`…/text.txt`
   ```

   Rules for this step:
   - Omit `操作步骤` when the video is not a tutorial, and omit `识别不确定处` when there are none. Keep every other section.
   - Mark a name as `可能是：XXX` when ASR likely garbled it; never silently rewrite a name.
   - Fix an obvious ASR error only when the video title or surrounding context makes the correction unambiguous, and list it under `识别不确定处`.
   - The summary is a digest, not a transcript replacement — do not paste the full `text.txt`.
   - Keep file paths out of the summary prose; they belong in `生成文件`.
   - If `text.txt` is empty or mostly unintelligible, say so plainly and point to the media files. Never invent a summary from the title.
   - If the user asked only for subtitles or the raw transcript, return the file path and skip this template.

## Pitfalls

- `yt-dlp` may identify the Douyin video but fail with “Fresh cookies are needed.” Browser extraction after user login is the preferred fallback.
- The page may include multiple `<video>` tags, including short UI/login clips. Pick the `douyinvod` URL with the real video duration.
- Douyin direct URLs expire. Download immediately after extraction.
- The downloaded file may be usable even if `ffprobe` is unavailable; use `ffmpeg` directly for audio extraction.
- Whisper warnings about unauthenticated Hugging Face requests or mel-spec runtime warnings can appear while transcription still succeeds; verify output files instead of assuming failure.
- First transcription may download a Whisper model and take several minutes.
- Do not expose or forward cookies, browser profile data, passwords, SMS codes, or 2FA codes.

## Verification

- Browser metadata includes the expected Douyin title and video ID.
- `video.mp4`, `audio.mp3`, `subtitle.srt`, and `text.txt` all exist in the run folder.
- Transcriber JSON reports plausible language, language probability, and segment count.
- Final answer states any ASR uncertainties and links local output paths only; do not share expiring `douyinvod` URLs unless the user explicitly asks.
