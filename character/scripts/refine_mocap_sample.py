import bpy,math,json,sys
from pathlib import Path
from mathutils import Vector
P=Path('/Users/asif/Documents/fitness-mocap-sample');s=bpy.context.scene;a=bpy.data.objects['Genesis9']
metrics=json.loads((P/'retarget-metrics.json').read_text())
required=[max(0,.018-min(x['feet_z'])) for x in metrics]
corrections=[max(required[max(0,i-1):min(len(required),i+2)]) for i in range(len(required))]
for frame,dz in enumerate(corrections,1):
 s.frame_set(frame);bpy.context.view_layer.update();b=a.pose.bones['hip'];w=a.matrix_world@b.matrix;w.translation.z+=dz;b.matrix=a.matrix_world.inverted()@w;b.keyframe_insert(data_path='location',frame=frame)
 metrics[frame-1]['ground_correction_m']=dz
 metrics[frame-1]['corrected_feet_z']=[v+dz for v in metrics[frame-1]['feet_z']]
(P/'retarget-metrics.json').write_text(json.dumps(metrics,indent=2))
# Repair the original hair's skin binding and drive its duplicate body controls.
a.data.pose_position='REST';bpy.context.view_layer.update()
hair=bpy.data.objects['aprilyshEirgridHair_428373.Shape'];world=hair.matrix_world.copy();hair.parent=a;hair.parent_type='OBJECT';hair.matrix_world=world
if not any(m.type=='ARMATURE' for m in hair.modifiers):m=hair.modifiers.new('Native hair skinning','ARMATURE');m.object=a;m.use_deform_preserve_volume=True
for b in a.pose.bones:
 if b.name.endswith('.008'):
  base=b.name.split('.')[0]
  if a.pose.bones.get(base):
   c=b.constraints.new('COPY_TRANSFORMS');c.name='Follow captured body';c.target=a;c.subtarget=base;c.target_space='POSE';c.owner_space='POSE'
a.data.pose_position='POSE';bpy.context.view_layer.update()
# Baked damped secondary motion on the existing hair bones, driven by captured head velocity.
prev=None;lag=Vector();vel=Vector();dt=1/24
chains=[b for b in a.pose.bones if b.name.startswith(('FrontLeft','FrontRight','BackLeft','BackRight'))]
for frame in range(1,337):
 s.frame_set(frame);bpy.context.view_layer.update();head=(a.matrix_world@a.pose.bones['head'].matrix).to_quaternion()
 if prev is None:drive=Vector()
 else:
  q=prev.rotation_difference(head);axis,angle=q.to_axis_angle()
  if angle>math.pi:angle-=math.tau
  drive=axis*(angle/dt)
 target=Vector((-drive.x*.10,-drive.y*.07,-drive.z*.08))
 if target.length>.075:target.normalize();target*=.075
 vel+=(target-lag)*(6*6*dt)-vel*(2*.85*6*dt);lag+=vel*dt
 for i,b in enumerate(chains):
  b.rotation_mode='XYZ';b.rotation_euler=(lag.x*(.5+i%3*.2),lag.y*.3,lag.z*(.5+i%3*.2));b.keyframe_insert(data_path='rotation_euler',frame=frame)
 prev=head.copy()
s['ground_calibration']='Per-clip offset plus a non-negative collision correction. Captured jumping is preserved.'
s['hair_motion']='Original weighted hair rig with damped secondary motion driven by captured head velocity; not a full strand simulation.'
s.frame_start=1;s.frame_end=336;s.eevee.taa_render_samples=24
bpy.ops.wm.save_as_mainfile(filepath=str(P/'kat-cmu-mocap-final.blend'),compress=True)
for frame in [24,144,216,312]:
 s.frame_set(frame);s.render.filepath=str(P/f'clean-{frame}.png');bpy.ops.render.render(write_still=True)
