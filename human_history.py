"""Creative direction only; uses the existing outline, narration and rendering pipeline."""
import hashlib
import json
import re

PROFILE = 'ancient-humans-explainer-v1'
IMAGE_PREFIX = 'Historical documentary reconstruction.'
IMAGE_NEGATIVE = 'anime, cartoon, stick figure, flat colors, line art, cel shading, modern buildings, modern equipment, plastic'


def image_negative(action, people=True, animals=False):
    cold = re.search(r'\bcold\b|\bgray ashes\b|\bgrey ashes\b', action, re.I)
    excluded_people = 'people, person, human face, human portrait, ' if animals else 'people, person, face, portrait, '
    return ('' if people else excluded_people) + (
        'flames, burning fire, glowing fire, smoke, ' if cold else '') + IMAGE_NEGATIVE


def visual_prompt(action, name='Ari', people=True, thumbnail=False, animals=False):
    """A concise environmental reconstruction, following the two reference repos."""
    action = re.split(r'\. (?:Character|Main character):', action, maxsplit=1)[0].strip().rstrip('.')
    if people:
        action = re.sub(r'\b'+re.escape(name)+r'\b', 'An adult in hide clothing', action, flags=re.I)
        design = 'Natural proportions, faces unobtrusive. '
    else:
        design = ''
    if animals:
        design += 'Natural animal anatomy and scale. '
    if thumbnail:
        # Dedicated packaging composition, not a wide documentary background.
        return (IMAGE_PREFIX + ' ' + action + '. Tight framing, dominant subject on right, '
                'uncluttered left third. Realistic textures, scene-appropriate lighting, natural exposure, sharp focal detail.')
    framing = 'Prominent focal object, uncluttered upper area. ' if thumbnail else 'Clear environmental composition. '
    return (IMAGE_PREFIX + ' ' + action + '. ' + design + framing +
            'Realistic stone, wood and earth textures, scene-appropriate natural lighting.')
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
THUMBNAIL_FALLBACKS = {
    'food_storage': 'KEEP FOOD SAFE', 'water': 'FINDING WATER',
    'fire': 'FIRE GONE?', 'childhood': 'LEARNING TO SURVIVE',
    'tools': 'WHY THIS TOOL?', 'cooperation': 'SURVIVING TOGETHER',
    'shelter': 'WHERE TO CAMP?', 'communication': 'PASSING KNOWLEDGE ON',
}
THUMBNAIL_SCHEMA = {'type': 'string', 'maxLength': 45,
                    'pattern': r"^[A-Za-z0-9][A-Za-z0-9!?'-]*( [A-Za-z0-9][A-Za-z0-9!?'-]*){1,4}$"}


def repair_thumbnail_text(story):
    """Keep valid copy; recover malformed model copy without losing the outline."""
    value = story.get('thumbnail_text')
    if isinstance(value, str):
        value = ' '.join(value.split())
        if 2 <= len(value.split()) <= 5 and len(value) <= 45:
            story['thumbnail_text'] = value
            return story
    # Do not truncate a sentence into an incomplete or misleading claim.
    story['thumbnail_text'] = THUMBNAIL_FALLBACKS[story['content_pillar']]
    return story


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
    if (not isinstance(story.get('thumbnail_text'), str) or
            not 2 <= len(story['thumbnail_text'].split()) <= 5 or
            len(story['thumbnail_text']) > 45):
        raise ValueError('Explainer thumbnail requires 2–5 words')


def direction(story):
    if story.get('content_profile') != PROFILE:
        return ''
    return ('This is an educational human-history explainer, not a fictional money story. '
            'Preserve the central question, evidence limits, time period, region and causal explanation. '
            'Distinguish archaeological evidence, inference and imagined reconstructions explicitly. '
            'Never invent studies, citations, dates, statistics or universal claims about all ancient humans. '
            'Visuals are illustrative historical reconstructions, not authentic photographs or eyewitness evidence. '
            'Expand explanations with concrete examples, not invented dialogue or adventures.')


def build_outline_schema(schema):
    keys = [f'chapter_{i:02}' for i in range(1, 21)]
    text = {'type': 'string'}
    scene = schema({'summary': text, 'image_prompt': text, 'continuity_note': text,
                    'image_prompts': {'type': 'array', 'items': text}})
    return schema({**{k: text for k in ('title', 'description', 'thumbnail_text',
        'thumbnail_prompt', 'character_description', 'protagonist_name', 'story_bible')},
        'thumbnail_text': THUMBNAIL_SCHEMA,
        'tags': {'type': 'array', 'items': text},
        'scenes': schema({key: scene for key in keys})})


