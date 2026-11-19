"""Keep one continuous front view; an exercise must not appear to teleport."""
import bpy, json, sys
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

out=Path('/Users/asif/Documents/fitness-pilates-review')
s=bpy.context.scene
c=s.camera
a=bpy.data.objects['Genesis9']
c.animation_data_clear()
front=(Vector((.48,-5.7,1.65)),Vector((0,0,.86)))
for frame,view in [(1,front),(288,front)]:
    c.location=view[0]
    c.rotation_euler=(view[1]-c.location).to_track_quat('-Z','Y').to_euler()
    c.keyframe_insert(data_path='location',frame=frame)
    c.keyframe_insert(data_path='rotation_euler',frame=frame)
for layer in c.animation_data.action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in bag.fcurves:
                for key in curve.keyframe_points:key.interpolation='CONSTANT'
review=json.loads((out/'contact-review.json').read_text())
for row in review['frames']:
    s.frame_set(row['frame'])
    for side,contact in zip(['l','r'],row['contacts']):
        pt=a.matrix_world@a.pose.bones[side+'_toes'].head
        uv=world_to_camera_view(s,c,pt)
        contact['pixel']=[uv.x*1920,(1-uv.y)*1080]
review['camera_cut_frame']=None
(out/'contact-review.json').write_text(json.dumps(review,indent=2))
s.frame_start=1;s.frame_end=288
s.render.filepath=str(out/'frames'/'f-')
s.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'kat-heel-raise-final.blend'),compress=True)
if '--quarter' in sys.argv:s.frame_start=133
bpy.ops.render.render(animation=True)
