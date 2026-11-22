"""Audit evaluated native joint rotations, not the overridden action channels."""
import bpy,math,json,os
from pathlib import Path
s=bpy.context.scene;a=bpy.data.objects['Genesis9'];rig=bpy.data.objects['Trainer_Rigify']
out=Path(os.environ.get('FITNESS_RIGIFY_DIR','/Users/asif/Documents/fitness-rigify-review'))
names=['hip','head','l_thigh','r_thigh','l_shin','r_shin','l_foot','r_foot']
previous={};maximum={n:0 for n in names}
for frame in range(1,241):
    s.frame_set(frame);bpy.context.view_layer.update()
    for n in names:
        q=(a.matrix_world@a.pose.bones[n].matrix).to_quaternion().normalized()
        if n in previous:maximum[n]=max(maximum[n],math.degrees(2*math.acos(min(1,abs(q.dot(previous[n]))))))
        previous[n]=q
assert max(maximum.values())<90,maximum
if (out/'gait-plan.json').exists():
    assert max(maximum['l_foot'],maximum['r_foot'])<20,('Walking ankle jerk returned',maximum)
assert all(rig.pose.bones['thigh_parent.'+side]['IK_Stretch']==0 for side in ['L','R'])
unpacked=[im.filepath for im in bpy.data.images if im.source=='FILE' and not im.packed_file]
assert not unpacked,unpacked
report={'evaluated_max_rotation_step_degrees':maximum,'packed_file_images':True,
        'stretch_disabled':True,'motion_source_preserved': 'Rokoko_Baked_Source' in bpy.data.objects}
(out/'evaluated-motion-review.json').write_text(json.dumps(report,indent=2))
print('EVALUATED_MOTION_REVIEW',report,flush=True)
