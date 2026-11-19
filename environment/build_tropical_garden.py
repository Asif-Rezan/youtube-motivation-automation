"""Original reusable tropical yoga environment. Blender 5.3, no external assets."""
import bpy, math, random
from pathlib import Path
from mathutils import Vector

random.seed(48)
OUT=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
s=bpy.context.scene

def material(name,color,rough=.5,noise=0,bump=.08,metal=0):
 m=bpy.data.materials.new(name);m.use_nodes=True
 n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF')
 p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
 if noise:
  t=n.new('ShaderNodeTexNoise');t.inputs['Scale'].default_value=noise;t.inputs['Detail'].default_value=4
  ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(*(c*.45 for c in color),1);ramp.color_ramp.elements[1].color=(*(min(1,c*1.35) for c in color),1)
  l.new(t.outputs['Fac'],ramp.inputs[0]);l.new(ramp.outputs[0],p.inputs['Base Color'])
  b=n.new('ShaderNodeBump');b.inputs['Strength'].default_value=bump;b.inputs['Distance'].default_value=.035;l.new(t.outputs['Fac'],b.inputs['Height']);l.new(b.outputs[0],p.inputs['Normal'])
 return m
wood=material('Warm teak • grain',(.32,.14,.055),.43,5,.25)
# Stretch grain along each board's length.
nodes=wood.node_tree.nodes;links=wood.node_tree.links
coord=nodes.new('ShaderNodeTexCoord');mapping=nodes.new('ShaderNodeVectorMath');mapping.operation='MULTIPLY';mapping.inputs[1].default_value=(2,85,5)
links.new(coord.outputs['Generated'],mapping.inputs[0]);links.new(mapping.outputs[0],next(n for n in nodes if n.type=='TEX_NOISE').inputs['Vector'])
soil=material('Moist earth',(.065,.043,.022),.95,45,.35)
grass=material('Living ground cover',(.095,.18,.035),.9,7,.2)
stone=material('Weathered pond stone',(.22,.235,.20),.85,6,.5)
bark=material('Coconut bark',(.23,.16,.09),.9,17,.4)
banana_stem=material('Banana petiole',(.24,.37,.07),.52,9,.1)
greens=[material('Leaf green '+str(i),c,.48,12,.12) for i,c in enumerate([(.055,.19,.025),(.12,.32,.035),(.20,.40,.055),(.035,.12,.016)])]
petals=[material('Petal '+str(i),c,.4,5,.025) for i,c in enumerate([(.65,.025,.15),(.94,.30,.48),(.93,.72,.26),(.84,.72,.91),(.96,.88,.69)])]
gold=material('Flower stamens',(.95,.48,.035),.48)
water=material('Pond water',(.018,.12,.10),.12)
p=water.node_tree.nodes.get('Principled BSDF');p.inputs['Transmission Weight'].default_value=.85;p.inputs['IOR'].default_value=1.333
n=water.node_tree.nodes;l=water.node_tree.links;t=n.new('ShaderNodeTexNoise');t.inputs['Scale'].default_value=15;t.inputs['Detail'].default_value=2;b=n.new('ShaderNodeBump');b.inputs['Strength'].default_value=.15;b.inputs['Distance'].default_value=.012;l.new(t.outputs['Fac'],b.inputs['Height']);l.new(b.outputs[0],p.inputs['Normal'])

def assign(o,m):o.data.materials.append(m);return o
def cube(name,loc,scale,m,bevel=0):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);assign(o,m)
 if bevel:mod=o.modifiers.new('Soft natural edge','BEVEL');mod.width=bevel;mod.segments=2;o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
 return o
def sphere(name,loc,scale,m,sub=2):
 bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub,radius=1,location=loc);o=bpy.context.object;o.name=name;o.scale=scale;assign(o,m)
 for p in o.data.polygons:p.use_smooth=True
 return o
def rod(name,a,b,r,m,r2=None):
 a,b=Vector(a),Vector(b);d=b-a;bpy.ops.mesh.primitive_cone_add(vertices=12,radius1=r,radius2=r if r2 is None else r2,depth=d.length,location=(a+b)/2);o=bpy.context.object;o.name=name;o.rotation_euler=d.to_track_quat('Z','Y').to_euler();assign(o,m)
 for p in o.data.polygons:p.use_smooth=True
 return o
