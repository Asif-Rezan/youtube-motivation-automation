# AI relaxation previews

Run `.github/workflows/relaxation-preview.yml` manually or update
`.generation/relaxation-preview-request.json` on main. This creates a 60-second
review sample without YouTube/Facebook publishing or a recurring schedule.
The full relaxation workflow publishes to the configured YouTube channel and Facebook Page, then cleans its temporary Drive media after publication verification.

## Episode planning and diversity

`relaxation/planning.py` uses the existing pinned Qwen CPU backend to generate a
new idea, meaningful concept ID, title, description, tags, environment, lighting,
palette, six views, piano/rain prompts, camera choices and thumbnail brief.
`relaxation/ideas.json` in the existing private Drive Store holds history. The
previous tropical garden sample seeds that history. Recent concepts/titles go
into the prompt; duplicate IDs, close titles/ideas, duplicate views/tags and
incorrect duration labels fail bounded validation. This reduces repetition;
it cannot prove that every image or melody is perceptually unique.

All scenes describe the same physical setting, rain, lighting and palette.
Chapters are generated from scene times and added to the AI description.
`metadata.json` contains category Music, English language, not made for kids,
no paid promotion, and synthetic media disclosure. It is a packaging draft;
publication remains blocked for the review and sound-model license.

## Image and video quality

New episodes use ultra-realistic nature photography prompts: real botanical textures,
believable water/reflections, natural daylight, camera perspective and true-to-life
colours. Negative prompts reject CGI, cartoon, storybook and plastic-looking scenes.
Video colour grading is gentle; thumbnail-only colour/contrast/brightness enhancement
and bright complementary outlined text improve readability. These are generation
instructions, not a guarantee that every AI image will be indistinguishable from a photo.
Saved episodes retain their original visual style and assets.

Six independent SSD-1B preview jobs generate 1024×576 images at 20 steps.
Depth Anything V2 Small (pinned Apache-2.0 checkpoint) generates a depth mask
per image. The 1280×720 output is scaled from that source, not native 1080p.
A new scene arrives every ten seconds with a two-second smooth dissolve.
Camera pan/zoom varies by AI scene. Subtle rain uses depth-dependent visibility;
distant mist uses inverse depth. Small ripple overlays use conservative
AI-specified lower water regions, image texture/colour screening, and soft
masks. These are approximations, not validated water segmentation or actual
simulation. Inspect visual masks before production. No text is drawn on the
relaxation film; a separate 1920×1080 thumbnail uses the AI brief.

## Sound and provenance

The successful sparse felt-piano/warm-pad style remains an original ACE-Step
composition. Natural rain now defaults to a real recording, rather than the
AudioLDM output that did not pass the user's listening review.

