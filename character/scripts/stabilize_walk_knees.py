"""Use captured knee planes and a smooth reachable pelvis height for foot IK."""
import bpy,json,math,sys,os
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(os.environ.get('FITNESS_REVIEW_DIR','/Users/asif/Documents/fitness-walk-review'));s=bpy.context.scene;a=bpy.data.objects['Genesis9'];src=bpy.data.objects['36_02']
rest={b.name:a.matrix_world@b.matrix_local for b in a.data.bones};rp=lambda n:rest[n].translation
wp=lambda n:a.matrix_world@a.pose.bones[n].head
wq=lambda n:(a.matrix_world@a.pose.bones[n].matrix).to_quaternion()
def setworld(n,q,pos=None):
    w=q.to_matrix().to_4x4()
    for i in range(3):
        for j in range(3):w[i][j]*=.01
    w.translation=wp(n) if pos is None else pos;a.pose.bones[n].matrix=a.matrix_world.inverted()@w;bpy.context.view_layer.update()
cache=[];poles={side:[] for side in ['l','r']}
for f in range(1,241):
    s.frame_set(2+round((.25+(f-1)/24)*120))
    p=lambda n:src.matrix_world@src.pose.bones[n].head
    lateral=p('LeftUpLeg')-p('RightUpLeg');forward=lateral.cross(Vector((0,0,1))).normalized()
    for side,name in [('l','Left'),('r','Right')]:
        h=p(name+'UpLeg');k=p(name+'Leg');ankle=p(name+'Foot');axis=(ankle-h).normalized()
        pole=(k-h)-axis*(k-h).dot(axis)
        if pole.length<.002:pole=forward-axis*forward.dot(axis)
        pole.normalize()
        if pole.dot(forward)<0:pole.negate()
        poles[side].append(pole)
    s.frame_set(f)
    cache.append({'hip':wp('hip').copy(),'hipq':wq('hip'),
        'legs':{side:{'h':wp(side+'_thigh').copy(),'ankle':wp(side+'_foot').copy(),
            'footq':wq(side+'_foot'),'toeq':wq(side+'_toes')} for side in ['l','r']}})
allowed=[]
for row in cache:
    cap=10
    for side,leg in row['legs'].items():
        l1=(rp(side+'_shin')-rp(side+'_thigh')).length;l2=(rp(side+'_foot')-rp(side+'_shin')).length
        h=leg['h'];g=leg['ankle'];horizontal=Vector((h.x-g.x,h.y-g.y,0)).length
        cap=min(cap,g.z+math.sqrt(max(.00001,(l1+l2-.0005)**2-horizontal*horizontal))-(h.z-row['hip'].z))
    allowed.append(cap)
def lowpass(values):
    return [sum(values[min(239,max(0,i+j))]*w for j,w in [(-2,1),(-1,4),(0,6),(1,4),(2,1)])/16 for i in range(240)]
heights=[row['hip'].z for row in cache] if '--orientation-only' in sys.argv else [min(v,cap) for v,cap in zip(lowpass([row['hip'].z for row in cache]),allowed)]
if '--orientation-only' not in sys.argv:
    for _ in range(4):heights=[min(v,smoothed) for v,smoothed in zip(heights,lowpass(heights))]
for side in ['l','r']:
    vectors=poles[side]
    poles[side]=[sum((vectors[min(239,max(0,i+j))]*w for j,w in [(-2,1),(-1,4),(0,6),(1,4),(2,1)]),Vector()).normalized() for i in range(240)]
def anatomical_frame(direction,pole):
    direction=direction.normalized();pole=(pole-direction*pole.dot(direction)).normalized()
    return Matrix((direction,pole,direction.cross(pole))).transposed().to_quaternion()
for i,row in enumerate(cache):
    f=i+1;s.frame_set(f);pos=row['hip'].copy();pos.z=heights[i];setworld('hip',row['hipq'],pos)
    for side,leg in row['legs'].items():
        tn=side+'_thigh';sn=side+'_shin';fn=side+'_foot';toe=side+'_toes';h=wp(tn);k=wp(sn);g=leg['ankle']
        l1=(rp(sn)-rp(tn)).length;l2=(rp(fn)-rp(sn)).length;axis=(g-h).normalized();d=(g-h).length
        pole=poles[side][i];bend=(pole-axis*pole.dot(axis)).normalized()
        c=max(-1,min(1,(l1*l1+d*d-l2*l2)/(2*l1*d)))
        knee=h+axis*l1*c+bend*l1*math.sqrt(max(0,1-c*c))
        # Define both direction and anatomical knee plane; do not accumulate
        # axial twist from successive swing-only quaternion corrections.
        for bone,start,end,target_direction in [(tn,tn,sn,knee-h),(sn,sn,fn,g-knee)]:
            rest_direction=rp(end)-rp(start)
            rotation=anatomical_frame(target_direction,pole)@anatomical_frame(rest_direction,Vector((0,-1,0))).inverted()@rest[bone].to_quaternion()
            setworld(bone,rotation)
        setworld(fn,leg['footq']);setworld(toe,leg['toeq'])
    for n in ['hip','l_thigh','r_thigh','l_shin','r_shin','l_foot','r_foot','l_toes','r_toes']:
        b=a.pose.bones[n];b.keyframe_insert(data_path='rotation_quaternion',frame=f)
        if n=='hip':b.keyframe_insert(data_path='location',frame=f)
s.frame_set(1);bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'kat-continuous-walk-final.blend'),compress=True)
