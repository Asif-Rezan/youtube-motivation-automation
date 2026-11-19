"""Prepare the official retarget for reusable native face and contact cleanup."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector,Quaternion
from bpy_extras.object_utils import world_to_camera_view
sys.path.insert(0,str(Path(__file__).parent))
from rig_repairs import repair_mouth_chain
P=Path('/Users/asif/Documents/fitness-rokoko-review');s=bpy.context.scene;a=bpy.data.objects['Genesis9'];body=bpy.data.objects['Genesis9.Shape']
repair_mouth_chain(a,bpy.data.objects['Genesis9Mouth.Shape'])
for name in ['Rokoko clean Daz proxy','Rokoko source 24fps']:
    obj=bpy.data.objects.get(name)
    if obj:bpy.data.objects.remove(obj,do_unlink=True)
rest_head=(a.matrix_world@a.data.bones['head'].matrix_local).to_quaternion()
poses=[];pitches=[]
for f in range(1,241):
    s.frame_set(f);q=(a.matrix_world@a.pose.bones['head'].matrix).to_quaternion();forward=(q@rest_head.inverted())@Vector((0,-1,0))
    pitches.append(math.asin(max(-1,min(1,-forward.z))));poses.append(q)
correction=max(0,sorted(pitches)[120]-math.radians(5))
old=json.loads(Path('/Users/asif/Documents/fitness-walk-review/walk-metrics.json').read_text());rows=[]
for i,q in enumerate(poses):
    f=i+1;s.frame_set(f);forward=(q@rest_head.inverted())@Vector((0,-1,0));forward.z=0;forward.normalize();right=Vector((0,0,1)).cross(forward).normalized()
    target=Quaternion(right,-correction)@q;b=a.pose.bones['head'];w=target.to_matrix().to_4x4()
    for x in range(3):
        for y in range(3):w[x][y]*=.01
    w.translation=a.matrix_world@b.head;b.matrix=a.matrix_world.inverted()@w;b.keyframe_insert(data_path='rotation_quaternion',frame=f)
    blink=max(math.exp(-((i/24-v)/.065)**2) for v in [1.9,5.2,8.7])
    for side,suffix in [('l','Left'),('r','Right')]:
        for name,angle in [('eyelidupper',50),('eyelidlower',-6)]:
            lid=a.pose.bones[side+'_'+name];lid.rotation_mode='QUATERNION';lid.rotation_quaternion=Quaternion((1,0,0),math.radians(angle)*blink);lid.keyframe_insert(data_path='rotation_quaternion',frame=f)
        key=body.data.shape_keys.key_blocks['EyeBlink'+suffix];key.value=blink;key.keyframe_insert(data_path='value',frame=f)
    feet={}
    for side in ['l','r']:
        pos=a.matrix_world@a.pose.bones[side+'_toes'].head;uv=world_to_camera_view(s,s.camera,pos)
        feet[side]={'position':list(pos),'target':list(pos),'pixel':[uv.x*1920,(1-uv.y)*1080],
            'contact':old[i]['feet'][side]['contact'],'weight':old[i]['feet'][side]['weight'],'sole_z':0}
    rows.append({'frame':f,'hip':list(a.matrix_world@a.pose.bones['hip'].head),'feet':feet})
(P/'walk-metrics.json').write_text(json.dumps(rows,indent=2))
s['gaze_calibration_degrees']=math.degrees(correction)
s.frame_set(1);bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'kat-continuous-walk-final.blend'),compress=True)
print('ROKOKO_NATIVE_READY',math.degrees(correction),flush=True)
