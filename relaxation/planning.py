"""Fresh Qwen relaxation concepts, coherent art direction and persisted diversity."""
import json,re,copy
from difflib import SequenceMatcher
from pathlib import Path
from jsonschema import validate as check,ValidationError
from .art_style import STYLE_ID,ART_DIRECTION

def obj(**fields):return dict(type='object',properties=fields,required=list(fields),additionalProperties=False)
def text(n):return dict(type='string',minLength=1,maxLength=n)
SCHEMA=obj(idea=text(300),concept_id=text(90),title=text(95),description=text(1600),
 tags=dict(type='array',minItems=8,maxItems=15,items=text(45)),environment=text(150),lighting=text(100),palette=text(100),
 music_prompt=text(500),rain_prompt=text(400),thumbnail=obj(headline=text(28),scene_index=dict(type='integer',minimum=0,maximum=5)),
 scenes=dict(type='array',minItems=6,maxItems=6,items=obj(chapter=text(50),view=text(250),
 camera=dict(type='string',enum=['pan_left','pan_right','zoom_in','zoom_out']),
 water_region=dict(type='string',enum=['none','lower_left','lower_center','lower_right']))))
INITIAL_HISTORY=[dict(title='Rain Garden — Gentle Piano & Soft Rain',idea='Tropical rainforest garden, lotus pond and bamboo with gentle piano and rain',concept_id='tropical-rain-garden',environment='tropical rainforest garden')]
def normalize(s):return ' '.join(re.findall(r'[a-z0-9]+',s.lower()))
def schema_for(seconds=60,image_count=6):
 schema=copy.deepcopy(SCHEMA)
 schema['properties']['scenes'].update(minItems=image_count,maxItems=image_count)
 schema['properties']['thumbnail']['properties']['scene_index']['maximum']=image_count-1
 if seconds>60:
  count=(seconds+899)//900
  schema['properties']['chapter_titles']=dict(type='array',items=text(50),minItems=count,maxItems=count)
  schema['required'].append('chapter_titles')
 return schema

def validate(data,history,seconds=60,image_count=6):
 check(data,schema_for(seconds,image_count))
 duration_pattern=r'(?:1[ -]minute|one[ -]minute|60[ -]seconds?)' if seconds==60 else r'(?:3[ -]hours?|three[ -]hours?|180[ -]minutes?)'
 if not re.search(duration_pattern,data['title'],re.I):raise ValueError('Title must accurately state the video length')
 if len(','.join(data['tags']))>450:raise ValueError('SEO tags exceed 450 characters')
 if len({normalize(t) for t in data['tags']})!=len(data['tags']):raise ValueError('Repeated SEO tags')
 if len({normalize(s['view']) for s in data['scenes']})!=image_count:raise ValueError('Distinct camera views are required for the image pool')
 for old in history:
  if normalize(old['concept_id'])==normalize(data['concept_id']):raise ValueError('Repeated episode concept')
  if SequenceMatcher(None,normalize(old['title']),normalize(data['title'])).ratio()>.85:raise ValueError('Title too close to a previous episode')
  if SequenceMatcher(None,normalize(old['idea']),normalize(data['idea'])).ratio()>.85:raise ValueError('Idea too close to a previous episode')
 return data

