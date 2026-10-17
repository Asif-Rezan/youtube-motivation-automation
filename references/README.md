# Financial story image reference

`video-reference-frame.png` is a frame captured at about 04:23 from
[POV: The Day Your Boss Realized You Could Walk Away Anytime](https://www.youtube.com/watch?v=DDLBhndYpfg).
It is included as a visual reference for the outline, muted palette, and office setting.

`financial-story-style-1024x576.png` is an original illustration made from that
style reference. The automated SSD-1B renderer uses this original image as its
image-to-image starting reference. It is exactly 1024 × 576 pixels.

The [SSD-1B model card](https://huggingface.co/segmind/SSD-1B) demonstrates short,
concrete prompts and recommends a negative prompt with guidance near 9.0. It does
not publish an inference seed for its example images. This workflow uses a
reproducible seed of `1700 + shot index`, with `10000` added for each required
detail-check retry. It keeps 16 steps and guidance 9.0.

Example prompt for the reference scene:

> A young office worker calmly leaves a modest workplace carrying a shoulder bag while his manager watches from the doorway. Cinematic 2D editorial story illustration, clean dark outlines, controlled cel shading, muted olive, tan and navy colors, wide landscape composition, consistent character clothing, no text.

Example negative prompt:

> watercolor, 3d render, glossy plastic, realistic skin texture, blurry, low detail, distorted anatomy, extra limbs, watermark, lettering, text

Example settings: `seed=1700`, `width=1024`, `height=576`, `steps=16`,
`guidance_scale=9.0`, `reference_strength=0.85`. The model and revision are pinned
in `image_cpu.py`. A seed is reproducible only with the same model, revision,
prompt, reference image, and generation settings.
