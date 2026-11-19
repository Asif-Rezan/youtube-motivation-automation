"""Continuous CMU walk/turn retarget with stance-foot IK and the repaired face.

Input: the packed kat-heel-raise-final.blend. No camera switches or clip splices.
"""
import bpy, math, json, sys
from pathlib import Path
from mathutils import Vector, Quaternion
from bpy_extras.object_utils import world_to_camera_view
sys.path.insert(0,str(Path(__file__).parent))
from rig_repairs import repair_mouth_chain

P=Path('/Users/asif/Documents/fitness-walk-review');P.mkdir(exist_ok=True)
s=bpy.context.scene;a=bpy.data.objects['Genesis9'];body=bpy.data.objects['Genesis9.Shape']
repair_mouth_chain(a,bpy.data.objects['Genesis9Mouth.Shape'])
for o in bpy.data.objects:
    if o.animation_data:o.animation_data_clear()
    keys=getattr(o.data,'shape_keys',None) if o.data else None
    if keys:
        keys.animation_data_clear()
        for k in keys.key_blocks:k.value=.22 if k.name.startswith('MouthSmile') else 0
for b in a.pose.bones:b.matrix_basis.identity();b.rotation_mode='QUATERNION'
root=bpy.data.objects['Workout motion root'];root.location=(0,0,.9);root.rotation_euler=(0,0,0)
bpy.context.view_layer.update()
rest={b.name:a.matrix_world@b.matrix_local for b in a.data.bones}
rp=lambda n:rest[n].translation.copy()
leg=(rp('l_shin')-rp('l_thigh')).length+(rp('l_foot')-rp('l_shin')).length
bpy.ops.preferences.addon_enable(module='io_anim_bvh')
bpy.ops.import_anim.bvh(filepath=str(P/'sources/36_02.bvh'),global_scale=.01,axis_forward='-Z',axis_up='Y',use_fps_scale=False,update_scene_fps=False)
src=bpy.context.object;src.hide_render=True
source_leg=(src.data.bones['LeftLeg'].head_local-src.data.bones['LeftUpLeg'].head_local).length+(src.data.bones['LeftFoot'].head_local-src.data.bones['LeftLeg'].head_local).length
scale=leg/source_leg;N=240;FPS=24;capture=[]
for f in range(N):
    s.frame_set(2+round((.25+f/FPS)*120));bpy.context.view_layer.update()
    capture.append({b.name:{'p':src.matrix_world@b.head,'q':(src.matrix_world@b.matrix).to_quaternion(),
        'restq':(src.matrix_world@b.bone.matrix_local).to_quaternion(),'restp':src.matrix_world@b.bone.head_local} for b in src.pose.bones})
center=Vector(((min(x['Hips']['p'].x for x in capture)+max(x['Hips']['p'].x for x in capture))/2,
               (min(x['Hips']['p'].y for x in capture)+max(x['Hips']['p'].y for x in capture))/2,0))*scale
core=[('hip','Hips'),('pelvis','Hips'),('spine1','LowerBack'),('spine2','Spine'),('spine3','Spine1'),('spine4','Spine1')]
limbs=[]
for side,source in [('l','Left'),('r','Right')]:
    for n,c,sn,sc in [('shoulder','upperarm','Shoulder','Arm'),('upperarm','forearm','Arm','ForeArm'),
        ('forearm','hand','ForeArm','Hand'),('hand','mid1','Hand','HandIndex1'),
        ('thigh','shin','UpLeg','Leg'),('shin','foot','Leg','Foot'),('foot','toes','Foot','ToeBase')]:
        limbs.append((side+'_'+n,side+'_'+c,source+sn,source+sc))
order=['hip','pelvis','spine1','spine2','spine3','spine4','l_shoulder','r_shoulder',
       'l_upperarm','r_upperarm','l_forearm','r_forearm','l_hand','r_hand','neck1','neck2','head',
       'l_thigh','r_thigh','l_shin','r_shin','l_foot','r_foot']
def wp(n):return a.matrix_world@a.pose.bones[n].head
def wq(n):return (a.matrix_world@a.pose.bones[n].matrix).to_quaternion()
def setworld(n,q,pos=None):
    b=a.pose.bones[n];w=q.to_matrix().to_4x4()
    for i in range(3):
        for j in range(3):w[i][j]*=.01
    w.translation=wp(n) if pos is None else pos
    b.matrix=a.matrix_world.inverted()@w;bpy.context.view_layer.update()

