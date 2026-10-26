"""Creative direction only; uses the existing outline, narration and rendering pipeline."""
import hashlib
import json
import re

PROFILE = 'ancient-humans-explainer-v1'
IMAGE_PREFIX = 'Hand-drawn 2D cartoon.'
IMAGE_NEGATIVE = 'tiny figure, distant person, panoramic landscape, realistic anatomy, detailed scenery, modern clothes, hat, crown'


def visual_prompt(action, name='Ari', people=True, thumbnail=False):
    """Keep the subject and action ahead of scenery within the short CLIP window."""
    action = re.split(r'\. (?:Character|Main character):', action, maxsplit=1)[0].strip().rstrip('.')
    if people:
        action = re.sub(r'\b'+re.escape(name)+r'\b', 'the caveman', action, flags=re.I)
        design = 'Stickman caveman, large white round face, black dot eyes, messy brown hair, brown fur tunic, black line limbs. '
    else:
        design = ''
    framing = 'Large face and main object fill frame, top strip empty. ' if thumbnail else 'Subject and action fill foreground. '
    return (IMAGE_PREFIX + ' ' + design + action + '. ' + framing +
            'Simple background, thick black outlines, flat colors.')
PILLARS = {
    'food_storage': 'How Ancient Humans Kept Food Before Refrigerators',
    'water': 'How Ancient Humans Found Water in Dry Landscapes',
    'fire': 'What Ancient Humans Did When Their Fire Went Out',
    'childhood': 'How Ancient Humans Learned the Skills to Survive',
    'tools': 'Why Ancient Humans Spent So Much Time Making Tools',
    'cooperation': 'How Ancient Humans Survived by Sharing',
    'shelter': 'How Ancient Humans Chose Where to Build a Camp',
    'communication': 'How Ancient Humans Passed Knowledge to the Next Generation',
}
CTA = (' Which part of ancient human life would you like us to explore next? '
       'Leave a comment, like this video, and subscribe for more human history explainers.')


def validate(story):
    if story.get('content_profile') != PROFILE:
        return
    if not re.search(r'\bHumans\b', story['title'], re.I):
        raise ValueError('Human history title must contain Ancient Humans or Humans')
    if story['content_pillar'] not in PILLARS:
        raise ValueError('Unknown human history topic pillar')
    if not story.get('story_bible', '').strip():
        raise ValueError('Human history requires an evidence and continuity brief')
    if not 2 <= len(story['thumbnail_text'].split()) <= 5:
        raise ValueError('Explainer thumbnail requires 2–5 words')


def direction(story):
    if story.get('content_profile') != PROFILE:
        return ''
    return ('This is an educational human-history explainer, not a fictional money story. '
            'Preserve the central question, evidence limits, time period, region and causal explanation. '
            'Distinguish archaeological evidence, inference and imagined reconstructions explicitly. '
            'Never invent studies, citations, dates, statistics or universal claims about all ancient humans. '
            'The recurring cartoon character illustrates examples; it is not a real historical witness. '
            'Expand explanations with concrete examples, not invented dialogue or adventures.')


