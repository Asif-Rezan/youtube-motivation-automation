# Private motivational storytelling workflow

## Current format

- Original English motivational stories targeting 10–15 minutes (600–900 seconds).
- 1920×1080 output at 30 fps.
- A newly generated image at 0, 10, 20, 30 seconds and every ten seconds thereafter.
  The final image lasts only for the remaining duration. Chapter boundaries do not reset this timeline.
- Ghibli-inspired hand-painted 2D illustrations, using pinned public
  Lykon/dreamshaper-8 safetensors weights on cloud CPUs.
- Kokoro English narration, Faster-Whisper aligned burned-in captions, zoom/fade
  transitions, original MusicRNN background music and illustrated thumbnails.
- Private uploads to the user-selected REZAN IT channel. Public publishing remains disabled.

The new-format private test passed in Actions run 38417265115:
13:37, 1920×1080, 82 distinct illustrated image clips with global ten-second
boundaries. Complete-file decoding, timeline checks, private REZAN IT upload,
HD processing, custom thumbnail, title, description and tags all passed.
The workflow is manual only again. The previous 4:25 video remains unchanged.

## Free cloud infrastructure

Standard GitHub Ubuntu runners perform the work even when the user's computer
is off. The dedicated illustration model is downloaded as public weights; no
paid inference provider, GPU runner, vidIQ service or paid storage is used.
Illustrations are generated at 640×360 then scaled into the 1080p video; they
are not native 1080p renders. Eight image workers share the work. Subjective
style quality and character continuity still require review before public release.

Owner-only Google Drive stores the story, prepared audio, captions, images,
clips, final video, thumbnail and checkpoints. No private media artifacts,
unpublished story payload, signed URLs or private Drive identifiers belong in
this public repository. Files are checked for owner-only permissions and the
pipeline stops near the free 15 GB storage allowance. No automatic deletion
or paid storage upgrade is performed.

The Drive OAuth app can only see files authorized to it. Unpublished test stories
are transferred into an app-created private input slot. Another authorized Drive
connection may replace that input's content in place, preserving its ID and
access. The workflow reads the input privately and never prints story text.

## New private test

Use **Ghibli long private video test** in Actions.
Preparation generates narration and measures the real duration before generating
images. Runs outside 600–900 seconds stop before image generation or upload.
The global shot plan is computed from measured narration; eight CPU workers
generate distinct illustrations and exact-duration silent clips. Each worker
stores outputs privately in Drive. Final assembly combines continuous narration,
music, transitions and captions, validates every clip's duration and decodes the
complete 1080p MP4 with strict FFmpeg error handling.

Model generation stages have no Google credentials in their environment.
Separate storage/upload steps receive the existing OAuth secrets.
The upload checks the expected channel, stores an upload-started checkpoint,
uploads privately, sets a custom thumbnail and waits for YouTube processing.
The final readback verifies the actual video's channel, private visibility,
HD status, title, description and tags.

## Configuration and daily readiness

Set GitHub Actions secrets directly; do not commit real credentials:
- DRIVE_TOKEN_JSON: authorized Google OAuth JSON. The owner-only workflow
  folder is automatically discovered; DRIVE_FOLDER_ID is optional.
- YOUTUBE_TOKEN_JSON: authorized Google OAuth JSON with upload/read access
  for REZAN IT. The expected channel ID is UCwNhdtzL9XZMIAMXm81UCbw.
- GROQ_API_KEY: required for fresh unattended daily story generation. This
  secret was still absent at the last cloud check. The private test uses an
  original AI-authored story provided through private Drive.

IMAGE_BACKEND=cpu, TTS_BACKEND=kokoro, CAPTION_BACKEND=cpu and
MUSIC_BACKEND=magenta are free-model defaults. See .env.example.

No daily schedule is registered. Daily mode requires DAILY_ENABLED=true and
a completed private HD test with validation proving the new ten-second,
Ghibli-inspired format. A fixed test story cannot be used in daily mode.
Before unattended operation, resolve OAuth Testing refresh-token expiry.
The requested 09:00 Asia/Dhaka start corresponds to 03:00 UTC; GitHub schedules
can be delayed. Scheduler activation remains pending.

The standard workflow.py test/daily commands use the same long-video renderer.
The parallel test workflow is the recommended new-format integration test.
Older fixture workflows are historical and do not demonstrate this format.

## Reliability and verification

Completed or ambiguous upload checkpoints prevent duplicate insertion.
Resumable chunks retry transient transfer failures. Ambiguous uploads require
reconciliation instead of repeating videos.insert. One workflow-level concurrency
group prevents overlapping complete video runs; image workers use separate keys.
Exact story hashes and history guard repeated scripts.

Eleven component checks cover private storage/quota rules, speech chunking,
caption bounds, story validation, real 1080p rendering, the global shot plan and
an actual image change across a ten-second boundary. These checks pass locally
and on cloud runners. They do not replace the full private-video upload test.

## Model documentation

- https://huggingface.co/Lykon/dreamshaper-8 (CreativeML OpenRAIL-M)
- https://huggingface.co/hexgrad/Kokoro-82M (Apache-2.0)
- https://github.com/magenta/magenta-js (Apache-2.0)
- https://developers.google.com/youtube/v3/guides/uploading_a_video
- https://docs.github.com/en/billing/concepts/product-billing/github-actions
