# Daily Hindi emotional motivational stories

The active pipeline now creates a **new original Hindi story every day**, rather than a three-video batch. Every finished video must measure **480–720 seconds (8–12 minutes)**. The former kids-rhyme pipeline is inactive and preserved below and in `legacy/kids-rhymes/`.

## Production behavior

- Qwen3-4B CPU writes an original six-chapter Hindi Devanagari story, about 1,100–1,500 words across 48 scenes. Approximately 75% is narration with short male/female character dialogue. The ending demonstrates the lesson through a decision rather than a long speech. Generation has no fixed-script fallback.
- Kokoro-82M (`kokoro==0.9.4`, `lang_code='h'`) speaks the complete story on CPU: narrator `hm_omega`, male character `hm_psi`, female character `hf_alpha`. `espeak-ng` provides Hindi phonemization. Actual audio samples determine every scene boundary. Native speech speed may be adjusted within 0.80–1.15 and re-synthesized to meet the duration range; the story is never cut short, looped or filled with minutes of silence. Out-of-range output fails before publication. Hindi pronunciation/emotion still require listening review; no voice-quality guarantee is made.
- **Reference image style retained:** [Saved example from the current rhyme run](assets/reference/storybook-look.png). the same pinned `segmind/SSD-1B`, 1024×576 sources, 20 steps and core prompts from the current kids-rhyme version: cute colorful 3D storybook cartoon, rounded soft shapes, expressive faces, bright pastels, detailed environments and soft lighting. Actions and human characters follow the Hindi story; fixed appearance/clothing/world descriptions are repeated within the episode. This is text-guided consistency, not reference-image conditioning, face locking or full character animation. Exact faces cannot be guaranteed. Eight image shards generate 48 scenes, with gentle camera pan/zoom in a 1920×1080 video.
- ACE-Step 1.5 `acestep-v15-turbo` produces **instrumental background music**, in independent parts no longer than 120 seconds. Nursery-rhyme reference audio is not used for stories. Parts cover the complete measured narration; no background looping or padding. Music is mixed quietly, ducked under speech and faded at the start/end.
- Titles/descriptions/tags belong to the individual Hindi story, replacing the kids pipeline's fixed rhyme metadata. Hindi audio/metadata, Education category (27), general audience (`made_for_kids=false`) and AI disclosure are used. Existing kids upload settings remain available for rollback and manual kids recovery.
- Private Drive story reservations/history use `stories/` keys inside the existing owned private automation folder, separate from rhyme history and publication state. Exact script/title, close summary similarity and repeated scene checks reject duplicates against reserved, scheduled and published stories. This practical check cannot prove global originality. The same run ID resumes the saved story; a new ID requests a new story.
- Uploads keep the existing exact channel guard and resumable publication checks. A saved YouTube ID is reused after scheduling/processing errors; ambiguous uploads stop instead of creating duplicates. Final audio/video duration and render fingerprints are checked before a new upload. Scheduled story backups remain on Drive for recovery; each daily run cleans only exact media files of older freshly verified public HD stories. Scripts, history and publication journals remain saved.

## Daily schedule and operation

Active workflow: [Daily Hindi emotional motivational story](.github/workflows/stories.yml).

- Daily generation starts at **03:00 Asia/Dhaka** (`0 21 * * *` UTC), gated by the existing `AUTOMATION_ENABLED=true` repository variable.
- `PUBLISH_ENABLED=true` keeps automatic YouTube upload on. Both switches were verified as true on 2026-10-30; this migration reuses the existing credentials and channel.
- Release remains the **first 06:00 America/New_York slot at least 72 elapsed hours after upload completion**. Therefore the first new story has the same three-plus-day release buffer. CPU time, queued runners and failed generation can leave gaps; cron is not a guarantee of daily completion.
- Run **Daily Hindi emotional motivational story** manually for an immediate generation. Leave `run_id` empty for `story-YYYY-MM-DD` in Dhaka time, or supply a stable identity. Resume an interrupted story using its original `run_id` plus its numeric previous STORY workflow run as `prepared_run`; do not use a kids-rhyme run. Available checkpoints expire after seven days; the reserved script remains in Drive.
- To resume only scheduling/verification of an existing uploaded story, use **Recover existing Hindi story publication**, with the original story run ID. It never generates or inserts another video.
- The old automatic rhyme Shorts and Facebook cross-post jobs are not invoked by the story workflow. Their manual/recovery tools and original settings are preserved. This migration schedules one new long-form Hindi story per day.
- Story backups stay in private Drive until a later daily run verifies public HD publication and cleans their temporary audio/video/thumbnail files. Cleanup errors retain media and retry later without blocking new generation. The existing guarded free-storage check stops rather than purchasing storage if quota still fills. No claim of a completed full model run or actual scheduled story should be inferred from component tests; inspect the live Actions run.

