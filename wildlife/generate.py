"""Generate and checkpoint a distinct wildlife episode with the existing Qwen CPU runtime."""
import argparse
import hashlib
import json
from dataclasses import fields
from pathlib import Path
import re

from lyrics_cpu import WILDLIFE_NARRATION_PATTERN

from .episodes import Beat
from .metadata import Packaging


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
SCENE = obj(label=STRING, narration={'type':'string','pattern':WILDLIFE_NARRATION_PATTERN}, visual=STRING, population={'type':'integer','minimum':0,'maximum':9999},
            forage_percent={'type':'integer','enum':list(range(0,101,5))}, camera=enum(('shore','aerial','pasture')),
            action=enum(('walk','graze')))


def ask(prompt, schema, seed, limit):
    from lyrics_cpu import request_story
    result = request_story('chat/completions', {
        'messages': [{'role':'user','content':prompt}],
        'response_format': {'type':'json_schema','json_schema':{'schema':schema}},
        'seed':seed, 'max_completion_tokens':limit, 'wildlife_narration':schema is not IDEA,
    })
    return json.loads(result['choices'][0]['message']['content'])


def packaging(idea):
    return Packaging(idea['title'], idea['species'], idea['opening'], idea['description'], tuple(idea['tags']))


def concept(idea):
    return [idea[key] for key in ('species','habitat','pressure')]


def validate_idea(idea):
    from jsonschema import validate
    validate({key:value for key,value in idea.items() if key != 'thumbnail_prompt'}, IDEA)
    packaging(idea).validate()
    if not re.fullmatch(r"[A-Za-z0-9 -]{4,22}", idea['thumbnail_text']):
        raise ValueError('Thumbnail text must be 4–22 plain characters')
    if not 40 <= len(idea['arc']) <= 700:
        raise ValueError('Invalid story arc length')


def validate_scenes(scenes):
    for field in ('label','visual'):
        if len({s[field].casefold().strip() for s in scenes}) != len(scenes):
            raise ValueError(f'Scene {field} must be distinct')
    for scene in scenes:
        if not 73 <= len(scene['narration'].split()) <= 91:
            raise ValueError('Each narrated scene needs 73–91 words')
        if not 3 <= len(scene['label'].strip()) <= 45 or not 24 <= len(scene['visual'].strip()) <= 220:
            raise ValueError('Missing concise scene label or background description')
        if scene['forage_percent'] not in range(0,101,5) or not 0 <= scene['population'] <= 9999:
            raise ValueError('Scene counters must be within the supported ranges')


def build(episode, store):
    key = f'wildlife/{episode}/plan.json'
    history = store.load(HISTORY_KEY, [])
    cached = store.load(key, None)
    if cached is not None:
        decode(cached, episode)
        if not any(row['episode'] == episode for row in history):
            idea = cached['idea']
            store.save(HISTORY_KEY, history + [{'episode':episode,'concept':concept(idea),'title':idea['title']}])
        return cached
    seed = int.from_bytes(hashlib.sha256(episode.encode()).digest()[:4],'big') % 2_000_000_000
    recent = [[['goats','grassland island','drought'],'2 Goats, 1 Island: What Happens When the Food Runs Out?']]
    recent += [[row['concept'],row['title']] for row in history]
    occupied = {tuple(row[0]) for row in recent}
    titles = {row[1].casefold() for row in recent}
    feedback = ''
    for attempt in range(5):
        idea = ask(
            'Invent one original English wildlife what-if for a hypothetical computer simulation. '
            'Use only the species, habitats and pressures allowed by the schema. Species is plural. '
            'Explore a mechanism beyond simple population growth. Pick a species, habitat and pressure '
            'combination not in the used list. Title 35–70 characters; start with the species, end in a '
            'curiosity-driven question, and make an accurate promise for the story. Opening 40–160 characters '
            'and naturally include the species. Write one short description paragraph, 6–10 distinct searchable '
            'tags including the species, and a 2–4 word thumbnail hook within 22 characters. '
            'The arc must be hypothetical and explain defensible '
            'ecological mechanisms. Avoid implying that repeated browsing makes saplings grow faster '
            'or claiming unsupported benefits from a habitat loss. Keep the arc under 600 characters. '
            f'Used topics: {json.dumps(recent[-60:])}. {feedback}',
            IDEA, seed+100*attempt, 1500)
        if not re.fullmatch(r'[A-Za-z0-9 -]{4,22}',idea['thumbnail_text']):
            idea['thumbnail_text'] = HEADLINES[idea['pressure']]
        try:
            validate_idea(idea)
        except ValueError as error:
            feedback = f'Repair this validation issue: {error}.'
            print('Idea retry:',error,flush=True)
            continue
        if tuple(concept(idea)) not in occupied and idea['title'].casefold() not in titles:
            break
        feedback = 'The combination or title repeated a previous episode. Choose a different species and pressure.'
    else:
        raise RuntimeError('No distinct, validated wildlife idea was generated')
    scenes = []
    schema = obj(scenes={'type':'array','items':SCENE,'minItems':4,'maxItems':4})
    for start in range(0,20,4):
        prior = [(s['label'],s['population'],s['forage_percent']) for s in scenes]
        feedback = ''
        for attempt in range(4):
            result = ask(
                f"Write exactly scenes {start+1} to {start+4} of this twenty-scene English wildlife "
                f"thought experiment. Plan: {json.dumps(idea)}. Prior beats: {json.dumps(prior)}. "
                "Exactly four distinct and chronological scenes. Aim for 82 words of narration per scene "
                "(allowed range 73–91) with single spaces and ASCII punctuation. Write a continuous story, with a concrete hook early and a resolution "
                "in scene 20. No citations or numerical claims about real studies. Give the fictional population as a "
                "whole number from 0 to 9999 and forage_percent as a multiple of five from 0 to 100. Keep each caption label under 38 characters. Each visual "
                "describes a different visible environment for its narration, text-free with no animals, within "
                f"180 characters. {feedback}",
                schema, seed+1000+start*20+attempt*3, 3500)
            try:
                validate_scenes(scenes+result['scenes'])
            except ValueError as error:
                counts = [len(s['narration'].split()) for s in result['scenes']]
                feedback = f'Rewrite all four scenes. {error}. Previous word counts were {counts}.'
                print(f'Scene batch {start+1} retry:',error,counts,flush=True)
                continue
            scenes.extend(result['scenes'])
            break
        else:
            raise RuntimeError(f'Could not validate the narration for scene batch {start+1}')
    payload = {'episode':episode, 'idea':idea, 'scenes':scenes}
    decode(payload, episode)
    store.save(key,payload)
    store.save(HISTORY_KEY, history + [{'episode':episode,'concept':concept(idea),'title':idea['title']}])
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