def generate(day, history, ask, pause, check_originality, schema):
    recent = history[-30:]
    excluded = {h.get('content_pillar') for h in recent[-3:]}
    candidates = [key for key in PILLARS if key not in excluded]
    pillar = min(candidates, key=lambda k: (
        sum(h.get('content_pillar') == k for h in recent),
        hashlib.sha256(f'{day}:{k}'.encode()).hexdigest()))
    keys = [f'chapter_{i:02}' for i in range(1, 21)]
    text = {'type': 'string'}
    scene = schema({'summary': text, 'image_prompt': text, 'continuity_note': text,
                    'image_prompts': {'type': 'array', 'items': text}})
    outline_schema = schema({**{k: text for k in ('title', 'description', 'thumbnail_text',
        'thumbnail_prompt', 'character_description', 'protagonist_name', 'story_bible')},
        'tags': {'type': 'array', 'items': text},
        'scenes': schema({key: scene for key in keys})})
    brief = '''Create an ORIGINAL English educational explainer about ancient human life.
    Use the assigned topic as a direction, invent a fresh question and wording.
    Every title MUST contain the exact phrase Ancient Humans (preferred) or the word Humans.
    Use it once, naturally, preferably early. Max 85 characters. Never use POV: You titles.
    Do not promise ranking, certainty, a secret discovery or a proven answer where evidence is limited.
    Focus on ordinary survival problems, practical mechanisms and surprising tradeoffs.
    Open with a specific physical problem; explain the answer progressively over twenty chapters.
    Chapters 1–3: question and immediate stakes. 4–8: mechanisms and concrete examples.
    9–14: complications, regional differences and alternative explanations.
    15–18: connect the evidence and clarify what remains unknown. 19–20: answer the opening question.
    This is not a fictional biography or motivational lesson. No invented named historical witnesses.
    Archaeological evidence is incomplete: distinguish known evidence, plausible inference and
    illustrative reconstruction. No invented sources, precise dates, statistics, quotes or studies.
    Do not generalize one recent hunter-gatherer society to all prehistoric populations.
    Avoid medical advice, present-day political claims and speculative evolutionary just-so stories.
    story_bible: <=180 words defining region, broad period, mechanisms, uncertainty and visual continuity.
    Description must identify an educational overview with illustrative reconstructions and uncertainty.
    Character is an ORIGINAL hand-drawn stick figure with large white round face, dot eyes, black line limbs,
    messy brown hair and brown fur tunic; avoid another channel's mascot.
    Give it an internal first name for visual continuity only. No photorealistic face description.
    Scene image prompts: subject + action + relevant objects + setting, maximum 18 words. Two visual beats per chapter.
    Alternate literal environmental scenes with simple explanatory object drawings on white when useful.
    Settings vary with the explanation: dry riverbed, camp, woodland, shelter interior, open grassland.
    Keep tools, plants, animals and clothing appropriate to the selected place and period.
    No generic scenic filler, modern offices, modern money props or decorative scenery.
    Thumbnail: ONE clear visual tension, large expressive stick figure, one large relevant object,
    colorful simplified background, bold black contours. Reserve the TOP QUARTER for a text overlay.
    thumbnail_text: 2–5 short curiosity words that complement rather than repeat the full title.
    thumbnail_prompt: original scene, no generated letters, no logos or copied compositions.
    Chapter summary <=18 words, continuity_note <=18 words, image_prompt <=22 words.
    No chapter headings or calls to action in the plan. No reference-channel titles or scripts to copy.'''
    outline = ask(f'{brief}\nTopic direction: {PILLARS[pillar]}\nAvoid recent concepts: '
                  f'{json.dumps(recent)}', 5200, outline_schema)
    outline['scenes'] = [outline['scenes'][key] for key in keys]
    outline.update(content_profile=PROFILE, content_pillar=pillar, format='human_history_explainer')
    # The old format-repeat rule belongs to rotating fictional story formats.
    check_originality({**outline, 'format': None}, history)
    validate(outline)
    previous = ''
    for begin in (0, 5, 10, 15):
        pause(60)
        group_keys = keys[begin:begin+5]
        group = ask(f'''Write only chapters {begin+1}–{begin+5} of this explainer.
        {direction(outline)}
        Title: {outline['title']}. Evidence and continuity brief: {outline['story_bible']}
        Full chapter plan: {json.dumps(outline['scenes'])}
        Previous ending: {previous[-700:]}
        Each chapter 82–88 spoken English words. Explain its assigned mechanism only; do not jump ahead.
        Keep a curious, conversational, lightly humorous tone. Use everyday comparisons with clear limits.
        No fictional financial plot, filler, headings, invented dialogue or viewer calls to action.
        Open chapter 1 inside the concrete problem; conclude the answer in chapter 20.
        Return narrations with exactly these keys: {group_keys}.''', 4200,
        schema({'narrations': schema({key: text for key in group_keys})}))
        for key, chapter in zip(group_keys, outline['scenes'][begin:begin+5]):
            narration = group['narrations'][key]
            if not isinstance(narration, str) or not narration.strip():
                raise ValueError('Missing explainer narration')
            chapter['narration'] = narration
        previous = outline['scenes'][begin+4]['narration']
    outline['scenes'][-1]['narration'] += CTA
    return outline
