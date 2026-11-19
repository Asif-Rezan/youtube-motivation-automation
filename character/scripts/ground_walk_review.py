"""Align the actual sole geometry to the deck, preserving captured foot roll."""
import bpy,json,math,os
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
P=Path(os.environ.get('FITNESS_REVIEW_DIR','/Users/asif/Documents/fitness-walk-review'));s=bpy.context.scene;a=bpy.data.objects['Genesis9'];body=bpy.data.objects['Genesis9.Shape']
s.camera.data.ortho_scale=4.2
rows=json.loads((P/'walk-metrics.json').read_text());deps=bpy.context.evaluated_depsgraph_get()
rest={b.name:a.matrix_world@b.matrix_local for b in a.data.bones};rp=lambda n:rest[n].translation
def wp(n):return a.matrix_world@a.pose.bones[n].head
def wq(n):return (a.matrix_world@a.pose.bones[n].matrix).to_quaternion()
def setworld(n,q,pos=None):
    b=a.pose.bones[n];w=q.to_matrix().to_4x4()
    for i in range(3):
        for j in range(3):w[i][j]*=.01
    w.translation=wp(n) if pos is None else pos;b.matrix=a.matrix_world.inverted()@w;bpy.context.view_layer.update()
indices={side:[v.index for v in body.data.vertices if v.co.y<10 and (v.co.x>0)==(side=='l')] for side in ['l','r']}
def soles():
    obj=body.evaluated_get(deps);mesh=obj.to_mesh()
    result={side:min((obj.matrix_world@mesh.vertices[i].co).z for i in ids) for side,ids in indices.items()}
    obj.to_mesh_clear();return result
def solve(side,goal):
    tn=side+'_thigh';sn=side+'_shin';fn=side+'_foot';toe=side+'_toes'
    H=wp(tn);K=wp(sn);F=wp(fn);G=goal-(wp(toe)-F);qf=wq(fn);qt=wq(toe)
    l1=(rp(sn)-rp(tn)).length;l2=(rp(fn)-rp(sn)).length;d=(G-H).length;direction=(G-H).normalized()
    if d>l1+l2-.0001:
        horizontal=Vector((G.x-H.x,G.y-H.y,0)).length
        down=H.z-G.z-math.sqrt(max(.00001,(l1+l2-.0001)**2-horizontal**2))
        if down>0:
            pos=wp('hip');pos.z-=down;setworld('hip',wq('hip'),pos);H=wp(tn);K=wp(sn);F=wp(fn);d=(G-H).length;direction=(G-H).normalized()
    bend=(K-H)-direction*(K-H).dot(direction)
    if bend.length<1e-5:bend=Vector((0,-1,0))-direction*direction.dot(Vector((0,-1,0)))
    bend.normalize();d=min(l1+l2-.00001,max(abs(l1-l2)+.00001,d));c=max(-1,min(1,(l1*l1+d*d-l2*l2)/(2*l1*d)))
    knee=H+direction*l1*c+bend*l1*math.sqrt(max(0,1-c*c))
    setworld(tn,(K-H).rotation_difference(knee-H)@wq(tn))
    setworld(sn,(wp(fn)-wp(sn)).rotation_difference(G-wp(sn))@wq(sn))
    setworld(fn,qf);setworld(toe,qt)

qa=[]
for row in rows:
    f=row['frame'];s.frame_set(f);goals={side:wp(side+'_toes').copy() for side in ['l','r']}
    before=soles()
    for iteration in range(3):
        z=soles()
        changed=False
        for side in ['l','r']:
            if row['feet'][side]['contact'] or z[side]<.001:
                delta=.001-z[side]
                if abs(delta)>.0001:
                    goals[side].z+=delta;solve(side,goals[side]);changed=True
        if not changed:break
    after=soles()
    for n in ['hip','l_thigh','r_thigh','l_shin','r_shin','l_foot','r_foot','l_toes','r_toes']:
        b=a.pose.bones[n];b.keyframe_insert(data_path='rotation_quaternion',frame=f)
        if n=='hip':b.keyframe_insert(data_path='location',frame=f)
    row['hip']=list(wp('hip'))
    for side in ['l','r']:
        pos=wp(side+'_toes');uv=world_to_camera_view(s,s.camera,pos)
        row['feet'][side].update(position=list(pos),pixel=[uv.x*1920,(1-uv.y)*1080],sole_z=after[side])
    qa.append({'frame':f,'before':before,'after':after})
    if f%48==0:print('GROUNDED',f,flush=True)
minimum=min(v['after'][side] for v in qa for side in ['l','r'])
print('FINAL_MIN_SOLE_Z_M',minimum,flush=True)
assert minimum>=-.0005,'Walking foot still penetrates the ground'
(P/'ground-review.json').write_text(json.dumps(qa,indent=2));(P/'walk-metrics.json').write_text(json.dumps(rows,indent=2))
s.frame_set(1);bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'kat-continuous-walk-final.blend'),compress=True)
for f in [1,48,96,144,192,240]:
    s.frame_set(f);s.render.filepath=str(P/f'grounded-{f}.png');bpy.ops.render.render(write_still=True)
