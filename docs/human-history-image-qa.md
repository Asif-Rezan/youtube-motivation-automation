# Human-history image QA — 2026-10-26

Status: execution checks pass; requested visual quality has NOT passed editorial review.

The initial SSD prompts exceeded both CLIP encoder limits (147–184 tokens versus 77).
Compact prompts now avoid repeated style prose, put the narrated action first, bound SSD
encoder inputs, allow large faces and suppress tiny figures. Cold-gray-ash scenes suppress
flames without suppressing ember scenes. Code changes pass 93 unit tests.

Three follow-up GitHub Actions runs were visually reviewed:

- https://github.com/Asif-Rezan/youtube-motivation-automation/actions/runs/40319431760
  SSD-1B, 1024×576, 16 steps, guidance 9.0: larger thumbnail face, but wrong fire state,
  inconsistent characters and missing ember action.
- https://github.com/Asif-Rezan/youtube-motivation-automation/actions/runs/40321254592
  SSD-1B, same settings, simpler figure and cold-ash negatives: flat stick-figure styling,
  but unwanted circular compositions, missing ash objects and an incorrect ember scene.
- https://github.com/Asif-Rezan/youtube-motivation-automation/actions/runs/40322682646
  Existing DreamShaper-8 alternative, 768×432, 28 steps, guidance 7.5: simple cartoon style,
  but gray ash became a large solid mound, ember became a torch, thumbnail omitted the
  topic object, and character appearance remained inconsistent.

All three runs completed successfully. That validates generation, safety checking, dimensions,
artifact retrieval and caption rendering; it does not validate action accuracy or style match.
DreamShaper was tested only as a preview alternative. The daily workflow still uses SSD-1B.
Voice, music, scheduling and upload behavior were not changed by these experiments.

Neither tested unconditioned CPU model reliably reproduced the requested character identity
and narrated actions. Further prompt-only retries are not an established fix. A reference-
conditioned generation method or a stronger image backend needs its own validation before
claiming the reference-inspired visual direction is production-ready.