def generate(out,run,seed_fn,seconds=60,image_count=6):
 from storage import Store
 from lyrics_cpu import request_story,MODEL_ID
 store=Store();key='relaxation/ideas.json';history=store.load(key,INITIAL_HISTORY)
 checkpoint=f'relaxation/{"previews" if seconds==60 else "production-drafts"}/{run}/plan.json';saved=store.load(checkpoint,None)
 if saved:
  if saved.get('run_id')!=run or saved.get('publish') is not False:raise ValueError('Saved plan identity mismatch')
  out.mkdir(parents=True,exist_ok=True);(out/'plan.json').write_text(json.dumps(saved,indent=2));(out/'metadata.json').write_text(json.dumps(saved['youtube'],indent=2));return saved
 prompt=('Create ONE original one-minute relaxation music preview, adults/general audience. '
  'Niche stays calming piano music and nature rain ambience. Fresh idea, title, description, search-specific tags, setting, lighting, palette, six scene views and thumbnail headline. '
  'All six views MUST belong to ONE coherent physical environment, weather and lighting, like six views of the same peaceful place. '
  'Choose a NEW environment/concept unlike the history; alternatives include a misty highland lake, quiet coastal pine garden, Japanese maple courtyard, rainy cabin landscape or fern-lined mountain stream. '
  'All scenes outdoors with gentle rain; no people, no indoor shelter/windows. No unrelated travel montage. '
  'Keep MUSIC STYLE gentle sparse felt piano and warm pads, slow tempo, no drums, no vocals, no speech, no sudden loud notes. This successful piano style is required, but compose a new melody. '
  'The rain prompt must describe only soft steady rain on leaves or water, no music, voices or thunder. '
  'For every view, water_region specifies a conservative LOWER image region containing calm pond/lake water suitable for tiny ripples; use none for dry ground, rocks, strong waterfalls or flowing creeks. '
  'Use varied slow camera movements. Six scenes of ten seconds each. Title must accurately say 1 Minute or 60 Seconds, with one uppercase mood power word such as CALM, PEACEFUL or SOOTHING; no cure, treatment, guaranteed sleep, frequency claims or fabricated research. '
  'Description is original prose; timestamps will be added. Tags are 8-15 unique relevant search phrases under 450 total characters. '
  'Thumbnail headline is 2-5 concise words, coherent with title, not sensational medical claims. concept_id is a meaningful unique slug. '
  'Creative seed '+str(seed_fn(run,500))+'. Avoid recent episode concepts and similar titles: '+json.dumps(history[-30:]))
 if seconds>60:
  prompt=('Create a fresh THREE-HOUR relaxation piano and nature-rain video package, not a one-minute preview. '
   'Stay in the calming piano and nature ambience niche. Choose ONE coherent outdoor setting, lighting, gentle rainy weather and colour palette, different from recent history. '
   'Write an original 3 Hours or 180 Minutes title, original description, 8-15 unique relevant SEO tags under 450 combined characters, meaningful concept_id, environment, lighting, palette, '
   'gentle sparse felt piano/warm pads music_prompt, steady gentle rain_prompt, thumbnail brief, TWENTY distinct reusable scene views, and TWELVE chapter_titles. '
   'Chapters start every 15 minutes. They describe visual/mood progression within this same setting; do not claim ocean/waterfall/birds audio unless it is actually present. '
   '20 AI images are reused over 1080 ten-second slots, with varied slow pan/zoom. Use camera enum and conservative water_region (none for dry ground, rocks, or flowing creeks). '
   'Do not write 1080 image prompts. All twenty views are the SAME location, weather and lighting, no people, no indoor scenes. '
   'No medical claims, guaranteed sleep, miracle frequencies, voices, thunder, loud sounds or drums. Keep a new gentle piano melody front and quiet steady rain below. '
   'Use one uppercase mood word in the title, e.g. CALM. Chapters and all packaging must describe this actual piano/rain content, not an unrelated montage. '
   'Thumbnail scene_index is 0-19. Chapter timestamps are added automatically. Creative seed '+str(seed_fn(run,500))+
   '. Avoid these recent concepts and close titles: '+json.dumps(history[-30:]))
 if seconds>60 and image_count>20:
  prompt=prompt.replace('TWENTY distinct reusable scene views','the first TWENTY distinct anchor scene views of a 100-image pool').replace('20 AI images are reused','100 AI images will be reused')
 prompt+=' Visual art direction: '+ART_DIRECTION+' Plan bright, vivid but relaxing lighting and palette; keep one consistent storybook look across all views.'
 planning_count=min(image_count,20) if seconds>60 else image_count
 schema=schema_for(seconds,planning_count)
 errors=[]
 for attempt in range(3):
  response=request_story('chat/completions',dict(messages=[dict(role='user',content=prompt+' Corrections: '+'; '.join(errors))],response_format=dict(type='json_schema',json_schema=dict(schema=schema)),seed=seed_fn(run,500+attempt),max_completion_tokens=2500 if seconds==60 else 6000,validation_attempts=2))
  data=json.loads(response['choices'][0]['message']['content'])
  data['tags']=list(dict.fromkeys(' '.join(t.lower().split()) for t in data['tags']))
  try:validate(data,history,seconds,planning_count);break
  except (ValueError,ValidationError) as e:errors.append(str(e)[:300])
 else:raise ValueError('AI relaxation package failed validation after three attempts')
 if image_count>len(data['scenes']):
  # Expand in bounded batches instead of asking for 100 views in one response.
  batch_schema=obj(scenes=SCHEMA['properties']['scenes'])
  batch_schema['properties']['scenes']=copy.deepcopy(SCHEMA['properties']['scenes'])
  batch_schema['properties']['scenes'].update(minItems=20,maxItems=20)
  while len(data['scenes'])<image_count:
   previous={normalize(s['view']) for s in data['scenes']}
   extra_prompt=('Create 20 additional DISTINCT scene views for this same relaxation location: '+data['environment']+
    '. Same lighting: '+data['lighting']+'. Same palette: '+data['palette']+
    '. Visual style: '+ART_DIRECTION+'. Gentle rain. No people or indoor scenes. Each view needs chapter (short shot label), view (under 250 characters), camera and water_region. '
    'Use none water_region when no still pond/lake water is visible. Avoid existing compositions: '+json.dumps([s['view'] for s in data['scenes']]))
   for attempt in range(3):
    response=request_story('chat/completions',dict(messages=[dict(role='user',content=extra_prompt)],response_format=dict(type='json_schema',json_schema=dict(schema=batch_schema)),seed=seed_fn(run,len(data['scenes'])+attempt+1500),max_completion_tokens=3000,validation_attempts=2))
    extra=json.loads(response['choices'][0]['message']['content']);check(extra,batch_schema)
    views=[normalize(s['view']) for s in extra['scenes']]
    if len(set(views))==20 and not set(views)&previous:break
   else:raise ValueError('AI additional view batch repeated existing compositions')
   data['scenes'].extend(extra['scenes'])
  if len(data['scenes'])!=image_count:raise ValueError('Incorrect expanded image budget')
  # The package thumbnail may still select any of the first twenty anchor views.
 data.update(run_id=run,seconds=seconds,fps=24,resolution=[1280,720],publish=False,
  models=dict(planning=MODEL_ID,images='segmind/SSD-1B',music='ACE-Step/Ace-Step1.5',nature='cvssp/audioldm-s-full-v2',depth='depth-anything/Depth-Anything-V2-Small-hf'),
  nature_license='CC-BY-NC-SA-4.0: noncommercial evaluation only; do not publish or monetize this preview',
  audio_design='Original AI piano plus three distinct AI rain takes with quality-screened segments and long overlaps',image_source_size=[1024,576],art_style=STYLE_ID,version=2)
 for i,s in enumerate(data['scenes']):
  s.update(index=i,start=i*10,duration=10,seed=seed_fn(run,i),prompt=f"Bright polished 3D storybook nature illustration, vivid colours. {data['environment']}. {s['view']}. Soft luminous light, dimensional foliage, rich balanced colours, layered depth. {data['lighting']}. Palette: {data['palette']}. Gentle rain, no people or text.")
 data['music_prompt']='Gentle sparse felt piano, warm ambient pads, slow peaceful tempo, no drums, no vocals or speech. '+data['music_prompt']
 if seconds==60:
  data['chapters']='\n'.join(f'0:{i*10:02d} {s["chapter"]}' for i,s in enumerate(data['scenes']))
 else:
  from .production import build_timeline,chapter_text
  data['timeline']=build_timeline(image_count,seconds,seed_fn(run,900))
  data['chapters']=chapter_text(data['chapter_titles'],seconds)
  for scene in data['scenes']:
   scene.pop('start',None);scene.pop('duration',None)
 data['description']+='\n\nChapters\n'+data['chapters']+'\n\nAI-generated imagery, piano music and nature ambience. Noncommercial evaluation draft; no therapeutic claims.'
 data['youtube']=dict(snippet=dict(title=data['title'],description=data['description'],tags=data['tags'],categoryId='10',defaultLanguage='en',defaultAudioLanguage='en'),status=dict(privacyStatus='private',selfDeclaredMadeForKids=False,containsSyntheticMedia=True),paidProductPlacementDetails=dict(hasPaidProductPlacement=False))
 data['publishing_blocked']='Review only; AudioLDM nature model is noncommercial'
 out.mkdir(parents=True,exist_ok=True);(out/'plan.json').write_text(json.dumps(data,indent=2));(out/'metadata.json').write_text(json.dumps(data['youtube'],indent=2))
 store.save(key,(history+[dict(run_id=run,title=data['title'],idea=data['idea'],concept_id=data['concept_id'],environment=data['environment'],thumbnail=data['thumbnail']['headline'])])[-200:])
 store.save(checkpoint,data)
 print(json.dumps(dict(title=data['title'],concept=data['concept_id'],model=MODEL_ID,publish=False)),flush=True);return data
