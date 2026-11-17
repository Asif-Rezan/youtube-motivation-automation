"""Render a 30-second jungle workout with the packed Maya rig."""

import math
from pathlib import Path
import sys

import bpy
from mathutils import Quaternion, Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from posed_cloth import PosedWaistband

scene=bpy.context.scene
args=sys.argv[sys.argv.index("--")+1:]
output=Path(args[0])
output.mkdir(parents=True,exist_ok=True)
only={int(x) for x in args[1:]}
rig=next(o for o in bpy.data.objects if o.name.startswith("Maya • reusable"))
camera=bpy.data.objects["Full body"]
scene.camera=camera
camera.location=(-2.45,-5.4,1.23)
camera.rotation_euler=(Vector((0,-.01,.85))-camera.location).to_track_quat("-Z","Y").to_euler()
camera.data.ortho_scale=1.91
bpy.data.objects["Studio backdrop"].hide_render=True
scene.render.film_transparent=True
scene.render.resolution_x=448
scene.render.resolution_y=544
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.render.image_settings.color_mode="RGBA"
scene.render.image_settings.compression=16
scene.eevee.taa_render_samples=6

# Head and mouth actions remain driven by the coaching frames at the start.
# Keep limb lengths and planted ankles independent of body height.
bones=rig.pose.bones
rest=rig.data.bones
identity=Quaternion()
root=bones["root"]
root_rest=root.bone.matrix_local.to_3x3().inverted()

def smooth(x):
    x=max(0.,min(1.,x))
    return x*x*(3.-2.*x)

def point(name):
    return rest[name].head_local.copy()

def align(name, relative):
    bone=bones[name]
    local=bone.bone.matrix_local.to_quaternion()
    bone.rotation_mode="QUATERNION"
    bone.rotation_quaternion=local.inverted()@relative@local

def knee_position(hip,foot,l1,l2,side):
    delta=foot-hip
    direction=delta.normalized()
    dist=min(delta.length,l1+l2-.00001)
    along=(l1*l1-l2*l2+dist*dist)/(2*dist)
    pole=Vector((side*.27,-1.,0))
    outward=(pole-direction*pole.dot(direction)).normalized()
    bend=math.sqrt(max(0.,l1*l1-along*along))
    return hip+direction*along+outward*bend

def squat_at(t):
    if 6<=t<25.5:
        phase=(t-6)%3.9
        return smooth(phase/1.50)*smooth((3.65-phase)/1.62)
    return 0.

def pose(t):
    depth=squat_at(t)
    settle=.011*math.sin(t*1.65)*(1-depth)
    offset=Vector((.003*math.sin(t*1.18),.111*depth,-.216*depth))
    root.location=root_rest@offset
    torso=Quaternion((1,0,0),.30*depth+.012*math.sin(t*1.3))
    align("spine04",torso)
    align("spine02",Quaternion((1,0,0),.015*math.sin(t*1.4)))
    for side,sign in (("L",1),("R",-1)):
        upper=f"upperleg01.{side}"
        lower=f"lowerleg01.{side}"
        foot=f"foot.{side}"
        h,k,a=map(point,(upper,lower,foot))
        knee=knee_position(h+offset,a,(k-h).length,(a-k).length,sign) if depth>.001 else k
        q1=(k-h).rotation_difference(knee-h-offset)
        q2=(a-k).rotation_difference(a-knee)
        align(upper,q1)
        align(lower,q1.inverted()@q2)
        align(foot,q2.inverted())
        shoulder=f"upperarm01.{side}"
        elbow=f"lowerarm01.{side}"
        wrist=f"wrist.{side}"
        sh,el,wr=map(point,(shoulder,elbow,wrist))
        wanted=Vector((sign*(.245+.09*depth),-.055-.88*depth,-.97+.86*depth))
        q_sh=(el-sh).rotation_difference(wanted)
        wanted_lower=Vector((sign*(.12-.10*depth),-.40-.61*depth,-.91+.97*depth+settle))
        q_el=(wr-el).rotation_difference(wanted_lower)
        align(shoulder,torso.inverted()@q_sh)
        align(elbow,q_sh.inverted()@q_el)
        align(wrist,Quaternion((0,1,0),-.03*sign))
    if t>=8:
        neck=bones["head"]
        neck.rotation_mode="XYZ"
        neck.rotation_euler=(-.09*depth,.011*math.sin(t*1.3),.025*math.sin(t*.65))
        ponytail=bones["ponytail"]
        ponytail.rotation_euler=(.07*depth,.023*math.sin(t*2.5),-.062*depth)
    bpy.context.view_layer.update()
    return offset

# During squats, the waistband follows the pelvis. Limit thigh weights at
# its top edge and hide the portions of the socks covered by these leggings.
leggings=next(o for o in bpy.data.objects if o.get("maya_outfit")=="studio-set")
pelvis=leggings.vertex_groups.get("root") or leggings.vertex_groups.new(name="root")
for vertex in leggings.data.vertices:
    z=vertex.co.z
    if .875<z<1.0:
        blend=.93*smooth((z-.875)/.081)
        original=[(g.group,g.weight) for g in vertex.groups]
        for group_id,weight in original:
            leggings.vertex_groups[group_id].add([vertex.index],weight*(1-blend),"REPLACE")
        root_weight=next((w for index,w in original if index==pelvis.index),0.)
        pelvis.add([vertex.index],(1-blend)*root_weight+blend,"REPLACE")
body=next(o for o in bpy.data.objects if o.get("maya_body"))
waist_fit=PosedWaistband(body,leggings)

shoes=next(o for o in bpy.data.objects if o.name.endswith(".shoes05"))
covered=shoes.vertex_groups.new(name="Socks under leggings")
covered.add([v.index for v in shoes.data.vertices if v.co.z>.125],1.,"REPLACE")
mask=shoes.modifiers.new("Hide covered sock cuffs","MASK")
mask.vertex_group=covered.name
mask.invert_vertex_group=True

for index in range(720):
    if (only and index not in only) or (not only and 238<index<612):
        continue
    t=index/24
    scene.frame_set(min(192,index+1))
    shift=pose(t)
    waist_fit.fit(shift)
    if t<6:
        camera.location=(-.67,-5.86,1.51)
        camera.rotation_euler=(Vector((0,-.03,1.44))-camera.location).to_track_quat("-Z","Y").to_euler()
        camera.data.ortho_scale=.88
    else:
        camera.location=(-2.94,-5.14,1.20)
        camera.rotation_euler=(Vector((0,-.01,.864))-camera.location).to_track_quat("-Z","Y").to_euler()
        camera.data.ortho_scale=1.91
    scene.render.filepath=str(output/f"{index:04}.png")
    bpy.ops.render.render(write_still=True)
