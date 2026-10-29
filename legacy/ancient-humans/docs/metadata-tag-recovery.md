# Metadata tag recovery — run 40632395483

The prepare job failed in stage-story after 34m55s of successful local Qwen requests. Its final error was `Use 8–18 distinct topic tags with no hashtags and total length <=400`. The log does not retain the rejected draft, so it does not identify which individual tag constraint failed. The Node.js 20 deprecation annotation was a warning, not the failed command.

The reference `youtube-dark-psychology-automation` uses the same core CPU Qwen/narration/rendering pipeline. This repository adds a completed-narration SEO stage with stronger metadata requirements than the reference. Previously its tags schema constrained only list/string types, while later application validation required count, uniqueness, hashtag exclusion and a joined character budget. The model could therefore produce structurally valid JSON twice and still terminate the entire preparation after all narration had been generated.

The fix:
- Keep valid tags unchanged.
- Normalize malformed tag lists locally, remove duplicates/hashtags, retain whole words, and bound count/character length.
- Fill sparse lists using episode titles, phrases found in completed narration and broad Ancient Humans subject terms, without adding specific unsupported historical claims.
- Keep title/description/content validation strict; formatting repair does not excuse invalid prose.
- Bound tag array/items in the model schema and compile the actual production metadata grammar in the existing early Qwen preflight.
- Exercise a complete twenty-chapter make_story flow with malformed final tags, and cover empty, duplicate, excessive, overlong, mixed-type, delimiter-packed and hashtag lists.

Validation before pushing: 126 local unit/component tests passed, including 18 focused metadata/explainer tests. Native llama.cpp grammar conversion is checked by the cloud component workflow on the production Python 3.12 runtime. No model, narration backend, image renderer, scheduling policy, credentials or channel configuration was changed.
