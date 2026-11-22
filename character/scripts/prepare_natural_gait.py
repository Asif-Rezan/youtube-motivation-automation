"""Rebuild stance timing from the untouched Rokoko bake, not old planted feet."""
import bpy,json,os,math,statistics
from pathlib import Path
from mathutils import Vector
out=Path(os.environ.get('FITNESS_RIGIFY_DIR','/Users/asif/Documents/fitness-rigify-upright-review'))
out.mkdir(parents=True,exist_ok=True)
raw=Path(os.environ.get('FITNESS_RAW_ROKOKO','/Users/asif/Documents/fitness-rokoko-review/kat-rokoko-retarget.blend'))
s=bpy.context.scene;src=bpy.data.objects['Rokoko_Baked_Source']
portable=Path(__file__).resolve().parents[1]/'motion/sources/rokoko-walk-native-bake.json'
if raw.exists():
    with bpy.data.libraries.load(str(raw)) as (available,loaded):loaded.objects=['Genesis9']
    imported=loaded.objects[0]
    # Only the preserved offline Rokoko action is needed; no meshes are appended.
    src.animation_data.action=imported.animation_data.action.copy()
    src.animation_data.action_slot=src.animation_data.action.slots[0]
    bpy.data.objects.remove(imported,do_unlink=True)
elif portable.exists():
    baked=json.loads(portable.read_text());src.animation_data_clear()
    for frame,pose in enumerate(baked['frames'],1):
        for name,(location,rotation,scale) in pose.items():
            b=src.pose.bones[name];b.rotation_mode='QUATERNION'
            b.location=location;b.rotation_quaternion=rotation;b.scale=scale
            for path in ['location','rotation_quaternion','scale']:b.keyframe_insert(data_path=path,frame=frame)
else:
    raise FileNotFoundError('Need the untouched Rokoko bake or the versioned portable native-pose capture')
rest={b.name:src.matrix_world@b.matrix_local for b in src.data.bones}
def smooth(values,radius=2):
    weights=[math.exp(-.5*(i/1.1)**2) for i in range(-radius,radius+1)]
    return [sum(values[min(len(values)-1,max(0,j+i))]*w for i,w in zip(range(-radius,radius+1),weights))/sum(weights) for j in range(len(values))]
names=['hip','pelvis','spine1','spine2','spine3','spine4','neck1','neck2','head']
for side in ['l','r']:names.extend(side+'_'+n for n in ['shoulder','upperarm','forearm','hand','thigh','shin','foot','toes'])
rows=[];poses=[]
for f in range(1,241):
    s.frame_set(f);bpy.context.view_layer.update()
    pose={}
    for name in names:
        loc,rot,scale=src.pose.bones[name].matrix_basis.decompose()
        pose[name]=[list(loc),list(rot),list(scale)]
    poses.append(pose)
    p=lambda n:src.matrix_world@src.pose.bones[n].head
    q=(src.matrix_world@src.pose.bones['hip'].matrix).to_quaternion()@rest['hip'].to_quaternion().inverted()
    fw=q@Vector((0,-1,0));fw.z=0;fw.normalize()
    row={'hip':list(p('hip')),'feet':{},'arm_swing':{}}
    for side in ['l','r']:
        row['feet'][side]={'raw':list(p(side+'_foot'))}
        d=p(side+'_shin')-p(side+'_thigh')
        row['arm_swing'][side]=max(-.32,min(.32,-.65*math.atan2(d.dot(fw),-d.z)))
    rows.append(row)
# Remove the common forward bias of the retargeted thighs from arm swing.
# Walking arms counterbalance one another rather than both staying behind.
opposition=[(r['arm_swing']['l']-r['arm_swing']['r'])*.5 for r in rows]
bias=statistics.median(opposition)
for row,value in zip(rows,opposition):
    row['arm_swing']={'l':value-bias,'r':-value+bias}
