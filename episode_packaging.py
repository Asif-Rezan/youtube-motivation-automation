"""Original story-grounded public metadata from the existing local Qwen model."""
import hashlib
import json
from jsonschema import Draft202012Validator, ValidationError

VERSION = 'episode-seo-packaging-v1'


def metadata_schema():
    return {'type':'object','additionalProperties':False,'required':['title','description','tags'],
        'properties':{'title':{'type':'string','minLength':10,'maxLength':100},
                      'description':{'type':'string','minLength':80,'maxLength':1800},
                      'tags':{'type':'array','minItems':5,'maxItems':15,'uniqueItems':True,
                              'items':{'type':'string','minLength':2,'maxLength':40}}}}


def candidate_scenes(song):
    count=len(song['scenes'])
    indexes=set(range(min(8,count)))
    if count>8:
        indexes.update(8+i*(count-9)//15 for i in range(16))
    return [song['scenes'][i] for i in sorted(indexes)]


def schema(song):
    return {'type':'object','additionalProperties':False,
        'required':['title_candidates','video','shorts','thumbnail'],
        'properties':{
            'title_candidates':{'type':'array','minItems':3,'maxItems':3,'uniqueItems':True,
                                'items':{'type':'string','minLength':10,'maxLength':100}},
            'video':metadata_schema(),'shorts':metadata_schema(),
            'thumbnail':{'type':'object','additionalProperties':False,'required':['scene_index','focus'],
                         'properties':{'scene_index':{'type':'integer','enum':[s['index'] for s in candidate_scenes(song)]},
                                       'focus':{'type':'string','minLength':15,'maxLength':180}}}}}


def source_identity(song):
    return hashlib.sha256(json.dumps({k:song.get(k) for k in
        ('title','description','lyrics','story_summary','visual_identity','scenes','duration')},
        sort_keys=True).encode()).hexdigest()


def validate_package(package, song):
    content={k:package[k] for k in ('title_candidates','video','shorts','thumbnail')}
    Draft202012Validator(schema(song)).validate(content)
    if package.get('version') != VERSION or package.get('source_sha256') != source_identity(song):
        raise ValueError('Episode packaging source/version mismatch')
    if content['video']['title'] not in content['title_candidates']:
        raise ValueError('Selected title must be one of the episode candidates')
    for kind in ('video','shorts'):
        tags=content[kind]['tags']
        if len({tag.strip().casefold() for tag in tags})!=len(tags) or sum(len(t)+2 for t in tags)>450:
            raise ValueError('Episode tags must be unique and fit the upload budget')
    return package


TAG_BUDGET = 450


def repair_package(package, recent=()):
    """Fix deterministic slips locally instead of re-asking the model.

    Only reorders or drops model-written values; never invents public text.
    """
    for kind in ('video','shorts'):
        meta=package.get(kind)
        if not isinstance(meta,dict) or not isinstance(meta.get('tags'),list):
            continue
        seen,tags,used=set(),[],0
        for tag in meta['tags']:
            if not isinstance(tag,str):
                continue
            tag=' '.join(tag.split())
            key=tag.casefold()
            if not tag or key in seen or used+len(tag)+2>TAG_BUDGET:
                continue
            seen.add(key);tags.append(tag);used+=len(tag)+2
        meta['tags']=tags
    candidates=package.get('title_candidates')
    video=package.get('video')
    if isinstance(candidates,list) and isinstance(video,dict):
        title=video.get('title')
        if title not in candidates or title in recent:
            fresh=[c for c in candidates if isinstance(c,str) and c not in recent]
            if fresh:
                video['title']=fresh[0]
    return package


def packaging_issue(error):
    """Safe diagnostic: locally authored messages, or schema location only."""
    if isinstance(error,ValidationError):
        return {'constraint':error.validator,'path':[str(p) for p in error.absolute_path]}
    if isinstance(error,KeyError):
        return {'constraint':'missing_field'}
    return {'constraint':'semantic','reason':str(error)}


def generate_package(song, history=(), seed_offset=0):
    from rhyme_writer import request_json
    from lyrics_cpu import StoryGenerationError
    identity=source_identity(song)
    facts={k:song.get(k) for k in ('title','description','story_summary','visual_identity','duration')}
    facts['verse_lyrics']=[s['lyric'] for s in song['scenes'] if s['lyric'] != 'dudi dudi dam dam dudi dudi dam']
    facts['refrain']='dudi dudi dam dam dudi dudi dam'
    facts['scenes']=[dict(index=s['index'],lyric=s['lyric'],action=s.get('visual_action',s['prompt'])[:180]) for s in candidate_scenes(song)]
    prompt=(
        'Create an original truthful YouTube title/thumbnail package for this English kids nursery rhyme. '
        'Use only the supplied lyrics, cast, setting and actions. No invented animals, lessons, events, '
        'educational guarantees, views, popularity, trend/search-volume claims or celebrity/cartoon brands. '
        'The sung Dudi refrain is intentional. Public metadata must differ between episodes. '
        'Write three distinct concise title candidates, ideally 45-75 characters. Front-load the actual '
        'story action or animal keyword, and naturally include a relevant search phrase such as Kids Dance Song '
        'or Nursery Rhyme. Avoid stuffing all keywords, ALL CAPS or clickbait. Choose the strongest honest '
        'title-thumbnail pair for video.title, exactly one of title_candidates. '
        'Write a unique video description: first two sentences describe the actual episode and its viewer '
        'payoff, then a short natural summary of real actions; mention the Dudi refrain and AI-made music '
        'and illustrations. No unrelated song names, fabricated timestamps, subscription requests or spam. '
        'Generate 5-15 distinct relevant tags, mixing actual story/animal terms and broad kids rhyme terms; '
        'each at most 40 characters, combined under 450 characters. Tags are secondary discovery metadata. '
        'For shorts, write a separate title, description and tags based ONLY on scenes 0-7 (first 40 seconds), '
        'not later events. A short may use #Shorts once. '
        'For thumbnail, choose one actual scene_index with a clear appealing baby-and-animal interaction. '
        'Write a compact focus describing the existing characters/emotion and real prop/action to emphasize; '
        'do not introduce a new cast, outfit, environment or disconnected disco-party scene. '
        'Aim for readable large faces, clear silhouettes, one focal interaction, color contrast and simple '
        'composition at mobile size. Keep the same soft cute 3D storybook style and dreamy natural scene, '
        'no text, logos or split panels. Do not claim a numerical CTR score. '
        'Avoid these recent public titles: '+json.dumps([h.get('public_title',h.get('title','')) for h in history[-20:]])+
        '\nActual episode: '+json.dumps(facts,ensure_ascii=False))
    recent={h.get('public_title',h.get('title','')) for h in history}
    # Stage-level retries pass a new offset so they don't replay identical seeds.
    base=(int(identity[:8],16)+seed_offset*104729) % (2**31-10000)
    for attempt in range(3):
        result=request_json(schema(song),prompt,base+attempt,budget=2800)
        result.update(version=VERSION,source_sha256=identity)
        try:
            repair_package(result,recent)
            validate_package(result,song)
            if result['video']['title'] in recent:
                raise ValueError('Public title repeats an earlier episode')
            return result
        except (ValueError,KeyError,ValidationError) as error:
            print(json.dumps({'check':'episode packaging retry','attempt':attempt+1,
                **packaging_issue(error)}),flush=True)
            prompt += '\nRepair the package: '+str(error)
    raise StoryGenerationError('Episode packaging validation exhausted; saved lyrics retained',
                               code='episode_packaging',retryable=True)


def public_metadata(song, kind='video'):
    """New episodes use their saved package; old unpublished artifacts use their story."""
    if kind not in ('video','shorts'):
        raise ValueError('Unknown upload format')
    if song.get('public_metadata_version') == VERSION:
        return {key:song[key] for key in ('title','description','tags')}
    package=song.get('packaging')
    if package:
        validate_package(package,song)
        return dict(package[kind],tags=list(package[kind]['tags']))
    # Recovery compatibility: never revert an old prepared song to shared fixed text.
    from kids_rhymes import metadata_tags, upload_description
    return dict(title=song['title'],description=upload_description(song),tags=metadata_tags(song))
