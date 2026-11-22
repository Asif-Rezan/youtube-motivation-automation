"""Rebuild, validate and render the corrected editable walking review."""
import os,sys,subprocess,json
from pathlib import Path
S=Path(__file__).resolve().parent
P=Path(os.environ.get('FITNESS_RIGIFY_DIR','/Users/asif/Documents/fitness-rigify-upright-review'))
P.mkdir(parents=True,exist_ok=True)
BLENDER=os.environ.get('BLENDER','/Applications/Blender.app/Contents/MacOS/Blender')
env=os.environ.copy();env['FITNESS_RIGIFY_DIR']=str(P)
receipt=[]
def stage(name,args,output=None):
    print('STAGE',name,flush=True)
    log=P/(name+'.log')
    with log.open('w') as stream:
        result=subprocess.run(args,env=env,stdout=stream,stderr=subprocess.STDOUT)
    text=log.read_text()
    if result.returncode or 'Traceback (most recent call last)' in text:
        raise RuntimeError(name+' failed: '+text[-2500:])
    if output is not None and not output.exists():raise RuntimeError('Missing '+str(output))
    receipt.append({'stage':name,'success':True})
    (P/'pipeline-receipt.json').write_text(json.dumps(receipt,indent=2))
def blender(name,input,scripts,output=None):
    args=[BLENDER,'-b',str(input)]
    for script in scripts:args.extend(['--python',str(S/script)])
    stage(name,args,output)
controls=P/'kat-rigify-controls.blend';final=P/'kat-rigify-final.blend'
if '--from-controls' not in sys.argv:
    blender('build',S.parent/'blender/kat-rokoko-walk-v1.blend',['build_rigify_trainer.py'],controls)
    blender('prepare',controls,['prepare_natural_gait.py'],P/'gait-plan.json')
elif not controls.exists() or not (P/'gait-plan.json').exists():
    raise FileNotFoundError('--from-controls needs prepared controls and gait-plan.json in the output directory')
blender('animate',controls,['animate_rigify_trainer.py'],P/'kat-rigify-motion.blend')
blender('contact',P/'kat-rigify-motion.blend',['clean_rigify_contacts.py'],final)
blender('review',final,['audit_walk_posture.py','audit_rigify_motion.py','review_rigify_trainer.py'],P/'posture-review.json')
if '--no-render' in sys.argv:raise SystemExit(0)
frames=P/'frames';frames.mkdir(exist_ok=True)
expression=("import bpy; s=bpy.context.scene; s.render.resolution_x=1920; s.render.resolution_y=1080; "
            "s.render.resolution_percentage=100; s.eevee.taa_render_samples=32; "
            f"s.render.filepath={str(frames/'f-')!r}; bpy.ops.render.render(animation=True)")
stage('render',[BLENDER,'-b',str(final),'--python-expr',expression])
from PIL import Image
def invalid_frames():
    invalid=[]
    for f in range(1,241):
        try:
            with Image.open(frames/f'f-{f:04d}.png') as im:im.load()
        except (OSError,ValueError):invalid.append(f)
    return invalid
for attempt in range(2):
    invalid=invalid_frames()
    if not invalid:break
    repair=("import bpy; s=bpy.context.scene; s.render.resolution_x=1920; s.render.resolution_y=1080; "
            "s.render.resolution_percentage=100; s.eevee.taa_render_samples=32; "
            f"frames={str(frames)!r}; "
            f"exec(\"for f in {invalid!r}:\\n s.frame_set(f); s.render.filepath=frames+'/f-'+str(f).zfill(4)+'.png'; bpy.ops.render.render(write_still=True)\")")
    stage('render-repair-'+str(attempt+1),[BLENDER,'-b',str(final),'--python-expr',repair])
if invalid_frames():raise RuntimeError('Rendered frames remain invalid after two repair attempts')
env.update(FITNESS_REVIEW_DIR=str(P),FITNESS_VIDEO_NAME='kat-upright-gait-10s.mp4',
           FITNESS_REVIEW_LABEL='Upright posture · Arm swing · Foot-contact IK')
stage('compose',[sys.executable,str(S/'compose_walk_review.py')],P/'kat-upright-gait-10s.mp4')
print('COMPLETE',P/'kat-upright-gait-10s.mp4',flush=True)
