import bpy,math,sys
from mathutils import Vector,Quaternion
from pathlib import Path
OUT=Path('/Users/asif/Documents/fitness-garden-demo');OUT.mkdir(exist_ok=True)
s=bpy.context.scene;arm=bpy.data.objects['Genesis9'];arm.animation_data_clear()
for b in arm.pose.bones:b.matrix_basis.identity()
bpy.context.view_layer.update()
# Repair imported clothing skinning, retaining the exact source garment geometry.
for o in list(bpy.data.objects):
 if o.type in {'LIGHT','CAMERA'} or o.name=='Plane':bpy.data.objects.remove(o,do_unlink=True)
for name in ['Bra_5382.Shape','V1_Pant_4526.Shape']:
 o=bpy.data.objects[name];w=o.matrix_world.copy();o.parent=arm;o.parent_type='OBJECT';o.matrix_world=w
 for g in o.vertex_groups:g.name=g.name.split('.')[0]
 m=o.modifiers.new('Workout garment skinning','ARMATURE');m.object=arm;m.use_deform_preserve_volume=True
# All animation is driven by the main skeleton, including garment twist weights.
root=bpy.data.objects.new('Workout motion root',None);s.collection.objects.link(root);root.location=(0,0,.9)
bpy.context.view_layer.update()
w=arm.matrix_world.copy();arm.parent=root;arm.matrix_world=w
def setrot(name,v):
 b=arm.pose.bones.get(name)
 if b:b.rotation_mode='XYZ';b.rotation_euler=v
