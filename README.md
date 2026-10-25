# Douyin Video Transcribe Skill

A Hermes/agent skill for transcribing user-provided Douyin videos through a live browser session.

Flow:

1. User logs in / completes CAPTCHA in the browser.
2. Agent extracts the real `douyinvod` video URL from the page.
3. Agent downloads the video locally.
4. `ffmpeg` extracts audio.
5. Bundled `faster-whisper` helper scripts create subtitles and plain text.
6. Agent summarizes from the transcript.

See [`SKILL.md`](./SKILL.md) for the full procedure and safety rules.

## Requirements

- Browser/session automation available to the agent.
- User can complete Douyin login/CAPTCHA locally. Do **not** share passwords, SMS codes, 2FA codes, browser cookies, or browser profile files.
- `python3`
- `curl`
- `ffmpeg`
- Network access to download the Douyin media URL and the first-run Whisper model.

The repository includes:

- `scripts/install_faster_whisper.py` — creates an isolated venv and installs `faster-whisper`.
- `scripts/transcribe_faster_whisper.py` — transcribes an audio file to `subtitle.srt` and `text.txt`.

## What the helper scripts do

### `install_faster_whisper.py`

This script prepares the local ASR runtime. It:

- probes PyPI mirrors and selects the fastest reachable one;
- creates a virtual environment, defaulting to `~/.cache/douyin-video-transcribe/faster-whisper-venv` when used by this skill;
- installs/upgrades `pip` and `faster-whisper`;
- verifies `faster_whisper` and `ctranslate2` imports;
- prints JSON containing the venv Python path, selected mirror, and installed versions.

### `transcribe_faster_whisper.py`

This script performs transcription. It:

- accepts an input audio path and `--output-dir`;
- reads optional runtime settings from `FW_MODEL_SIZE`, `FW_DEVICE`, and `FW_COMPUTE_TYPE`;
- auto-selects CPU/CUDA and a supported compute type;
- runs `faster-whisper` with VAD;
- writes `subtitle.srt` and `text.txt`;
- prints JSON containing language, probability, segment count, and output paths.

## How the agent summarizes

The scripts do not summarize anything — they only produce `subtitle.srt` and `text.txt`. The agent reads the transcript and writes the summary itself, using a fixed template so different agents produce comparable output:

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

Rules that keep the summary honest:

- Summaries come from `text.txt` only; the video title alone is never enough.
- `操作步骤` is omitted for non-tutorial videos, and `识别不确定处` is omitted when nothing is uncertain.
- A garbled name is marked `可能是：XXX` rather than silently corrected.
- The summary is a digest — the full transcript is not pasted into the answer.
- If the transcript is empty or unintelligible, the agent says so instead of inventing content.

## Safety

- Use only for videos the user is allowed to access.
- Do not use for private/unauthorized videos or bulk scraping.
- Do not publish downloaded media automatically.
- Do not expose expiring `douyinvod` URLs, browser cookies, or credentials.

## Quick install for agents

Clone this repository into a skills directory and load `SKILL.md`:

```bash
git clone https://github.com/edenlanehello/douyin-video-transcribe-skill.git ~/.hermes/skills/media/douyin-video-transcribe
```

Then ask the agent to summarize a Douyin URL.