Local stage commands (CPU dependencies and model downloads required):

```sh
python daily_story.py --run-id story-example --stage plan --check-history
python daily_story.py --run-id story-example --stage voice
python daily_story.py --run-id story-example --stage images
python daily_story.py --run-id story-example --stage music
python daily_story.py --run-id story-example --stage render
python daily_story.py --run-id story-example --stage publish
```

For a local script preview without Drive, omit `--check-history`; production always checks and reserves private history. Model/runtime references: [Kokoro](https://huggingface.co/hexgrad/Kokoro-82M), [Hindi voices](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md), and the pinned ACE-Step runtime already recorded in `music_cpu.py`.

## Validation

- Python 3.12: 98 component tests passed, including Hindi script/length checks, saved-story resumption, duplicate checks, timeline continuity, story upload metadata, public-HD cleanup isolation and all existing kids/publication tests.
- All active workflows passed actionlint 1.7.12.
- An actual FFmpeg render with synthetic test inputs measured exactly 480.0 seconds and produced a thumbnail/render fingerprint. This checks rendering, not generated story/image/music quality.
- Actual Kokoro CPU Hindi synthesis succeeded for all three configured voices: `hm_omega` (11.12 s), `hm_psi` (11.22 s), `hf_alpha` (10.47 s) on the same sample sentence. This verifies runtime output, not subjective pronunciation quality.
- First production story run: [41048162989](https://github.com/Asif-Rezan/youtube-motivation-automation/actions/runs/41048162989), dispatched on main at migration commit `f30ff85` on 2026-10-30 with automatic scheduled publishing. At this documentation checkpoint it is running; a finished generated video or successful publication has not yet been established.

## Saved kids-rhyme version and exact rollback

Saved immediately before this migration on **2026-10-30**:

- Migration implementation commit: `9b45c9b` (`Replace daily rhymes with original 8-12 minute Hindi motivational stories`).
- Full pre-migration commit: `40e20e938eca937344570f0231a01777c17638f7`
- Commit: `Merge pull request #22 from Asif-Rezan/fix-youtube-processing-wait`
- Backup branch: `codex/archive-kids-rhymes-20261030`
- Exact tracked pre-migration source snapshot: [`legacy/kids-rhymes/`](legacy/kids-rhymes/), including its original README, tests and workflows. Existing Ancient Humans archive is retained separately in `legacy/ancient-humans/`.
- The previous daily workflow is also retained **commented out** at [`.github/music-kids-rhymes.yml.commented`](.github/music-kids-rhymes.yml.commented), outside `.github/workflows/`, so it cannot trigger alongside stories. Old Python is archived intact instead of commenting every line and damaging its executable rollback copy. Root kids modules remain for shared infrastructure/manual recovery; `daily_story.py` is the new production entry point.
- [Full saved 40-commit log](docs/kids-rhymes-commit-log.txt).

To inspect or run the exact saved code in a separate checkout:

```sh
git fetch origin
git worktree add ../kids-rhymes-saved origin/codex/archive-kids-rhymes-20261030
```

To restore the exact kids version as a new reversible commit (from a clean checkout):

```sh
git fetch origin
git switch -c codex/restore-kids-rhymes origin/main
git restore --source=40e20e938eca937344570f0231a01777c17638f7 --staged --worktree -- .
git commit -m "Restore saved kids-rhyme automation"
git push -u origin codex/restore-kids-rhymes
# Review and merge this branch into main to activate the old daily workflow.
```

This restores tracked files and removes the story workflow through normal Git history, without reset or force push. Repository variables/secrets, existing uploads and Drive data are external to Git: review them separately. Old already-started Actions runs execute their original commit. The in-progress kids run `41036770322` was canceled during the switch to prevent another rhyme upload. The original YouTube channel and release policy are unchanged by rollback.

Recent commits at the saved point:

```text
40e20e9 | 2026-10-30 | Merge pull request #22 from Asif-Rezan/fix-youtube-processing-wait
b9405bd | 2026-10-30 | Wait through normal YouTube processing before scheduling existing uploads
fa525d7 | 2026-10-30 | Merge pull request #21 from Asif-Rezan/isolate-facebook-failures
d8d84fa | 2026-10-30 | Isolate optional Facebook failures from YouTube publishing
4aa25c1 | 2026-10-30 | Merge pull request #20 from Asif-Rezan/facebook-landscape-validation
30d0e28 | 2026-10-30 | Record successful landscape upload and correct Drive account
ee414ad | 2026-10-30 | Merge pull request #19 from Asif-Rezan/facebook-live-validation
14a21be | 2026-10-30 | Record production app and live Facebook Reel validation
a256a39 | 2026-10-30 | Merge pull request #18 from Asif-Rezan/facebook-production-policy
52fc6fa | 2026-10-30 | Publish privacy and deletion policy for Meta app
c555883 | 2026-10-30 | Merge pull request #17 from Asif-Rezan/facebook-page-integration
b118d01 | 2026-10-30 | Document confirmed Meta app and business identity
26a9f1b | 2026-10-30 | Add scheduled Facebook Page videos and Reels with durable recovery
7201136 | 2026-10-29 | Merge pull request #16 from Asif-Rezan/restore-automatic-publication
9db2c34 | 2026-10-29 | Restore original YouTube channel identity across publishing workflows
```

## Historical kids-rhyme README (superseded for daily generation)

The following is preserved as historical documentation. Use the story instructions above for new daily videos; kids/recovery notes below refer to the saved version.

---

## Facebook Page cross-posting

Facebook integration setup and recovery: [docs/facebook-publishing.md](docs/facebook-publishing.md). The destination is Rezan Relaxation (`297892583408910`). Existing YouTube generation/upload remains active; Facebook requires its own Page authorization and `FACEBOOK_PAGE_ACCESS_TOKEN` secret. Facebook is enabled independently with `FACEBOOK_PUBLISH_ENABLED=true` after the authorized live test. Do not treat the code installation as a completed Meta connection.

## Automatic upload restored for the existing channel

The existing destination is `UCztvMrNCT34DO3DtzLPgWaw`, preserved from the archived Ancient Humans workflow. All active workflows resolve `EXPECTED_CHANNEL_ID` from an existing secret, then an optional repository variable, then that original channel ID. The uploader still verifies that OAuth belongs to this exact destination. No new OAuth token is required for this migration.

`PUBLISH_ENABLED=true` enables long/Short uploads, and `AUTOMATION_ENABLED=true` enables daily generation at 03:00 Asia/Dhaka. Uploaded videos use the reference automatic scheduling policy: first 06:00 America/New_York slot at least 72 hours after upload completion. These are repository Actions variables, not secrets. Explicit false disables the corresponding behavior. Existing token and Drive secrets are reused.

## Shorts preview recovery and publication preflight

Preview generation (`PUBLISH_ENABLED` unset or false) does not require YouTube credentials. Reusable Shorts workflow secrets are optional at dispatch time; enabling publication requires all four existing repository secrets, checked before model generation and before Shorts rendering. Missing values produce a diagnostic listing names only. No credentials or publication variables are changed automatically.

If long video/music/portrait jobs completed but Shorts orchestration failed, run **Create and publish a rhyme Short** on the current main branch with `source_run=40902873254`, `run_id=kids-rhyme-20261029-2134`, `prepared_music=true`, `prepared_portraits=true`, start 0, duration 40. This reuses the saved music/portrait artifacts instead of running the models again. Artifacts expire after seven days. Rerunning an old workflow uses its old workflow definition, so dispatch the corrected workflow for this recovery.

## Repository account compatibility fix

This repository uses its existing `DRIVE_TOKEN_JSON`, `DRIVE_FOLDER_ID`, `YOUTUBE_TOKEN_JSON` and `EXPECTED_CHANNEL_ID` secrets, not the reference project's hardcoded account/channel. The authenticated Drive user must own the configured active private folder; shared/foreign/trashed folders are rejected. A private `Kids Rhymes - YouTube Automation` child folder marked `youtube_kids_rhymes_root=v1` is created once and reused. Kids history/checkpoints and cleanup stay inside that child, leaving Ancient Humans data untouched. Connection verification may initialize this child folder; it never uploads videos. YouTube continues to require an exact match with `EXPECTED_CHANNEL_ID`. Account setup requires an explicitly supplied channel ID, without requiring the reference channel handle. Older reference-specific account/folder instructions below are superseded by this section.

# YouTube Motivation Automation — kids rhymes migration

This repository now runs the kids rhymes pipeline copied from [dudi_dam_tv](https://github.com/Asif-Rezan/dudi_dam_tv/tree/6add42d9d315c4f73ec0d40c51c128fb2be76c15) at commit `6add42d9d315c4f73ec0d40c51c128fb2be76c15`.
The active reference files are unchanged except this README and `setup_accounts.py`, whose GitHub secret destination is this repository.

## Preserved Ancient Humans project

Previous main commit: `1db8f8262ff00570a4496c919511491357fbabe3` ([view original](https://github.com/Asif-Rezan/youtube-motivation-automation/tree/1db8f8262ff00570a4496c919511491357fbabe3)).
Every tracked file from that commit is preserved byte-for-byte under `legacy/ancient-humans/`, including its README, tests, assets and workflows. This directory is an inactive archive: the former workflows are outside `.github/workflows/` and the active pipeline never imports it. The old files are preserved as working source rather than adding comment markers that would damage Python/YAML/assets. Do not run old scripts from this archive against production credentials.

To inspect the original project without changing the kids pipeline:

```sh
git fetch origin
git worktree add ../ancient-humans-restored 1db8f8262ff00570a4496c919511491357fbabe3
```

To prepare a reversible restoration of the original project as a new branch:

```sh
git fetch origin
git switch -c restore-ancient-humans origin/main
git restore --source=1db8f8262ff00570a4496c919511491357fbabe3 --staged --worktree -- .
git commit -m "Restore Ancient Humans pipeline"
git push -u origin restore-ancient-humans
```

Run these commands from a clean checkout. Review and merge that branch through a pull request to restore the old project. This preserves the kids migration in Git history; no reset or force push is needed. Review repository Actions variables/secrets before enabling old uploads again. Uncommitted work in other local checkouts is untouched and is not part of this remote snapshot.

## Configure this repository

- Run account setup in this repository: `setup_accounts.py` writes secrets to `Asif-Rezan/youtube-motivation-automation`.
- Configure its own `YOUTUBE_TOKEN_JSON`, `EXPECTED_CHANNEL_ID`, `DRIVE_TOKEN_JSON`, and `DRIVE_FOLDER_ID` Actions secrets. Git cloning does not copy repository secrets or variables.
- The copied setup retains the reference channel guard (`@dudi_dum_tv`), Drive account guard and `dudi_dam_tv_root=v1` folder lookup. It can reuse the reference folder for the same account. For isolated history/artifacts, configure a separate private folder with the required app property and set this repository's `DRIVE_FOLDER_ID` explicitly. Review `storage.py` and `setup_accounts.py` before using another channel/account.
- Set `AUTOMATION_ENABLED=true` for daily generation and `PUBLISH_ENABLED=true` for uploads only when these repository credentials are ready. Existing repository variable values still apply after merging; they are not reset by this migration.
- Use **Verify Google connections** first, then manually generate a fresh run ID and review the result. The same reference long-video/Shorts generation and publishing workflows are included. No live generation or YouTube upload is performed by this code migration.
- Install `requirements.txt` and run `python -m unittest -v` for component verification. Full model inference additionally requires the pinned CPU dependencies, model downloads and FFmpeg documented below.

The original reference README follows; its project names, channel branding and behavior are retained intentionally. Any reference to account setup targeting `Asif-Rezan/dudi_dam_tv` below is superseded by the destination above.

---

# Dudi Dam TV — kids rhyme video automation

Copied from [Heart-and-Mind](https://github.com/Asif-Rezan/Heart-and-Mind) at `0fca9240b5edf786f09a806401a62dcc386eb0f6`. The first repository commit is the unchanged copy. The kids adaptation retains pinned CPU music/image inference, resumable artifacts, Google account setup, verified YouTube publishing and exact-file Drive cleanup.

## Current behavior

- Default: 600 seconds. Set `VIDEO_DURATION_SECONDS` to 480–720 in five-second steps.
- Sweet adult female singing voice requested, original AI-written English verses alternating with **dudi dudi dam dam dudi dudi dam**. This phrase is a sung refrain, not musical chord notation.
- The first lyrics job runs the pinned local Qwen3-4B CPU model to write a fresh adventure outline, new English verses, and matching visual descriptions. Only the Dudi refrain is fixed. There is no template fallback. Each run ID uses a different generation seed.
- A new SSD-1B cartoon illustration for every five seconds (96–144 images), plus a thumbnail. Sixteen image workers split generation and checkpoint each completed image.
- ACE-Step generates separate sections up to 120 seconds, then FFmpeg joins them. Music is not looped or padded. Short or incorrectly sized sections fail. Section joins and voice/character consistency need listening/viewing review.
- A 30-second excerpt of the user-supplied MP3 is included at `assets/reference/style-reference.mp3`; the full original is not committed. The pinned API exposes `reference_audio`. Inference receives the excerpt for style conditioning; actual influence and singing quality require a model run. Set `REFERENCE_AUDIO_PATH` to a different local file or leave unset to generate without conditioning. Use reference material you have permission to use.
- Storyboard lyrics drive image actions and the pictures change exactly every five seconds. Singing is generative: this is planned timing, **not forced alignment or transcription**. Precise word-level synchronization is not yet implemented.

## Generate before connecting Google

Run **Dudi Dam TV kids rhyme generation** from GitHub Actions with a new `run_id`. The lyrics job checks and reserves lyric originality in private Drive history; connected Drive credentials are required for the production workflow. Local generation without history can run without Google credentials. Download `kids-video-RUN_NUMBER` for the MP4, thumbnail and song/storyboard JSON. Generation is computationally expensive and has not yet been verified end to end on Actions. Existing model revisions and CPU dependencies come from the reference; 120-second sections reload the model for bounded worker isolation. Model memory/time limits may require a larger runner.

Automatic scheduling is off unless repository variable `AUTOMATION_ENABLED=true`. Publishing requires `PUBLISH_ENABLED=true`. The scheduled time inherited from the reference is 03:00 Asia/Dhaka. The workflow defaults to 600 seconds; adjust `VIDEO_DURATION_SECONDS` in its workflow-level env for other durations.

For local AI lyric writing (downloads the pinned Qwen GGUF model):

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-lyrics.txt
python prepare_music.py --run-id first-rhyme --stage lyrics
```

Image preparation also requires CPU PyTorch and `requirements-images-cpu.txt`. Music preparation needs CPU torch/torchaudio, `requirements-music-cpu.txt` and ACE-Step source at revision `ca1e85fe9430179831e6bc6be790c332190a3866` in `.vendor/ace-step`. See the workflow for exact installation. Install FFmpeg for audio joining and video rendering.

## Connect later

1. Configure a Google Cloud OAuth client with YouTube Data API v3 and Google Drive API enabled.
2. Use `python setup_accounts.py --help` for the inherited account setup commands targeting `Asif-Rezan/dudi_dam_tv`. Drive remains restricted to the account in `storage.py`; update it deliberately if using another owner.
3. Add secrets `YOUTUBE_TOKEN_JSON`, `EXPECTED_CHANNEL_ID`, `DRIVE_TOKEN_JSON`, `DRIVE_FOLDER_ID`. Create a new Dudi Dam TV Drive folder with the `dudi_dam_tv_root=v1` application property via setup; do not reuse the reference channel folder.
4. After reviewing a downloaded preview, set `PUBLISH_ENABLED=true`. Uploads declare `selfDeclaredMadeForKids=true`; the configured channel ID must match. Drive stores the scene sources/manifests as `storyboard.tar.gz`, and cleanup removes media only after verified public HD publication.

Google OAuth and the dedicated Drive folder can be checked with the **Verify Google connections** workflow. This only verifies identity, folder privacy and refresh tokens; it does not upload videos. No finished music/video is claimed until inference succeeds and the result is reviewed.

## Verification

`python -m unittest -v` covers duration boundaries, complete contiguous storyboards, cache/shard coverage, missing scene failures, rendering arguments and inherited guarded Drive cleanup. Original reference tests remain in `reference_tests/` as historical specifications; their adult-music assumptions do not describe this adaptation.

## Upload details and scheduling

The workflow dispatch form exposes `upload_mode` (`public` or `scheduled`), `publish_at`, `video_language`, `audio_language`, and `category_id`. Scheduled times must include a timezone (for example `2026-11-01T18:00:00+06:00`) and still be in the future when the upload starts. Allow enough time for generation. With an explicit timestamp, a scheduled upload is private with `publishAt` set; it is verified as scheduled after HD processing. Reusing its run ID checks the same upload rather than creating another one.

`upload_settings.json` stores explicit defaults for English metadata/audio, Music category (10), made for kids, AI disclosure, standard YouTube license, embedding, public statistics, subscriber notifications, and no paid placement. The kids and AI disclosures are enforced for this pipeline. Title, description, tags and thumbnail come from the generated song artifact. Review/edit that artifact before publishing if needed. Comments, cards/end screens and some other Studio-only features are subject to made-for-kids restrictions and are not exposed by this uploader.

Scheduled media is retained on Drive. After its release, rerun the same publishing identity to verify public HD status before cleanup. OAuth Production status removes testing-mode token expiry; it does not guarantee that Google will never revoke a refresh token. Actual upload acceptance/public visibility is always checked rather than assumed from OAuth status.


## Daily 6 AM New York releases

Daily generation starts at 21:00 UTC (03:00 Asia/Dhaka). Once each video finishes uploading, it is scheduled for the first **06:00 America/New_York** slot at least **72 elapsed hours after upload completion**. New York daylight saving changes are handled by the IANA timezone database. The actual wait is 72 hours up to the next qualifying 6 AM slot (normally less than 96 hours). There is an initial three-plus-day buffer before the first release; generation failures/delays can leave gaps.

The default upload is private without a publication timestamp. After YouTube returns its video ID, the pipeline records upload completion, computes and saves the target, then updates YouTube `status.publishAt`. Retry attempts reuse the saved target rather than delaying it again. This step needs `youtube.force-ssl` authorization in addition to the existing upload/read scopes. Default workflow mode is `scheduled` and `publish_at` is empty, so both daily and manual runs follow this policy unless explicitly overridden. `AUTOMATION_ENABLED=true` enables daily generation and `PUBLISH_ENABLED=true` enables uploading.


## Animated picture treatment

Every five-second lyric scene now has continuous 25 fps camera motion: gentle alternating horizontal pan, a slow push-in, a small rhythmic pulse and vertical sway. Translucent bubbles drift independently along the edges for foreground depth. A 0.28-second dissolve uses the previous scene's actual final frame, so scene changes do not add time or shift the soundtrack. The original song is muxed once after the silent clips are joined.

This gives still illustrations a lively storybook presentation; it does not rig character limbs or lip-sync mouths. Motion follows the requested 100 BPM arrangement as a visual guide, not measured audio beats. Full videos remain 1920×1080 and 8–12 minutes, with a new illustration every five seconds. Rendering is split into small clips to bound memory. `render-state.json` fingerprints the renderer version and inputs so an old static video is regenerated automatically.

For a local short preview without model inference or publishing, run `python preview_motion.py image1.png image2.png --audio song.wav --output output/motion-preview.mp4`. Preview images/audio are supplied locally and are never used as a production fallback.


## Fresh AI lyrics on each new run

`rhyme_writer.py` calls the pinned Qwen CPU model first for an original episode outline/title/description, then for new five-second verse lines and corresponding scene actions in chapters up to two minutes long. A 10-minute episode has 60 original lines alternating with 60 fixed Dudi refrain lines. Drafts checkpoint after the outline and each chapter; retries with the same run ID resume that story. Use a new run ID to request a new song.

Normalized verse lines and four-word phrase overlap are checked against `lyrics-history.json` in the private Drive folder, excluding the shared refrain. New lyric identities are reserved before music/image jobs start, including scheduled or unfinished episodes. Repeated or overly similar verses trigger rewriting, then failure if the bounded retries cannot produce a valid result. This is a practical duplicate check, not a guarantee that every possible phrase is globally unique. The workflow installs `requirements-lyrics.txt` and allows 90 minutes for CPU writing; it never substitutes the former template verses on model failure.

Overlong generated titles and descriptions are shortened at word/sentence boundaries before schema validation. Sung lyrics and scene actions are never truncated. Invalid content receives up to three attempts with the failed constraint and actual length supplied to the model. Failure artifacts include an initial draft and `failure.json` with safe error codes and diagnostics, allowing inspection or checkpoint resumption without exposing credentials.

Verse validation keeps accepted lines and requests only missing replacements, with word-count and duplicate feedback. Up to six repair requests are allowed per chapter per invocation. Partial chapters checkpoint after each response; resuming the same identity preserves accepted lines and advances repair seeds. Exhaustion records `lyrics_verse_validation` with chapter, accepted/required counts and rejection reasons; lyrics are never truncated or replaced with templates.

## Recover a finished upload

Use **Recover finished video publication** with the original GitHub run number and song run ID. It restores music, scene sources, the finished MP4 and render fingerprints, verifies them, then resumes the original Drive/YouTube checkpoint without generating or uploading another video. Publication logs expose exact local guard failures without API bodies. If YouTube omits the synthetic-media readback, the publisher explicitly updates the existing video disclosure while preserving live visibility and schedule, and records a successful write receipt bound to that video. An explicit false readback still fails verification.

## Lyric-led cartoon variety

New episodes choose a story-specific cast (animals, friendly vehicles or gentle fantasy creatures), setting, props and pastel palette instead of always using a yellow duckling and white bunny. The cast description stays consistent within that episode. Each image prompt starts with the lyric-specific action, followed by the episode cast/world and the existing cute 3D storybook style. Recent visual identities are saved alongside lyric history to guide variety in future outlines. This guides the image model; exact character consistency and visual uniqueness still depend on its output.

Use a new `run_id` for this writer version. Finished songs and old storyboards keep their existing lyrics and cast; old writer drafts require a fresh run ID.

Visual planning prose (`characters` and `visual_world`) is normalized at word/sentence boundaries before schema validation, just like titles and descriptions. The saved normalized identity is used for every chapter; sung lyrics and scene actions are never truncated. Character/world limits are 320/240 characters, explicitly included in the outline instructions. Retryable model/schema failures receive up to three request rounds with different seeds, each retaining the existing three validation attempts. Completed chapters and accepted verse lines remain checkpointed. Permanent failures still report safe diagnostics and preserve recovery artifacts instead of publishing invalid content.

## Shorts with native portrait illustrations

Every new generation starts **16 landscape image shards plus 4 separate portrait image shards**, all after lyrics are ready. The portrait shards generate only the eight five-second scenes needed for the default first 40 seconds, at native 576×1024 (9:16). They use the same lyric scene actions and episode character descriptions with vertical composition instructions and separate seeds. Landscape scenes and portrait scenes have separate folders and resumable manifests.

After the long-video, portrait and Shorts music jobs finish, the Shorts workflow animates those portrait images full-screen at 1080×1920 using the existing storybook motion renderer. It uses separately synthesized Shorts audio from `short-audio/clip-START-DURATION/song.wav`. No blurred landscape filler is used. Missing, corrupt or non-9:16 portrait illustrations stop export instead of silently restoring the old layout. Selected lyrics are reused; portrait images and Shorts music are generated separately.

The Short follows the parent's public/scheduled mode. Scheduled remains the default: the existing first 6AM New York slot at least 72 hours after upload. `PUBLISH_ENABLED=true` is required to upload; otherwise a downloadable preview is saved. Kids/AI disclosures remain enabled. The long-video custom-thumbnail upload is skipped for Shorts.

For an older finished video, run **Create and publish a rhyme Short** with its GitHub `source_run` and original song `run_id`. Its `kids-video-SOURCE_RUN` artifact must still be available (seven-day retention). This standalone workflow starts four portrait image shards and one independent music job in parallel. Choose start 0, 10, 20, etc. and duration 20, 30, 40 or 50 seconds. Automatic calls reuse the already prepared portrait shards, avoiding a second generation.

Portrait publication checkpoints use `shorts/RUN_ID/music-portrait-clip-START-DURATION/state.json`, separate from the previous blurred-layout Short. Existing scheduled/uploaded Shorts are not replaced or deleted by this change. Repeating a portrait request with the same inputs resumes its upload; a changed source is refused under that same identity. Unknown upload outcomes require reconciliation rather than risking a duplicate. Private Drive checkpoints remain outside long-video media cleanup.

For a local export, supply `output/RUN_ID/song.json`, `short-audio/clip-START-DURATION/song.wav` and `portrait/scene-NNN-source.png` for the selected range, then run `python shorts.py --run-id RUN_ID --start 0 --seconds 40`. Source/output hashes and a full video/audio decode validate the export before upload. `rhyme-short-*` artifacts contain the finished Short; `short-publication-*` contain publication checkpoints; `short-artwork-*` contain native portrait images and generation manifests.

## Fixed public title, description and blank tags

All new YouTube uploads, including Shorts, use the exact owner-supplied title and description in `upload_metadata.json`. Tags are always `[]`. The description is sent verbatim: no automatic credit line, extra hashtags, or `#Shorts` suffix is added. The fixed title is 97 characters and the description is 3213 characters. Internal story titles/descriptions remain available for lyric planning, novelty checks, and source identification; they are not selected as public metadata. This avoids breaking saved storyboards or treating every song as a duplicate because the public title is shared.

The previous metadata selection is commented out in `pipeline.publish` and `shorts.short_metadata`. To restore story-based metadata, restore the two commented assignment lines in `pipeline.publish` instead of the fixed metadata assignments; in `shorts.short_metadata`, restore the commented return block instead of `fixed_metadata()`. Keep the existing settings, upload checkpointing, disclosures, and verification intact. The original `kids_rhymes.upload_description` and `metadata_tags` helpers remain available.

This selection applies when starting a new upload. Existing uploaded/scheduled video IDs keep their checkpointed metadata, so resuming an upload does not silently change a live video's title or description. Updating existing YouTube videos requires a separate explicit metadata update. No existing video is edited by this code change.

Shorts title override: new Shorts use `shorts_title` in `upload_metadata.json`: `Dudi dudi dum dum 🍼😻#shorts #shortsfeed #dudidudidam`. Long videos retain the fixed `title`. Both formats keep the same fixed description and empty tags. The Shorts publisher explicitly selects the Shorts metadata variant before upload.

## Independent Shorts music

The `short_music` job starts immediately after lyrics, alongside long-form music, the 16 landscape image shards and the 4 portrait image shards. It uses the pinned ACE-Step CPU runtime to synthesize a fresh 40-second female-vocal dance arrangement using the selected eight storyboard lines; no audio is cut from the long video. The audio reference continues to provide the existing channel style. New instrumentation/melody is model-generated and not guaranteed to differ in every detail. The renderer uses that new audio starting at its beginning; `clip_start` selects lyrics/images, not an offset inside the new music.

Music requests and progress are checkpointed separately under `output/RUN_ID/short-audio/clip-START-DURATION/`. Saved outputs are fingerprinted and duration-checked. Too-short results get up to three attempts; no looping/padding is used. `short-music-*` artifacts carry the new audio and checkpoints. Automatic Shorts reuse the prepared music; manual Shorts requests launch their own music job in parallel with portrait generation. New portrait/music uploads use a separate checkpoint namespace so existing uploaded Shorts are not overwritten.

Parallel jobs reduce serial waiting, but runner limits can queue jobs and synthesis time still varies. Workflows already started use their original commit; this change applies to newly started workflows.

## Recover a Shorts scheduling failure

New uploads allow up to 30 minutes (90 polls, 20 seconds apart) for YouTube processing readiness before automatic scheduling, within a shared 40-minute scheduling/HD-verification budget. Normal processing longer than two minutes no longer prematurely fails the upload. Pending checkpoints retain the same video ID and frozen release time for recovery. The uploader confirms the exact frozen timestamp by readback. Temporary server/rate errors and a recent, owned private upload's generic 403 receive bounded readiness retries. Named permission/quota failures, wrong ownership, rejected processing, and changed visibility stop with the original video ID retained. Retries never insert another video or report an unconfirmed schedule as complete.

For an already uploaded Short whose schedule/verification failed, run **Recover existing Shorts publication** with the failed workflow's `source_run` and original song `run_id`. It loads `short-publication-SOURCE_RUN`, requires the same uploaded video ID and source fingerprint in private Drive, and resumes only that existing video. It does not generate images, audio or video. Checkpoints are saved even if recovery fails. YouTube permission changes or service failures cannot be guaranteed away; permanent failures require resolving the reported account/service condition.
