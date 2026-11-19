"""Release the toes smoothly after push-off and verify continuous stored motion."""
import bpy,json,math,os
from pathlib import Path
from mathutils import Vector,Quaternion
from bpy_extras.object_utils import world_to_camera_view
P=Path(os.environ.get('FITNESS_REVIEW_DIR','/Users/asif/Documents/fitness-walk-review'));s=bpy.context.scene;a=bpy.data.objects['Genesis9'];body=bpy.data.objects['Genesis9.Shape']
rows=json.loads((P/'walk-metrics.json').read_text());angles={(v['frame'],v['side']):math.radians(v['sole_pitch_deg']) for v in json.loads((P/'footroll-review.json').read_text())}
rest={b.name:a.matrix_world@b.matrix_local for b in a.data.bones}
def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
for side in ['l','r']:
    i=0
    while i<240:
        if rows[i]['feet'][side]['contact']:i+=1;continue
        start=i
        while i<240 and not rows[i]['feet'][side]['contact']:i+=1
        for j in range(start,i):
            phase=(j-start)/max(1,i-start-1)
            if phase>=.25:continue
            s.frame_set(j+1);foot=a.pose.bones[side+'_foot'];toe=a.pose.bones[side+'_toes']
            q=(a.matrix_world@foot.matrix).to_quaternion()@rest[side+'_foot'].to_quaternion().inverted()
            forward=q@Vector((0,-1,0));yaw=math.atan2(forward.x,-forward.y)
            angle=angles[(j+1,side)]*smooth(phase/.25)
            target=Quaternion((0,0,1),yaw)@Quaternion((1,0,0),angle)@rest[side+'_toes'].to_quaternion()
            world=target.to_matrix().to_4x4()
            for x in range(3):
                for y in range(3):world[x][y]*=.01
            world.translation=a.matrix_world@toe.head;toe.matrix=a.matrix_world.inverted()@world
            toe.keyframe_insert(data_path='rotation_quaternion',frame=j+1)

# q and -q encode the same orientation, but their interpolation can spin a limb.
curves={}
for layer in a.animation_data.action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for c in bag.fcurves:
                if c.data_path.endswith('rotation_quaternion'):curves.setdefault(c.data_path,{})[c.array_index]=c
flips=0
for channels in curves.values():
    if len(channels)!=4:continue
    keys=[{round(k.co.x,5):k for k in channels[i].keyframe_points} for i in range(4)]
    frames=sorted(set.intersection(*(set(k) for k in keys)));prev=None
    for f in frames:
        q=Quaternion([keys[i][f].co.y for i in range(4)])
        if prev is not None and q.dot(prev)<0:
            q.negate();flips+=1
            for i in range(4):
                k=keys[i][f];k.co.y*=-1;k.handle_left.y*=-1;k.handle_right.y*=-1
        prev=q
    for c in channels.values():c.update()
names=['hip','l_thigh','r_thigh','l_shin','r_shin','l_foot','r_foot','l_toes','r_toes','neck1','neck2','head']
previous={};max_angle={n:0 for n in names};hips=[];min_ground=1e9;deps=bpy.context.evaluated_depsgraph_get()
indices=[v.index for v in body.data.vertices if v.co.y<10]
foot_indices={side:[i for i in indices if (body.data.vertices[i].co.x>0)==(side=='l')] for side in ['l','r']}
shadows=[]
def hull(points):
    points=sorted(set(points))
    def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lower=[];upper=[]
    for point in points:
        while len(lower)>=2 and cross(lower[-2],lower[-1],point)<=0:lower.pop()
        lower.append(point)
    for point in reversed(points):
        while len(upper)>=2 and cross(upper[-2],upper[-1],point)<=0:upper.pop()
        upper.append(point)
    return lower[:-1]+upper[:-1]
for f in range(1,241):
    s.frame_set(f);hips.append(a.matrix_world@a.pose.bones['hip'].head)
    for n in names:
        q=a.pose.bones[n].rotation_quaternion.copy()
        if n in previous:max_angle[n]=max(max_angle[n],math.degrees(2*math.acos(min(1,abs(q.normalized().dot(previous[n].normalized()))))))
        previous[n]=q
    obj=body.evaluated_get(deps);mesh=obj.to_mesh()
    min_ground=min(min_ground,min((obj.matrix_world@mesh.vertices[i].co).z for i in indices))
    feet={}
    for side,ids in foot_indices.items():
        vertices=[obj.matrix_world@mesh.vertices[i].co for i in ids];height=min(v.z for v in vertices);points=[]
        for v in vertices:
            if v.z<=height+.003:
                v.z=0;uv=world_to_camera_view(s,s.camera,v);points.append((round(uv.x*1920,3),round((1-uv.y)*1080,3)))
        feet[side]={'height':height,'outline':hull(points)}
    shadows.append(feet);obj.to_mesh_clear()
report={'frames':240,'fps':24,'camera_cuts':0,'source':'CMU 36_02 captured body; phase-corrected native foot roll',
    'retargeter':s.get('retargeter','Legacy direction-based retarget'),
    'max_root_step_m':max((hips[i]-hips[i-1]).length for i in range(1,240)),
    'max_bone_step_degrees':max_angle,'minimum_sole_z_m':min_ground,'quaternion_sign_repairs':flips}
assert report['max_root_step_m']<.08,'Root jumps between frames'
assert min_ground>=-.0005,'Foot intersects the deck'
(P/'continuity-review.json').write_text(json.dumps(report,indent=2));print(report,flush=True)
(P/'contact-shadows.json').write_text(json.dumps(shadows))
s.frame_set(1);bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'kat-continuous-walk-final.blend'),compress=True)
