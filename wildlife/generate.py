"""Generate and checkpoint a distinct wildlife episode with the existing Qwen CPU runtime."""
import argparse
import hashlib
import json
from dataclasses import fields
from pathlib import Path
import re

from lyrics_cpu import StoryGenerationError, WILDLIFE_NARRATION_PATTERN

from .episodes import Beat
from .narration import spoken_text
from .metadata import POWER_WORDS, Packaging, emphasize_title, normalize_generated_tags
from .whatif import TOPICS, select_topic


SPECIES = {'goats': 'goat', 'deer': 'deer', 'rabbits': 'rabbit'}
HABITATS = ('wooded island', 'grassland island', 'coastal dunes', 'rocky island', 'marsh island')
PRESSURES = ('drought', 'winter', 'food competition', 'vegetation loss', 'water shortage', 'habitat recovery')
HEADLINES = {'drought':'WHEN RAIN STOPS','winter':'WINTER ARRIVES',
             'food competition':'FOOD RUNS LOW','vegetation loss':'THE GREEN VANISHES',
             'water shortage':'WATER RUNS OUT','habitat recovery':'CAN IT RECOVER'}
HISTORY_KEY = 'wildlife/ideas.json'
STRING = {'type': 'string'}
CAMERA_VIEWS = {
    'shore': 'Wide view from the edge of the setting.',
    'aerial': 'Overhead view of the surrounding environment.',
    'pasture': 'Ground-level view across the immediate surroundings.',
}


def obj(**props):
    return {'type': 'object', 'properties': props, 'required': list(props), 'additionalProperties': False}


def enum(values):
    return {'type': 'string', 'enum': list(values)}


IDEA = obj(species=enum(SPECIES), habitat=enum(HABITATS), pressure=enum(PRESSURES),
           title=STRING, opening=STRING, description=STRING,
           tags={'type': 'array', 'items': STRING, 'minItems': 4, 'maxItems': 12},
           thumbnail_text=STRING, arc=STRING)
GENERAL_IDEA = obj(**{key:value for key,value in IDEA['properties'].items()
                     if key not in ('species','habitat','pressure')}, premise=STRING)
SCENE = obj(label=STRING, narration={'type':'string','pattern':WILDLIFE_NARRATION_PATTERN}, visual=STRING, population={'type':'integer','minimum':0,'maximum':9999},
            forage_percent={'type':'integer','enum':list(range(0,101,5))}, camera=enum(('shore','aerial','pasture')),
            action=enum(('walk','graze')))


def ask(prompt, schema, seed, limit):
    from lyrics_cpu import request_story
    result = request_story('chat/completions', {
        'messages': [{'role':'user','content':prompt}],
        'response_format': {'type':'json_schema','json_schema':{'schema':schema}},
        'seed':seed, 'max_completion_tokens':limit, 'wildlife_narration':'scenes' in schema['properties'],
        'validation_attempts': 1 if 'scenes' in schema['properties'] else 3,
    })
    return json.loads(result['choices'][0]['message']['content'])


def packaging(idea):
    subject = idea.get('subject') or idea['species']
    title = emphasize_title(idea['title'],subject,idea.get('pressure'),topic=idea.get('topic'))
    return Packaging(title,subject,idea['opening'],idea['description'],tuple(idea['tags']),topic=idea.get('topic',''),premise=idea.get('premise',''))


def concept(idea):
    if idea.get('domain') and idea['domain'] != 'wildlife':
        return [idea['domain'],idea['topic'],idea['premise']]
    return [idea[key] for key in ('species','habitat','pressure')]


def history_entry(episode, idea):
    return {'episode':episode,'concept':concept(idea),'title':idea['title'],
            'domain':idea.get('domain','wildlife'),'topic':idea.get('topic','')}



