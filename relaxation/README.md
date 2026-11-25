# AI relaxation previews

Run `.github/workflows/relaxation-preview.yml` manually or update
`.generation/relaxation-preview-request.json` on main. This creates a 60-second
review sample without YouTube/Facebook publishing or a recurring schedule.
Existing production publishing and Drive cleanup workflows are unchanged.

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

Six independent SSD-1B jobs generate 1024×576 landscape images at 20 steps.
Depth Anything V2 Small (pinned Apache-2.0 checkpoint) generates a depth mask
per image. The 1280×720 output is scaled from that source, not native 1080p.
A new scene arrives every ten seconds with a two-second smooth dissolve.
Camera pan/zoom varies by AI scene. Subtle rain uses depth-dependent visibility;
distant mist uses inverse depth. Small ripple overlays use conservative
AI-specified lower water regions, image texture/colour screening, and soft
masks. These are approximations, not validated water segmentation or actual
simulation. Inspect visual masks before production. No text is drawn on the
relaxation film; a separate 1920×1080 thumbnail uses the AI brief.

## Sound

Keep the successful sparse felt-piano/warm-pad style while generating a new
ACE-Step 24-second instrumental. AudioLDM produces three distinct accepted
15-second rain takes (up to four candidates, 40 inference steps). Each take is
trimmed to its steadiest ten-second window. Numerical screening rejects silence,
large peaks and unstable energy; it cannot reliably reject voices or establish
naturalness. Original takes and the review report are kept for listening.

A gentle 90–5800 Hz filter softens rumble/hiss; soft peak control reduces
spikes. Three selected clips overlap for four seconds each, yielding a
22-second bed, which is extended with further overlaps. Piano is foreground,
rain quieter; the full mix gets three-second fades and peak limiting. No
procedural replacement sound or static fallback package is silently used.

**AudioLDM small-v2 is CC-BY-NC-SA-4.0. This is a noncommercial evaluation
sample. Do not publish or monetize it.** Replace this sound model with a
suitably licensed source or obtain rights before commercial rollout.
Source: https://huggingface.co/cvssp/audioldm-s-full-v2 .

## Outputs and recovery

Intermediate artifacts last seven days; final MP4, thumbnail, metadata, plan,
contact sheet and quality report last fourteen days. No sample media is sent
to Drive; only idea history and plan checkpoints use existing Drive storage.
Successful generation can be reused through `relaxation-recover.yml` by setting
its recovery request to the source run ID. Old version-1 assets remain readable
by the compositor. Model inference still takes CPU time; no real-time inference
or guaranteed rain-quality claim is made.


## Three-hour draft workflow (manual only)

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

The draft reuses the generated short piano/rain beds to cover three hours; it
does not generate three hours of distinct original composition. Intermediate
artifacts expire in seven days. This workflow has no publishing or schedule and
was not triggered when adding these settings: the one-minute review remains
the current preview. Signal/schedule tests and a synthetic full-duration concat test validate
three-hour timing and embedded chapters; a real three-hour AI production render
has not been run. The noncommercial nature-model restriction still applies.
