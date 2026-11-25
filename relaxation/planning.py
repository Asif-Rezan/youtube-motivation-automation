"""Fresh Qwen relaxation concepts, coherent art direction and persisted diversity."""
import json,re
from difflib import SequenceMatcher
from pathlib import Path
from jsonschema import validate as check,ValidationError

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
def validate(data,history):
 check(data,SCHEMA)
 if not re.search(r'(?:1[ -]minute|one[ -]minute|60[ -]seconds?)',data['title'],re.I):raise ValueError('Title must accurately state the one-minute preview length')
 if len(','.join(data['tags']))>450:raise ValueError('SEO tags exceed 450 characters')
 if len({normalize(t) for t in data['tags']})!=len(data['tags']):raise ValueError('Repeated SEO tags')
 if len({normalize(s['view']) for s in data['scenes']})!=6:raise ValueError('Six distinct camera views are required')
 for old in history:
  if normalize(old['concept_id'])==normalize(data['concept_id']):raise ValueError('Repeated episode concept')
  if SequenceMatcher(None,normalize(old['title']),normalize(data['title'])).ratio()>.85:raise ValueError('Title too close to a previous episode')
  if SequenceMatcher(None,normalize(old['idea']),normalize(data['idea'])).ratio()>.85:raise ValueError('Idea too close to a previous episode')
 return data

def generate(out,run,seed_fn):
 from storage import Store
 from lyrics_cpu import request_story,MODEL_ID
 store=Store();key='relaxation/ideas.json';history=store.load(key,INITIAL_HISTORY)
 checkpoint=f'relaxation/previews/{run}/plan.json';saved=store.load(checkpoint,None)
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
 errors=[]
 for attempt in range(3):
  response=request_story('chat/completions',dict(messages=[dict(role='user',content=prompt+' Corrections: '+'; '.join(errors))],response_format=dict(type='json_schema',json_schema=dict(schema=SCHEMA)),seed=seed_fn(run,500+attempt),max_completion_tokens=2500,validation_attempts=2))
  data=json.loads(response['choices'][0]['message']['content'])
  data['tags']=list(dict.fromkeys(' '.join(t.lower().split()) for t in data['tags']))
  try:validate(data,history);break
  except (ValueError,ValidationError) as e:errors.append(str(e)[:300])
 else:raise ValueError('AI relaxation package failed validation after three attempts')
 data.update(run_id=run,seconds=60,fps=24,resolution=[1280,720],publish=False,
  models=dict(planning=MODEL_ID,images='segmind/SSD-1B',music='ACE-Step/Ace-Step1.5',nature='cvssp/audioldm-s-full-v2',depth='depth-anything/Depth-Anything-V2-Small-hf'),
  nature_license='CC-BY-NC-SA-4.0: noncommercial evaluation only; do not publish or monetize this preview',
  audio_design='Original AI piano plus three distinct AI rain takes with quality-screened segments and long overlaps',image_source_size=[1024,576],version=2)
 for i,s in enumerate(data['scenes']):
  s.update(index=i,start=i*10,duration=10,seed=seed_fn(run,i),prompt=f"Photorealistic cinematic nature landscape. {data['environment']}. {data['lighting']}. Colours: {data['palette']}. Gentle rain, same coherent location and weather. {s['view']}. Natural proportions, refined detail, no people, no writing.")
 data['music_prompt']='Gentle sparse felt piano, warm ambient pads, slow peaceful tempo, no drums, no vocals or speech. '+data['music_prompt']
 data['chapters']='\n'.join(f'0:{i*10:02d} {s["chapter"]}' for i,s in enumerate(data['scenes']))
 data['description']+='\n\nChapters\n'+data['chapters']+'\n\nAI-generated imagery, piano music and nature ambience. One-minute noncommercial evaluation preview; no therapeutic claims.'
 data['youtube']=dict(snippet=dict(title=data['title'],description=data['description'],tags=data['tags'],categoryId='10',defaultLanguage='en',defaultAudioLanguage='en'),status=dict(privacyStatus='private',selfDeclaredMadeForKids=False,containsSyntheticMedia=True),paidProductPlacementDetails=dict(hasPaidProductPlacement=False))
 data['publishing_blocked']='Review only; AudioLDM nature model is noncommercial'
 out.mkdir(parents=True,exist_ok=True);(out/'plan.json').write_text(json.dumps(data,indent=2));(out/'metadata.json').write_text(json.dumps(data['youtube'],indent=2))
 store.save(key,(history+[dict(run_id=run,title=data['title'],idea=data['idea'],concept_id=data['concept_id'],environment=data['environment'],thumbnail=data['thumbnail']['headline'])])[-200:])
 store.save(checkpoint,data)
 print(json.dumps(dict(title=data['title'],concept=data['concept_id'],model=MODEL_ID,publish=False)),flush=True);return data