`assets/rain-alex36917-blanket.ogg` is pinned to a verified Git blob and SHA-256.
It comes from “rain ambience” by alex36917 (Freesound #524605), edited by
Porrumentzio for Blanket, under CC BY 4.0. `assets/rain-source.json` holds the
source, mirror revision, checksum, license URL and complete credit. The sound
credit and processing disclosure are included in the AI description and
`nature-license.txt`. Attribution must remain with published derivatives.
Source: https://freesound.org/people/alex36917/sounds/524605/ .

The selector excludes the final 30 seconds of the recording (the original
page mentions a distant train horn near its end) and chooses a steady one-minute
window. It gently filters 55–7600 Hz, keeps recorded stereo, places the rain
below the piano and uses long loop overlaps and global end fades. Numerical
selection does not guarantee the absence of every external sound; listen before
publication. `rain-provenance.json` records the selected interval.

Legacy saved AudioLDM plans remain readable, but their original noncommercial
restriction still applies. The legacy artifact name `relaxation-ai-rain` is
retained for recovery compatibility; the new job, plan, provenance and credits
correctly identify field-recorded rain.

## Editing profile: nature-polish-v1

All ten requested edits are connected to previews and reusable production
clips: slow depth parallax, moving distant mist, masked foliage sway, masked
water texture/reflection movement and ripples, three wind/rain layers, subtle
light drift, four safe camera framings, two-second scene dissolves and smooth
audio transitions, consistent brighter colour grading, and minimal labels.

The preview intro title fades after four seconds; preview scene labels are
brief. Production labels are applied only at the twelve actual fifteen-minute
chapter boundaries, not on every repeated image. Only those twelve clips are
encoded again; the rest still use fast concatenation.

Depth/colour/texture masks are approximations. A still image does not contain
hidden surfaces or actual plant/water geometry. Keep shifts small and review
mask placement before production; this is gentle 2.5D motion, not physically
accurate 3D animation or a transformation of old photographs into new artwork.
New AI generations use the natural photographic direction described above.

## Outputs and recovery

Intermediate artifacts last seven days; final MP4, thumbnail, metadata, plan,
contact sheet and quality report last fourteen days. No sample media is sent
to Drive; only idea history and plan checkpoints use existing Drive storage.
Successful generation can be reused through `relaxation-recover.yml` by setting
its recovery request to the source run ID. Old version-1 assets remain readable
by the compositor. Model inference still takes CPU time; no real-time inference
or guaranteed rain-quality claim is made.


## Three-hour production workflow

`relaxation-production.yml` is configured for exactly 10,800 seconds, with up to
20 parallel image/depth workers (five images per worker) and up to 20 parallel reusable-clip workers,
subject to account concurrency limits. Each image worker loads the image model
once, generates its five distinct images, then generates their depth maps. Music and rain generation run alongside
images; long audio rendering runs alongside reusable visual rendering.

Qwen creates a fresh full-length package and twelve content-appropriate chapter
titles. One hundred coherent views are planned in bounded batches of twenty. The 1,080 ten-second slots reuse one hundred
images (10 or 11 times each), never on consecutive slots. Four pan/zoom variants per
image give four hundred reusable ten-second clips. The image order is shuffled once
per episode and then cycles, making its two-second transitions reusable too.
Final assembly concatenates already encoded clips without rendering all three
hours again. Chapters start at 00:00, 15:00, …, 02:45:00 and appear both in the
AI description and embedded MP4 chapter metadata. Titles must match the actual
shared piano/rain theme; no invented ocean/waterfall audio is claimed.

The production video reuses generated short piano/rain beds to cover three hours;
it does not generate three hours of distinct original composition. Intermediate
artifacts expire in seven days. Daily generation is enabled at 21:00 UTC (03:00 Asia/Dhaka), retaining the previous project schedule.

### Full publication and cleanup

Updating `.generation/relaxation-production-request.json` on main, or manually dispatching
`relaxation-production.yml`, starts an explicitly authorized full production run.
A preflight verifies the configured YouTube channel, Facebook Page and Drive credentials.
After assembly, the full episode and thumbnail are backed up to Drive. YouTube is
published as Music, English, not made for kids, no paid placement, with AI disclosure.
The AI description retains all twelve chapters and the recorded rain attribution.
Facebook publication follows verified YouTube publication. Cleanup requires both platform
receipts plus fresh Facebook/YouTube checks; only this episode's temporary media are
deleted. AI idea history, upload IDs and cleanup journals remain in Drive.

Rerun failed jobs on the original Actions run to retain the same episode identity.
Saved upload IDs are reused; an ambiguous YouTube upload without a saved ID stops
for reconciliation instead of risking a duplicate. Failed publication preserves Drive media.
The one-minute preview remains unpublished.

### AI scene planning recovery

Each accepted planning batch is checkpointed to Drive. Duplicate views are discarded
individually while valid new views are retained. Requests target only the remaining
image budget and include corrective feedback. After bounded repeated AI failures,
remaining prompts use distinct foreground/viewpoint layouts around the AI-authored
scene anchors; each image still receives its own AI generation and seed. This
prevents repeated text in one batch from aborting all 100 images. Failed-job retries
resume the original run's accepted planning progress. Progress logs report accepted
view counts and when composition recovery was used.

### Recover an existing full run after compositor fixes

The production CLI routes stages explicitly to their worker functions; the audio
command invokes `audio_worker`. Regression coverage exercises every worker command
and actually encodes an audio sample with FFmpeg. Audio is published as a completed
artifact only after duration, stereo and 48 kHz readback validation.

`.github/workflows/relaxation-production-recovery.yml` restores source inputs named
in `.generation/relaxation-production-recovery.json`. Keep `RELAX_EPISODE` equal to
that source run ID so Drive checkpoints and duplicate-upload protection retain the
original episode identity. Recovery waits up to 95 minutes for all 20 image artifacts,
plan, piano and rain, validates completeness, then performs rendering, assembly,
YouTube/Facebook publication and guarded Drive cleanup using updated code.

### Search-friendly packaging and upload details

AI packaging prompts lead with accurate piano/rain search intent, then the distinct
episode setting/mood and duration. Descriptions explain actual content early; tags
mix relevant broad and setting-specific phrases without keyword stuffing. Twelve
chapter names describe the real visual/mood progression and include natural relevant
phrases without claiming sound sources absent from the mix. Thumbnail text remains
short and episode-specific. These changes aim to improve clarity and appeal; search
ranking, CTR and virality are not guaranteed.

Production publishes Music category 10, English title/audio metadata, not made for
kids, no paid promotion, AI disclosure, standard YouTube license, embedding and
public statistics enabled. Platform readback checks verify configured upload details,
thumbnail and publication before cleanup. Chapters and CC BY rain credits remain
in the actual uploaded description.

### Daily schedule

The full production workflow runs every day at **03:00 Asia/Dhaka (21:00 UTC)**,
using the latest code on main: AI idea/metadata, 100 photographic images, three-hour
video, YouTube and Facebook publishing, then verified Drive cleanup. GitHub may
delay scheduled jobs during load. This is the generation start time; publishing
follows successful processing. The concurrency group prevents overlapping full
production runs from executing simultaneously. Recovery and preview workflows
remain manual/marker-triggered.
