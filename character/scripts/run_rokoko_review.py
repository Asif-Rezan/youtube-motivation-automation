"""Finish and render the prepared free-Rokoko demo with reproducible stage logs."""
import os,subprocess,json,sys
from pathlib import Path
P=Path('/Users/asif/Documents/fitness-rokoko-review')
S=Path(__file__).resolve().parent
BLENDER='/Applications/Blender.app/Contents/MacOS/Blender'
env=os.environ.copy();env['FITNESS_REVIEW_DIR']=str(P)
stages=['finish_walk_performance.py','retime_walk_footroll.py','plan_walk_contacts.py',
        'stabilize_walk_knees.py','audit_walk_continuity.py']
receipt=[]
for script in stages:
    print('STAGE',script,flush=True)
    with (P/(script+'.log')).open('w') as log:
        result=subprocess.run([BLENDER,'--background',str(P/'kat-continuous-walk-final.blend'),
            '--python',str(S/script)],env=env,stdout=log,stderr=subprocess.STDOUT)
    # Blender can exit zero after a Python exception, so inspect the stage log too.
    output=(P/(script+'.log')).read_text()
    if result.returncode or 'Traceback (most recent call last)' in output:
        raise RuntimeError(f'{script} failed: '+output[-2500:])
    receipt.append({'stage':script,'success':True})
    (P/'pipeline-receipt.json').write_text(json.dumps(receipt,indent=2))
if '--no-render' in sys.argv:raise SystemExit(0)
print('STAGE render',flush=True)
frames=P/'frames';frames.mkdir(exist_ok=True)
expression=f"import bpy; bpy.context.scene.render.filepath={str(frames/'f-')!r}; bpy.ops.render.render(animation=True)"
with (P/'render.log').open('w') as log:
    result=subprocess.run([BLENDER,'--background',str(P/'kat-continuous-walk-final.blend'),'--python-expr',expression],env=env,stdout=log,stderr=subprocess.STDOUT)
if result.returncode or len(list(frames.glob('f-*.png')))!=240:raise RuntimeError('Incomplete walking render')
print('STAGE encode',flush=True)
subprocess.run([sys.executable,str(S/'compose_walk_review.py')],env=env,check=True)
print('COMPLETE',P/'kat-continuous-human-walk-10s.mp4',flush=True)