def generate(day, history, ask, pause, check_originality, schema, *, draft=None, checkpoint=None):
    recent = history[-30:]
    excluded = {h.get('content_pillar') for h in recent[-3:]}
    candidates = [key for key in PILLARS if key not in excluded]
    pillar = min(candidates, key=lambda k: (
        sum(h.get('content_pillar') == k for h in recent),
        hashlib.sha256(f'{day}:{k}'.encode()).hexdigest()))
    keys = [f'chapter_{i:02}' for i in range(1, 21)]
    text = {'type': 'string'}
    outline_schema = build_outline_schema(schema)
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
    Description here is a working summary; final title, description and tags will be written from completed narration.
    Visuals are realistic prehistoric documentary reconstructions, not cartoons or stick figures.
    Prioritize narrated places, shelters, landscapes, tools, hearths and material evidence.
    Include realistic people and animals whenever they participate in the narrated action or explanation.
    Show hunting, gathering, teaching, cooperation and encounters through visible participants and their actions,
    not empty scenery replacing the event. Use medium or environmental views with natural proportions.
    Keep animal species, scale and habitat appropriate to the selected region and period.
    character_description records period-appropriate hide clothing and practical appearance, not a mascot design.
    An internal first name is for continuity only, not a claimed historical eyewitness.
    Scene image prompts: subject + action + relevant objects + setting, maximum 18 words. Two visual beats per chapter.
    Alternate environmental reconstructions with realistic close details of narrated objects and materials.
    Settings vary with the explanation: dry riverbed, camp, woodland, shelter interior, open grassland.
    Keep tools, plants, animals and clothing appropriate to the selected place and period.
    No generic scenic filler, modern offices, modern money props or decorative scenery.
    Thumbnail is a dedicated click-worthy composition, not a generic landscape or video background.
    Choose ONE truthful tension the video resolves, with one dominant subject and one supporting object at most.
    Show a large meaningful object, clear action or believable human/animal emotion when the story supports it.
    The subject must remain recognizable at phone size. No tiny distant subject, cluttered cave scenery,
    invented dangers, unsupported before/after claims, irrelevant shocked faces or guaranteed-CTR promises.
    thumbnail_prompt: MAXIMUM 24 words describing the exact subject, action, meaningful prop and emotion.
    The renderer adds tight framing, subject on right, uncluttered space on the left and realistic lighting.
    thumbnail_text: 2–4 short curiosity words that ADD a question/stake rather than repeat the full title.
    Pair text and imagery with the title's honest promise. No generated letters, logos or copied compositions.
    Chapter summary <=18 words, continuity_note <=18 words, image_prompt <=22 words.
    No chapter headings or calls to action in the plan. No reference-channel titles or scripts to copy.'''
    if draft is not None:
        outline = json.loads(json.dumps(draft))
        if (outline.get('content_profile') != PROFILE or outline.get('content_pillar') not in PILLARS
            or not isinstance(outline.get('scenes'), list) or len(outline['scenes']) != 20):
            raise ValueError('Invalid run-scoped story checkpoint')
    else:
        outline = ask(f'{brief}\nTopic direction: {PILLARS[pillar]}\nAvoid recent concepts: '
                      f'{json.dumps(recent)}', 5200, outline_schema)
        outline['scenes'] = [outline['scenes'][key] for key in keys]
        outline.update(content_profile=PROFILE, content_pillar=pillar, format='human_history_explainer')
    repair_thumbnail_text(outline)
    # The old format-repeat rule belongs to rotating fictional story formats.
    check_originality({**outline, 'format': None}, history)
    validate(outline)
    if checkpoint:
        checkpoint(json.loads(json.dumps(outline)))
    previous = ''
    for begin in (0, 5, 10, 15):
        chapters = outline['scenes'][begin:begin+5]
        if all(isinstance(chapter.get('narration'), str) and chapter['narration'].strip() for chapter in chapters):
            previous = chapters[-1]['narration']
            continue
        pause(60)
        group_keys = keys[begin:begin+5]
        # Constrain local decoding to complete chapters near the spoken-duration target.
        word = r"[A-Za-z0-9][A-Za-z0-9,.;:!?'\-]*"
        final_word = r"[A-Za-z0-9][A-Za-z0-9'\-]*[.!?]"
        narration_schema = {'type': 'string', 'pattern': '^' + word + '( ' + word + '){72,102} ' + final_word + '$'}
        group = ask(f'''Write only chapters {begin+1}–{begin+5} of this explainer.
        {direction(outline)}
        Title: {outline['title']}. Evidence and continuity brief: {outline['story_bible']}
        Full chapter plan: {json.dumps(outline['scenes'])}
        Previous ending: {previous[-700:]}
        Each chapter targets 82–88 spoken English words (74–104 permitted). Use plain English, single spaces and ASCII punctuation; finish with a complete sentence. Explain its assigned mechanism only; do not jump ahead.
        Keep a curious, conversational, lightly humorous tone. Use everyday comparisons with clear limits.
        No fictional financial plot, filler, headings, invented dialogue or viewer calls to action.
        Open chapter 1 inside the concrete problem; conclude the answer in chapter 20.
        Return narrations with exactly these keys: {group_keys}.''', 4200,
        schema({'narrations': schema({key: narration_schema for key in group_keys})}))
        for key, chapter in zip(group_keys, outline['scenes'][begin:begin+5]):
            narration = group['narrations'][key]
            if not isinstance(narration, str) or not narration.strip():
                raise ValueError('Missing explainer narration')
            chapter['narration'] = narration
        previous = outline['scenes'][begin+4]['narration']
        if checkpoint:
            checkpoint(json.loads(json.dumps(outline)))
    if not outline['scenes'][-1]['narration'].endswith(CTA):
        outline['scenes'][-1]['narration'] += CTA
    if checkpoint:
        checkpoint(json.loads(json.dumps(outline)))
    from video_metadata import generate_metadata
    outline.update(generate_metadata(outline, ask, pause, schema))
    check_originality({**outline, 'format': None}, history)
    validate(outline)
    return outline
