"""Generate a distinct lyric scene for each five-second slot, with resumable cache."""
import hashlib
import json
import os
import random
from pathlib import Path
from PIL import Image
from image_cpu import MODEL, REVISION

THUMBNAIL_REFERENCE = Path(__file__).resolve().parent/'assets/thumbnail/kids-dance-reference.png'

def thumbnail_reference():
    path=Path(os.getenv('THUMBNAIL_REFERENCE_IMAGE',str(THUMBNAIL_REFERENCE)))
    strength=float(os.getenv('THUMBNAIL_DENOISE_STRENGTH','0.50'))
    if not 0 < strength <= 1:
        raise ValueError('Thumbnail denoise strength must be greater than zero and at most one')
    with Image.open(path) as image:
        image.verify()
    return dict(reference_image=str(path.relative_to(Path(__file__).resolve().parent))
                if path.is_relative_to(Path(__file__).resolve().parent) else str(path),
                reference_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),strength=strength)


def thumbnail_cast(identity):
    """Repeatable choices per episode, independent of the scene image seeds."""
    rng=random.Random(int(hashlib.sha256((identity+'thumbnail-cast-v2').encode()).hexdigest(),16))
    animals=rng.sample(['puppies','kittens','bunnies','ducklings','lambs','pandas',
                        'baby elephants','baby turtles','baby deer','chicks'],2)
    colors=rng.sample(['coral','teal','orange','pink','white','black','cyan','magenta'],5)
    faces=rng.sample(['curly black hair, brown eyes','straight auburn hair, green eyes',
                      'wavy brown hair, blue eyes','short blond hair, hazel eyes',
                      'black pigtails, dark eyes','brown bob, freckles'],5)
    genders=['girl','boy','girl','boy',rng.choice(['girl','boy'])]
    rng.shuffle(genders)
    return dict(animals=animals,children=[dict(gender=g,color=c,face=f)
                for g,c,f in zip(genders,colors,faces)])


def thumbnail_prompt(cast):
    species={'puppies':'brown puppy','kittens':'gray kitten','bunnies':'white bunny',
             'ducklings':'white duckling','lambs':'white lamb','pandas':'black and white panda',
             'baby elephants':'gray elephant calf','baby turtles':'green turtle',
             'baby deer':'brown fawn','chicks':'yellow chick'}
    animals=' and '.join(species[a] for a in cast['animals'])
    colors=', '.join(c['color'] for c in cast['children'])
    return ('Cute 3D storybook. Five smiling toddlers: girls with black pigtails, boys with brown curls. '
            'Left to right '+colors+' shorts. A '+animals+' in front. '
            'Different faces, dancing, colorful party lights.')


def thumbnail_negative(cast):
    exclusions=('blue shorts, red shorts, green shorts, purple shorts, yellow shorts, '
                'blond hair, identical faces, cloned children, matching clothes, all boys, all girls')
    if not any(a in ('chicks','ducklings') for a in cast['animals']):
        exclusions='chicks, chickens, ducks, yellow animals, birds, '+exclusions
    return exclusions


def image_plan(song):
    from kids_rhymes import validate_storyboard
    validate_storyboard(song)
    identity = hashlib.sha256(json.dumps(song, sort_keys=True).encode()).hexdigest()
    portrait = os.getenv('IMAGE_VARIANT') == 'portrait'
    scenes = song['scenes']
    if portrait:
        from shorts import validate_clip
        start, seconds = int(os.getenv('CLIP_START', '0')), int(os.getenv('CLIP_SECONDS', '40'))
        validate_clip(start, seconds)
        if start + seconds > song['duration']:
            raise ValueError('Portrait clip exceeds song duration')
        scenes = scenes[start//5:(start+seconds)//5]
        identity += '-portrait-v2'
    entries = [(f"scene-{s['index']:03d}", s['prompt']) for s in scenes]
    if portrait:
        entries = [(kind, 'Portrait 9:16 composition, full-height storybook scene. ' +
                    prompt.replace('wide landscape', 'vertical composition') +
                    ' Keep characters and lyric props visible, no borders or panels.')
                   for kind, prompt in entries]
    else:
        cast=thumbnail_cast(identity)
        entries.append(('thumbnail',thumbnail_prompt(cast)))
    plans = [dict(kind=kind, prompt=prompt, seed=int(hashlib.sha256((identity+kind).encode()).hexdigest()[:8],16),
        model=MODEL, revision=REVISION, width=int(os.getenv('CPU_IMAGE_WIDTH','576' if portrait else '1024')),
        height=int(os.getenv('CPU_IMAGE_HEIGHT','1024' if portrait else '576')), steps=int(os.getenv('CPU_IMAGE_STEPS','16')),
        visual_style='dudi-storybook-v2', allow_text=False) for kind,prompt in entries]
    if not portrait:
        plans[-1].update(thumbnail_reference(),visual_style='dudi-reference-storybook-v4-directed',thumbnail_cast=cast,extra_negative_prompt=thumbnail_negative(cast))
    return plans


def generate_song_images(root, song):
    from image_cpu import generate
    root = Path(root)
    if os.getenv('IMAGE_VARIANT') == 'portrait':
        root = root/'portrait'
    root.mkdir(parents=True, exist_ok=True)
    shard, count = int(os.getenv('IMAGE_SHARD','0')), int(os.getenv('IMAGE_SHARDS','1'))
    if not 0 <= shard < count:
        raise ValueError('Invalid image shard')
    manifest = root/f'image-manifest-{shard:02d}.json'
    previous = json.loads(manifest.read_text()) if manifest.exists() else {}
    completed = {}
    for i, plan in enumerate(image_plan(song)):
        if i % count != shard:
            continue
        kind = plan['kind']
        target = root/f'{kind}-source.png'
        valid = False
        if previous.get(kind) == plan and target.exists():
            try:
                with Image.open(target) as im:
                    im.verify()
                valid = True
            except (OSError,ValueError):
                pass
        if not valid:
            temporary = target.with_suffix('.tmp.png')
            reference_options={}
            if plan.get('reference_image'):
                reference=Path(plan['reference_image'])
                if not reference.is_absolute():
                    reference=Path(__file__).resolve().parent/reference
                reference_options=dict(reference_image=reference,strength=plan['strength'],
                                       extra_negative_prompt=plan.get('extra_negative_prompt',''))
            generate(plan['prompt'], temporary, seed=plan['seed'], allow_text=False,
                     width=plan['width'], height=plan['height'], steps=plan['steps'],**reference_options)
            with Image.open(temporary) as im:
                im.verify()
            temporary.replace(target)
        completed[kind] = plan
        temp = manifest.with_suffix('.tmp')
        temp.write_text(json.dumps(completed,indent=2))
        temp.replace(manifest)
    return completed