def validate_idea(idea):
    from jsonschema import validate
    domain = idea.get('domain','wildlife')
    if domain not in TOPICS:
        raise ValueError('Unknown what-if category')
    validate({key:value for key,value in idea.items()
              if key not in ('thumbnail_prompt','domain','topic','subject')},
             IDEA if domain == 'wildlife' else GENERAL_IDEA)
    if domain != 'wildlife':
        registered = {(topic,subject) for topic,subject,_ in TOPICS[domain]}
        if (idea.get('topic'),idea.get('subject')) not in registered:
            raise ValueError('The episode needs a topic from its what-if category')
        if not 30 <= len(idea['premise']) <= 300:
            raise ValueError('The episode needs a concrete what-if premise')
    packaging(idea).validate()
    if not re.fullmatch(r"[A-Za-z0-9 -]{4,22}", idea['thumbnail_text']):
        raise ValueError('Thumbnail text must be 4–22 plain characters')
    if not 40 <= len(idea['arc']) <= 700:
        raise ValueError('Invalid story arc length')


def unique_scene_labels(previous, batch):
    used = {scene['label'].strip().casefold() for scene in previous}
    normalized = []
    for scene in batch:
        label = base = scene['label'].strip()
        part = 2
        while label.casefold() in used:
            suffix = f' ({part})'
            label = base[:45-len(suffix)].rstrip() + suffix
            part += 1
        used.add(label.casefold())
        normalized.append(dict(scene,label=label))
    return normalized


def repair_scene_copy(scene, index):
    """Keep the story and render controls when display text needs repair."""
    label = re.sub(r'[<>]', '', ' '.join(scene['label'].split()))
    if len(label) > 45:
        label = label[:46].rsplit(' ', 1)[0] if ' ' in label[:46] else label[:45]
        label = label.rstrip(' ,:;-')
    if len(label) < 3:
        label = f'Scene {index}'

    visual = ' '.join(scene['visual'].split())
    if len(visual) > 220:
        visual = visual[:221].rsplit(' ', 1)[0] if ' ' in visual[:221] else ''
    if len(visual) < 24:
        visual = CAMERA_VIEWS[scene['camera']]
    repaired = dict(scene, label=label, visual=visual)
    changed = [field for field in ('label', 'visual') if repaired[field] != scene[field]]
    if changed:
        print(f'Wildlife scene {index}: repaired {", ".join(changed)}', flush=True)
    return repaired


def validate_scenes(scenes):
    for scene in scenes:
        if not 73 <= len(scene['narration'].split()) <= 91:
            raise ValueError('Each narrated scene needs 73–91 words')
        if not 3 <= len(scene['label'].strip()) <= 45:
            raise ValueError('Scene label must be 3–45 characters')
        if not 24 <= len(scene['visual'].strip()) <= 220:
            raise ValueError('Scene background description must be 24–220 characters')
        if scene['forage_percent'] not in range(0,101,5) or not 0 <= scene['population'] <= 9999:
            raise ValueError('Scene counters must be within the supported ranges')


def validate_opening(narration):
    first_words = narration.split()[:34]
    if narration.casefold().startswith(('welcome', 'hello', 'hey everyone', 'in this video',
                                       'today we', 'today, we')):
        raise ValueError('Start with the episode event instead of a greeting or introduction')
    if not any(word.endswith('?') for word in first_words):
        raise ValueError('Ask a specific unanswered question within the first 34 spoken words')