def leaf(name,start,angle,length,width,lift,mat,split=False):
 # Curved leaf mesh, a folded central vein, and ragged tropical edges.
 st=Vector(start);direction=Vector((math.cos(angle),math.sin(angle),0));side=Vector((-direction.y,direction.x,0));verts=[];faces=[];steps=18
 for i in range(steps+1):
  t=i/steps;center=st+direction*(length*t)+Vector((0,0,lift*math.sin(math.pi*t*.8)-length*.17*t*t))
  w=width*math.sin(math.pi*t)**.7
  if split and i%4==0:w*=.65
  for k in (-1,0,1):verts.append(tuple(center+side*w*k+Vector((0,0,-abs(k)*w*.18))))
 for i in range(steps):
  for j in range(2):a=i*3+j;faces.append((a,a+1,a+4,a+3))
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update();o=bpy.data.objects.new(name,mesh);s.collection.objects.link(o);assign(o,mat)
 for f in mesh.polygons:f.use_smooth=True
 return o

# Clearing and a raised 4.8 x 3.5 metre deck, with individual teak boards.
cube('Garden earth',(0,1,-.20),(40,40,.35),soil)
cube('Deck foundation',(0,0,.02),(4.85,3.55,.24),wood,.035)
for i in range(25):
 y=-1.7+i*.14
 for j in range(3):
  x=-1.6+j*1.6
  cube('Teak plank %02d-%d'%(i,j),(x,y,.17),(1.584,.132,.085),wood,.008)
  for xx in (x-.71,x+.71):sphere('Recessed board pin',(xx,y,.214),(.006,.006,.002),stone,1)
cube('Front step',(0,-1.97,-.005),(2.2,.4,.12),wood,.025)
mat=material('Woven warm ivory yoga mat',(.42,.37,.28),.95,130,.18)
cube('Yoga mat • full-body staging',(0,-.05,.235),(1.1,2.0,.025),mat,.025)

# Lotus pond on the right, below deck level.
cx,cy=4.1,1.4
sphere('Dark pond bed',(cx,cy,-.04),(2.6,3.1,.25),soil,4)
bpy.ops.mesh.primitive_circle_add(vertices=128,radius=1,fill_type='NGON',location=(cx,cy,.025));pond=bpy.context.object;pond.name='Lotus pond • rippled water';pond.scale=(2.45,2.95,1);assign(pond,water)
for i in range(42):
 a=i*math.tau/42;x=cx+2.5*math.cos(a);y=cy+3.0*math.sin(a)
 o=sphere('Pond border rock',(x,y,.01+random.uniform(0,.06)),(random.uniform(.24,.4),random.uniform(.18,.35),random.uniform(.15,.28)),stone,2);o.rotation_euler=(random.random(),random.random(),random.random())
def lotus(x,y,idx):
 bpy.ops.mesh.primitive_circle_add(vertices=40,radius=.31,fill_type='NGON',location=(x,y,.052));o=bpy.context.object;o.name='Floating lotus pad';assign(o,greens[1]);o.scale=(1,.8,1)
 if idx%2==0:
  z=.20;rod('Lotus stem',(x,y,.04),(x,y,z),.008,banana_stem)
  for ring in range(2):
   for j in range(9):
    a=j*math.tau/9+ring*.3
    leaf('Pink lotus petal',(x,y,z+ring*.03),a,.18-ring*.03,.045,.13,petals[1])
  sphere('Lotus golden centre',(x,y,z+.055),(.035,.035,.035),gold)
for i in range(18):lotus(cx+random.uniform(-1.8,1.8),cy+random.uniform(-2.0,2.0),i)

def palm(x,y,h):
 bend=random.uniform(-.4,.4);parts=13
 for j in range(parts):
  z=h*j/parts;xx=x+bend*(j/parts)**2
  rod('Ringed coconut trunk',(xx,y,z),(x+bend*((j+1)/parts)**2,y,h*(j+1)/parts),.13*(1-.3*j/parts),bark,.13*(1-.3*(j+1)/parts))
 crown=(x+bend,y,h)
 for j in range(10):
  angle=j*math.tau/10+random.uniform(-.15,.15);length=random.uniform(1.8,2.6)
  direction=Vector((math.cos(angle),math.sin(angle),0))
  for k in range(1,15):
   t=k/15;start=Vector(crown)+direction*length*t+Vector((0,0,.5*math.sin(math.pi*t)-.7*t*t))
   for sign in (-1,1):leaf('Coconut frond leaflet',start,angle+sign*1.05,.45*(1-t*.65),.045,.06,greens[(j+k)%4])
 for j in range(4):sphere('Coconut',(x+bend+random.uniform(-.2,.2),y+random.uniform(-.2,.2),h-.15),(.13,.13,.17),bark)
for x,y,h in [(-4,1,4.6),(-3.6,5.0,5.2),(3.7,6,5.6),(7,2.3,5.0),(-7,-.4,5.3),(0,8,5.8)]:palm(x,y,h)
def banana(x,y,h):
 rod('Banana pseudostem',(x,y,0),(x+.1,y,h),.11,banana_stem,.065)
 for j in range(7):leaf('Banana broad leaf',(x+.1,y,h-j*.08),j*2.399,random.uniform(1.2,1.8),.29,.45,greens[j%3],True)
