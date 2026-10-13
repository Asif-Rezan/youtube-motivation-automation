# Private YouTube motivational storytelling cloud workflow

Code is implemented, but no complete AI story video has been rendered/uploaded
and no daily schedule is active. Component checks pass with synthetic fixtures.

## Free infrastructure

Use standard GitHub-hosted Ubuntu runners in this public repository for compute.
Use the existing Google Drive free allowance for owner-only checkpoints and test
videos. No S3, AWS credentials, paid bucket, Render service, or storage subscription
is required. Private video files are never committed or attached as GitHub Actions
artifacts in this public repository. Google Drive storage is shared with Gmail and
Photos. The pipeline stops near the 15 GB free allowance and never purchases space.
No automatic deletion is implemented; clear older videos yourself when needed.

## Pipeline

Groq original fictional English motivational story plus title/description/tags →
Hugging Face cinematic images → English AI narration → Whisper word timestamps →
FFmpeg 1920×1080 video with slow zoom, fades, subtitles and ducked background music
→ generated thumbnail → duration/decode validation → private Drive → private YouTube.
Speech model/account availability still needs a live check; configured defaults
follow the documented example and are not guaranteed available on every account.

## Music: YouTube Audio Library only

Download an instrumental track directly from YouTube Studio → Audio Library.
Prefer the Attribution not required filter. Record its title, artist and license.
For Creative Commons tracks, copy the exact attribution from YouTube Studio.
Do not copy music from arbitrary YouTube videos or commit a library track publicly.

Upload the downloaded track and provenance record into your private workflow
Drive folder from an authorized cloud session:

```
python setup_music.py /secure/downloads/track.mp3 --title "TRACK TITLE" --artist "ARTIST" --license "YouTube Audio Library License"
```

For attribution-required tracks add `--attribution-required --attribution "EXACT CREDIT"`.
The script stores music-manifest.json containing track ID, provenance, license and
SHA-256. Every live run downloads it privately, verifies the hash and adds required
attribution to the YouTube description. No library track is installed yet.

## Secure configuration

Add the following to GitHub repository Settings → Secrets and variables → Actions.
Do not send passwords, API keys or OAuth tokens in chat or commit them.

Secrets:
- GROQ_API_KEY: newly rotated key, not the exposed key from chat.
- HF_TOKEN: Hugging Face token with Inference Providers permission, not a password.
- DRIVE_TOKEN_JSON: authorized-user Google OAuth JSON with refresh token and drive.file scope.
- DRIVE_FOLDER_ID: owner-only workflow folder accessible to that OAuth application.
- YOUTUBE_TOKEN_JSON: authorized-user OAuth JSON with refresh token, youtube.upload and youtube.readonly scopes.

Variables:
- IMAGE_MODEL: current Hugging Face text-to-image model available to your account.
- EXPECTED_CHANNEL_ID: intended YouTube channel ID.
- TTS_MODEL / TTS_VOICE: supported English speech model and voice; optional documented defaults.

Enable Drive API and YouTube Data API in the OAuth project's Google Cloud console.
Authorize securely with the intended Google account. Limited drive.file access is
sufficient for files created by/selected for the app. Never broaden token scopes
without completing the Google consent flow. Existing ChatGPT connector access does
not automatically provide tokens to a GitHub runner. OAuth testing-mode refresh
token expiry may break unattended execution; configure production consent correctly.

## Test before scheduling

The cloud-test workflow has only workflow_dispatch; committing it does not run it.
Select Actions → Private cloud video test → Run workflow → checks first.
`render` performs generation and saves privately in Drive. `private-upload` uploads
privately after channel verification. Both need credentials and imported music.
No public publishing code exists. Watch the full private video and verify quality.
A completed private upload records last-private-test.json. Daily generation requires
this record AND DAILY_ENABLED=true. The pipeline does not check YouTube processing
or playback end-to-end automatically; that validation is still pending.

After the complete test passes, register 09:00 Asia/Dhaka (03:00 UTC), cron
`0 3 * * *`, command `python workflow.py daily`. GitHub scheduled workflows can be
delayed and do not guarantee exact start time. No schedule is registered now.
render-cron.example.yaml is a legacy optional billable example, NOT the free path.

## Reliability and limitations

Each Bangladesh date has a run key. Completed or ambiguous uploads block retries.
Resumable upload chunks retry transient failures without repeating videos.insert.
A checkpoint marked upload_started needs manual reconciliation before another run.
One concurrent runner is enforced by the workflow concurrency group. Never run
independent manual workers simultaneously: no distributed lock exists.

Story history and exact hashes reduce repeated content, but do not guarantee semantic
originality or quality. Character continuity, pronunciation, music balance and final
story coherence require review during initial testing. Transcription supplies word
caption timestamps. Videos outside 180–600 seconds fail before upload.

Generation calls are not automatically retried to avoid repeated credit consumption.
Scene assets are cached only within one runner; after a failed run they are not yet
restored into a fresh runner, so new attempts can regenerate limited-credit assets.
No failure notification integration is configured. Private Drive copies have no
automatic retention deletion. API generation free tiers are limited and may run out.

## Component checks

```
pip install -r requirements.txt
python -m unittest -v
python workflow.py preflight
```

The six original component tests validate an actual 1080p synthetic render, caption
timing, story validation, time rounding, missing credentials and disabled daily runs.
They are not a completed motivational-video test.

Documentation:
- https://support.google.com/youtube/answer/3376882
- https://docs.github.com/en/billing/concepts/product-billing/github-actions
- https://support.google.com/googleone/answer/2375123
- https://developers.google.com/workspace/drive/api/guides/api-specific-auth
- https://console.groq.com/docs/api-reference
- https://huggingface.co/docs/huggingface_hub/en/package_reference/inference_client
- https://developers.google.com/youtube/v3/guides/uploading_a_video