# Source toe speed/height detects stance; speed alone would lock the swing apex.
contact={};weights={}
for side,source in [('l','Left'),('r','Right')]:
    pts=[x[source+'ToeBase']['p']*scale for x in capture]
    low=sorted(v.z for v in pts)[round(N*.10)]
    raw=[]
    for i,p in enumerate(pts):
        velocity=(pts[min(N-1,i+1)]-pts[max(0,i-1)])*(FPS/2)
        raw.append(p.z<low+.035 and Vector((velocity.x,velocity.y,0)).length<.22)
    # Fill one-frame holes, then reject tiny spurious contacts.
    flags=raw.copy()
    for i in range(1,N-1):
        if raw[i-1] and raw[i+1]:flags[i]=True
    for i in range(N):
        if flags[i] and sum(flags[max(0,i-2):min(N,i+3)])<3:flags[i]=False
    contact[side]=flags
    weights[side]=[min(1,sum(flags[max(0,i-1):min(N,i+2)])/3) if flags[i] else 0 for i in range(N)]

saved=[];offset=None
for f,x in enumerate(capture,1):
    s.frame_set(f)
    for b in a.pose.bones:
        if not b.constraints:b.matrix_basis.identity()
    bpy.context.view_layer.update();rot={}
    for tn,sn in core:rot[tn]=(x[sn]['q']@x[sn]['restq'].inverted())@rest[tn].to_quaternion()
    for tn,tc,sn,sc in limbs:
        desired=(x[sc]['p']-x[sn]['p']).normalized();sr=(x[sc]['restp']-x[sn]['restp']).normalized();tr=(rp(tc)-rp(tn)).normalized()
        delta=x[sn]['q']@x[sn]['restq'].inverted();swing=sr.rotation_difference(desired);twist=swing.inverted()@delta
        axis,angle=twist.to_axis_angle()
        if angle>math.pi:angle-=math.tau
        angle*=1 if axis.dot(sr)>=0 else -1
        rot[tn]=Quaternion(desired,angle)@tr.rotation_difference(desired)@rest[tn].to_quaternion()
    lateral=x['LeftUpLeg']['p']-x['RightUpLeg']['p'];yaw=math.atan2(lateral.y,lateral.x)
    heading=Quaternion((0,0,1),yaw)
    for name,start,end in [('neck1','Neck','Neck1'),('neck2','Neck1','Head'),('head','Neck1','Head')]:
        direction=(x[end]['p']-x[start]['p']).normalized()
        tilt=Vector((0,0,1)).rotation_difference(direction);axis,angle=tilt.to_axis_angle()
        rot[name]=Quaternion(axis,min(.10,angle))@heading@rest[name].to_quaternion()
    pos=x['Hips']['p']*scale-center
    for name in order:setworld(name,rot[name],pos if name=='hip' else None)
    if offset is None:offset=.020-min(wp(side+'_toes').z for side in ['l','r'])
    pos.z+=offset;setworld('hip',rot['hip'],pos)
    saved.append({'rot':{n:wq(n).copy() for n in order},'hip':wp('hip').copy(),
        'toe':{side:wp(side+'_toes').copy() for side in ['l','r']}})

# Per-stance anchors, rather than a root reset, keep the planted foot in one place.
targets={side:[] for side in ['l','r']}
for side in ['l','r']:
    anchor=None
    for i,pose in enumerate(saved):
        current=pose['toe'][side].copy()
        if contact[side][i]:
            if anchor is None:anchor=current.copy();anchor.z=.020
            goal=current.lerp(anchor,weights[side][i])
        else:anchor=None;goal=current.copy()
        targets[side].append(goal)

def solve_leg(side,goal):
    tn=side+'_thigh';sn=side+'_shin';fn=side+'_foot';toe=side+'_toes'
    H=wp(tn);K=wp(sn);F=wp(fn);toe_offset=wp(toe)-F
    footq=wq(fn);toeq=(a.matrix_world@a.pose.bones[toe].matrix).to_quaternion()
    G=goal-toe_offset;L1=(rp(sn)-rp(tn)).length;L2=(rp(fn)-rp(sn)).length
    direction=G-H;distance=direction.length
    direction.normalize();distance=min(L1+L2-.00001,max(abs(L1-L2)+.00001,distance))
    bend=(K-H)-direction*(K-H).dot(direction)
    if bend.length<1e-5:bend=Vector((0,-1,0))-direction*direction.dot(Vector((0,-1,0)))
    bend.normalize();cosine=max(-1,min(1,(L1*L1+distance*distance-L2*L2)/(2*L1*distance)))
    knee=H+direction*(L1*cosine)+bend*(L1*math.sqrt(max(0,1-cosine*cosine)))
    setworld(tn,(K-H).rotation_difference(knee-H)@wq(tn))
    setworld(sn,(wp(fn)-wp(sn)).rotation_difference(G-wp(sn))@wq(sn))
    setworld(fn,footq);setworld(toe,toeq)

