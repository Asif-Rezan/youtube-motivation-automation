"""Build a bright, six-second Blender storybook tidal marsh. Run with Blender -b -t 8 --python."""
import json
import math
import os
from pathlib import Path
from random import Random

import bpy
from mathutils import Vector

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
rng = Random(38)
settings = json.loads(os.environ['WILDLIFE_BLENDER_SHOT'])
frames = Path(settings['output'])
frame_end = settings.get('frames', 1)
thumbnail = settings.get('thumbnail')
water_start = -.05 + .35 * settings['start']
water_end = -.05 + .35 * settings['end']
shot = settings.get('shot', 0)
take_flight = water_end - water_start >= .03 or thumbnail == 'wide'
frames.mkdir(parents=True, exist_ok=True)


def material(name, color, roughness=.5):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Roughness'].default_value = roughness
    return mat


def texture(mat, scale, colors, distance):
    tree = mat.node_tree
    shader = tree.nodes.get('Principled BSDF')
    noise = tree.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = scale
    noise.inputs['Detail'].default_value = 3
    ramp = tree.nodes.new('ShaderNodeValToRGB')
    for element, color in zip(ramp.color_ramp.elements, colors):
        element.color = (*color, 1)
    bump = tree.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = .38
    bump.inputs['Distance'].default_value = distance
    tree.links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
    tree.links.new(ramp.outputs['Color'], shader.inputs['Base Color'])
    tree.links.new(noise.outputs['Fac'], bump.inputs['Height'])
    tree.links.new(bump.outputs['Normal'], shader.inputs['Normal'])
    return noise


def mesh(name, vertices, faces, mat):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def ellipsoid(name, center, scale, mat, parent=None, angle=0):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12)
    obj = bpy.context.object
    obj.name = name
    obj.parent = parent
    obj.location = center
    obj.scale = scale
    obj.rotation_euler.y = angle
    obj.data.materials.append(mat)
    for face in obj.data.polygons:
        face.use_smooth = True
    return obj


def limb(name, start, end, radius, mat, parent):
    axis = Vector(end) - Vector(start)
    bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=radius, depth=axis.length)
    obj = bpy.context.object
    obj.name, obj.parent = name, parent
    obj.location = (Vector(start) + Vector(end)) / 2
    obj.rotation_euler = axis.to_track_quat('Z', 'Y').to_euler()
    obj.data.materials.append(mat)
    return obj


def empty(name, parent=None):
    obj = bpy.data.objects.new(name, None)
    scene.collection.objects.link(obj)
    obj.parent = parent
    return obj


def key(obj, field, frame, value):
    setattr(obj, field, value)
    obj.keyframe_insert(data_path=field, frame=frame)


mud = material('Wet sand', (.55,.31,.095), .70)
texture(mud, 36, ((.49,.245,.046), (.93,.56,.16)), .085)
reed_colors = [material('Cordgrass ' + str(i), rgb, .85) for i, rgb in enumerate(
    ((.05,.29,.059), (.09,.42,.07), (.22,.56,.083), (.47,.64,.115)))]
water = material('Tidal water', (.013,.35,.47), .26)
noise = texture(water, 62, ((.008,.31,.32),(.026,.57,.49)), .12)
noise.inputs['Roughness'].default_value = .52
noise.noise_dimensions = '4D'
for frame, value in ((1,0), (max(2, frame_end),max(1,frame_end/36))):
    noise.inputs['W'].default_value = value
    noise.inputs['W'].keyframe_insert(data_path='default_value', frame=frame)

def elevation(x, y):
    bank = 1.4 - .19*y - .16*x + .32*math.sin(x*.52 + y*.3)
    return -1.1 + 1.8 / (1 + math.exp(-max(-50,min(50,bank))))

n = 89
vertices = [(x, y, elevation(x,y)) for y in [(-12+j*.64) for j in range(n)]
            for x in [(-25+i*.58) for i in range(n)]]
faces = [(j*n+i, j*n+i+1, (j+1)*n+i+1, (j+1)*n+i) for j in range(n-1) for i in range(n-1)]
land = mesh('Tidal mudflat', vertices, faces, mud)
for face in land.data.polygons:
    face.use_smooth = True
ocean = mesh('Rising tide', [(-100,-100,0),(100,-100,0),(100,100,0),(-100,100,0)], [(0,1,2,3)],water)
for frame, level in ((1,water_start),(max(2,frame_end),water_end)):
    key(ocean,'location',frame,(0,0,level))

for mat in reed_colors:
    verts, quads = [], []
    for _ in range(1050):
        x,y = rng.uniform(-14,12),rng.uniform(-3,24)
        z = elevation(x,y)
        if z < .05 or (.1 < x < 5 and y < 3) or math.sin(x*1.4)*math.cos(y*.62) < -.32:
            continue
        height, lean, width = rng.uniform(.26,.92),rng.uniform(-.22,.35),rng.uniform(.014,.04)
        offset = len(verts)
        verts.extend(((x-width,y,z),(x+width,y,z),(x+lean,y+.16,z+height),
                      (x,y-width,z),(x,y+width,z)))
        quads.extend(((offset,offset+1,offset+2),(offset+3,offset+4,offset+2)))
    mesh('Marsh grasses', verts, quads, mat)

