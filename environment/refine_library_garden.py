import bpy,math,random
from pathlib import Path
from mathutils import Vector
random.seed(19)
s=bpy.context.scene
for o in list(s.objects):
 if o.name.startswith(('Tropical Forest • Plam','Tropical Forest • tree','Tropical flower','Flower stem','Flower pollen')):
  bpy.data.objects.remove(o,do_unlink=True)
# Tropical Forest's correctly oriented broad leaves, palms and ferns remain.
base=next(o for o in s.objects if o.name.startswith('Summer Garden • tall tree'))
for i in range(12):
 o=base.copy();o.data=base.data;s.collection.objects.link(o)
 o.location=(random.uniform(-25,25),random.uniform(25,38),-.1);o.rotation_euler.z=random.uniform(0,6.28);o.scale*=random.uniform(.9,1.4)
s.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.22
for o in s.objects:
 if o.type=='LIGHT':
  if o.data.type=='SUN':o.data.energy=.8;o.data.angle=.12
  else:o.data.energy=250
s.view_settings.exposure=-.65
s.cycles.samples=64
s.render.resolution_x=1920;s.render.resolution_y=1080
s.camera=bpy.data.objects['Full-body front']
out=Path('/Users/asif/Documents/Blender Assets/Yoga Garden')
bpy.ops.wm.save_as_mainfile(filepath=str(out/'library-yoga-garden.blend'),compress=True)
for name,label in [('Full-body front','front'),('Three-quarter','three-quarter')]:
 s.camera=bpy.data.objects[name];s.render.filepath=str(out/(label+'.png'));bpy.ops.render.render(write_still=True)
print('COMPLETE',flush=True)