def build(episode, store, *, requested_topic=None):
    key = f'wildlife/{episode}/plan.json'
    history = store.load(HISTORY_KEY, [])
    cached = store.load(key, None)
    if cached is not None:
        decode(cached, episode)
        if not any(row['episode'] == episode for row in history):
            idea = cached['idea']
            store.save(HISTORY_KEY, history + [history_entry(episode,idea)])
        return cached
    seed = int.from_bytes(hashlib.sha256(episode.encode()).digest()[:4],'big') % 2_000_000_000
    recent = [[['goats','grassland island','drought'],'2 Goats, 1 Island: What Happens When the Food Runs Out?']]
    recent += [[row['concept'],row['title']] for row in history]
    occupied = {tuple(row[0]) for row in recent}
    titles = {row[1].casefold() for row in recent}
    domain, topic, subject, starter, reused = select_topic(history,seed)
    if requested_topic:
        domain, topic, subject, starter = next(
            (name, *entry) for name, entries in TOPICS.items()
            for entry in entries if entry[0] == requested_topic)
        reused = any(row.get('topic') == topic for row in history)
    wildlife = domain == 'wildlife'
    schema = IDEA if wildlife else GENERAL_IDEA
    angle = ('Use this as a loose starting point for a materially different hypothetical: ' if reused
             else 'Build the episode around this concrete what-if: ') + starter
    historical_premises = [str(row[0][2]) for row in recent if row[0][0] == domain]
    feedback = ''
    for attempt in range(5):
        idea = ask(
            'Write an original English what-if story for a series about nature and ecosystems. '
            f'{angle} State the specific initiating change in the premise, explore a surprising consequence '
            'that travels through habitats, resources or the food web. Reveal the answer in the final '
            'scenes. Keep the central question ecological and avoid a generic disaster or population boom. '
            'Distinguish the assumed conditions from real facts. Title 35–70 characters, with '
            f'{subject} near the start, one fitting power word from {", ".join(sorted(POWER_WORDS))}, '
            f'and a question ending. Include {subject} in the opening of 40–160 characters and in a tag. '
            'Write one short description paragraph that tees up the main consequence without giving away the answer. '
            'Use 6–10 distinct topic-specific search phrases, including the habitat and ecological mechanism. '
            'Write a 2–4 word thumbnail hook that adds a time, stakes or an unexpected detail from the story '
            'and avoids echoing the title. The hook must fit '
            '22 plain characters. '
            'The arc must fit 600 characters. '
            f'Prior stories to avoid: {json.dumps(recent[-60:])}. {feedback}',
            schema,seed+100*attempt,1500)
        if not re.fullmatch(r'[A-Za-z0-9 -]{4,22}',idea['thumbnail_text']):
            idea['thumbnail_text'] = HEADLINES[idea['pressure']] if wildlife else 'WHAT CHANGES'
        idea.update(domain=domain,topic=topic)
        if not wildlife:
            idea['subject'] = subject
        original_tags = idea['tags']
        idea['tags'] = normalize_generated_tags(original_tags, idea.get('subject') or idea['species'])
        if idea['tags'] != original_tags:
            print(f'Normalized the search tags for {domain}/{topic}', flush=True)
        original_title = idea['title']
        idea['title'] = packaging(idea).title
        if idea['title'] != original_title:
            print(f'Normalized the title for {domain}/{topic}',flush=True)
        try:
            validate_idea(idea)
        except ValueError as error:
            feedback = f'Repair this validation issue: {error}.'
            print('Idea retry:',error,flush=True)
            continue
        if not wildlife:
            tokens = set(re.findall(r'[a-z]+',idea['premise'].lower()))
            if any(len(tokens & other) / max(1,len(tokens | other)) >= .65
                   for other in (set(re.findall(r'[a-z]+',text.lower())) for text in historical_premises)):
                feedback = 'The premise repeats an older story. Change the initiating event and consequence.'
                continue
        if tuple(concept(idea)) not in occupied and idea['title'].casefold() not in titles:
            break
        feedback = 'The premise or title repeated an earlier episode. Change the central consequence.'
    else:
        raise StoryGenerationError(
            'The planner could not produce distinct, valid episode metadata.',
            code='what_if_metadata', details={'domain':domain,'topic':topic,'attempts':5,'last_check':feedback})
    scenes = []
    for _ in range(20):
        scenes.append(generate_scene(idea, scenes, seed, wildlife))
    payload = {'episode':episode, 'idea':idea, 'scenes':scenes}
    decode(payload, episode)
    store.save(key,payload)
    store.save(HISTORY_KEY, history + [history_entry(episode,idea)])
    return payload


