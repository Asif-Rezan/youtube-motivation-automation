"""Smooth complete foot paths between captured stance anchors.

Do not abruptly snap an airborne foot down when a noisy contact flag starts.
Captured body and step positions remain; swing clearance and foot roll are planned.
"""
import bpy,json,math,sys,os
from pathlib import Path
from mathutils import Vector,Quaternion
from bpy_extras.object_utils import world_to_camera_view
sys.path.insert(0,str(Path(__file__).parent))
from walk_kinematics import WalkRig
P=Path(os.environ.get('FITNESS_REVIEW_DIR','/Users/asif/Documents/fitness-walk-review'));s=bpy.context.scene;a=bpy.data.objects['Genesis9'];r=WalkRig(a,bpy.data.objects['Genesis9.Shape']);src=bpy.data.objects['36_02']
rows=json.loads((P/'walk-metrics.json').read_text());N=len(rows)
pitch={(v['frame'],v['side']):math.radians(v['sole_pitch_deg']) for v in json.loads((P/'footroll-review.json').read_text())}
def smooth(t):t=max(0,min(1,t));return t*t*t*(10+t*(-15+6*t))
plans={side:[None]*N for side in ['l','r']}
for side in ['l','r']:
    runs=[];i=0
    while i<N:
        state=rows[i]['feet'][side]['contact'];start=i
        while i<N and rows[i]['feet'][side]['contact']==state:i+=1
        end=i;points=[Vector(rows[j]['feet'][side]['target']) for j in range(start,end)]
        anchor=Vector((sorted(p.x for p in points)[len(points)//2],sorted(p.y for p in points)[len(points)//2],0)) if state else None
        runs.append((start,end,state,anchor))
    for index,(start,end,state,anchor) in enumerate(runs):
        previous=runs[index-1][3] if index>0 else Vector(rows[start]['feet'][side]['position'])
        following=runs[index+1][3] if index+1<len(runs) else Vector(rows[end-1]['feet'][side]['position'])
        for j in range(start,end):
            u=(j-start)/max(1,end-start-1)
            xy=anchor.copy() if state else previous.lerp(following,smooth(u))
            clearance=0 if state else .075*math.sin(math.pi*u)**2
            plans[side][j]={'xy':xy,'clearance':clearance,'phase':u,'contact':state}
metrics=[]
for i,row in enumerate(rows):
    f=i+1;s.frame_set(2+round((.25+i/24)*120))
    p=lambda n:src.matrix_world@src.pose.bones[n].head
    forward=(p('LeftUpLeg')-p('RightUpLeg')).cross(Vector((0,0,1))).normalized();poles={}
    for side,name in [('l','Left'),('r','Right')]:
        h=p(name+'UpLeg');k=p(name+'Leg');g=p(name+'Foot');axis=(g-h).normalized();pole=(k-h)-axis*(k-h).dot(axis)
        if pole.length<.002:pole=forward-axis*forward.dot(axis)
        if pole.dot(forward)<0:pole.negate()
        poles[side]=pole.normalized()
    s.frame_set(f)
    goals={}
    for side in ['l','r']:
        fn=side+'_foot';toe=side+'_toes';delta=r.q(fn)@r.rest[fn].to_quaternion().inverted();forward=delta@Vector((0,-1,0));yaw=math.atan2(forward.x,-forward.y)
        heading=Quaternion((0,0,1),yaw);angle=pitch[(f,side)];plan=plans[side][i]
        r.set(fn,heading@Quaternion((1,0,0),angle)@r.rest[fn].to_quaternion())
        toe_angle=0 if angle>0 and plan['contact'] else angle
        if not plan['contact'] and angle>0:toe_angle=angle*smooth(plan['phase']/.25)
        r.set(toe,heading@Quaternion((1,0,0),toe_angle)@r.rest[toe].to_quaternion())
    z=r.soles()
    for side in ['l','r']:
        plan=plans[side][i];goal=r.p(side+'_toes');goal.x=plan['xy'].x;goal.y=plan['xy'].y;goal.z+=.001+plan['clearance']-z[side];goals[side]=goal
    for iteration in range(3):
        for side in ['l','r']:r.solve(side,goals[side],poles[side])
        actual=r.soles()
        for side in ['l','r']:goals[side].z+=.001+plans[side][i]['clearance']-actual[side]
    actual=r.soles()
    for n in ['hip','l_thigh','r_thigh','l_shin','r_shin','l_foot','r_foot','l_toes','r_toes']:
        b=a.pose.bones[n];b.keyframe_insert(data_path='rotation_quaternion',frame=f)
        if n=='hip':b.keyframe_insert(data_path='location',frame=f)
    row['hip']=list(r.p('hip'))
    for side in ['l','r']:
        pos=r.p(side+'_toes');uv=world_to_camera_view(s,s.camera,pos)
        row['feet'][side].update(position=list(pos),pixel=[uv.x*1920,(1-uv.y)*1080],sole_z=actual[side])
    metrics.append({'frame':f,'actual_clearance_m':actual,'planned_clearance_m':{side:plans[side][i]['clearance'] for side in ['l','r']}})
    if f%48==0:print('SMOOTH_CONTACTS',f,flush=True)
assert min(v['actual_clearance_m'][side] for v in metrics for side in ['l','r'])>=-.0005
(P/'planned-contact-review.json').write_text(json.dumps(metrics,indent=2));(P/'walk-metrics.json').write_text(json.dumps(rows,indent=2))
s['foot_path']='Captured step anchors with continuous quintic swing paths, 7.5cm swing clearance, native heel-flat-toe roll and sole geometry ground alignment.'
s.frame_set(1);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(P/'kat-continuous-walk-final.blend'),compress=True)
