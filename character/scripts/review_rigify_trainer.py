"""Render inspection angles and measure the Rigify -> Daz rest-offset bridge."""
import bpy,json,os
from pathlib import Path
from mathutils import Vector
OUT=Path(os.environ.get('FITNESS_RIGIFY_DIR','/Users/asif/Documents/fitness-rigify-review'))
s=bpy.context.scene;a=bpy.data.objects['Genesis9'];src=bpy.data.objects['Rokoko_Baked_Source']
rig=bpy.data.objects['Trainer_Rigify']
s.frame_set(48);bpy.context.view_layer.update()
before=a.matrix_world@a.pose.bones['l_foot'].head
ctrl=rig.pose.bones['foot_ik.L'];old=ctrl.matrix.copy();m=old.copy();m.translation.x+=.04;ctrl.matrix=m
bpy.context.view_layer.update()
movement=((a.matrix_world@a.pose.bones['l_foot'].head)-before).length
assert movement>.005,('Foot IK does not drive native character',movement)
ctrl.matrix=old;bpy.context.view_layer.update()
(OUT/'control-edit-check.json').write_text(json.dumps({'foot_control_delta_m':.04,'native_ankle_response_m':movement},indent=2))
rows=[]
for f in [1,48,96,144,192,240]:
    s.frame_set(f);bpy.context.view_layer.update()
    row={'frame':f,'joint_errors_m':{}}
    for name in ['hip','head','l_hand','r_hand','l_foot','r_foot']:
        row['joint_errors_m'][name]=((a.matrix_world@a.pose.bones[name].head)-(src.matrix_world@src.pose.bones[name].head)).length
    rows.append(row)
(OUT/'bridge-review.json').write_text(json.dumps(rows,indent=2))
s.render.resolution_x=960;s.render.resolution_y=540;s.render.resolution_percentage=100
s.eevee.taa_render_samples=16
for f in [1,96,192]:
    s.frame_set(f);s.render.filepath=str(OUT/f'front-{f:04d}.png');bpy.ops.render.render(write_still=True)
s.frame_set(48);s.camera.location=(5,-2,1.65)
s.camera.rotation_euler=(Vector((0,0,.85))-s.camera.location).to_track_quat('-Z','Y').to_euler()
s.render.filepath=str(OUT/'side-0048.png');bpy.ops.render.render(write_still=True)
print('RIGIFY_REVIEW_DONE',rows,flush=True)
