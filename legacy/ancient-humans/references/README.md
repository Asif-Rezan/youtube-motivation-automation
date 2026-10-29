# Financial story image reference

`video-reference-frame.png` is a frame captured at about 04:23 from
[POV: The Day Your Boss Realized You Could Walk Away Anytime](https://www.youtube.com/watch?v=DDLBhndYpfg).
It is included as a visual reference for the outline, muted palette, and office setting.

`financial-story-style-cool-1024x576.png` is an original illustration made from
that style reference, then recolored to a cool slate blue, teal, and gray palette.
The automated SSD-1B renderer combines its illustration style with the project's
brighter color description without copying the cool reference palette.
Every scene starts from fresh noise,
not this image. Style guidance is textual; it is not pixel-level style transfer.
It is exactly 1024 × 576 pixels.

`preview/faithful/financial-story-seed-1700.png` is the verified SSD-1B
historical output using img2img strength 0.35. It retained the two people and
office layout, which also caused unrelated scenes to repeat the reference.
This composition-preserving path is no longer used. Its `.image.json` records the model revision,
reference hash, seed, dimensions and render duration. The earlier `preview/cool/`
image used strength 0.85 and changed the composition substantially. See
[successful preview run #3](https://github.com/Asif-Rezan/youtube-motivation-automation/actions/runs/39021905959).

The [SSD-1B model card](https://huggingface.co/segmind/SSD-1B) demonstrates short,
concrete prompts and recommends a negative prompt with guidance near 9.0. It does
not publish an inference seed for its example images. This workflow uses a
reproducible seed of `1700 + shot index`, with `10000` added for each required
detail-check retry. It keeps 16 steps and guidance 9.0.

Example prompt for the reference scene:

> A young office worker calmly leaves a modest workplace carrying a shoulder bag while his manager watches from the doorway. Cinematic 2D editorial story illustration, clean dark outlines, controlled cel shading, muted slate blue, dusty teal and cool gray colors, soft overcast daylight, wide landscape composition, consistent character clothing, no text.

Example negative prompt:

> watercolor, 3d render, glossy plastic, realistic skin texture, blurry, low detail, distorted anatomy, extra limbs, watermark, lettering, text, warm orange lighting, red color cast, sepia

Example settings: `seed=1700`, `width=1024`, `height=576`, `steps=16`,
`guidance_scale=9.0`, `reference_mode=style-only-v1`. The model and revision are pinned
in `image_cpu.py`. A seed is reproducible only with the same model, revision,
prompt, reference image, and generation settings.
