import bpy,json
from pathlib import Path
from bpy_extras.object_utils import world_to_camera_view
P=Path('/Users/asif/Documents/fitness-mocap-sample');s=bpy.context.scene;a=bpy.data.objects['Genesis9']
env=json.loads((P/'speech-envelope.json').read_text());shadows=[]
for frame,amount in enumerate(env,1):
 s.frame_set(frame);bpy.context.view_layer.update()
 b=a.pose.bones['lowerjaw'];b.rotation_mode='XYZ';b.rotation_euler.x=.09*amount;b.keyframe_insert(data_path='rotation_euler',frame=frame)
 for name in ['l_liplower','r_liplower','liplowermiddle']:
  b=a.pose.bones.get(name)
  if b:b.location.y=-.13*amount;b.keyframe_insert(data_path='location',frame=frame)
 for side in ['l','r']:
  b=a.pose.bones[side+'_cheek'];b.location.y=.1;b.keyframe_insert(data_path='location',frame=frame)
 feet=[]
 for name in ['l_toes','r_toes']:
  pt=a.matrix_world@a.pose.bones[name].head;z=pt.z;pt.z=0;uv=world_to_camera_view(s,s.camera,pt);feet.append([uv.x*1920,(1-uv.y)*1080,z])
 shadows.append(feet)
(P/'shadows.json').write_text(json.dumps(shadows))
s['speech']='Voice amplitude jaw/lower-lip animation, not phoneme-level visemes.'
s.frame_start=1;s.frame_end=336;s.render.fps=24;s.render.filepath=str(P/'frames'/'f-');(P/'frames').mkdir(exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'kat-cmu-mocap-final.blend'),compress=True)
bpy.ops.render.render(animation=True)