for side in ['l','r']:
    points=[Vector(r['feet'][side]['raw']) for r in rows]
    velocity=[(points[min(239,i+1)]-points[max(0,i-1)]).xy.length*12 for i in range(240)]
    flags=[velocity[i]<.24 and points[i].z<.135 for i in range(240)]
    # Remove isolated one-frame labels; preserve the final swing instead of
    # treating a clip-boundary foot as permanently planted.
    for i in range(1,239):
        if flags[i-1]==flags[i+1]:flags[i]=flags[i-1]
    i=0;segments=[]
    while i<240:
        start=i;flag=flags[i]
        while i<240 and flags[i]==flag:i+=1
        segments.append((start,i,flag))
    for start,end,contact in segments:
        anchor=Vector((statistics.median(p.x for p in points[start:end]),statistics.median(p.y for p in points[start:end]),.065))
        for j in range(start,end):
            duration=end-start
            phase=(j-start)/max(1,duration-1)
            if contact and end==240:phase=(j-start)/max(22,duration-1)
            if contact and start==0:phase=(j+max(0,22-duration))/max(22,duration-1)
            goal=points[j].copy()
            if contact:
                goal=anchor.copy()
                pitch=math.radians(-7*max(0,1-phase/.25) + 35*max(0,(phase-.55)/.45))
                # Heel rise is part of toe-off: pinning the ankle to the deck
                # while the body advances was forcing the old pelvis crouch.
                goal.z+=.13*math.sin(max(0,pitch))+.025*math.sin(max(0,-pitch))
            else:
                goal.z=.065+min(.12,max(0,goal.z-.087)*.65)
                pitch=math.radians(10*(1-phase)-6*phase)
            rows[j]['feet'][side].update(goal=list(goal),contact=contact,pitch=pitch,phase=phase)
    # Smooth the transition into/out of anchored support, retaining captured
    # travel and the correctly detected toe-off at the end of the clip.
    for axis in range(3):
        values=smooth([r['feet'][side]['goal'][axis] for r in rows])
        for r,v in zip(rows,values):r['feet'][side]['goal'][axis]=v
    values=smooth([r['arm_swing'][side] for r in rows])
    for r,v in zip(rows,values):r['arm_swing'][side]=v
    # Avoid a 35 -> 10 degree one-frame snap at the toe-off/swing boundary.
    values=smooth([r['feet'][side]['pitch'] for r in rows])
    for r,v in zip(rows,values):r['feet'][side]['pitch']=v
    print('STANCE_SEGMENTS',side,segments,flush=True)
caps=[]
for row in rows:
    hip=Vector(row['hip']);cap=hip.z-.018
    for side in ['l','r']:
        offset=rest[side+'_thigh'].translation-rest['hip'].translation
        # Rotate the lateral hip offset into the current captured heading.
        f=len(caps)+1;s.frame_set(f)
        q=(src.matrix_world@src.pose.bones['hip'].matrix).to_quaternion()@rest['hip'].to_quaternion().inverted()
        h=hip+q@offset;g=Vector(row['feet'][side]['goal'])
        length=(rest[side+'_shin'].translation-rest[side+'_thigh'].translation).length+(rest[side+'_foot'].translation-rest[side+'_shin'].translation).length
        reach=math.sqrt(max(.1,(length*.992)**2-(h.xy-g.xy).length_squared))
        cap=min(cap,g.z+reach-(h.z-hip.z))
    caps.append(cap)
height=smooth(caps,3)
for i,row in enumerate(rows):row['root_z']=min(height[i],caps[i])
(out/'gait-plan.json').write_text(json.dumps(rows))
(out/'rokoko-walk-native-bake.json').write_text(json.dumps({'fps':24,'provenance':'Official Rokoko 1.4.4 retarget of CMU 36_02, before custom foot locks','frames':poses},separators=(',',':')))
src['provenance']='Untouched official Rokoko offline retarget bake; previous contact/root corrections removed'
s.frame_set(1);bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out/'kat-rigify-controls.blend'),compress=True)
print('NATURAL_GAIT_PREPARED',min(height),max(height),flush=True)
