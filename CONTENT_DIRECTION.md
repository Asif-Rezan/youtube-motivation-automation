# Ancient Humans documentary explainers

Updated 2026-10-27. New runs use CONTENT_TYPE=human-history. Every new title must contain
Ancient Humans (preferred) or Humans. Twenty chapters retain the existing measured video
length, voice, captions, music, image interval and upload process.

## Current image direction

SSD-1B stays pinned at segmind/SSD-1B revision 60987f37e94cd59c36b1cba832b9f97b57395a10,
1024×576, 16 steps, guidance 9.0. Cartoon and stick-figure styling is discontinued.
Use historical documentary reconstructions: realistic stone, wood, hide and earth textures,
scene-appropriate natural lighting and clear environmental compositions.

Prioritize the narrated place and material evidence: limestone shelters, camps, hearths,
flint tools, tinder, firewood, grassland and woodland. Do not replace narration-specific images
with unrelated historical buildings. Buildings, plants, tools and climate must fit the chosen
period and region; no modern equipment or generic fantasy castles in prehistoric scenes.
People and animals appear whenever they participate in the narration: hunting, gathering,
teaching, cooperation or wildlife encounters must retain the participants and their actions.
Use natural proportions, animal anatomy, scale and period-appropriate habitat. Do not replace
these events with empty scenery. Object-only shots can omit people; the empty preview samples
are not a global prohibition on humans or animals.
No recurring cartoon mascot or demand for identical generated faces.

Prompt pattern: specific subject/action + important materials + setting + short documentary style.
Keep the concrete subject before the encoder limit. Isolated objects use realistic close detail,
not a flat white diagram. Cold-ash scenes suppress flames; ember scenes can retain glow.
Negative prompts suppress anime, cartoon, flat colors, line art, cel shading and CGI. They no
longer suppress photorealism, cinematic realism or realistic skin texture.

Inspired by implementation patterns in the owner's Somoy-Jatri and Rezan-After-Dark repos:
short concrete scenes, realistic material texture, atmospheric but scene-appropriate light,
and anti-cartoon negatives. Do not import their religious restrictions or horror tone into
Ancient Humans episodes. These images are illustrative reconstructions, not historical evidence.

## Topics, narration and thumbnails

Final search metadata is generated from the completed narration, not just the outline.
The metadata prompt lives in video_metadata.py. Titles include Ancient Humans or Humans,
prefer natural readable phrasing around 50–75 characters and are capped at 85. Descriptions
target 4000–4400 characters within the 5000-character YouTube limit: keyword-bearing opening, episode-specific overview, 3–5 learning
bullets, a brief evidence/reconstruction note, one viewer question and a short subscribe CTA.
The final line has 3–5 relevant hashtags starting with #AncientHumans. Generate 10–18 distinct
topic search phrases as tags, within the existing 400-character comma-joined budget.
Do not invent keyword metrics, links, timestamps or topics absent from the script. No keyword stuffing.
Short descriptions, invalid hashtags, duplicate tags and production/music notes trigger one
bounded repair request, then stop if still invalid. The automatic Magenta music footer is removed;
audio generation is unchanged. These changes apply to new scripts, not edits to existing YouTube uploads.

Rotate food preservation, water, fire, learning survival skills, tools, sharing, camps and
transmitting knowledge. Distinguish archaeological evidence, inference and reconstruction;
do not invent sources, quotes, studies, dates or statistics. Source review remains necessary.

Thumbnails use a dedicated composition, not a reused wide scenic background: tight framing,
one dominant narrated subject on the right, truthful visual tension, realistic textures and
scene-appropriate lighting and natural exposure. Use relevant human/animal emotion when supported.
Reserve uncluttered space on the left for a compact two-line caption: white first line, warm yellow second line, thin outline. Do not darken the image to accommodate text.
Generated art contains no letters; caption typography is added afterward.
The planning model receives the title and story context and writes a concise thumbnail scene
and complementary curiosity text. These are design heuristics, not measured CTR predictions.
Only live audience testing can establish an improvement in clicks and watch time.

## Production retained

SSD-1B CPU, Kokoro am_michael, Magenta music, seven-second image interval, 1080p/30fps final
video, current schedule, credentials, safety checker, checkpoint storage and private upload flow.
The preview action generates sample images only and never uploads a video to YouTube.

Daily uploads declare synthetic media, English (United States) metadata/audio, and no paid promotion. After HD verification, schedule the first 06:00 America/New_York at least 24 elapsed hours after upload completion. Persist the UTC anchor and target across retries; follow New York daylight saving. Old runs without a scheduling request remain private.

Native end screens, cards and quizzes require YouTube Studio and are not supported by the uploader API. These elements are not claimed as inserted. This change applies to future uploads.

All text generation (outline, narration, metadata, measured-shot prompts and duration rewrites) uses local Qwen/Qwen3-4B-Instruct-2507, Q4_K_M, with pinned public weights and checksum verification. No hosted text service, external text key or fallback is used. Kokoro, local Whisper and SSD-1B remain unchanged. Reference implementation: Asif-Rezan/youtube-dark-psychology-automation story_cpu.py.
Reference snapshot: d5dd9c6c755be7a3118d48282358a09ed78bffe1. The daily prepare job allows up to 300 minutes for CPU text generation; image jobs retain their existing SSD-1B settings.
