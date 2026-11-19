"""Run after add_face_animation.py; preserve anatomical hand scale and floor alignment."""
import bpy,math,sys
from pathlib import Path
from mathutils import Vector,Matrix
p=Path('/Users/asif/Documents/fitness-garden-demo');s=bpy.context.scene;a=bpy.data.objects['Genesis9']
for frame in range(961,1153):
 s.frame_set(frame);bpy.context.view_layer.update()
 for side,sign in [('l',-1),('r',1)]:
  b=a.pose.bones[side+'_hand'];r=b.bone
  f=(a.data.bones[side+'_mid1'].head_local-r.head_local).normalized()
  cross=(a.data.bones[side+'_index1'].head_local-a.data.bones[side+'_pinky1'].head_local).normalized();cross=(cross-f*cross.dot(f)).normalized();normal=f.cross(cross).normalized()
  rest=Matrix((f,cross,normal)).transposed();target=Matrix(((1,0,0),(0,sign,0),(0,0,sign))).transposed()
  rot=target@rest.transposed()@r.matrix_local.to_3x3();rot*=a.matrix_world.to_scale().x;world=rot.to_4x4();world.translation=a.matrix_world@b.head;b.matrix=a.matrix_world.inverted()@world
  b.keyframe_insert(data_path='rotation_euler',frame=frame);b.keyframe_insert(data_path='location',frame=frame);bpy.context.view_layer.update()
s.frame_start=1;s.frame_end=1440
bpy.ops.wm.save_as_mainfile(filepath=str(p/'garden-workout-face-hq.blend'),compress=True)
if '--render' in sys.argv:
 s.frame_start=1;s.render.filepath=str(p/'frames-hq'/'f-');bpy.ops.render.render(animation=True)
