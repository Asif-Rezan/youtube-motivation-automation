"""Validate and reuse successful AI artifacts while restarting a failed render."""
import argparse,json,math,wave
from pathlib import Path
from PIL import Image
from .plan import validate

def recover(stage,out,run_id,source_run):
    plan=json.loads((out/'plan.json').read_text());validate(plan)
    if plan.get('seconds')!=60 or plan.get('fps')!=24 or plan.get('publish') is not False:
        raise ValueError('Recovery artifact is not a non-publishing one-minute preview')
    if stage=='plan':
        if str(plan.get('run_id'))!=source_run:raise ValueError('Recovery source plan belongs to a different run')
        plan.update(run_id=run_id,recovery_source_run=source_run)
        (out/'plan.json').write_text(json.dumps(plan,indent=2))
        (out/'metadata.json').write_text(json.dumps(plan['youtube'],indent=2))
    elif stage in ['voice','music']:
        with wave.open(str(out/(stage+'.wav'))) as audio:
            seconds=audio.getnframes()/audio.getframerate()
            if abs(seconds-60)>.1:raise ValueError('Recovered audio duration differs from the preview')
        if stage=='voice':
            env=json.loads((out/'speech-envelope.json').read_text())
            if len(env)!=1440 or not all(isinstance(x,(int,float)) and math.isfinite(x) and 0<=x<=1 for x in env):raise ValueError('Invalid recovered speech alignment')
            cues=json.loads((out/'voice-cues.json').read_text())
            if [c['text'] for c in cues]!=[c['text'] for c in plan['narration']]:raise ValueError('Recovered voice does not match the AI script')
    elif stage=='thumbnail':
        brief=json.loads((out/'thumbnail-brief.json').read_text())
        if brief.get('title')!=plan['title'] or brief.get('headline')!=plan['thumbnail']['headline']:
            raise ValueError('Recovered thumbnail belongs to a different title')
        for name in ['thumbnail.jpg','thumbnail.png','thumbnail-before.png','thumbnail-after.png']:
            with Image.open(out/name) as im:
                im.load()
                if im.size!=(1920,1080):raise ValueError('Recovered thumbnail has an invalid resolution')
    else:raise ValueError('Unknown recovery stage')
    print('VERIFIED_RECOVERED_AI_ARTIFACT',stage,'source',source_run,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['plan','voice','music','thumbnail']);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--run-id',required=True);p.add_argument('--source-run',required=True)
    a=p.parse_args();recover(a.stage,a.out,a.run_id,a.source_run)
