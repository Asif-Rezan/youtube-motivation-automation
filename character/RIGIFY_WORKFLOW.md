# Rigify control rig and Rokoko motion

This branch adds an editable Rigify body control rig to the existing Kat trainer.
The Daz mesh, face controls, skin, hair and clothing remain on the original
Genesis9 deform skeleton. It does not regenerate the character or auto-weight
the face. The earlier Rokoko and heel-raise scenes remain available.

The saved editable scene is `blender/kat-rigify-walk-v1.blend`; the rendered
sample is `preview/kat-rigify-walk-10s.mp4`. Verification reports are stored in
`motion/reviews/rigify/`.

## Build a separate review scene

Use Blender 5.3 with its bundled Rigify add-on. Set `FITNESS_RIGIFY_DIR` to an
output directory; the scripts default to the local `fitness-rigify-review` folder.

1. Open `character/blender/kat-rokoko-walk-v1.blend` and run
   `character/scripts/build_rigify_trainer.py`.
2. Open the resulting `kat-rigify-controls.blend` and run
   `character/scripts/animate_rigify_trainer.py`.
3. Open `kat-rigify-motion.blend` and run `clean_rigify_contacts.py`.
4. Open the resulting `kat-rigify-final.blend`; run `review_rigify_trainer.py`
   to render inspection angles and measure the native-rig bridge.
5. Run `audit_rigify_motion.py` on the final saved scene to check evaluated
   rotations, packed textures and disabled leg stretch.

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

The 240-frame review measured a minimum sole height of -1.22 mm, within the
2 mm review tolerance, and root travel below 4.23 cm per frame. The ankle can
depart from the original capture by up to 3.64 cm during contact cleanup.
These measurements do not establish correct form for other exercises.