def smooth(v):v=max(0,min(1,v));return v*v*(3-2*v)
def pose(t):
 for b in arm.pose.bones:b.rotation_mode='XYZ';b.rotation_euler=(0,0,0);b.location=(0,0,0)
 root.location=(0,0,.9);root.rotation_euler=(0,0,0)
 seg=min(6,int(t/8));u=t-seg*8
 if t>=48:seg=6;u=t-48
 length=12 if seg==6 else 8
 env=smooth(u/.65)*smooth((length-u)/.65)
 a=math.sin(u*math.tau/2);c=(1-math.cos(u*math.tau/2))/2
 rots={'l_upperarm':(0,0,-.68),'r_upperarm':(0,0,.68)}
 z=0
 if seg==0:
  for side,sign in [('l',1),('r',-1)]:rots[side+'_upperarm']=(.45*math.sin(u*3)*env,.12*math.cos(u*3)*env,sign*(-.68+1.3*env));rots[side+'_forearm']=(0,0,sign*.1)
 elif seg==1:
  q=c*env
  rots.update(l_upperarm=(0,0,-.68+2.7*q),r_upperarm=(0,0,.68-2.7*q),l_thigh=(0,0,.28*q),r_thigh=(0,0,-.28*q))
  z=.08*abs(math.sin(u*math.pi))*env
 elif seg==2:
  q=.82*c*env;z=-.78*(1-math.cos(q))
  for side in ['l','r']:
   rots[side+'_thigh']=(-q,0,0);rots[side+'_shin']=(2*q,0,0);rots[side+'_foot']=(-q,0,0)
   rots[side+'_upperarm']=(-1.25*env,0,(-.68 if side=='l' else .68)*.5);rots[side+'_forearm']=(-.25*env,0,0)
  rots['spine1']=(.16*c*env,0,0)
 elif seg==3:
  for side,sign in [('l',1),('r',-1)]:
   q=max(0,sign*a)*env;rots[side+'_thigh']=(-1.1*q,0,0);rots[side+'_shin']=(1.25*q,0,0);rots[side+'_upperarm']=(-.55*max(0,-sign*a)*env,0,-sign*.68);rots[side+'_forearm']=(-.7*env,0,0)
 elif seg==4:
  q=.65*c*env;z=-.17*c*env
  rots.update(l_thigh=(-q,0,0),l_shin=(1.15*q,0,0),r_thigh=(q*.7,0,0),r_shin=(.8*q,0,0),spine1=(.1*env,0,0))
 elif seg==5:
  # Side-on floor sequence, both hands and toes contacting the same deck plane.
  root.rotation_euler=(math.pi/2,0,math.pi/2)
  root.location=(0,0,.43-.10*c)
  rots.update(l_upperarm=(-1.65,0,-.5),r_upperarm=(-1.65,0,.5),l_forearm=(-.3-.55*c,0,0),r_forearm=(-.3-.55*c,0,0),l_hand=(-.275+.55*c,0,0),r_hand=(-.275+.55*c,0,0),head=(-.12,0,0))
 else:
  beat=u*math.tau/1.25
  root.location.x=.18*math.sin(beat/2)*env;z=.045*(1-math.cos(beat*2))*env
  root.rotation_euler.z=.25*math.sin(beat/2)*env
  rots.update(spine1=(.03,.08*math.sin(beat)*env,.10*math.sin(beat)*env),head=(0,.06*math.sin(beat),0))
  for side,sign in [('l',1),('r',-1)]:
   rots[side+'_upperarm']=(-.3*math.sin(beat+sign)*env,0,-sign*.68+sign*(.5+.4*math.sin(beat+sign))*env)
   rots[side+'_forearm']=(-(.6+.35*math.sin(beat+sign))*env,0,0)
   q=max(0,sign*math.sin(beat))*.35*env;rots[side+'_thigh']=(-q,0,sign*.05*env);rots[side+'_shin']=(q*1.3,0,0)
 root.location.z+=z
 for n,v in rots.items():setrot(n,v)
 if seg==5:
  # Solve a shared floor plane for the wrists and toes instead of floating.
  bpy.context.view_layer.update()
  def joint(n):return arm.matrix_world@arm.pose.bones[n].head
  toe=(joint('l_toes')+joint('r_toes'))/2
  hand=(joint('l_hand')+joint('r_hand'))/2
  delta=hand-toe
  angle=math.atan2(delta.z,delta.x)
  root.rotation_euler=(Quaternion((0,1,0),angle)@root.rotation_euler.to_quaternion()).to_euler()
  bpy.context.view_layer.update()
  toe=(joint('l_toes')+joint('r_toes'))/2
  root.location.z+=.045-toe.z
 # A small natural head motion and secondary hair motion.
 if seg!=5:setrot('head',(.018*math.sin(t*2),.035*math.sin(t),0))
 for b in arm.pose.bones:
  if 'twist' in b.name and '.' not in b.name:
   # twist joints inherit their animated parent; no independent rotation required
   pass
 for b in arm.pose.bones:
  b.keyframe_insert(data_path='rotation_euler',frame=round(t*12)+1)
 root.keyframe_insert(data_path='location',frame=round(t*12)+1);root.keyframe_insert(data_path='rotation_euler',frame=round(t*12)+1)
for f in range(720):pose(f/12)
def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(0,-5,1.4));cam=bpy.context.object;aim(cam,(0,0,.86));cam.data.type='ORTHO';cam.data.ortho_scale=4.25;s.camera=cam
for pos,power,size in [((-3,-4,5),450,5),((3,-1,3),170,4),((0,3,4),200,3)]:
 bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.data.energy=power;o.data.shape='DISK';o.data.size=size;aim(o,(0,0,1))
s.world.color=(.15,.15,.15)
s.render.engine='CYCLES';s.cycles.samples=6;s.cycles.use_denoising=True;s.cycles.max_bounces=3
s.render.film_transparent=True;s.render.resolution_x=1280;s.render.resolution_y=720;s.render.resolution_percentage=100
s.render.fps=12;s.frame_start=1;s.frame_end=720;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA'
s.render.filepath=str(OUT/'frames'/'f-');(OUT/'frames').mkdir(exist_ok=True)
s.view_settings.view_transform='AgX';s.view_settings.exposure=.15
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'garden-workout-60s.blend'),compress=True)
if '--prepare-only' in sys.argv:pass
elif '--preview' in sys.argv:
 for frame in [19,139,247,331,427,523,637]:
  s.frame_set(frame);s.render.filepath=str(OUT/f'pose-{frame}.png');bpy.ops.render.render(write_still=True)
else:bpy.ops.render.render(animation=True)
