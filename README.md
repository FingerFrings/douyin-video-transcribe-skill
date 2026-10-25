# Douyin Video Transcribe Skill

A Hermes/agent skill for transcribing user-provided Douyin videos through a live browser session.

Flow:

1. User logs in / completes CAPTCHA in the browser.
2. Agent extracts the real `douyinvod` video URL from the page.
3. Agent downloads the video locally.
4. `ffmpeg` extracts audio.
5. `faster-whisper` transcribes to `.srt` and `.txt`.
6. Agent summarizes from the transcript.

See [`SKILL.md`](./SKILL.md) for the full procedure and safety rules.

## Safety

- Do not ask users for passwords, SMS codes, 2FA codes, browser cookies, or browser profile data.
- Do not use for private/unauthorized videos or bulk scraping.
- Use only for user-provided videos that the user is allowed to access.
