"""Retarget real CMU BVH recordings onto the existing Daz character, not procedural motion."""
import bpy,math,json,sys
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
P=Path('/Users/asif/Documents/fitness-mocap-sample');P.mkdir(exist_ok=True)
s=bpy.context.scene;a=bpy.data.objects['Genesis9']
# Remove the earlier synthetic body animation while keeping its materials and rig repairs.
for o in bpy.data.objects:
 if o.animation_data:o.animation_data_clear()
for b in a.pose.bones:b.matrix_basis.identity();b.rotation_mode='QUATERNION'
root=bpy.data.objects['Workout motion root'];root.location=(0,0,.9);root.rotation_euler=(0,0,0)
bpy.context.view_layer.update()
restW={b.name:a.matrix_world@b.matrix_local for b in a.data.bones}
def rp(n):return restW[n].translation.copy()
legT=(rp('l_shin')-rp('l_thigh')).length+(rp('l_foot')-rp('l_shin')).length
bpy.ops.preferences.addon_enable(module='io_anim_bvh')
samples=[];clips=[]
for file,start,count in [('14_20.bvh',1,192),('05_12.bvh',1,144)]:
 bpy.ops.import_anim.bvh(filepath=str(P/'sources'/file),global_scale=.01,axis_forward='-Z',axis_up='Y',use_fps_scale=False,update_scene_fps=False)
 src=bpy.context.object;src.hide_render=True
 legS=(src.data.bones['LeftLeg'].head_local-src.data.bones['LeftUpLeg'].head_local).length+(src.data.bones['LeftFoot'].head_local-src.data.bones['LeftLeg'].head_local).length
 scale=legT/legS
 data=[]
 for f in range(count):
  s.frame_set(1+int((start+f/24)*120));bpy.context.view_layer.update()
  data.append({b.name:{'p':src.matrix_world@b.head,'q':(src.matrix_world@b.matrix).to_quaternion(),'r':(src.matrix_world@b.bone.matrix_local).to_quaternion(),'rest':src.matrix_world@b.bone.head_local} for b in src.pose.bones})
 center=sum((x['Hips']['p'] for x in data),Vector())/len(data)
 print('CAPTURE',file,'scale',scale,'root bounds',[(min(x['Hips']['p'][k] for x in data),max(x['Hips']['p'][k] for x in data)) for k in range(3)],flush=True)
 for x in data:samples.append((x,scale,center,file))
 clips.append({'file':file,'start_seconds':start,'duration_seconds':count/24,'source_fps':120})
# Bone targets: core rotations retain captured lean/twist; limbs use captured directions
# plus captured axial twist so bind-pose differences do not produce knock knees.
core=[('hip','Hips'),('pelvis','Hips'),('spine1','LowerBack'),('spine2','Spine'),('spine3','Spine1'),('spine4','Spine1'),('neck1','Neck'),('neck2','Neck1'),('head','Head')]
limbs=[('l_shoulder','l_upperarm','LeftShoulder','LeftArm'),('r_shoulder','r_upperarm','RightShoulder','RightArm'),('l_upperarm','l_forearm','LeftArm','LeftForeArm'),('r_upperarm','r_forearm','RightArm','RightForeArm'),('l_forearm','l_hand','LeftForeArm','LeftHand'),('r_forearm','r_hand','RightForeArm','RightHand'),('l_hand','l_mid1','LeftHand','LeftHandIndex1'),('r_hand','r_mid1','RightHand','RightHandIndex1'),('l_thigh','l_shin','LeftUpLeg','LeftLeg'),('r_thigh','r_shin','RightUpLeg','RightLeg'),('l_shin','l_foot','LeftLeg','LeftFoot'),('r_shin','r_foot','RightLeg','RightFoot'),('l_foot','l_toes','LeftFoot','LeftToeBase'),('r_foot','r_toes','RightFoot','RightToeBase')]
ordered=['hip','pelvis','spine1','spine2','spine3','spine4','l_shoulder','r_shoulder','l_upperarm','r_upperarm','l_forearm','r_forearm','l_hand','r_hand','neck1','neck2','head','l_thigh','r_thigh','l_shin','r_shin','l_foot','r_foot']
def setworld(name,q,pos=None):
 b=a.pose.bones[name];w=q.to_matrix().to_4x4()
 for i in range(3):
  for j in range(3):w[i][j]*=a.matrix_world.to_scale().x
 w.translation=pos if pos is not None else a.matrix_world@b.head
 b.matrix=a.matrix_world.inverted()@w
 bpy.context.view_layer.update()
