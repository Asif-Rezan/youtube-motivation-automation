# Daz character and Blender animation

## Current character

- Face and skin: Kat, from Genesis 9 Starter Essentials.
- Body: Laura / Genesis 9 female.
- Hair: brown Eirgrid Hair. The experimental perlk ponytail is hidden and is not the selected hairstyle.
- Outfit: black G9 Base Bra and LVA Pant (Leather Viking Armor). These pants are intentionally the selected leather pants, not fitted leggings.
- Demo: 6 seconds, 144 frames at 24 fps, 512 × 768, silent.

The Daz scene is the character-design source. Blender is the animation and rendering source.
This is a motion sample, not a finished photorealistic workout production. The motion is limited
to an arm/hand gesture and head movement. Lip-sync, a full exercise library, cloth simulation,
and automatic fitness publishing have not been completed. Inspect skin, eyes, hair, clothing
binding, and clipping before using a new pose in a production video.

## Pull the real files

Install Git LFS, then run from the repository root:

```sh
git lfs install
git pull
git lfs pull
git lfs fsck
```

`blender/kat-animated.blend` is the editable animation scene with packed image textures.
`blender/kat-outfit-trainer.fbx` is the Daz export used to construct it.
`daz/` contains both saved Daz outfit scenes. Version 2 is the latest saved scene;
the first version preserves the earlier pose for comparison.
`preview/kat-blender-animation.mp4` is the rendered demo.
Files use ordinary Git LFS storage, with no encryption or recovery password.

## Open and update

For Blender editing, open `blender/kat-animated.blend` in Blender 5.3 or newer.
The original render used Blender 4.5.16; the portable texture-packed backup was saved with 5.3.
The main armature is `Genesis9`. Pose bones and the saved timeline contain the gesture.
Adjust camera, lighting, skin/hair materials, or garment materials, save the blend file,
and render again. Pack newly added external textures before committing.

For Daz editing, install the licensed dependencies through Daz Install Manager:
Genesis 9 Starter Essentials (including Kat, Laura and Base Clothing), Eirgrid Hair for
Genesis 9, and dForce Leather Viking Armor for Genesis 9. Open a scene from `daz/`.
The DUF files reference those installed products; this folder does not replace the Daz
content library. These assets being free does not make their meshes/textures public domain;
their vendor licenses still apply.

## Run the saved scripts on another computer

From the repository root:

```sh
python3 character/prepare.py --daz-library '/path/to/My DAZ 3D Library'
```

This creates ignored working copies in `character/runtime/` and replaces the original
machine-specific paths in the scripts. The scripts in `scripts/` preserve the exact
original implementation as provenance; run the prepared copies, not the originals.

1. In Daz, open the prepared saved scene. Merge `runtime/reference_free_outfit.dsa`
   to apply Kat face and the selected outfit. Inspect the result before saving.
2. Merge `runtime/export_trainer_blender.dsa` to export the current character to FBX.
3. Import and inspect the FBX in Blender:

```sh
blender -b -P character/runtime/inspect_fbx.py
```

4. To rebuild the demonstrated gesture and render a preview:

```sh
blender -b character/runtime/trainer-import.blend -P character/runtime/animate_kat.py
blender -b character/runtime/kat-blender-short/kat-animated.blend -P character/runtime/render_kat_short.py
ffmpeg -framerate 24 -i character/runtime/kat-blender-short/frames/frame-%04d.png -frames:v 144 -c:v libx264 -crf 18 -pix_fmt yuv420p -movflags +faststart character/runtime/kat-demo.mp4
```

The importer contains a narrowly scoped workaround for stale Daz FBX skin bindings.
It runs only inside that Blender process and does not modify Blender's installed files.
It does not guarantee correct skinning for other characters or new outfits.
The eye composite image preserves Daz's separate sclera and iris layers.

## Save future changes to GitHub

Copy the final DUF and packed blend into their folders, update this README and preview,
then commit only the intended files:

```sh
git add character README.md
git commit -m 'Update Kat character and animation'
git push
```

## Automation

The daily `Wildlife simulation video` cron trigger has been removed. Manual dispatch
and its existing publication logic remain available. Hourly Drive cleanup remains on.
The fitness character demo is not wired into that wildlife workflow. No new generation
or publication run is started by this backup change.
