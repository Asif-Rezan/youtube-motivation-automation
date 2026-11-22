"""Blender entry point: reviewed continuous motion, neural-voice face and real skin contact."""
import bpy,json,math,os,sys
from pathlib import Path
from mathutils import Quaternion,Vector
from bpy_extras.object_utils import world_to_camera_view
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'character/scripts'))
from rig_repairs import repair_mouth_chain
from fitness.timeline import FRAMES_PER_SHARD

out=Path(os.environ.get('FITNESS_OUTPUT','output/fitness-preview'));index=int(os.environ.get('FITNESS_SHARD','0'))
plan=json.loads((out/'plan.json').read_text());s=bpy.context.scene
a=bpy.data.objects['Genesis9'];body=bpy.data.objects['Genesis9.Shape']
repair_mouth_chain(a,bpy.data.objects['Genesis9Mouth.Shape'])
assert bpy.app.version>=(5,3,0),'The packed character needs Blender 5.3+'
assert not [im.name for im in bpy.data.images if im.source=='FILE' and not im.packed_file]
for im in bpy.data.images:
    if im.source=='FILE' and max(im.size)>2048:
        scale=2048/max(im.size);im.scale(round(im.size[0]*scale),round(im.size[1]*scale))
s.render.engine='BLENDER_EEVEE';s.eevee.taa_render_samples=32
s.render.resolution_x=1920;s.render.resolution_y=1080;s.render.resolution_percentage=100
s.render.film_transparent=True;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA'
thumb=os.environ.get('FITNESS_THUMBNAIL')=='1'
if thumb:
    s.camera.animation_data_clear()
    if plan['thumbnail']['angle']=='front':s.camera.location=(0,-5.7,1.65)
    else:s.camera.location=(2.4,-5.4,1.65)
    s.camera.rotation_euler=(Vector((0,0,.86))-s.camera.location).to_track_quat('-Z','Y').to_euler()
    for label in ['before','after']:
        s.frame_set(plan['thumbnail'][label+'_frame']);s.render.filepath=str(out/f'thumbnail-{label}.png')
        bpy.ops.render.render(write_still=True)
    print('FITNESS_THUMBNAIL_POSES_READY',flush=True)
    raise SystemExit(0)

envelope=json.loads((out/'speech-envelope.json').read_text())
formulas=json.loads((ROOT/'fitness/facial-rig.json').read_text())
parts=out/f'render-{index:02d}';parts.mkdir(parents=True,exist_ok=True)
rows=[];minimum=1e6;indices={side:[v.index for v in body.data.vertices if v.co.y<10 and (v.co.x>0)==(side=='l')] for side in ['l','r']}
seed=plan['creative_seed']%100/100
start=int(os.environ.get('FITNESS_FRAME_FIRST',str(index*FRAMES_PER_SHARD)))
count=int(os.environ.get('FITNESS_FRAME_COUNT',str(FRAMES_PER_SHARD)))
for frame in range(start,start+count):
    path=parts/f'f-{frame:04d}.png';checkpoint=parts/f'f-{frame:04d}.json'
    if path.exists() and checkpoint.exists():
        rows.append(json.loads(checkpoint.read_text()));continue
    s.frame_set(frame%288+1);t=frame/24
    amount=envelope[frame]*.22
    body.data.shape_keys.key_blocks['JawOpen'].value=amount
    for formula in formulas:
        b=a.pose.bones.get(formula['bone'])
        if not b:continue
        channel=formula['channel'];axis='xyz'.index(channel[-1]);coefficient=formula['coefficient']
        if channel.startswith('translation/'):b.location[axis]=coefficient*amount
        else:
            direction=[0,0,0];direction[axis]=1;b.rotation_mode='QUATERNION'
            b.rotation_quaternion=Quaternion(direction,math.radians(coefficient)*amount)
    blink=math.exp(-(((t-seed-1.6+1.75)%3.5-1.75)/.065)**2)
    for side,suffix in [('l','Left'),('r','Right')]:
        body.data.shape_keys.key_blocks['EyeBlink'+suffix].value=blink
        for name,angle in [('eyelidupper',50),('eyelidlower',-6)]:
            b=a.pose.bones[side+'_'+name];b.rotation_mode='QUATERNION'
            b.rotation_quaternion=Quaternion((1,0,0),math.radians(angle)*blink)
    bpy.context.view_layer.update()
    ob=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ob.to_mesh();feet={}
    for side,ids in indices.items():
        vertices=[ob.matrix_world@mesh.vertices[i].co for i in ids];low=min(v.z for v in vertices);minimum=min(minimum,low)
        points=[]
        for v in vertices:
            if v.z<low+.004:
                uv=world_to_camera_view(s,s.camera,Vector((v.x,v.y,0)))
                points.append([uv.x*1920,(1-uv.y)*1080])
        feet[side]=dict(height=low,points=points)
    ob.to_mesh_clear()
    if minimum<-.002:raise RuntimeError('Native foot mesh penetrates the yoga deck')
    row=dict(frame=frame,feet=feet);rows.append(row)
    # Do not load each rendered PNG back into the live EEVEE image/GPU cache.
    # The separate Python supervisor fully decodes it after this worker exits.
    temporary=path.with_suffix('.partial.png');s.render.filepath=str(temporary)
    bpy.ops.render.render(write_still=True)
    os.replace(temporary,path)
    meta=checkpoint.with_suffix('.json.part');meta.write_text(json.dumps(row));os.replace(meta,checkpoint)
    print('FITNESS_FRAME_CHECKPOINT',frame,flush=True)
(parts/'contacts.json').write_text(json.dumps(rows))
(parts/'render-review.json').write_text(json.dumps(dict(frames=count,first_frame=start,minimum_sole_z_m=minimum,
    fps=24,resolution=[1920,1080],speech_animation='Audio-aligned native jaw and corrective morph; timed eyelid blink')))
print('FITNESS_RENDER_READY',index,count,minimum,flush=True)