hill_mat = material('Distant headlands', (.07,.39,.20), .85)
for i in range(10):
    ellipsoid('Distant headland', (i*9-37,65+rng.uniform(0,14),-.2),
              (rng.uniform(6,12),5,rng.uniform(.7,2.5)),hill_mat)

# Soft cloud clusters and small flowers give the frame an illustrated depth.
cloud = material('Warm white cloud', (.89,.94,1), .93)
cloud_shader = cloud.node_tree.nodes.get('Principled BSDF')
cloud_shader.inputs['Emission Color'].default_value = (.78,.87,1,1)
cloud_shader.inputs['Emission Strength'].default_value = .18
for x,y,z,scale in ((-18,69,8,1.35),(3,72,11,1.0),(23,64,7,1.24)):
    for dx,dz,rx,rz in ((-3,0,3.1,.78),(-.7,.55,2.4,1.38),(1.8,.35,2.2,1.05),(4,0,2.7,.69)):
        ellipsoid('Cloud puff',(x+dx*scale,y,z+dz*scale),(rx*scale,1.7,rz*scale),cloud)

petals = [
    material('Coral blossom', (.91,.105,.22), .76),
    material('Golden blossom', (.98,.52,.042), .74),
    material('Lavender blossom', (.45,.19,.76), .76),
]
pollen = material('Golden pollen', (1,.67,.10), .7)
flowers = Random(31)
for i in range(34):
    x,y = flowers.uniform(-4.6,5.8), flowers.uniform(-3.8,3.6)
    z = elevation(x,y)
    if z < .22 or (1<x<4.2 and y>1.2):
        continue
    height = flowers.uniform(.12,.29)
    limb('Flower stem',(x,y,z),(x+.05,y,z+height),.012,reed_colors[1],None)
    center = Vector((x+.05,y,z+height))
    for k in range(5):
        angle = k * math.tau / 5
        offset = Vector((.046*math.cos(angle),.046*math.sin(angle),0))
        ellipsoid('Flower petal',center+offset,(.040,.036,.026),petals[i%3])
    ellipsoid('Flower center',center+Vector((0,0,.019)),(.028,.028,.022),pollen)

glint = material('Sea glass glint', (.22,.76,.77), .24)
shader = glint.node_tree.nodes.get('Principled BSDF')
shader.inputs['Emission Color'].default_value = (.15,.69,.71,1)
shader.inputs['Emission Strength'].default_value = .18
ripples = Random(91)
verts, strips = [], []
for i in range(145):
    x,y = ripples.uniform(-20,25),ripples.uniform(-2,44)
    length = ripples.uniform(.17,1.15)
    index = len(verts)
    verts.extend([(x,y,.003),(x+length*.32,y+.031,.003),
                  (x+length,y+.019,.003),(x+length*.61,y-.017,.003)])
    strips.append(tuple(index+k for k in range(4)))
mesh('Tidal ripples',verts,strips,glint).parent = ocean

white = material('Ivory feathers', (.93,.87,.64), .64)
slate = material('Slate feathers', (.044,.17,.24), .59)
black = material('Eye and bill', (.025,.027,.024), .34)
legs = material('Wader legs', (.68,.29,.06), .54)


