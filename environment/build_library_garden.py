"""Compose locally downloaded Royalty Free Blendkit assets; do not redistribute sources."""
import bpy, math, random, json
from pathlib import Path
from mathutils import Vector, Matrix
random.seed(72)
ROOT=Path('/Users/asif/Documents/Blender Assets')
SRC=ROOT/'Garden Sources'
OUT=ROOT/'Yoga Garden'; OUT.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
s=bpy.context.scene
def append(path,names):
 with bpy.data.libraries.load(str(path),link=False) as (a,b): b.objects=[n for n in names if n in a.objects]
 return [o for o in b.objects if o]
def prototype(file,name,label):
 o=append(SRC/file,[name])[0]
 # Bake source transform into geometry, then center the root at ground level.
 m=o.data.copy(); m.transform(o.matrix_world)
 vs=[Vector(v) for v in o.bound_box]; world=[o.matrix_world@v for v in vs]
 lo=Vector(tuple(min(v[i] for v in world) for i in range(3)));hi=Vector(tuple(max(v[i] for v in world) for i in range(3)))
 m.transform(Matrix.Translation(Vector((-(lo.x+hi.x)/2,-(lo.y+hi.y)/2,-lo.z))))
 p=bpy.data.objects.new(label,m)
 bpy.data.objects.remove(o)
 return p,max(.01,hi.z-lo.z)
def place(proto,pos,height,angle=0):
 p,h=proto;o=p.copy();o.data=p.data;s.collection.objects.link(o);o.location=pos;o.scale=(height/h,)*3;o.rotation_euler.z=angle;return o
trees=[prototype('summer-garden.blend','tree.002','Summer Garden • broadleaf'),prototype('summer-garden.blend','tree.010','Summer Garden • tall tree')]
plants=[prototype('tropical-forest.blend',n,'Tropical Forest • '+n) for n in ['lady plam','Elephant_ear','Plam','tree','_Giant_fern']]
for i,(x,y,h) in enumerate([(-6,3,9),(7,5,10),(-7,11,12),(1,14,12),(10,13,11),(-13,8,13),(14,8,14),(-10,20,14),(7,23,16)]):
 place(trees[i%2],(x,y,-.07),h,random.random()*6.28)
for i,(x,y,h) in enumerate([(-3.8,2.5,3.6),(4.8,6,4.5),(-5,6,4.2),(7,-.3,4.5),(-7,-.5,4.4),(-1,8,4.2)]):
 place(plants[2],(x,y,0),h,random.random()*6.28)
for i in range(170):
 x=random.uniform(-13,13);y=random.uniform(-3,17)
 if abs(x)<2.8 and y<3.3:continue
 if ((x-4.1)/3.1)**2+((y-1.4)/3.5)**2<1:continue
 p=plants[[0,1,4,3][i%4]]
 place(p,(x,y,-.03),random.uniform(.6,1.5) if i%4!=3 else random.uniform(2,3.5),random.random()*6.28)
# Reuse only the deck, pond and flower details from our original scene.
original=Path(__file__).parent/'tropical-garden.blend'
with bpy.data.libraries.load(str(original),link=False) as (a,b):
 b.objects=[n for n in a.objects if n.startswith(('Deck foundation','Teak plank','Recessed board pin','Front step','Yoga mat','Lotus pond','Pond border rock','Floating lotus','Pink lotus','Lotus golden','Lotus stem','Tropical flower','Flower stem','Flower pollen'))]
for o in b.objects:
 if o:s.collection.objects.link(o)
ground=bpy.data.materials.new('Garden soil and moss');ground.use_nodes=True
n=ground.node_tree.nodes;l=ground.node_tree.links;p=n.get('Principled BSDF');p.inputs['Roughness'].default_value=.95
t=n.new('ShaderNodeTexNoise');t.inputs['Scale'].default_value=7
r=n.new('ShaderNodeValToRGB');r.color_ramp.elements[0].color=(.025,.032,.009,1);r.color_ramp.elements[1].color=(.13,.19,.035,1)
l.new(t.outputs['Fac'],r.inputs[0]);l.new(r.outputs[0],p.inputs['Base Color'])
bpy.ops.mesh.primitive_plane_add(size=100,location=(0,0,-.08));bpy.context.object.name='Garden ground';bpy.context.object.data.materials.append(ground)
# Genuine low foliage from the summer garden as linked mesh instances.
grass=prototype('summer-garden.blend','Foliage001_2K-JPG_Color.008','Summer Garden • ground foliage')
for i in range(600):
 x=random.uniform(-15,15);y=random.uniform(-5,22)
 if abs(x)<2.7 and -2.5<y<2:continue
 if ((x-4.1)/2.8)**2+((y-1.4)/3.3)**2<1:continue
 place(grass,(x,y,-.07),random.uniform(.15,.3),random.random()*6.28)
world=bpy.data.worlds.new('Soft morning sky');world.use_nodes=True;s.world=world
n=world.node_tree.nodes;l=world.node_tree.links;sky=n.new('ShaderNodeTexSky');sky.sky_type='MULTIPLE_SCATTERING';sky.sun_elevation=math.radians(28);sky.sun_rotation=math.radians(125)
l.new(sky.outputs[0],n.get('Background').inputs['Color']);n.get('Background').inputs['Strength'].default_value=.35
def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.light_add(type='SUN',location=(-4,-5,9));o=bpy.context.object;o.rotation_euler=(math.radians(25),math.radians(-35),math.radians(-30));o.data.energy=2;o.data.angle=.08
bpy.ops.object.light_add(type='AREA',location=(0,-3,6));o=bpy.context.object;o.data.energy=650;o.data.shape='DISK';o.data.size=7;aim(o,(0,0,0))
def camera(name,pos,target,lens):
 bpy.ops.object.camera_add(location=pos);o=bpy.context.object;o.name=name;o.data.lens=lens;aim(o,target);return o
front=camera('Full-body front',(0,-8,2.8),(0,1,1.2),27)
quarter=camera('Three-quarter',(7,-8,3.7),(0,1.5,1.0),30)
dolly=camera('Slow dolly',(-1,-8,2.8),(0,1,1.2),28)
for f,pos in [(1,(-1,-8,2.8)),(240,(1,-7.2,2.6))]:
 dolly.location=pos;aim(dolly,(0,1,1.2));dolly.keyframe_insert(data_path='location',frame=f);dolly.keyframe_insert(data_path='rotation_euler',frame=f)
s.frame_end=240;s.render.fps=24;s.camera=front;s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.use_denoising=True
s.render.resolution_x=1280;s.render.resolution_y=720;s.render.resolution_percentage=100
s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast'
s['sources']='Blendkit Tropical Forest + Summer Garden, Royalty Free; local use only; see source JSON metadata.'
s['staging']='Yoga deck foot level 0.26m. Front, three-quarter and dolly cameras.'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'library-yoga-garden.blend'),compress=True)
for cam,label in [(front,'front'),(quarter,'three-quarter')]:
 s.camera=cam;s.render.filepath=str(OUT/(label+'.png'));bpy.ops.render.render(write_still=True)
print('COMPLETED',flush=True)