def generate_scene(idea, previous, seed, wildlife):
    index = len(previous) + 1
    attempts = 3
    prior = [(scene['label'], scene['population'], scene['forage_percent']) for scene in previous]
    if index == 1:
        direction = (
            'Open scene 1 with the event promised by the title and show its subject. '
            'Within the first 34 spoken words, tease a surprising clue and ask one specific question. '
            'Leave its answer open. Skip greetings, channel intros, invented statistics and calls to subscribe.'
        )
    else:
        opening = ' '.join(previous[0]['narration'].split()[:34])
        direction = f'The opening promise was {json.dumps(opening)}. Continue with a fresh discovery.'
    if index == 11:
        direction += ' In scene 11, reveal an early surprise and ask a question that follows from it.'
    if index == 20:
        direction += ' In scene 20, answer the opening question, explain the cause and return to the opening subject.'
    else:
        direction += ' Build toward the outcome without resolving the opening question.'
    counters = (
        'Use whole-number population from 0 to 9999 and forage_percent in steps of five from 0 to 100.'
        if wildlife else 'Set population to zero and vary forage_percent in steps of five from 0 to 100.'
    )
    schema = obj(scenes={'type': 'array', 'items': SCENE, 'minItems': 1, 'maxItems': 1})
    feedback = ''
    for attempt in range(attempts):
        try:
            result = ask(
                f'Write scene {index} of this twenty-scene English story. Plan: {json.dumps(idea)}. Prior beats: {json.dumps(prior)}. '
                'Aim for 82 spoken words per scene (73–91 allowed), single spaces and ASCII punctuation. '
                'Keep facts separate from hypothetical conditions. Name time jumps early in the narration. '
                'Narration is only words spoken to the viewer. Keep visual directions, field labels, '
                'camera angles, actions and raw simulation counters in their own fields. '
                f'{direction} {counters} Use a specific 3–38 character caption. '
                'Describe a distinct visible background with no text or animals in one sentence of '
                f'24–160 characters. {feedback}',
                schema, seed + 1005 + index * 20 + attempt * 3, 1100)
            scene = repair_scene_copy(result['scenes'][0], index)
            narration = spoken_text(scene['narration'])
            if narration != scene['narration']:
                if len(narration.split()) < 73:
                    raise ValueError('Replace production cues with spoken story sentences and keep 73–91 words')
                print(f'Wildlife scene {index}: removed production cues from narration', flush=True)
                scene['narration'] = narration
            validate_scenes([scene])
            if index == 1:
                validate_opening(scene['narration'])
        except StoryGenerationError as error:
            if not error.retryable:
                raise
            constraint = error.details.get('constraint', error.code)
            field = error.details.get('field', '$')
            feedback = f'Repair the JSON constraint {constraint} at {field}.'
        except ValueError as error:
            feedback = str(error)
        else:
            return unique_scene_labels(previous, [scene])[0]
        print(f'Wildlife scene {index}, attempt {attempt+1}/{attempts}: {feedback}', flush=True)
    raise StoryGenerationError(
        f'Could not generate valid wildlife scene {index}',
        code='what_if_narration', retryable=True,
        details={'scene': index, 'attempts': attempts, 'last_check': feedback})


def decode(payload, episode):
    from jsonschema import validate
    if payload.get('episode') != episode or len(payload.get('scenes',[])) != 20:
        raise ValueError('Episode plan identity or scene count mismatch')
    idea, scenes = payload['idea'], payload['scenes']
    validate_idea(idea)
    for scene in scenes:
        validate(scene,SCENE)
    validate_scenes(scenes)
    names = [field.name for field in fields(Beat)]
    beats = tuple(Beat(**{key:scene[key] for key in names if key not in ('forage','narration')},
                       narration=spoken_text(scene['narration']), forage=scene['forage_percent']/100)
                  for scene in scenes)
    if any(not beat.narration for beat in beats):
        raise ValueError('A saved scene has no spoken narration after removing production cues')
    return packaging(idea), beats


def load(path, episode):
    payload = json.loads(Path(path).read_text())
    return payload, *decode(payload, episode)


if __name__ == '__main__':
    from storage import Store
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--episode',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    manifest = build(args.episode,Store())
    args.output.write_text(json.dumps(manifest,indent=2)+'\n')
