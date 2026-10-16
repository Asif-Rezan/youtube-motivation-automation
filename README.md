# Motivational financial storytelling automation

## Current format

- Original English motivational financial stories targeting 10–15 minutes (600–900 seconds).
- 1920×1080 output at 30 fps.
- A newly generated image at 0, 7, 14, 21 seconds and every seven seconds thereafter.
  The final image lasts only for the remaining duration. Chapter boundaries do not reset this timeline.
- Narration-matched cinematic 2D editorial story images with clean outlines,
  restrained cel shading, muted natural colors and recognizable everyday settings at 1024×576, using pinned public
  segmind/SSD-1B safetensors weights on cloud CPUs with 16 generation steps.
- Kokoro English narration, Faster-Whisper aligned burned-in captions, zoom/fade
  transitions, original MusicRNN background music and full-frame cinematic
  thumbnails without the previous large text band.
- Daily videos upload privately to Rezan Relaxation, remain private after HD/metadata verification.
- Generation starts once daily at 01:00 Asia/Dhaka; temporary run media is cleaned after verified private upload.

The previous ten-second private test passed in Actions run 38450919780.
The current seven-second update derives each visual from actual measured word
timestamps after speech generation, including windows crossing chapter boundaries.
Groq produces concise scene prompts using the exact words spoken in that window
and chapter context for pronouns and continuity. Image generation refuses a plan
without full narration-window coverage. Subject/action/object prompts precede style
text so the image model prioritizes the story. The final shorter shot covers the
remaining narration. Component tests do not replace a complete live generation/upload verification.

The reviewed story has a direct opening crisis, coherent escalating setbacks,
and a final narrator request to like, comment and subscribe. Future stories
use Groq GPT-OSS 120B with strict chapter schemas and rate-spaced batches;
the final CTA is added reliably by the application. Previous story titles are
included in Groq planning to reduce repeated topics. Historical private tests
remain manual; the new daily workflow generates a fresh story on each run.

## Free cloud infrastructure

Standard GitHub Ubuntu runners perform the work even when the user's computer
is off. The dedicated image model is downloaded as public weights; no
paid inference provider, GPU runner, vidIQ service or paid storage is used.
Images are generated at 1024×576 then scaled into the 1080p video; they
are not native 1080p renders. Sixteen image workers share the work. The
[CPU image benchmark](docs/image-cpu-benchmark.md) compares SSD-1B with the previous
DreamShaper model. Subjective
style quality and character continuity still require review before public release.

Owner-only Google Drive stores the story, prepared audio, captions, images,
clips, final video, thumbnail and checkpoints. No private media artifacts,
unpublished story payload, signed URLs or private Drive identifiers belong in
this public repository. Files are checked for owner-only permissions and the
pipeline stops near the free 15 GB storage allowance. Verified daily runs
permanently delete only tagged disposable media; no paid storage upgrade is performed.

The Drive OAuth app can only see files authorized to it. Unpublished test stories
are transferred into an app-created private input slot. Another authorized Drive
connection may replace that input's content in place, preserving its ID and
access. The workflow reads the input privately and never prints story text.

## New private test

Use **Ghibli long private video test** in Actions.
Preparation generates narration and measures the real duration before generating
images. Runs outside 600–900 seconds stop before image generation or upload.
The global shot plan is computed from measured narration; twenty CPU workers
generate distinct story images and exact-duration silent clips. Each worker
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
  for Rezan Relaxation. Private daily uploads reuse the existing upload/read OAuth permissions.
  No public-publishing permission is required.
  The expected channel ID is UCztvMrNCT34DO3DtzLPgWaw.
- GROQ_API_KEY: required for fresh unattended daily story generation. It is also
  required for narration-aligned scene prompts. Fresh tests generate an original
  story and store all unpublished content privately.

IMAGE_BACKEND=cpu, TTS_BACKEND=kokoro, CAPTION_BACKEND=cpu and
MUSIC_BACKEND=magenta are free-model defaults. See .env.example.

The daily parallel workflow has its own private-verification path. Legacy
`workflow.py daily` retains its private-test gate. A fixed test story cannot be
used for fresh daily generation. OAuth credentials must remain valid for
unattended operation; resolve OAuth Testing refresh-token expiry before relying
on long-term scheduling. The 01:00 Asia/Dhaka start corresponds to 19:00 UTC
on the previous calendar day; GitHub can delay scheduled starts.

The standard workflow.py test/daily commands use the same long-video renderer.
The parallel test workflow is the recommended new-format integration test.
Older fixture workflows are historical and do not demonstrate this format.

## Reliability and verification

Completed or ambiguous upload checkpoints prevent duplicate insertion.
Resumable chunks retry transient transfer failures. Ambiguous uploads require
reconciliation instead of repeating videos.insert. The daily workflow concurrency group prevents overlapping daily runs; image
workers use separate keys. Do not run legacy private-test workflows concurrently
with daily runs because they share the upload history.
Exact story hashes and history guard repeated scripts.

