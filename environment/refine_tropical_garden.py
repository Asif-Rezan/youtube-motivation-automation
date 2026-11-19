"""Visual corrections after inspecting the initial environment renders."""
import bpy,random,math
from pathlib import Path
from mathutils import Vector
random.seed(602)
s=bpy.context.scene;out=Path(__file__).resolve().parent
# The bed intersected the water plane. Use the garden ground as the submerged bed.
for o in list(bpy.data.objects):
 if o.name.startswith('Dark pond bed'):o.hide_render=True
water=bpy.data.materials['Pond water'].node_tree.nodes.get('Principled BSDF')
water.inputs['Transmission Weight'].default_value=.12;water.inputs['Metallic'].default_value=.35
water.inputs['Roughness'].default_value=.11
for m in bpy.data.materials:
 if m.name.startswith('Leaf green'):
  ramp=next(n for n in m.node_tree.nodes if n.type=='VALTORGB')
  for e in ramp.color_ramp.elements:
   e.color=tuple(c*.28 for c in e.color[:3])+(1,)
for name in ('Warm teak • grain','Weathered pond stone'):
 m=bpy.data.materials[name];r=next(n for n in m.node_tree.nodes if n.type=='VALTORGB')
 for e in r.color_ramp.elements:e.color=tuple(c*.42 for c in e.color[:3])+(1,)
s.view_settings.exposure=-.7
sky=next(n for n in s.world.node_tree.nodes if n.type=='TEX_SKY');sky.sun_disc=False
s.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.24
for o in bpy.data.objects:
 if o.type=='LIGHT' and o.data.type=='SUN':o.data.energy=1.5;o.data.angle=.06
# Replace solid background balls with many individually oriented leaf instances.
mesh=bpy.data.meshes.new('Tropical elliptical leaf instance')
mesh.from_pydata([(0,0,0),(.09,.06,.025),(.25,.075,.02),(.42,0,0),(.25,-.075,.02),(.09,-.06,.025)],[],[(0,1,2,3,4,5)])
mesh.materials.append(bpy.data.materials['Leaf green 0'])
canopies=[o for o in bpy.data.objects if o.name.startswith('Distant lush canopy')]
for canopy in canopies:
 canopy.hide_render=True
 for i in range(180):
  direction=Vector((random.uniform(-1,1),random.uniform(-1,1),random.uniform(-1,1))).normalized()
  pos=canopy.location+Vector(tuple(direction[j]*canopy.scale[j]*random.uniform(.55,1) for j in range(3)))
  o=bpy.data.objects.new('Layered tropical canopy leaf',mesh);s.collection.objects.link(o);o.location=pos;o.rotation_euler=(random.uniform(-.8,.8),random.uniform(-.8,.8),random.uniform(0,math.tau));o.scale=(random.uniform(.9,1.8),)*3
# Dense low fern-like foliage conceals the empty brown garden floor.
for i in range(1500):
 x=random.uniform(-10,10);y=random.uniform(-3,12)
 if abs(x)<2.7 and y<2.2:continue
 if ((x-4.1)/2.9)**2+((y-1.4)/3.4)**2<1:continue
 o=bpy.data.objects.new('Living floor leaf',mesh);s.collection.objects.link(o);o.location=(x,y,.04);o.rotation_euler=(random.uniform(-.6,.6),random.uniform(-.6,.6),random.uniform(0,math.tau));o.scale=(random.uniform(.7,1.6),)*3
# Add a visible, continuous palm frond rachis and widen existing leaflets.
for o in bpy.data.objects:
 if o.name.startswith('Coconut frond leaflet'):
  # Mesh coordinates are world-space, so scale around their first vertex.
  origin=o.data.vertices[0].co.copy()
  for v in o.data.vertices:v.co=origin+(v.co-origin)*1.4
focus=bpy.data.objects.new('Presenter focus • standing height',None);s.collection.objects.link(focus);focus.location=(0,0,1.1)
for o in bpy.data.objects:
 if o.type=='CAMERA':o.data.dof.use_dof=True;o.data.dof.focus_object=focus;o.data.dof.aperture_fstop=6.3
s.cycles.samples=64;s.camera=bpy.data.objects['01 • Full-body front']
bpy.ops.wm.save_as_mainfile(filepath=str(out/'tropical-garden.blend'))
for camera,label in [('01 • Full-body front','front'),('02 • Three-quarter','three-quarter')]:
 s.camera=bpy.data.objects[camera];s.render.filepath=str(out/('tropical-garden-'+label+'.png'));bpy.ops.render.render(write_still=True)
