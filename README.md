# YouTube motivational storytelling cloud workflow

Implementation draft. No cloud service or daily schedule has been activated.
No finished AI-narrated story has been produced or uploaded yet.

## Pipeline

Groq original English story and metadata → Hugging Face cinematic images → Groq
speech per scene → Whisper word timestamps → FFmpeg 1920×1080 video with slow
zoom, fades, subtitles and ducked licensed instrumental music → generated
thumbnail → validation → private S3-compatible storage → private YouTube upload.

No public publishing code exists. YouTube OAuth is checked against
EXPECTED_CHANNEL_ID before upload. Wrong accounts fail closed. Videos outside
180–600 seconds fail before upload. The test aims for about 5–6 minutes.

## Current blockers

1. Target repository access is now verified. Cloud deployment is not yet created.
2. GROQ_API_KEY, HF_TOKEN and IMAGE_MODEL must be configured. Confirm current
   provider/model availability and licenses before live testing. TTS defaults
   follow the API example but account availability has not been verified.
3. YouTube authorized-user OAuth JSON must include upload and read permissions,
   with a refresh token and the intended channel. Create Google Cloud OAuth app,
   enable YouTube Data API, authorize through a secure consent flow, and place
   the resulting JSON in the host's secret settings. Never paste secrets in chat
   or commit them. Google OAuth testing-mode token expiration can interrupt
   unattended jobs; configure production consent appropriately.
4. Private S3-compatible bucket and narrowly scoped storage credentials needed.
5. MUSIC_URL must point to downloadable instrumental music with permission to
   use on monetized YouTube videos. Put attribution in MUSIC_CREDIT if required.
6. Budget approval is needed before billable deployment. Free tiers are limited;
   no cloud AI service here is assumed unlimited or guaranteed free.

## Build and verify in a cloud runner

```
docker build -t youtube-motivation .
docker run --rm youtube-motivation python -m unittest -v
docker run --rm --env-file /secure/path/workflow.env youtube-motivation python workflow.py preflight
docker run --rm --env-file /secure/path/workflow.env youtube-motivation python workflow.py test
```

First keep UPLOAD_ENABLED=false. Inspect rendered video, music balance, character
consistency, caption timings, pronunciation, thumbnail and metadata. Then enable
UPLOAD_ENABLED=true for the private test, after inspecting/resetting the test
checkpoint as necessary. An upload_started checkpoint must be reconciled against
YouTube before retrying; do not delete it blindly. Verify YouTube processing and
playback of the entire private video. Only then set DAILY_ENABLED=true and create
the actual scheduler.

Daily schedule: 09:00 Asia/Dhaka = 03:00 UTC; cron expression `0 3 * * *`.
Command: `python workflow.py daily`. Render cron has a minimum monthly charge
and cannot attach a persistent disk. S3 checkpoints survive individual runs.
Nothing in this package creates or activates a scheduler automatically.

## Reliability and remaining hardening

The run key is Bangladesh calendar date. Completed or ambiguous uploads are
blocked on repeat runs, preventing silent duplicate inserts. Upload uses
resumable chunks with retries. Story and final assets are kept in private object
storage; no credentials or provider error bodies are logged. Image generation
and narration are not automatically retried to avoid repeated credit spending.
API outages stop the run rather than substitute stock images or synthetic voices.

Six component tests pass, including an actual 1920×1080 render, caption timing,
story validation, time rounding, missing secrets and disabled daily execution.
Rendering is tested with synthetic fixtures, not claimed as a complete AI video
test. Local caches resume within a retained workspace; assets generated before a
failed run are not yet restored from object storage on a fresh worker, so those
generations may be repeated. The production scheduler must ensure one active
run per service (Render cron does). No distributed lock is implemented for
independent manual workers; do not run them concurrently.

Originality includes prompting against recent titles and exact script hashing.
This does not guarantee semantic uniqueness or quality; production operation
needs visual review initially and monitoring for repeated plots. Automated final
audio intelligibility, character consistency, and full video semantic QA remain
to be implemented/validated. No notification integration is configured.

## Documentation used

- https://console.groq.com/docs/api-reference
- https://huggingface.co/docs/huggingface_hub/en/package_reference/inference_client
- https://developers.google.com/youtube/v3/guides/uploading_a_video
