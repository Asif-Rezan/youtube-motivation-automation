# Continuous walking and foot-contact review

The current recommended tool-based workflow is documented in
`ROKOKO_WORKFLOW.md`. This file describes the earlier custom-retarget prototype.

The walking demo keeps one camera for the whole shot. It uses the existing Kat
character, its selected black Base Bra/Leather Pants outfit and the approved
garden background. This does not change production publishing or scheduling.

Body motion comes from CMU trial `36_02`, a continuous walk, turn and return,
using the Bruce Hahne BVH conversion from the `una-dinosauria/cmu-mocap` mirror.
The source sample begins at 0.25 seconds and lasts 10 seconds at 24 fps.
The source is stored locally in `fitness-walk-review/sources/36_02.bvh`.

## Repairs

- Removed the old camera cut. The heel-raise camera repair also produces a
  separate `kat-heel-raise-continuous-view-12s.mp4` so viewers do not reuse a
  cached copy of the previous two-angle video.
- Added stance anchors and two-bone leg IK instead of moving a rigid avatar.
- Repaired the mouth accessory's duplicate jaw/teeth ancestry. Its tongue had
  been left on the stationary imported skeleton and stretched during turns.
- Added native neutral sole alignment. The Daz and BVH ankle-to-toe bind vectors
  have different slopes; simply aiming one at the other produced pointed feet.
- Added heel-strike, flat-stance and toe-off phases, with gradual toe release.
- Replaced abrupt contact-flag height snapping with complete swing trajectories
  between captured step anchors. Toe paths use continuous quintic interpolation
  with 7.5 cm swing clearance and actual sole-mesh alignment to the ground.
- Stabilized the knee bend direction using the captured knee plane and used a
  smooth, reachable pelvis height rather than letting a nearly straight leg flip.
- Added a relaxed finger pose and small damped hair follow-through.
- Preserved native smile and blink controls from the facial repair.

The body is captured motion; the corrected foot paths/roll, relaxed fingers and
hair follow-through are authored controls. This is not an unmodified recording,
a universal movement generator or a full muscle/cloth/strand simulation.

## Local rebuild

Use Blender with the existing `io_anim_bvh` importer installed. Start from the
packed `fitness-pilates-review/kat-heel-raise-final.blend`, then run:

1. `scripts/build_walk_review.py`
2. Open its `fitness-walk-review/kat-continuous-walk.blend` and run
   `scripts/review_walk_geometry.py`.
3. From `kat-continuous-walk-final.blend`, run `ground_walk_review.py`, then
   `finish_walk_performance.py`, `retime_walk_footroll.py`,
   `plan_walk_contacts.py`, `stabilize_walk_knees.py` and
   `audit_walk_continuity.py`, reopening the saved final file between scripts.
4. Inspect foot contact and continuity reports and representative poses.
5. Render frames 1–240 as RGBA PNG to `fitness-walk-review/frames/f-0001.png`
   through `f-0240.png` from the final packed Blender file.
6. Run `compose_walk_review.py` in Python with Pillow/NumPy and ffmpeg.

The final file is `fitness-walk-review/kat-continuous-walk-final.blend` and the
video is `kat-continuous-human-walk-10s.mp4`. Scripts currently use the local
`/Users/asif/Documents/` working directories. The saved scene contains the
character and baked motion; a renderer does not rebuild the Daz character.

Numerical review reports are `walk-metrics.json`, `ground-review.json`,
`footroll-review.json`, `planned-contact-review.json` and
`continuity-review.json`. Camera continuity, floor clearance and frame-to-frame
root motion are checked. These checks do not certify every aspect of human gait
or exercise form. Each future exercise needs its own suitable motion and review.

References:
- [CMU motion capture](https://mocap.cs.cmu.edu/)
- [BVH conversion notes](https://github.com/una-dinosauria/cmu-mocap/blob/master/READMEFIRST.txt)
- [AAPM&R: biomechanics of normal gait](https://now.aapmr.org/biomechanics-normal-gait/)
- [NHS: heel-to-toe gait](https://www.leicspart.nhs.uk/wp-content/uploads/2019/02/660-Advice-on-gait.pdf)