previous={};ground_offsets={};metrics=[]
for f,(x,scale,center,clip) in enumerate(samples,1):
 s.frame_set(f)
 for b in a.pose.bones:b.matrix_basis.identity()
 bpy.context.view_layer.update()
 rotations={}
 for tn,sn in core:rotations[tn]=(x[sn]['q']@x[sn]['r'].inverted())@restW[tn].to_quaternion()
 for tn,tc,sn,sc in limbs:
  desired=(x[sc]['p']-x[sn]['p']).normalized();sr=(x[sc]['rest']-x[sn]['rest']).normalized();tr=(rp(tc)-rp(tn)).normalized()
  delta=x[sn]['q']@x[sn]['r'].inverted();swing=sr.rotation_difference(desired);twist=swing.inverted()@delta
  axis,angle=twist.to_axis_angle()
  if angle>math.pi:angle-=math.tau
  angle*=1 if axis.dot(sr)>=0 else -1
  rotations[tn]=Quaternion(desired,angle)@tr.rotation_difference(desired)@restW[tn].to_quaternion()
 pos=x['Hips']['p']*scale;pos.x-=center.x*scale;pos.y-=center.y*scale
 for tn in ordered:setworld(tn,rotations[tn],pos if tn=='hip' else None)
 # Constant per-clip ground calibration preserves captured jumps and weight shifts.
 feet=[(a.matrix_world@a.pose.bones[n].head).z for n in ['l_toes','r_toes']]
 if clip not in ground_offsets:ground_offsets[clip]=.02-min(feet)
 pos.z+=ground_offsets[clip];setworld('hip',rotations['hip'],pos)
 # Captured root travel retained; no sine-wave body movement is added.
 for tn in ordered:
  b=a.pose.bones[tn];q=b.rotation_quaternion
  if tn in previous and previous[tn].dot(q)<0:q.negate()
  previous[tn]=q.copy();b.keyframe_insert(data_path='rotation_quaternion',frame=f)
  if tn=='hip':b.keyframe_insert(data_path='location',frame=f)
 t=(f-1)/24;blink=max(math.exp(-((t-v)/.075)**2) for v in [2,5.6,9.4,12.6])
 for side in ['l','r']:
  for suffix,value in [('eyelidupper',-.85),('eyelidlower',.2)]:
   b=a.pose.bones[side+'_'+suffix];b.location.y=value*blink;b.keyframe_insert(data_path='location',frame=f)
  b=a.pose.bones[side+'_lipcorner'];b.location=(.13 if side=='l' else -.13,.32,0);b.keyframe_insert(data_path='location',frame=f)
 metrics.append({'frame':f,'clip':clip,'hip':list(pos),'feet_z':[(a.matrix_world@a.pose.bones[n].head).z for n in ['l_toes','r_toes']]})
print('BAKED',len(samples),'frames',flush=True)
s.render.fps=24;s.frame_start=1;s.frame_end=len(samples);s.render.engine='BLENDER_EEVEE';s.eevee.taa_render_samples=24
s.render.resolution_x=1920;s.render.resolution_y=1080;s.render.resolution_percentage=100;s.render.film_transparent=True
s.camera.data.ortho_scale=4.6;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA'
s['motion_source']='CMU Graphics Lab: 14_20 exercise, 05_12 dance; original BVH conversion by Bruce Hahne, obtained from una-dinosauria/cmu-mocap mirror.'
s['mocap_sample']='14 seconds at 24fps. Real captured body motion, retargeted to Daz. Not trainer-validated.'
(P/'retarget-metrics.json').write_text(json.dumps(metrics,indent=2));(P/'clips.json').write_text(json.dumps(clips,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(P/'kat-cmu-mocap.blend'),compress=True)
if '--render' in sys.argv:
 (P/'frames').mkdir(exist_ok=True);s.render.filepath=str(P/'frames'/'f-');bpy.ops.render.render(animation=True)
else:
 for frame in [24,72,144,192,216,264,312]:
  s.frame_set(frame);s.render.filepath=str(P/f'preview-{frame}.png');bpy.ops.render.render(write_still=True)
