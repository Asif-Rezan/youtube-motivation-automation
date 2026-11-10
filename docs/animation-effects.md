# Episode animation effects

The approved animation set includes tummy wiggle, gentle jelly bounce, clap/step, penguin movement, floating balloons, glowing fireflies, ripple hops and bubbles. The existing wave, waist, step, sway and hop variants remain available. Scene lyrics select explicit actions; otherwise a repeatable four-scene dance phrase is used.

The original sky/foliage/grass motion, bounded camera zoom/pan, character approach/rest actions and story props remain. Landscape episodes and portrait Shorts use the same animation engine.

Smile/mouth deformation, head/ear warping and whole-sprite spinning remain disabled. A brief blink is permitted only on a conservative single eye-pair rig with opaque, low-texture surrounding skin; uncertain faces remain untouched. At least the upper 65% of each cropped actor (more for a lower detected face) is protected from body deformation. Balloons, fireflies and ripple hops retain their original sprite pixels before the optional blink/compositing.

Dancers share the requested musical beat phase across scenes; energy differences and half-beat ripple delays provide variation. Normal dance keeps the root on the floor, with alternating swing feet. Explicit hop/jelly moves alone lift the whole actor. Poses blend around a beat-aligned middle switch. This is CPU image deformation, not inferred anatomical joints or audio beat detection.

Camera pushes/pans ease in and out with cast bounds enforced. There is no hard mid-shot punch-in. Final assembly blends the outgoing held frame into each incoming shot over 160 ms while preserving five seconds per scene and the original audio timeline. Only two clips decode at once, and verified transition renders are cached.

Animation cache versions invalidate old rendered clips while preserving existing segmentation and background layers. These effects apply to new generation runs using the updated code; already uploaded videos and in-progress runs pinned to an older commit are unchanged.
