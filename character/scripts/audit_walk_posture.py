"""Regression checks for the hunched neck, frozen trailing foot and hip collapse."""
import bpy,json,os,math
from pathlib import Path
from mathutils import Vector
out=Path(os.environ.get('FITNESS_RIGIFY_DIR','/Users/asif/Documents/fitness-rigify-upright-review'))
s=bpy.context.scene;a=bpy.data.objects['Genesis9']
rest={b.name:a.matrix_world@b.matrix_local for b in a.data.bones}
rows=[]
for f in range(1,241):
    s.frame_set(f);bpy.context.view_layer.update()
    p=lambda n:a.matrix_world@a.pose.bones[n].head
    delta=(a.matrix_world@a.pose.bones['hip'].matrix).to_quaternion()@rest['hip'].to_quaternion().inverted()
    fw=delta@Vector((0,-1,0));fw.z=0;fw.normalize()
    def lean(v):return math.degrees(math.atan2(v.dot(fw),v.z))
    row={'frame':f,'hip_z':p('hip').z,'chest_lean_deg':lean(p('neck1')-p('hip')),
         'neck_lean_deg':lean(p('head')-p('neck1')),'right_ankle':list(p('r_foot')),'arm_swing_deg':{}}
    for side in ['l','r']:
        v=p(side+'_forearm')-p(side+'_upperarm')
        row['arm_swing_deg'][side]=math.degrees(math.atan2(v.dot(fw),-v.z))
    rows.append(row)
report={'minimum_hip_z_m':min(r['hip_z'] for r in rows),'final_hip_z_m':rows[-1]['hip_z'],
    'max_abs_chest_lean_deg':max(abs(r['chest_lean_deg']) for r in rows),
    'max_abs_neck_lean_deg':max(abs(r['neck_lean_deg']) for r in rows),
    'last_trailing_ankle_travel_m':(Vector(rows[-1]['right_ankle'])-Vector(rows[-12]['right_ankle'])).length,
    'arm_swing_ranges_deg':{side:[min(r['arm_swing_deg'][side] for r in rows),max(r['arm_swing_deg'][side] for r in rows)] for side in ['l','r']}}
(out/'posture-review.json').write_text(json.dumps(report,indent=2))
(out/'posture-frames.json').write_text(json.dumps(rows))
assert report['final_hip_z_m']>.87,('Hip collapsed at clip boundary',report)
assert report['max_abs_neck_lean_deg']<10,('Neck hunch returned',report)
assert report['max_abs_chest_lean_deg']<6,('Excessive chest lean',report)
assert report['last_trailing_ankle_travel_m']>.05,('Trailing foot remained frozen',report)
assert all(lo<-3 and hi>3 for lo,hi in report['arm_swing_ranges_deg'].values()),('Arm swing is one-sided',report)
print('POSTURE_REVIEW',report,flush=True)
