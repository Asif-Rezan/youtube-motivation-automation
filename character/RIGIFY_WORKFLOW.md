# Rigify control rig and Rokoko motion

This branch adds an editable Rigify body control rig to the existing Kat trainer.
The Daz mesh, face controls, skin, hair and clothing remain on the original
Genesis9 deform skeleton. It does not regenerate the character or auto-weight
the face. The earlier Rokoko and heel-raise scenes remain available.

The saved editable scene is `blender/kat-rigify-walk-v1.blend`; the rendered
sample is `preview/kat-rigify-walk-10s.mp4`. Verification reports are stored in
`motion/reviews/rigify/`.

## Build a separate review scene

Use Blender 5.3 with its bundled Rigify add-on. Set `FITNESS_RIGIFY_DIR` to the
same output directory for every stage. The complete runner defaults to the
local `fitness-rigify-upright-review` folder.

After preparing the portable scripts, `run_natural_gait_review.py` runs the
complete build, source restoration, animation, contact cleanup, regression
checks, render and composition. Set `BLENDER` to the Blender executable and use
a Python environment with Pillow/NumPy plus ffmpeg on PATH. `--no-render` stops
after the checked editable scene; `--from-controls` resumes from already
prepared controls and their gait plan. Each stage records a log and receipt;
a Python traceback stops the pipeline even when Blender exits with code zero.

1. Open `character/blender/kat-rokoko-walk-v1.blend` and run
   `character/scripts/build_rigify_trainer.py`.
2. Open the resulting `kat-rigify-controls.blend` and run
   `prepare_natural_gait.py`. Keep the same `FITNESS_RIGIFY_DIR` for all stages.
   This restores the untouched Rokoko bake from the versioned native-pose JSON,
   detects stance/swing from the capture, and writes `gait-plan.json` plus an
   updated `kat-rigify-controls.blend`. An original intermediate Rokoko blend
   can optionally be supplied through `FITNESS_RAW_ROKOKO`.
3. Open the updated controls file and run `animate_rigify_trainer.py`.
4. Open `kat-rigify-motion.blend` and run `clean_rigify_contacts.py`.
5. Open the resulting `kat-rigify-final.blend`; run `audit_walk_posture.py`,
   `audit_rigify_motion.py` and `review_rigify_trainer.py`. These check the neck,
   final hip height, trailing-foot release, arm swing, evaluated rotations,
   packed textures, disabled leg stretch and actual control response.

Blender can return exit code zero after a Python error. Check each log for a
traceback and require the expected output file before continuing.

Render frames 1–240 from the final scene at 1920×1080, 24 fps, with RGBA PNG
output named `frames/f-0001.png` through `frames/f-0240.png` under the output
directory. `clean_rigify_contacts.py` writes `contact-shadows.json` there.
Run the prepared `compose_walk_review.py` with `FITNESS_REVIEW_DIR` pointing
to that directory, `FITNESS_VIDEO_NAME=kat-rigify-walk-10s.mp4` and
`FITNESS_REVIEW_LABEL="Rigify controls · Rokoko motion · Leg IK"`.
It combines the approved garden, projected foot shadows and quiet demo audio.
Pillow, NumPy and ffmpeg are required for this composition step.

## Editing

Select `Trainer_Rigify`, enter Pose Mode and use the generated controls.
`foot_ik.L/R` move the feet; `thigh_ik_target.L/R` control the knee poles.
Leg stretching is disabled. The torso and arm FK controls carry the captured
performance. The independent `Rokoko_Baked_Source` preserves the original
official Rokoko retarget result, avoiding a dependency cycle.

The hidden `Rigify Native Rest Offsets` helpers calibrate the different Daz and
Rigify bone axes. Do not replace their rotation-only bridge with world-space
Copy Transforms: the original Daz skeleton uses centimetres while Rigify uses
metres. Copying scale would enlarge the character 100 times.

The generated Rigify UI is stored as a Blender text block. Enable the bundled
Rigify add-on to regenerate the rig. Only allow the embedded rig UI script for
this reviewed local scene if you want its extra snapping panels; the ordinary
pose controls and saved animation do not require enabling arbitrary scripts.

## Limits

This is a walking/turning rig verification sample. Exercise-specific mocap,
hand contacts, floor transitions and form checks still need their own reviews.
Rigify is a control system, not automatic human physics or proof of correct
Pilates technique. Production fitness publishing and the daily schedule remain
pending the expanded movement library requested by the user.

The earlier version held the trailing foot at the clip boundary, forcing the
pelvis down to 0.776 m. It also retained a forward neck angle of about 23 degrees
and both arms behind the torso. The corrected version restores the unmodified
Rokoko capture, detects toe-off from its motion, raises the ankle with heel roll,
and limits pelvis height by actual leg reach. Foot pitch is smoothed across
toe-off so it cannot jump from 35 to 10 degrees in one frame. Opposing arm swing follows the
captured thigh phase; the head looks ahead and the chest stays over the pelvis.

The corrected 240-frame review measured final hip height 0.900 m, neck lean
below 7.64 degrees, opposite arm swings of about +/-16 degrees and trailing
ankle travel of 10.5 cm over the final 12 frames. The maximum evaluated ankle
rotation step decreased from about 25.7 to 10.1 degrees per frame. Minimum sole height was
-0.077 mm, within the 2 mm review tolerance. A portable-capture rebuild matched
the original gait plan to within 0.00014 mm. These checks catch the reported
regressions; they do not establish correct form for other exercises.
