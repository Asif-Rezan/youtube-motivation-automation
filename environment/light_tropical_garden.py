import bpy,math
from pathlib import Path
from mathutils import Vector
s=bpy.context.scene;out=Path(__file__).resolve().parent
s.view_settings.exposure=.25
bpy.ops.object.light_add(type='AREA',location=(-3,-4,6))
key=bpy.context.object;key.name='Morning warm bounce';key.data.energy=1600;key.data.color=(1,.82,.61);key.data.shape='DISK';key.data.size=4
key.rotation_euler=(Vector((0,1,0))-key.location).to_track_quat('-Z','Y').to_euler()
for o in bpy.data.objects:
 if o.type=='LIGHT' and o.data.type=='SUN':o.data.color=(1,.88,.72);o.data.energy=2.0
s.camera=bpy.data.objects['01 • Full-body front']
bpy.ops.wm.save_as_mainfile(filepath=str(out/'tropical-garden.blend'))
for camera,label in [('01 • Full-body front','front'),('02 • Three-quarter','three-quarter')]:
 s.camera=bpy.data.objects[camera];s.render.filepath=str(out/('tropical-garden-'+label+'.png'));bpy.ops.render.render(write_still=True)
print('Verified cameras:',[o.name for o in bpy.data.objects if o.type=='CAMERA'])
print('Dolly keyframes:',len(bpy.data.objects['03 • Slow dolly'].animation_data.action.layers))
