"""Relax uncaptured fingers and add restrained, damped hair follow-through."""
import bpy,math,os
from pathlib import Path
from mathutils import Vector
P=Path(os.environ.get('FITNESS_REVIEW_DIR','/Users/asif/Documents/fitness-walk-review'));s=bpy.context.scene;a=bpy.data.objects['Genesis9']
prev=None;lag=Vector();velocity=Vector();dt=1/24
chains=[b for b in a.pose.bones if b.name.startswith(('FrontLeft','FrontRight','BackLeft','BackRight'))]
for f in range(1,241):
    s.frame_set(f);head=(a.matrix_world@a.pose.bones['head'].matrix).to_quaternion()
    if prev is None:drive=Vector()
    else:
        q=prev.rotation_difference(head);axis,angle=q.to_axis_angle()
        if angle>math.pi:angle-=math.tau
        drive=axis*angle/dt
    target=Vector((-drive.x*.08,-drive.y*.05,-drive.z*.07))
    if target.length>.055:target.normalize();target*=.055
    velocity+=(target-lag)*(36*dt)-velocity*(2*.85*6*dt);lag+=velocity*dt
    for i,b in enumerate(chains):
        b.rotation_mode='XYZ';b.rotation_euler=(lag.x*(.5+i%3*.2),lag.y*.3,lag.z*(.5+i%3*.2))
        b.keyframe_insert(data_path='rotation_euler',frame=f)
    for side,sign in [('l',-1),('r',1)]:
        for finger in ['index','mid','ring','pinky']:
            for joint,angle in [(1,.13),(2,.20),(3,.12)]:
                b=a.pose.bones.get(f'{side}_{finger}{joint}')
                if b:
                    b.rotation_mode='XYZ';b.rotation_euler.y=sign*angle
                    b.keyframe_insert(data_path='rotation_euler',frame=f)
    prev=head.copy()
s['secondary_motion']='Damped head-driven hair rig, not strand/cloth simulation. Fingers use a relaxed resting pose.'
s.frame_set(1);bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'kat-continuous-walk-final.blend'),compress=True)
for f in [48,96,192]:
    s.frame_set(f);s.render.filepath=str(P/f'performance-{f}.png');bpy.ops.render.render(write_still=True)
