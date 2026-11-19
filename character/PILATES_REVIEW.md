# Heel-raise animation review

This isolated 12-second demo repairs the existing Kat character and demonstrates
one slow controlled standing double heel raise. It does not change the production
AI planner, publishing, Drive cleanup, or the disabled daily schedule.

## Files

- `scripts/build_pilates_review.py`: reset the previous generic CMU movement;
  bind a gentle native smile, native blink correctives and eyelid rotations;
  author smooth weight transfer, raise, hold, lower and return phases.
- `scripts/finish_pilates_review.py`: add restrained voice-amplitude jaw controls,
  check floor penetration and approximate static balance, render review views.
- `scripts/compose_pilates_review.py`: generate timed local voice cues and quiet
  original music, composite the approved garden image, countdown and movement cues.
- Working output: `/Users/asif/Documents/fitness-pilates-review/`.
- Editable final scene: `kat-heel-raise-final.blend`.
- Final video: `kat-pilates-heel-raise-12s.mp4`.

The input scene is
`/Users/asif/Documents/fitness-mocap-sample/kat-cmu-mocap-final.blend`.
The installed Daz Genesis 9 FACS files are needed to rebuild the facial morphs.

## Rebuild order

1. Run `compose_pilates_review.py --audio` using the local Python environment
   with NumPy and Pillow. This needs macOS `say` and ffmpeg.
2. Open the input Blender file in background mode and run
   `build_pilates_review.py` to generate `kat-heel-raise-review.blend`.
3. Open that review file and run `finish_pilates_review.py`. Inspect its face,
   blink, talking and quarter-view images and the numerical reports.
4. Open `kat-heel-raise-final.blend` and run `render_pilates_views.py`. It keeps
   a fixed camera throughout and renders frames 1–288 at 24 fps,
   1920×1080, RGBA PNG, to `frames/f-0001.png` through `frames/f-0288.png`.
   The legacy `--quarter` option rerenders only frames 133–288 to repair an old
   two-angle render; it now uses the same fixed front view.
5. Run `compose_pilates_review.py` without arguments to encode the video.

## Repairs and checks

Shape keys must explicitly start from the Basis, with `from_mix=False`. Creating
successive corrective keys from the mixed shape accumulated unrelated facial
deformations during blinking. Native blink also requires the native eyelid bone
rotations, not just its corrective mesh deltas. Neck and head are no longer
driven by mismatched general-exercise capture in this sample. Body skinning uses
preserve-volume deformation.

`rig_repairs.py` also connects the mouth accessory's duplicate jaw/teeth parent
chain to the main facial rig. The tongue retained its duplicate skeleton after
vertex-group renaming; without this repair, rotating the head stretched the
mouth mesh back toward its old bind position.

Forefoot joint markers are anchored; ankle plantarflexion and root movement are
solved together. Weight moves forward before the heels rise. A constant sole
calibration prevents the imported mesh from intersecting the deck. Reports:

- `contact-review.json`: forefoot drift, phases, foot angle and body lean.
- `foot-mesh-review.json`: all 288 frames, lowest foot vertex, approximate
  segment-mass center of mass and acceleration-based zero-moment point inside
  the near-contact hull. The initial quick transfer failed this dynamic check;
  the delivered version uses a slower 1.5-second transfer before heel lift.
  This point-mass balance approximation omits centroidal angular momentum.

The body-mass distribution is an approximate animation plausibility model,
not a measured person. The animation uses kinematics, not a rigid-body, cloth,
or muscle simulation. Jaw movement follows voice amplitude, not phoneme visemes.
This sample is reference-authored, not motion capture. It has not received a
qualified Pilates instructor's form review and must not be labeled certified
instruction or silently published as a full workout.

Exercise reference: [NHS standing exercises](https://www.nth.nhs.uk/resources/standing-exercises/).
Topic/style reference: [BEST PILATES WORKOUT](https://www.youtube.com/@BESTPILATESWORKOUT).
Production ideas, titles, descriptions and tags should continue to come from the
existing AI model, with each exercise mapped to its exact reviewed animation.
