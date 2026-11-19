# Tropical garden yoga environment

Original procedural Blender scene for a full-body yoga/workout presenter. It uses
3D geometry and procedural materials, not a background photograph. No paid assets
or external textures are required.

## Files

- `build_tropical_garden.py`: deterministic scene builder (seed 48).
- `tropical-garden.blend`: editable Blender scene.
- `tropical-garden-front.png` and `tropical-garden-three-quarter.png`: rendered previews.

## Rebuild

```sh
blender -b -t 6 -P environment/build_tropical_garden.py
blender -b environment/tropical-garden.blend -t 6 -P environment/refine_tropical_garden.py
blender -b environment/tropical-garden.blend -t 6 -P environment/light_tropical_garden.py
```

Built with Blender 5.3. Scene dimensions use metres. The teak deck is 4.8 × 3.5 m;
the yoga mat marks the character placement near the origin. Place feet at deck/mat
height (approximately Z=0.26 m) and check floor contact before animating.

## Cameras

- `01 • Full-body front`: front-facing presenter composition.
- `02 • Three-quarter`: wider oblique garden composition.
- `03 • Slow dolly`: keyed movement over 240 frames, 24 fps (10 seconds).

Select the camera in Blender before rendering. The scene includes individual deck
boards, pond stones, rippled transmissive water, lotus pads and flowers, ringed coconut
trunks, curved palm leaflets, broad banana leaves, flower beds and ground foliage.
The sun and sky are arranged for soft morning light; adjust rotation to control leaf shadows.

## Editing and quality

The scene is separate from the Daz character files and does not modify the selected
Kat character. Import/link that character into this scene for a combined video.
Preview renders use Cycles with 48 samples and denoising. For final output, increase
resolution and samples after checking the framing and render time on the target CPU.
Photorealism needs visual review; these are procedural plants, not scanned vegetation assets.

The generated environment geometry and materials are original to this project.
