"""Generate and checkpoint a distinct wildlife episode with the existing Qwen CPU runtime."""
import argparse
import hashlib
import json
from dataclasses import fields
from pathlib import Path
import re

from lyrics_cpu import StoryGenerationError, WILDLIFE_NARRATION_PATTERN

from .episodes import Beat
from .metadata import POWER_WORDS, Packaging, emphasize_title
from .whatif import TOPICS, select_topic


SPECIES = {'goats': 'goat', 'deer': 'deer', 'rabbits': 'rabbit'}
HABITATS = ('wooded island', 'grassland island', 'coastal dunes', 'rocky island', 'marsh island')
PRESSURES = ('drought', 'winter', 'food competition', 'vegetation loss', 'water shortage', 'habitat recovery')
HEADLINES = {'drought':'WHEN RAIN STOPS','winter':'WINTER ARRIVES',
             'food competition':'FOOD RUNS LOW','vegetation loss':'THE GREEN VANISHES',
             'water shortage':'WATER RUNS OUT','habitat recovery':'CAN IT RECOVER'}
HISTORY_KEY = 'wildlife/ideas.json'
STRING = {'type': 'string'}


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


def validate_scenes(scenes):
    for scene in scenes:
        if not 73 <= len(scene['narration'].split()) <= 91:
            raise ValueError('Each narrated scene needs 73–91 words')
        if not 3 <= len(scene['label'].strip()) <= 45 or not 24 <= len(scene['visual'].strip()) <= 220:
            raise ValueError('Missing concise scene label or background description')
        if scene['forage_percent'] not in range(0,101,5) or not 0 <= scene['population'] <= 9999:
            raise ValueError('Scene counters must be within the supported ranges')


def validate_opening(narration):
    first_words = narration.split()[:34]
    if narration.casefold().startswith(('welcome', 'hello', 'hey everyone', 'in this video',
                                       'today we', 'today, we')):
        raise ValueError('Start with the episode event instead of a greeting or introduction')
    if not any(word.endswith('?') for word in first_words):
        raise ValueError('Ask a specific unanswered question within the first 34 spoken words')


def build(episode, store):
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
    schema = obj(scenes={'type':'array','items':SCENE,'minItems':4,'maxItems':4})
    for start in range(0,20,4):
        prior = [(s['label'],s['population'],s['forage_percent']) for s in scenes]
        if start == 0:
            direction = (
                'Open scene 1 with a short, concrete line (about 12 words) that immediately delivers '
                'the event promised by the title and shows the subject in the opening shot. Within '
                'the first 34 spoken words, tease a surprising clue and ask one specific question '
                'about its consequence. Leave its answer open. No greeting, channel intro, generic '
                'teaser, invented statistics or call to subscribe. Let scene 2 build on that clue. '
            )
        else:
            opening = ' '.join(scenes[0]['narration'].split()[:34])
            direction = (
                f'The opening promise was: {json.dumps(opening)}. '
                'Build toward its answer with a fresh discovery or consequence in each scene. '
                'If this batch includes scene 20, answer the opening question with the outcome '
                'and explain which change caused it. In earlier scenes give clues without resolving it. '
            )
        feedback = ''
        for attempt in range(4):
            result = ask(
                f"Write exactly scenes {start+1} to {start+4} of this twenty-scene English what-if "
                f"thought experiment. Plan: {json.dumps(idea)}. Prior beats: {json.dumps(prior)}. "
                "Exactly four distinct and chronological scenes. Aim for 82 words of narration per scene "
                "(allowed range 73–91) with single spaces and ASCII punctuation. Write a continuous story. "
                "Keep real facts separate from the hypothetical conditions. " + direction
                + ("Give the fictional population as a whole number from 0 to 9999 and "
                   "forage_percent as a multiple of five from 0 to 100. " if wildlife else
                   "Set population to zero. Set forage_percent from 0 to 100 in steps of five "
                   "to guide the animation intensity for the scenario, with meaningful changes across scenes. ")
                + "Keep each caption label specific to its scene and under 38 characters. Each visual "
                "describes a different visible environment for its narration, text-free with no animals, within "
                f"180 characters. {feedback}",
                schema, seed+1000+start*20+attempt*3, 3500)
            try:
                validate_scenes(result['scenes'])
                if start == 0:
                    validate_opening(result['scenes'][0]['narration'])
            except ValueError as error:
                counts = [len(s['narration'].split()) for s in result['scenes']]
                feedback = f'Rewrite all four scenes. {error}. Previous word counts were {counts}.'
                print(f'Scene batch {start+1} retry:',error,counts,flush=True)
                continue
            scenes.extend(unique_scene_labels(scenes,result['scenes']))
            break
        else:
            raise StoryGenerationError(
                f'Could not validate the narration for scene batch {start+1}',
                code='what_if_narration', details={'first_scene':start+1,'attempts':4,'last_check':feedback})
    payload = {'episode':episode, 'idea':idea, 'scenes':scenes}
    decode(payload, episode)
    store.save(key,payload)
    store.save(HISTORY_KEY, history + [history_entry(episode,idea)])
    return payload


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
    beats = tuple(Beat(**{key:scene[key] for key in names if key != 'forage'},
                       forage=scene['forage_percent']/100) for scene in scenes)
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
