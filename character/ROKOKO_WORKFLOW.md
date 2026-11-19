# Recommended animation workflow: Blender + free Rokoko retargeting

Keep the chosen Daz Genesis 9/Kat character and its black Base Bra/Leather Pants.
Use Blender for retargeting, IK/contact cleanup, baking and rendering. No paid
Daz animation product was purchased. This review does not alter the production
AI idea/metadata generator, publishing, Drive cleanup or disabled schedule.

## Tool verified

Official Rokoko Studio Live Blender add-on **1.4.4** was installed from the
Rokoko GitHub release and successfully retargeted the sample in Blender **5.3.0**.
The official documentation states retargeting is free and does not need a
premium account. This automation uses the offline retarget operator; streaming,
account login and its optional login libraries are not needed.

`retarget_with_rokoko.py` creates a clean metre-scale proxy using the native Daz
bone lengths, aligns its arms to the source T-pose, invokes the actual official
`rsl.retarget_animation` operator and bakes rotations/root travel to the original
deform rig. The proxy prevents the retargeter's armature transform application
from changing the character's accessory/mesh bindings. The existing face,
materials, clothing and original rig are retained.

The add-on is installed locally at:
`~/Library/Application Support/Blender/5.3/scripts/addons/rokoko_studio_live`.
Archive hash and release provenance are in
`/Users/asif/Documents/fitness-rokoko-review/addon-provenance.json`.

## Rebuild the review sample

Working directory: `/Users/asif/Documents/fitness-rokoko-review`.
Current input character/source scene:
`/Users/asif/Documents/fitness-walk-review/kat-continuous-walk-final.blend`.

1. Open that input in background Blender and run `scripts/retarget_with_rokoko.py`.
   This produces `kat-rokoko-retarget.blend` and `bone-map.json`.
2. Open the raw retarget and run `scripts/prepare_rokoko_walk.py`. This produces
   `kat-continuous-walk-final.blend` with native blink/smile, mouth-chain repair,
   calibrated gaze and the captured contact timing.
3. Run `scripts/run_rokoko_review.py` with the local Python environment containing
   NumPy/Pillow and ffmpeg. It runs the recorded cleanup stages, verifies their
   logs, renders 240 RGBA frames and encodes a 10-second, 1920×1080, 24fps video.
   `--no-render` stops after the baked scene and numerical review are ready.
4. Run `check_heel_toe_contacts.py` inside final Blender with
   `FITNESS_REVIEW_DIR=/Users/asif/Documents/fitness-rokoko-review` to measure
   the heel/toe skin geometry at representative phases.

The output video is `kat-continuous-human-walk-10s.mp4`. The final packed editable
scene is `kat-continuous-walk-final.blend`. Rendering this baked file does not
recreate the Daz character or require Rokoko/account access.

## Contact and continuity cleanup

Raw retargeting does not guarantee natural contact for different proportions.
The cleanup preserves captured body motion and step anchors, adds native-neutral
heel-strike/flat-stance/toe-off roll, smooth swing paths and toe release, solves
leg IK, stabilizes the knee plane/pelvis height and checks sole clearance.
Contact shadows follow the actual lowest heel/sole/toe patch projected onto the
garden ground plane rather than a floating toe-joint marker.

The camera remains fixed throughout. The tongue accessory's duplicate jaw chain
follows the main facial rig. Native blink controls, a gentle smile, relaxed
fingers and restrained damped hair follow-through are retained.

Review files include `pipeline-receipt.json`, `continuity-review.json`,
`planned-contact-review.json`, `heel-toe-contact-review.json` and
`contact-shadows.json`. These are animation checks, not instructor certification.
Different exercises require suitable licensed motion and their own contact/form
review. This is not a universal one-click natural-motion guarantee, an unchanged
mocap recording or a full muscle/cloth simulation.

References:
- [Official free Rokoko retargeting guide](https://support.rokoko.com/hc/en-us/articles/4410463481489-Retarget-an-animation-in-Blender?page=1)
- [Official Rokoko releases](https://github.com/Rokoko/rokoko-studio-live-blender/releases)
- [CMU motion capture](https://mocap.cs.cmu.edu/)
- [AAPM&R normal gait biomechanics](https://now.aapmr.org/biomechanics-normal-gait/)
