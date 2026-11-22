"""Fresh Qwen idea, coaching script, packaging and title-specific thumbnail brief."""
import argparse,hashlib,json,re
from pathlib import Path
from jsonschema import ValidationError

def obj(**fields):
    return dict(type='object',properties=fields,required=list(fields),additionalProperties=False)
def string(limit):return dict(type='string',maxLength=limit,minLength=1)
TEXT=string(100)
SCHEMA=obj(idea=string(350),title=string(95),description=string(1800),
    tags=dict(type='array',items=string(45),minItems=8,maxItems=15),
    music_prompt=string(450),bpm=dict(type='integer',enum=[96,104,112,120]),
    thumbnail=obj(headline=string(24),before_label=string(14),after_label=string(14),
        focus=dict(type='string',enum=['full_body','calves','posture']),
        accent_hue=dict(type='integer',minimum=0,maximum=359),
        before_frame=dict(type='integer',enum=[1,24,48,240,288]),
        after_frame=dict(type='integer',enum=[96,120,144]),
        angle=dict(type='string',enum=['front','three_quarter']),
        layout=dict(type='string',enum=['split','diagonal','inset'])),
    cycles=dict(type='array',minItems=5,maxItems=5,items=obj(
        movement=dict(type='string',enum=['heel_raise']),duration=dict(type='integer',enum=[10,12,14]),chapter=string(50),ready=TEXT,lift=TEXT,hold=TEXT,lower=TEXT,reset=TEXT)))
TIMING=[('ready',0,2.0),('lift',2.2,1.9),('hold',4.3,1.8),('lower',6.3,2.2),('reset',8.7,3.0)]

def validate(plan):
    from jsonschema import validate as check
    check({k:plan[k] for k in SCHEMA['required']},SCHEMA)
    if not any(w in plan['title'] for w in ['RESET','BOOST','WAKE','QUICK','EASY','SIMPLE','POWER']):
        raise ValueError('Title needs an uppercase power word')
    if not re.search(r'(?:1.minute|one.minute|60.second|60 seconds)',plan['title'],re.I):
        raise ValueError('Title must accurately describe the one-minute routine')
    if len(','.join(plan['tags']))>450:raise ValueError('SEO tags exceed the upload budget')
    for cycle in plan['cycles']:
        for name,_,_ in TIMING:
            if not 2<=len(cycle[name].split())<=6:raise ValueError('Coaching cues need 2–6 words')
    from fitness.sequence import compile_sequence
    compile_sequence(plan)
    return plan