metrics=[];previous={}
for i,pose in enumerate(saved):
    f=i+1;s.frame_set(f)
    for b in a.pose.bones:
        if not b.constraints:b.matrix_basis.identity()
    bpy.context.view_layer.update()
    for name in order:setworld(name,pose['rot'][name],pose['hip'] if name=='hip' else None)
    # Lower the captured pelvis only if a locked ankle would overextend a leg.
    correction=0
    for side in ['l','r']:
        if not contact[side][i]:continue
        H=wp(side+'_thigh');G=targets[side][i]-(wp(side+'_toes')-wp(side+'_foot'))
        length=(rp(side+'_shin')-rp(side+'_thigh')).length+(rp(side+'_foot')-rp(side+'_shin')).length-.0001
        horizontal=Vector((H.x-G.x,H.y-G.y,0)).length
        ceiling=G.z+math.sqrt(max(.00001,length*length-horizontal*horizontal))
        correction=max(correction,H.z-ceiling)
    if correction>0:
        p=wp('hip');p.z-=correction;setworld('hip',wq('hip'),p)
    for side in ['l','r']:solve_leg(side,targets[side][i])
    t=i/FPS;blink=max(math.exp(-((t-v)/.065)**2) for v in [1.9,5.2,8.7])
    for side,suffix in [('l','Left'),('r','Right')]:
        k=body.data.shape_keys.key_blocks['EyeBlink'+suffix];k.value=blink;k.keyframe_insert(data_path='value',frame=f)
        for n,angle in [('eyelidupper',50),('eyelidlower',-6)]:
            b=a.pose.bones[side+'_'+n];b.rotation_quaternion=Quaternion((1,0,0),math.radians(angle)*blink)
            b.keyframe_insert(data_path='rotation_quaternion',frame=f)
    for name in order+['l_toes','r_toes']:
        b=a.pose.bones[name];q=b.rotation_quaternion
        if name in previous and previous[name].dot(q)<0:q.negate()
        previous[name]=q.copy();b.keyframe_insert(data_path='rotation_quaternion',frame=f)
        if name=='hip':b.keyframe_insert(data_path='location',frame=f)
    metrics.append({'frame':f,'hip':list(wp('hip')),'pelvis_reach_correction_m':correction,
        'feet':{side:{'position':list(wp(side+'_toes')),'target':list(targets[side][i]),
            'contact':contact[side][i],'weight':weights[side][i],
            'ik_error_m':(wp(side+'_toes')-targets[side][i]).length} for side in ['l','r']}})
    if f%48==0:print('RETARGET',f,flush=True)

c=s.camera;c.location=(.2,-6,1.65);c.rotation_euler=(Vector((0,0,.85))-c.location).to_track_quat('-Z','Y').to_euler()
c.data.type='ORTHO';c.data.ortho_scale=4.8
s.frame_start=1;s.frame_end=N;s.render.fps=FPS;s.render.engine='BLENDER_EEVEE';s.eevee.taa_render_samples=32
s.render.resolution_x=1920;s.render.resolution_y=1080;s.render.resolution_percentage=100
s.render.film_transparent=True;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA'
for row in metrics:
    s.frame_set(row['frame'])
    for side in ['l','r']:
        v=wp(side+'_toes');uv=world_to_camera_view(s,c,v);row['feet'][side]['pixel']=[uv.x*1920,(1-uv.y)*1080]
(P/'walk-metrics.json').write_text(json.dumps(metrics,indent=2))
s['motion_source']='CMU 36_02: continuous walking, turning and walking back; Bruce Hahne BVH conversion'
s['review_status']='Animation review, not an exercise instruction clip. Stance-foot IK applied.'
s.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(P/'kat-continuous-walk.blend'),compress=True)
if '--render' in sys.argv:
    (P/'frames').mkdir(exist_ok=True);s.render.filepath=str(P/'frames/f-');bpy.ops.render.render(animation=True)
else:
    for f in [1,48,96,144,192,240]:
        s.frame_set(f);s.render.filepath=str(P/f'pose-{f}.png');bpy.ops.render.render(write_still=True)
