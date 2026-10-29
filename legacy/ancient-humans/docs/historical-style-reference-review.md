# SSD-1B historical-style implementation review — 2026-10-27

Read-only references:
- Somoy-Jatri: image_cpu.py, workflow.py, long_video.py and islamic_content.py.
- Rezan-After-Dark: image_cpu.py, workflow.py and long_video.py.

Both use the same pinned SSD-1B weights, float32 CPU inference, DPM-Solver++ with Karras sigmas,
16 steps and guidance 9.0. Somoy-Jatri emphasizes realistic materials, natural daylight,
architecture, objects and landscape. Rezan-After-Dark emphasizes realistic materials,
scene-specific props and atmospheric lighting. Both explicitly suppress anime, cartoon,
flat colors, line art and cel shading in negative prompts.

The Ancient Humans implementation previously requested cartoon figures and explicitly
suppressed photorealism/cinematic realism. That conflict with the new requested direction
was removed. Production prompts now favor narration-specific prehistoric environments and
objects, with realistic textures and natural lighting. The model, resolution, steps,
guidance, scheduler, safety checker, voice, music, timing and upload flow remain unchanged.

No religious visual rules, horror mood, source code execution, account settings or publishing
behavior were imported from either reference repository. The reference code was inspected;
its output image quality was described by the owner, not independently established by this review.