def generate(out,run_id):
    from lyrics_cpu import request_story
    from storage import Store
    store=Store();history=store.load('fitness/ideas.json',[])
    checkpoint=f'fitness/previews/{run_id}/plan.json'
    saved=store.load(checkpoint,None)
    if saved:
        validate(saved)
        if saved.get('run_id')!=run_id or saved.get('seconds')!=60 or saved.get('publish') is not False:
            raise ValueError('Saved preview plan identity differs from this run')
        out.mkdir(parents=True,exist_ok=True)
        (out/'plan.json').write_text(json.dumps(saved,indent=2))
        (out/'metadata.json').write_text(json.dumps(saved['youtube'],indent=2))
        return saved
    seed=int.from_bytes(hashlib.sha256(run_id.encode()).digest()[:4],'big')%(2**31-3)
    prompt=('Create a fresh English adult fitness video package, NOT kids content. '
        'The duration is exactly ONE MINUTE: five consecutive controlled standing '
        'heel-raise repetitions. YOU choose each repetition duration: 10, 12 or 14 seconds, totaling exactly 60 seconds. Each cycle must set movement=heel_raise and duration. Select pacing to fit your title and coaching; avoid sudden fast movement. Only this reviewed motion is available for this preview. '
        'No squats, walking, floor exercises, jumping or movements absent from the animation. '
        'Choose a distinctive idea/audience/angle such as a desk break, morning reset, balance '
        'practice or a calm calf warm-up. All copy must match the actual gentle heel raises. '
        'Write a compelling search-friendly title with 1-Minute or 60 Seconds and one uppercase '
        'power word RESET, BOOST, WAKE, QUICK, EASY, SIMPLE or POWER. Write a useful original '
        'description prose (chapter timestamps are added automatically) and 8–15 distinct specific SEO tags (under 450 combined characters). '
        'Each cycle has a chapter and five spoken coaching cues: ready at 0s, lift at 2.2s, '
        'hold at 4.3s, lower at 6.3s, reset at 8.7s on a 12-second reference cycle; cue timing scales with your chosen duration. Every cue MUST have only 2–6 words; '
        'use short natural language and vary the encouragement between repetitions. '
        'No promises of weight loss, a changed physique, cures, guaranteed results or invented research. '
        'The music prompt is ORIGINAL upbeat instrumental workout music, no vocals, suitable under speech. '
        'Design a unique BEFORE/AFTER thumbnail concept tied to this exact title. Compare a flat-foot '
        'starting stance and raised heels, not fictional body transformation. Choose useful focus, '
        'a brief single-line curiosity headline, contextual before/after labels (do not repeat the words BEFORE or AFTER), an accent hue, varied layout and camera angle. '
        f'Creative seed for this new episode: {seed}. '
        'Do not reuse these recent ideas, titles or thumbnail headlines: '+json.dumps(history[-15:]))
    failures=[]
    for attempt in range(3):
        response=request_story('chat/completions',dict(messages=[dict(role='user',content=prompt+''.join(failures))],
            response_format=dict(type='json_schema',json_schema=dict(schema=SCHEMA)),
            seed=(seed+attempt)%(2**31-3),max_completion_tokens=2800,validation_attempts=2))
        plan=json.loads(response['choices'][0]['message']['content'])
        plan['title']=' '.join(plan['title'].split())
        for key in ['headline','before_label','after_label']:plan['thumbnail'][key]=' '.join(plan['thumbnail'][key].split())
        plan['tags']=list(dict.fromkeys(' '.join(tag.lower().split()) for tag in plan['tags']))
        try:
            validate(plan)
            normalize=lambda text:' '.join(re.findall(r'[a-z0-9]+',text.lower()))
            if any(normalize(x['title'])==normalize(plan['title']) or normalize(x['thumbnail'])==normalize(plan['thumbnail']['headline']) for x in history):
                raise ValueError('A previous title or thumbnail headline was repeated; create a genuinely new angle and hook')
            break
        except (ValueError,ValidationError) as error:
            failures.append(' Correct this validation issue in the complete replacement JSON: '+str(error))
    else:raise ValueError('AI fitness plan failed bounded validation')
    from fitness.sequence import compile_sequence, narration
    sequence=compile_sequence(plan)
    chapters='\n'.join(f'0:{row["start_frame"]//24:02d} {c["chapter"]}' for row,c in zip(sequence,plan['cycles']))
    plan.update(run_id=run_id,seconds=60,fps=24,resolution=[1920,1080],movement='heel_raise',
        creative_seed=seed,publish=False,chapters=chapters,
        workout_sequence=sequence,animation_pipeline='ai-sequence-to-native-rig-v1',
        narration=narration(plan,TIMING),
        models=dict(planning='Qwen/Qwen3-4B-Instruct-2507',voice='hexgrad/Kokoro-82M',music='ACE-Step/Ace-Step1.5'))
    plan['description']+='\n\nChapters\n'+chapters+'\n\nAI-created virtual instructor, narration and original instrumental music.\n#StandingWorkout #CalfRaises #FitnessBreak'
    plan['youtube']=dict(snippet=dict(title=plan['title'],description=plan['description'],tags=plan['tags'],
        categoryId='17',defaultLanguage='en',defaultAudioLanguage='en'),
        status=dict(privacyStatus='private',selfDeclaredMadeForKids=False,containsSyntheticMedia=True),
        paidProductPlacementDetails=dict(hasPaidProductPlacement=False))
    out.mkdir(parents=True,exist_ok=True)
    (out/'plan.json').write_text(json.dumps(plan,indent=2))
    (out/'metadata.json').write_text(json.dumps(plan['youtube'],indent=2))
    store.save('fitness/ideas.json',history+[dict(run_id=run_id,title=plan['title'],idea=plan['idea'],thumbnail=plan['thumbnail']['headline'])])
    store.save(checkpoint,plan)
    print(json.dumps(dict(title=plan['title'],duration=60,publish=False,models=plan['models'])),flush=True)
    return plan

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--run-id',required=True)
    args=p.parse_args();generate(args.out,args.run_id)
