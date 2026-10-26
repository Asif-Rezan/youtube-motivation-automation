# Ancient Humans explainers

Updated 2026-10-26. New runs use `CONTENT_TYPE=human-history`; existing saved scripts are not replaced.
The legacy financial profile remains explicitly selectable for compatibility.

## Titles and topics

Every new title must contain **Ancient Humans** (preferred) or **Humans**, naturally and once.
The validator rejects titles missing Humans. Use a concrete question, problem or consequence,
with the keyword preferably early; no keyword stuffing or guaranteed ranking claims.

Eight rotating directions: food preservation, finding water, maintaining fire, learning survival
skills, making tools, sharing, choosing camps and transmitting knowledge. Avoid the last three
pillars and favor less-used recent ones. Original titles and explanations; no copied reference plots.

Example directions:
- How Ancient Humans Kept Food Before Refrigerators
- What Ancient Humans Did When Their Fire Went Out
- How Ancient Humans Found Water in Dry Landscapes
- Why Ancient Humans Spent So Much Time Making Tools

Twenty chapters retain the existing approximate 1,650–1,800 word target and measured 10–15 minute
video duration. Explain one central question progressively. Historical evidence, inference and
illustrative reconstructions must be distinguished. Do not fabricate sources, studies, statistics,
quotes or exact dates. The prompts encourage these limits but do not fact-check model output;
source-based editorial review remains necessary before treating a script as verified history.

## Scene images

Original hand-drawn 2D stick figures, cream oval heads, expressive simple faces, thin limbs,
bold irregular black contours, flat natural colors and little shading. Recurring illustration
character: short curly dark hair, ochre tunic and blue wrist tie. Backgrounds follow the actual
narration: camp, grassland, woodland, dry riverbed, shelter interior, or white for explanatory objects.
Do not force a mascot into object-only scenes or use the same camp for every explanation.

Prompt pattern: active subject + concrete action + important objects + period-appropriate setting.
Example: “Ari shields fading embers with a clay-free stone windbreak beside a grassy camp at dusk.”
This is a visual prompt example, not an archaeological claim about a specific population.
The renderer adds the cartoon styling. SSD's second text encoder receives compact style guidance
first to reduce style loss from long continuity descriptions. The old financial reference palette
is disabled for new workflow runs.

## Thumbnails

One expressive cartoon figure or small group, one large problem/contrast, simple colorful setting,
clear silhouette, room in the top quarter for a caption. Generate art without letters; overlay
2–5 uppercase yellow words with a black outline afterward for reliable readability.
Example: fire topic → cold embers and worried figure, caption “FIRE GONE?”
Adapt the general visual approach with original scenes and character design.

## Production retained

No changes to schedule, hosting, credentials, voice, music, safety checks, checkpoint storage,
upload/publishing logic, image interval or render size/steps. Existing workflow: SSD-1B CPU,
1024×576, 16 steps, guidance 9.0, new images every seven seconds, 1080p/30fps final video,
Kokoro am_michael, captions and Magenta music.
These are local source changes; no workflow was triggered, deployed or uploaded by this update.