Component checks cover private storage/quota rules, speech chunking,
caption bounds, story validation, real 1080p rendering, the global shot plan and
an actual image change across a seven-second boundary. These checks run locally and in GitHub Actions. They do not replace the full private-video upload test.

## Model documentation

- https://huggingface.co/Lykon/dreamshaper-8 (CreativeML OpenRAIL-M)
- https://huggingface.co/hexgrad/Kokoro-82M (Apache-2.0)
- https://github.com/magenta/magenta-js (Apache-2.0)
- https://developers.google.com/youtube/v3/guides/uploading_a_video
- https://docs.github.com/en/billing/concepts/product-billing/github-actions

## Daily financial storytelling publishing

`.github/workflows/daily-upload.yml` starts at **01:00 Asia/Dhaka** daily
(`0 19 * * *` UTC), and supports manual dispatch.
GitHub may delay scheduled starts. The workflow must be on the default branch,
with Actions and scheduled workflows enabled. Existing secrets are reused:
`GROQ_API_KEY`, `DRIVE_TOKEN_JSON`, `DRIVE_FOLDER_ID`, `YOUTUBE_TOKEN_JSON`.
The configured destination remains channel `UCztvMrNCT34DO3DtzLPgWaw`.

The existing twenty CPU image workers, exact seven-second narration timeline,
10–15 minute validation, local narration, original music, captions and thumbnail
pipeline are reused. Fresh Groq financial stories cover financial growth, money
psychology, saving and investing habits, business decisions, moral parables and
everyday money mistakes. Historical documentaries require verified source material;
without it, generation uses clearly labelled fiction. Prior titles are included
in planning and exact story hashes prevent duplicate uploads. The planner rotates
financial story formats (decision drama, business postmortem, money psychology,
family tradeoff, everyday mistake, and two-path comparison), records each format
in upload history, and rejects a format used in either of the last two uploads or
a near-duplicate recent title. Each script must have its own central problem,
setting, relationships, turning points, and resolution. Review the finished private
video before public release: automated variety checks cannot guarantee YouTube
monetization eligibility.

Uploads remain **private**. `daily_publish.py` reads back the exact video ID,
channel, title, tags, complete description, successful processing and HD
definition, requires confirmed thumbnail upload, and verifies private visibility
before deletion. It never calls `videos.update` or changes visibility.
Failed, incomplete, ambiguous, or unverified uploads retain all Drive assets.

Disposable media created by this daily workflow receive run-specific Drive
appProperties. Cleanup persists an ID manifest, then rechecks each file's run,
workflow-key hash, parent folder, private ownership, and explicit disposable name
before permanent deletion. It never deletes folders, unrelated files, older
untagged runs, story/state records, history, hashes, configuration or credentials.
Preparation audio, scene images/clips/QA, final music, captions, thumbnail, video
and plan are disposable. Deletion is permanent and recovers storage space.

Cleanup retries transient failures and records each completed deletion. A 404 on
an already journaled ID is safe. If private verification or cleanup fails, rerun only the
failed `publish-cleanup` job, or manually dispatch with `cleanup_run` set to its
`daily-<GitHub run ID>`. That mode skips all generation/upload jobs, rechecks the
existing video and resumes cleanup without calling `videos.insert` again.
Never rerun all jobs to recover an ambiguous upload; reconcile its persisted
state first. Daily uploads use the existing durable pre-insert state guard.

Validation: `python -m unittest -v` includes deletion-safety, idempotency,
missing-verification, wrong-channel and essential-data preservation tests.

Daily readiness checks validate existing upload/read access before model generation.
Review the **Google OAuth check** Actions run after changing credentials.

## One-time private tests

Use Actions > Daily financial storytelling publishing > Run workflow, leaving
`cleanup_run` blank. Updating `.github/workflows/private-video-trigger.txt` on
main also starts a single fresh private test. Neither method changes the daily 01:00 Asia/Dhaka schedule. The existing OAuth token supports private upload; the
optional `authorize_youtube.py` helper is unnecessary for private-only operation.

### Recovering Drive checkpoint timeouts

Small JSON checkpoint saves use non-resumable uploads with bounded backoff for
network timeouts, connection failures, rate limits and temporary server errors.
Each write retries against a fixed file ID. New checkpoints preallocate their
ID so an ambiguous successful create cannot create duplicates on retry. A create
conflict is accepted only when the saved JSON matches the intended checkpoint.
Cleanup journals checkpoint every ten deletions and once at completion, reducing
Drive requests. If interrupted between checkpoints, already-deleted manifest IDs
return 404 and are safely recorded on the next attempt.

Use **Resume verified private video cleanup** to recover a completed run without
any video generation or `videos.insert` call. Enter its original `daily-<run ID>`.
The cleanup worker rechecks private visibility, successful HD processing and
exact metadata before resuming. The daily 01:00 Asia/Dhaka schedule is unchanged.