for x,y in [(-3.1,2.8),(-4.6,3.6),(-2.3,5),(2.3,5.3),(6.7,4.5),(7,-1.8)]:banana(x,y,random.uniform(1.6,2.5))

def flower(x,y,z,index):
 rod('Flower stem',(x,y,.01),(x,y,z),.008,greens[0])
 for j in range(5):
  a=j*math.tau/5;o=sphere('Tropical flower petal',(x+.065*math.cos(a),y+.065*math.sin(a),z),(.07,.043,.025),petals[index%5],2);o.rotation_euler.z=a
 sphere('Flower pollen',(x,y,z+.018),(.028,.028,.025),gold,2)
for center in [(-2.9,-1),(-3.2,1.2),(2.9,4.6),(6.7,-.4),(-1,4.6)]:
 for i in range(23):
  x=center[0]+random.uniform(-.6,.6);y=center[1]+random.uniform(-.6,.6)
  flower(x,y,random.uniform(.25,.6),i)
  for j in range(3):leaf('Flower bed foliage',(x,y,.1),j*2.4+random.random(),.3,.045,.14,greens[j%3])
# Ground-cover clusters and distant layered foliage; keep the deck free for exercise.
for i in range(210):
 x=random.uniform(-12,12);y=random.uniform(-4,13)
 if abs(x)<2.8 and y<3:continue
 if ((x-cx)/2.9)**2+((y-cy)/3.4)**2<1:continue
 for j in range(4):leaf('Ground foliage',(x,y,0),random.random()*math.tau,random.uniform(.2,.5),.04,.2,greens[j%4])
for i in range(35):
 x=random.uniform(-15,15);y=random.uniform(8,15)
 sphere('Distant lush canopy',(x,y,random.uniform(1.2,3)),(random.uniform(1,2),random.uniform(1,2),random.uniform(1,2)),greens[i%4],3)

world=bpy.data.worlds.new('Tropical morning sky');world.use_nodes=True;s.world=world
nodes=world.node_tree.nodes;links=world.node_tree.links;sky=nodes.new('ShaderNodeTexSky');sky.sky_type='MULTIPLE_SCATTERING';sky.sun_elevation=math.radians(22);sky.sun_rotation=math.radians(125);sky.altitude=.2;sky.air_density=1.1
links.new(sky.outputs[0],nodes.get('Background').inputs['Color']);nodes.get('Background').inputs['Strength'].default_value=.3
bpy.ops.object.light_add(type='SUN',location=(-5,-5,8));sun=bpy.context.object;sun.name='08 AM soft sunlight • leaf shadows';sun.rotation_euler=(math.radians(28),math.radians(-35),math.radians(-35));sun.data.energy=2.2;sun.data.angle=math.radians(3)
bpy.ops.object.light_add(type='AREA',location=(0,-3,4));fill=bpy.context.object;fill.name='Soft sky fill';fill.data.energy=120;fill.data.shape='DISK';fill.data.size=5
def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
aim(fill,(0,0,1))
def camera(name,pos,target,lens):
 bpy.ops.object.camera_add(location=pos);o=bpy.context.object;o.name=name;o.data.lens=lens;aim(o,target);o.data.dof.use_dof=False;return o
front=camera('01 • Full-body front',(0,-8,2.5),(0,.6,1.0),27)
quarter=camera('02 • Three-quarter',(6.6,-7.0,3.2),(0,1.3,1.1),28)
dolly=camera('03 • Slow dolly',(-1.5,-7.7,2.5),(0,.6,1),28)
for frame,pos in [(1,(-1.5,-7.7,2.5)),(241,(1.3,-6.8,2.3))]:
 dolly.location=pos;aim(dolly,(0,.6,1));dolly.keyframe_insert(data_path='location',frame=frame);dolly.keyframe_insert(data_path='rotation_euler',frame=frame)
s.camera=front;s.frame_start=1;s.frame_end=240;s.render.fps=24
s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.use_denoising=True
s.render.resolution_x=1280;s.render.resolution_y=720;s.render.resolution_percentage=100
s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast'
s['environment_spec']='Original procedural 3D tropical garden; teak yoga deck, lotus pond, palms, banana plants, flowers; morning sunlight. No static backdrop image.'
s['license']='Original generated scene geometry and procedural materials; no third-party assets.'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'tropical-garden.blend'))
for cam,name in [(front,'front'),(quarter,'three-quarter')]:
 s.camera=cam;s.render.image_settings.file_format='PNG';s.render.filepath=str(OUT/('tropical-garden-'+name+'.png'));bpy.ops.render.render(write_still=True)
