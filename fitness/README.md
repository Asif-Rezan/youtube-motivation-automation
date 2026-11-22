# Fitness production preview

Run **Fitness production preview · 60 seconds** from GitHub Actions. A commit
changing `.generation/fitness-preview-request.json` on main also starts a fresh
run. Daily scheduling remains disabled; no publishing credentials are used.

The graph runs Qwen planning and a real Linux Blender preflight, followed by
Kokoro voice, ACE-Step music, 20 Blender workers, the title-specific thumbnail,
final assembly, private Drive archive and a separate Drive cleanup audit.

The preview is exactly 60 seconds, 1920×1080, 24 fps, with five continuous
12-second heel-raise cycles. It uses the reviewed `kat-heel-raise-v1.blend` and
approved tropical garden image. It does not invent unbuilt Pilates poses. A
broader movement library remains necessary before making other workout claims.

## Models and production assets

- Idea, coaching copy, title, description, tags and thumbnail direction:
  pinned Qwen3-4B-Instruct-2507 using the existing checksum-verified CPU runtime.
- Voice: Kokoro-82M, `af_heart`, with timed cues fitted within their actual motion
  phases. Native Daz jaw/corrective morphs follow the real voice envelope. This
  is audio-aligned mouth motion, not phoneme-level facial capture.
- Music: pinned ACE-Step 1.5, generating a new 24-second instrumental bed from
  the episode's AI prompt. Sections overlap with crossfades to cover the minute.
  No stock track or procedural placeholder replaces a failed model generation.
- Character: Daz Kat/Laura, Eirgrid hair, black Base Bra and Leather Viking pants.
  Packed textures are verified, and Blender 5.3.0 is downloaded with a pinned
  official SHA-256 checksum. The Linux preflight must render before workers start.
- Thumbnail: two fresh Blender pose renders directed by the title's AI brief,
  composed with complementary colours and a split, diagonal or inset layout.
  The comparison concerns posture/raised heels, not a fictional physique change.

## Review and storage

Download `fitness-production-preview-RUN_ID`: `fitness-preview.mp4`,
`thumbnail.jpg/png`, `plan.json`, `metadata.json`, `quality-report.json`, voice
timings and the thumbnail brief. Final media is decoded and checked for exactly
1,440 frames, 60 seconds, 1080p and an AAC audio stream. Source-frame decode
failure stops composition. Foot skin must stay within the 2 mm floor tolerance.

Production intermediates are GitHub artifacts with one-day retention. Final
preview and audit artifacts remain for 14 days. The existing private Drive
configuration archives the verified MP4, thumbnail, plan, metadata and quality
receipt under `fitness/previews/RUN_ID/`. Cleanup audits only managed temporary
objects in that exact run namespace, and keeps final previews. Other projects,
historical previews and their publishing workflows are not swept by this job.

`DRIVE_TOKEN_JSON` and `DRIVE_FOLDER_ID` are the existing repository secrets.
No new paid API subscription is required. CPU music generation can be much
slower than rendering; jobs upload state/logs for diagnosis rather than silently
substituting canned audio.

The uploaded metadata marks English audio, Sports category, not made for kids,
no paid product placement and synthetic content. Privacy is private, and the
preview never calls either publishing API. The later ten-minute publish run
requires the user's review and request.

## Native render crash recovery

The first Linux run hit Blender exit 139 after roughly 30 frames in a long
process. The renderer now starts a fresh Blender process every 12 frames, uses
32 EEVEE samples at the same 1080p/24 fps, and avoids loading rendered PNGs back
into the live EEVEE image cache. Independent Python code fully decodes each PNG
and checks its geometry metadata before accepting it.

Each frame and its contact metadata are written atomically. A crashed batch
restarts only missing/invalid frames, up to three attempts. Complete validated
outputs may survive an abnormal renderer shutdown; a Python traceback or
semantic error always stops the job. Timeouts terminate the process group,
including the Blender/Xvfb children. Input fingerprints prevent mixing caches
from different scripts, characters or voice envelopes. Failure artifacts keep
completed checkpoints and per-attempt logs.

The `source_run` manual input, or the same field in the push request, restores
successful plan, voice, music and thumbnail artifacts from a failed run. The
recovery validates script/audio alignment, duration, thumbnail/title identity and
non-publishing status. This resumes the same episode; fresh runs still create
new AI ideas. Saved render checkpoints are restored when available. The final
output still requires all 1,440 frames in the correct order and a full decode.


AI workout prescription → native rig
------------------------------------
The AI package now prescribes each repetition's movement and duration, rather than
writing copy over an independent fixed loop. `fitness/sequence.py` checks the
exercise asset, allowed pace and exact 60-second total; it compiles output frames
to fractional source frames. Voice cues, chapter times, overlays and rig animation
all follow this prescription. The current verified asset supports heel raises at
10/12/14 seconds per repetition. New exercise types need a reviewed motion asset
before they can be executed. This is not automatic medical/form certification.
The renderer is still Blender EEVEE; this sequencing change does not remove CPU
render cost or promise realtime rendering. Fresh requests omit `source_run`.
