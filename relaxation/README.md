# Relaxation preview

Run `.github/workflows/relaxation-preview.yml` manually or update
`.generation/relaxation-preview-request.json` on main. This creates a private
60-second sample, with no scheduled generation, YouTube/Facebook publication,
or changes to the fitness workflow. The existing Drive cleanup workflow is
unchanged; this sample uses expiring GitHub artifacts and no Drive uploads.

Six independent SSD-1B jobs generate 768×432 landscape images from different
nature prompts. Composition scales them to a 1280×720, 24 FPS MP4. A new scene
arrives every ten seconds with a 0.8-second dissolve. Image generation is real
CPU inference, not a static preselected image collection.

A separate pinned ACE-Step 1.5 job creates a 24-second original ambient piano
instrumental. A pinned AudioLDM small-v2 job creates ten seconds of gentle rain.
The mixer extends both with overlapping crossfades, balances the levels, fades
the ends and limits peaks. No ungenerated procedural sound is substituted if a
model fails. Prompt adherence, naturalness and absence of vocals require human
listening review; numeric audio checks cannot establish those properties.

**The AudioLDM checkpoint is CC-BY-NC-SA-4.0. This sample is only for private
noncommercial evaluation. Do not publish or monetize it.** Replace the nature
sound model with a suitably licensed option or obtain the necessary rights
before commercial rollout. The model card is
https://huggingface.co/cvssp/audioldm-s-full-v2 .

All successful intermediate outputs are kept as artifacts for seven days; the
final sample is kept for fourteen days. Native model generation can still take
substantial CPU time; this pipeline avoids per-frame 3D rendering but does not
claim that model inference is instantaneous. Source code does not use secrets,
paid inference APIs, narration, generated claims of therapeutic benefits, or
Blender assets.
