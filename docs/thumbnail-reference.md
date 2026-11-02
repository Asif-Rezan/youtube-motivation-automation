# Reference-guided 3D storybook thumbnails

Landscape episode thumbnails use `assets/thumbnail/kids-dance-reference.png`, supplied by the user, as an img2img starting image. The scene images and portrait artwork still use the existing text-to-image path. The reference is not the numeric random seed: thumbnails retain an episode-specific numeric seed as well.

The prompt prioritizes cute stylized 3D storybook characters, joyful dancing poses, a large central toddler with companions, colorful rompers, baby animal friends and a vibrant dreamy garden party. Photorealism remains in the negative prompt. This guides restyling; likeness, character count and exact composition are not guaranteed by the model.

`THUMBNAIL_DENOISE_STRENGTH` defaults to `0.50`. Lower values retain more of the reference (including photographic features); higher values permit more change toward the prompt. It is denoising strength, not a similarity percentage. Adjust after visual review. Accepted range is greater than zero through one, with at least one effective denoising step. `THUMBNAIL_REFERENCE_IMAGE` can override the bundled reference path.

The same pinned SSD-1B model and CPU settings are reused through Diffusers `AutoPipelineForImage2Image.from_pipe`, without loading duplicate model weights. Existing output safety checks and retry behavior apply to reference-guided output too. Missing/corrupt references and invalid settings fail explicitly. The manifest stores the reference checksum and strength so a changed reference or strength invalidates the thumbnail cache, while scene cache entries stay unchanged. Previously published thumbnails are not changed.

Implementation follows the official [Diffusers img2img guide](https://github.com/huggingface/diffusers/blob/main/docs/source/en/using-diffusers/img2img.md). Automated checks cover routing, cache changes, validation and pipeline calls with a simulated model. Actual generated appearance requires a visual preview; no claim of visual similarity is made by those tests.

Thumbnail cast v2 selects two animal species, five distinct hairstyle/eye descriptions, five unique clothing colors and a mix of boys and girls per episode. Selection is repeatable for retries and stored in the thumbnail manifest. The prompt puts species and color variation early and avoids appending the episode scene prompt, which could otherwise reintroduce conflicting fixed animals. At strength 0.50 the reference may still dominate faces and species; this is requested variation, not a guarantee of changed output. A real preview is required to assess adherence.
