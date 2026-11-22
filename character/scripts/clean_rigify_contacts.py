"""Correct native ankle contact through Rigify controls and audit the saved mesh."""
import bpy,json,os,math
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
OUT=Path(os.environ.get('FITNESS_RIGIFY_DIR','/Users/asif/Documents/fitness-rigify-review'))
s=bpy.context.scene;rig=bpy.data.objects['Trainer_Rigify'];a=bpy.data.objects['Genesis9']
src=bpy.data.objects['Rokoko_Baked_Source'];body=bpy.data.objects['Genesis9.Shape']
plan_path=OUT/'gait-plan.json'
plan=json.loads(plan_path.read_text()) if plan_path.exists() else None
ids={side:[v.index for v in body.data.vertices if v.co.y<10 and (v.co.x>0)==(side=='l')] for side in ['l','r']}
def update():bpy.context.view_layer.update()
def soles():
    ob=body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ob.to_mesh()
    result={side:[ob.matrix_world@me.vertices[i].co for i in indices] for side,indices in ids.items()}
    ob.to_mesh_clear();return result
def hull(points):
    points=sorted(set(points))
    def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    halves=[]
    for seq in [points,points[::-1]]:
        half=[]
        for p in seq:
            while len(half)>1 and cross(half[-2],half[-1],p)<=0:half.pop()
            half.append(p)
        halves.append(half[:-1])
    return halves[0]+halves[1]
shadows=[];minimum=1e6;maxerr=0;positions=[]
for f in range(1,241):
    s.frame_set(f);update()
    for _ in range(3):
        for side,suffix in [('l','L'),('r','R')]:
            goal=(Vector(plan[f-1]['feet'][side]['goal']) if plan else
                  src.matrix_world@src.pose.bones[side+'_foot'].head)
            actual=a.matrix_world@a.pose.bones[side+'_foot'].head
            b=rig.pose.bones['foot_ik.'+suffix];m=b.matrix.copy();m.translation+=goal-actual;b.matrix=m;update()
    # Skin movement differs slightly from control movement near full extension.
    # Re-evaluate after each correction instead of assuming a one-to-one response.
    for iteration in range(40):
        verts=soles();lows={side:min(v.z for v in verts[side]) for side in ['l','r']}
        if min(lows.values())>=.0008:break
        for side,suffix in [('l','L'),('r','R')]:
            low=lows[side]
            if low<.001:
                b=rig.pose.bones['foot_ik.'+suffix];m=b.matrix.copy();m.translation.z+=.001-low;b.matrix=m;update()
    for side,suffix in [('l','L'),('r','R')]:
        b=rig.pose.bones['foot_ik.'+suffix]
        for path in ['location','rotation_quaternion']:b.keyframe_insert(data_path=path,frame=f)
    verts=soles();feet={}
    for side in ['l','r']:
        low=min(v.z for v in verts[side]);minimum=min(minimum,low)
        points=[]
        for v in verts[side]:
            if v.z<=low+.003:
                uv=world_to_camera_view(s,s.camera,Vector((v.x,v.y,0)))
                points.append((round(uv.x*1920,3),round((1-uv.y)*1080,3)))
        feet[side]={'height':low,'outline':hull(points)}
        maxerr=max(maxerr,((a.matrix_world@a.pose.bones[side+'_foot'].head)-(src.matrix_world@src.pose.bones[side+'_foot'].head)).length)
    shadows.append(feet);positions.append(a.matrix_world@a.pose.bones['hip'].head)
    if f%60==0:print('CONTACT_FRAME',f,minimum,maxerr,flush=True)
report={'frames':240,'minimum_sole_z_m':minimum,'max_ankle_source_difference_m':maxerr,
        'max_root_step_m':max((b-a).length for a,b in zip(positions,positions[1:])),
        'camera_cuts':0,'note':'Geometry checks, not a certified exercise or full dynamics simulation.'}
(OUT/'contact-shadows.json').write_text(json.dumps(shadows))
(OUT/'rigify-contact-review.json').write_text(json.dumps(report,indent=2))
assert minimum>-.002,report
assert report['max_root_step_m']<.08,report
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from finalize_rigify_animation import finalize
finalize(rig)
s.frame_set(1);rig['review_status']='Foot mesh penetration and root continuity checked; visual sample supplied'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'kat-rigify-final.blend'),compress=True)
print('CONTACT_REVIEW',report,flush=True)
