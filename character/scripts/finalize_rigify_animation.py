"""Keep dense Rigify mocap keys continuous between captured samples."""
import bpy

def finalize(rig):
    # Dense mocap keys should interpolate continuously, without q/-q spin or
    # Bezier overshoot between the contact-corrected samples.
    action=rig.animation_data.action
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                groups={}
                for curve in bag.fcurves:
                    for point in curve.keyframe_points:point.interpolation='LINEAR'
                    if curve.data_path.endswith('rotation_quaternion'):
                        groups.setdefault(curve.data_path,{})[curve.array_index]=curve
                for channels in groups.values():
                    if len(channels)!=4:continue
                    points=[{round(k.co.x,5):k for k in channels[i].keyframe_points} for i in range(4)]
                    previous=None
                    for frame in sorted(set.intersection(*(set(row) for row in points))):
                        values=[points[i][frame].co.y for i in range(4)]
                        if previous is not None and sum(a*b for a,b in zip(previous,values))<0:
                            values=[-v for v in values]
                            for i in range(4):points[i][frame].co.y=values[i]
                        previous=values
                    for curve in channels.values():curve.update()

if __name__ == "__main__":
    from pathlib import Path
    finalize(bpy.data.objects["Trainer_Rigify"])
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,compress=True)