def wader(index, x, y, size, takeoff):
    root = empty(f'Shorebird {index}')
    root.scale = (size,)*3
    root.rotation_euler.z = .35 + index*.17
    ground = elevation(x,y)
    ellipsoid('Breast', (0,0,.56),(.40,.21,.24),white,root)
    ellipsoid('Tail', (-.32,0,.57),(.28,.10,.081),slate,root)
    head = empty('Head and bill', root)
    head.location = (.23,0,.61)
    ellipsoid('Neck', (.05,0,.11),(.12,.11,.19),white,head,angle=.40)
    ellipsoid('Head', (.16,0,.24),(.15,.13,.13),white,head)
    for side in (-1,1):
        ellipsoid('Eye', (.205,side*.106,.273),(.025,.023,.023),black,head)
        limb('Leg', (0,side*.093,.47),(.06,side*.106,.18),.019,legs,root)
        limb('Ankle', (.06,side*.106,.18),(.03,side*.12,.028),.014,legs,root)
        limb('Toe', (.03,side*.12,.029),(.16,side*.12,.025),.01,legs,root)
    mesh_bill = mesh('Pointed bill',[(.23,-.045,.245),(.23,.045,.245),(.23,0,.20),(.62,0,.181)],
                     [(0,1,3),(1,2,3),(2,0,3),(0,2,1)],black)
    mesh_bill.parent = head
    for side in (-1,1):
        joint = empty('Wing joint',root)
        joint.location = (.05,side*.13,.64)
        wing = mesh('Wing',[(.12,0,0),(-.29,0,0),(-.44,side*.72,-.025),
                            (-.26,side*1.08,-.07),(-.07,side*.59,.01)],
                    [(0,1,2,3,4)],slate)
        wing.parent = joint
        modifier = wing.modifiers.new('Feather thickness','SOLIDIFY')
        modifier.thickness = .035
        ellipsoid('Folded feathers', (-.075,side*.16,.60),(.31,.094,.10),slate,root)
        key(wing,'scale',1,(1,.13,1))
        key(wing,'scale',takeoff-5,(1,.13,1))
        if take_flight:
            key(wing,'scale',takeoff+2,(1,1,1))
        key(joint,'rotation_euler',1,(0,0,0))
        key(joint,'rotation_euler',takeoff-5,(0,0,0))
        for f in range(takeoff,frame_end+1,4) if take_flight else ():
            key(joint,'rotation_euler',f,(side*.74*math.cos((f-takeoff)*math.pi/4),0,0))
    for f in range(1,takeoff-4 if take_flight else frame_end+1,7):
        key(head,'rotation_euler',f,(0,.76 if (f//7+index)%3==1 else 0,0))
    if take_flight:
        key(head,'rotation_euler',takeoff,(0,0,0))
        positions = ((1,(x,y,ground)),(takeoff-5,(x+.24,y,ground)),
                     (takeoff+10,(x+1.34,y+.75,ground+.88)),
                     (max(takeoff+11, frame_end),(x+10,y+7,ground+3.0)))
    else:
        positions = ((1,(x,y,ground)),(max(2,frame_end),(x+.22,y+.1,ground)))
    for f, position in positions:
        key(root,'location',f,position)


takeoff = 13 if thumbnail else max(13, min(42, frame_end//3))
bird_count = 3 if settings['end'] < .8 or thumbnail else 2
for index in range(bird_count):
    x = (1.6, 3.4, 4.4)[index] + (shot%3-1)*.15
    y = (1.8, 3.15, 4.1)[index] + (shot%5-2)*.18
    wader(index,x,y,(1.16,.89,.81)[index],takeoff+index*6)

scene.world = bpy.data.worlds.new('Estuary sky')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.16,.58,1,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value = .88
bpy.ops.object.light_add(type='SUN',location=(-6,-4,8))
sun = bpy.context.object
sun.rotation_euler = (.61,-.67,-.90)
sun.data.energy = 2.15
sun.data.color = (1,.91,.73)
sun.data.angle = .16
bpy.ops.object.light_add(type='AREA', location=(1,-6,5))
fill = bpy.context.object
fill.data.energy = 850
fill.data.shape = 'DISK'
fill.data.size = 8
fill.data.color = (1,.94,.83)
fill.rotation_euler = (Vector((2,2,.5))-fill.location).to_track_quat('-Z','Y').to_euler()

bpy.ops.object.camera_add()
camera = bpy.context.object
camera.data.clip_end = 270
scene.camera = camera
views = {
    'shore': ((3.9,-8.7,2.45),(2.1,3.4,.67),38),
    'pasture': ((.4,-5.9,1.85),(2.1,3.1,.7),35),
    'aerial': ((7.6,-9,7.25),(2.5,9.4,.35),38),
}
if thumbnail == 'close':
    position, target, lens = (3.0,-2.85,1.65),(2.55,2.85,1.13),34
elif thumbnail == 'wide':
    position, target, lens = views['aerial']
else:
    position, target, lens = views[settings['camera']]
camera.data.lens = lens
for frame, offset in ((1,0),(max(2,frame_end),1)):
    location = Vector(position) + Vector((-offset*.85,offset*.6,offset*.11))
    focus = Vector(target) + Vector((offset*1.2,offset*.8,offset*.18))
    key(camera,'location',frame,location)
    key(camera,'rotation_euler',frame,(focus-location).to_track_quat('-Z','Y').to_euler())

scene.render.engine = os.environ.get('WILDLIFE_BLENDER_ENGINE','CYCLES')
if scene.render.engine == 'CYCLES':
    scene.cycles.samples = 6 if thumbnail else 3
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 2
    scene.cycles.diffuse_bounces = 1
    scene.cycles.glossy_bounces = 1
else:
    scene.eevee.taa_render_samples = 24
scene.view_settings.view_transform = 'Standard'
scene.view_settings.look = 'None'
scene.render.resolution_x = 960 if thumbnail else 640
scene.render.resolution_y = 1080 if thumbnail else 360
scene.render.fps = 12
scene.frame_start = 1
scene.frame_end = frame_end
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
if thumbnail:
    scene.frame_set(31 if thumbnail == 'wide' else 18)
    scene.render.filepath = str(frames/'plate.png')
    bpy.ops.render.render(write_still=True)
else:
    scene.render.filepath = str(frames) + '/'
    bpy.ops.render.render(animation=True)
