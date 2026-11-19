"""Use a neutral sole, then heel/flat/toe phases instead of aiming ankle at toe.

BVH and Daz ankle-to-toe bind vectors have different slopes. Aligning those
vectors directly made a captured stance look like standing on pointed toes.
"""
import bpy,json,math,os
from pathlib import Path
from mathutils import Vector,Quaternion
P=Path(os.environ.get('FITNESS_REVIEW_DIR','/Users/asif/Documents/fitness-walk-review'));s=bpy.context.scene;a=bpy.data.objects['Genesis9']
rows=json.loads((P/'walk-metrics.json').read_text());N=len(rows)
rest={b.name:a.matrix_world@b.matrix_local for b in a.data.bones};rp=lambda n:rest[n].translation
def wp(n):return a.matrix_world@a.pose.bones[n].head
def wq(n):return (a.matrix_world@a.pose.bones[n].matrix).to_quaternion()
def setworld(n,q,pos=None):
    b=a.pose.bones[n];w=q.to_matrix().to_4x4()
    for i in range(3):
        for j in range(3):w[i][j]*=.01
    w.translation=wp(n) if pos is None else pos;b.matrix=a.matrix_world.inverted()@w;bpy.context.view_layer.update()
def solve(side,goal):
    tn=side+'_thigh';sn=side+'_shin';fn=side+'_foot';toe=side+'_toes'
    H=wp(tn);K=wp(sn);F=wp(fn);G=goal-(wp(toe)-F);qf=wq(fn);qt=wq(toe)
    l1=(rp(sn)-rp(tn)).length;l2=(rp(fn)-rp(sn)).length;d=(G-H).length;direction=(G-H).normalized()
    bend=(K-H)-direction*(K-H).dot(direction)
    if bend.length<1e-5:bend=Vector((0,-1,0))-direction*direction.dot(Vector((0,-1,0)))
    bend.normalize();d=min(l1+l2-.00001,max(abs(l1-l2)+.00001,d));c=max(-1,min(1,(l1*l1+d*d-l2*l2)/(2*l1*d)))
    knee=H+direction*l1*c+bend*l1*math.sqrt(max(0,1-c*c))
    setworld(tn,(K-H).rotation_difference(knee-H)@wq(tn));setworld(sn,(wp(fn)-wp(sn)).rotation_difference(G-wp(sn))@wq(sn))
    setworld(fn,qf);setworld(toe,qt)
def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
pitch={side:[None]*N for side in ['l','r']};phases={side:['swing']*N for side in ['l','r']}
for side in ['l','r']:
    i=0
    while i<N:
        state=rows[i]['feet'][side]['contact'];start=i
        while i<N and rows[i]['feet'][side]['contact']==state:i+=1
        end=i
        for j in range(start,end):
            p=(j-start)/max(1,end-start-1)
            if state:
                if start==0:p=.4+.6*p
                if end==N:p*=.65
                angle=-8*(1-smooth(p/.22)) if p<.22 else 0 if p<.68 else 18*smooth((p-.68)/.32)
                phases[side][j]='heel strike' if p<.22 else 'flat stance' if p<.68 else 'toe off'
            else:
                angle=18*(1-smooth(p/.45)) if p<.45 else -8*smooth((p-.45)/.55)
            pitch[side][j]=math.radians(angle)
review=[]
for i,row in enumerate(rows):
    f=i+1;s.frame_set(f)
    for side in ['l','r']:
        fn=side+'_foot';toe=side+'_toes';delta=wq(fn)@rest[fn].to_quaternion().inverted()
        forward=delta@Vector((0,-1,0));yaw=math.atan2(forward.x,-forward.y)
        heading=Quaternion((0,0,1),yaw);angle=pitch[side][i]
        goal=wp(toe).copy()
        setworld(fn,heading@Quaternion((1,0,0),angle)@rest[fn].to_quaternion())
        toe_angle=0 if angle>0 and row['feet'][side]['contact'] else angle
        setworld(toe,heading@Quaternion((1,0,0),toe_angle)@rest[toe].to_quaternion())
        # Keep the original planted horizontal position; leg joints absorb bind differences.
        goal.z=wp(toe).z;solve(side,goal)
        review.append({'frame':f,'side':side,'phase':phases[side][i],'sole_pitch_deg':math.degrees(angle)})
    for n in ['l_thigh','r_thigh','l_shin','r_shin','l_foot','r_foot','l_toes','r_toes']:
        a.pose.bones[n].keyframe_insert(data_path='rotation_quaternion',frame=f)
(P/'footroll-review.json').write_text(json.dumps(review,indent=2))
s['foot_roll']='Native neutral sole alignment; contact-phase heel strike, flat stance and toe-off. Captured body motion retained.'
s.frame_set(1);bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'kat-continuous-walk-final.blend'),compress=True)
for f in [36,44,54,60,192]:
    s.frame_set(f);s.render.filepath=str(P/f'footroll-{f}.png');bpy.ops.render.render(write_still=True)
