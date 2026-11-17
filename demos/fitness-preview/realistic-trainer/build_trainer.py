"""Build an original Blender trainer from the CC0 MakeHuman core assets.

blender -b -P build_trainer.py -- /path/to/mpfb/src /path/to/system/assets
"""
from pathlib import Path
import json
from math import exp, sin, pi
from bisect import bisect_right
import sys

import bpy
from mathutils import Quaternion, Vector

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from wardrobe import PALETTES, OUTFITS, HAIR_STYLES, OUTFIT_PROXIES, set_appearance
from refine_waistband import fit_waistband, hide_covered_waist
module_dir,asset_dir=map(Path,sys.argv[sys.argv.index("--")+1:])
sys.path.insert(0,str(module_dir))
import mpfb

bpy.ops.wm.read_factory_settings(use_empty=True)
extension_path=bpy.utils.extension_path_user
local_path=asset_dir.parent/"blender-user-data"
local_path.mkdir(exist_ok=True)
bpy.utils.extension_path_user=lambda package,*args,**kwargs: str(local_path) if package=="mpfb" else extension_path(package,*args,**kwargs)
try:
    bpy.context.preferences.addons.new().module="mpfb"
    mpfb.register()
finally:
    bpy.utils.extension_path_user=extension_path
from mpfb.services.humanservice import HumanService
from mpfb.services.targetservice import TargetService
from mpfb.entities.objectproperties import HumanObjectProperties

human=HumanService.create_human()
human.name="Maya • adult trainer"
human["maya_body"]=True
for name,value in {"gender":0.0,"age":.5,"caucasian":1.0,"asian":0.,"african":0.,
                   "muscle":.46,"weight":.49,"height":.54,"cupsize":.63,"firmness":.70}.items():
    HumanObjectProperties.set_value(name,value,entity_reference=human)
TargetService.reapply_macro_details(human)
targets=module_dir/"mpfb/data/targets"
for name,amount in (("breast-volume-vert-up",.30),("breast-trans-up",.22),("breast-dist-decr",.09),("breast-point-decr",.25)):
    TargetService.load_target(human,str(targets/"breast"/(name+".target.gz")),weight=amount)
for region,name,amount in (
    ("chin","chin-width-decr",.17),
    ("chin","chin-height-decr",.12),
    ("cheek","l-cheek-volume-incr",.15),
    ("cheek","r-cheek-volume-incr",.15),
    ("nose","nose-nostrils-width-decr",.10),
    ("eyes","l-eye-scale-incr",.11),
    ("eyes","r-eye-scale-incr",.11),
    ("mouth","mouth-upperlip-volume-incr",.15),
    ("mouth","mouth-lowerlip-volume-incr",.10),
    ("mouth","mouth-cupidsbow-width-decr",.07),
):
    TargetService.load_target(human,str(targets/region/(name+".target.gz")),weight=amount)
for region,name,amount in (
    ("torso","torso-scale-horiz-decr",.22),
    ("neck","neck-scale-horiz-decr",.17),
    ("hip","hip-scale-horiz-incr",.35),
    ("hip","hip-scale-depth-incr",.20),
    ("stomach","stomach-tone-decr",.12),
):
    TargetService.load_target(human,str(targets/region/(name+".target.gz")),weight=amount)
for side in ("l","r"):
    for region,name,amount in (
        ("arms","upperarm-scale-horiz-decr",.24),
        ("arms","upperarm-scale-depth-decr",.20),
        ("arms","lowerarm-scale-horiz-decr",.15),
        ("legs","upperleg-scale-horiz-incr",.15),
        ("legs","upperleg-scale-depth-incr",.13),
    ):
        TargetService.load_target(human,str(targets/region/(side+"-"+name+".target.gz")),weight=amount)

# Keep the waist transition gradual. Apply before fitting the clothes so
# their own geometry follows the revised proportions.
body_contour=human.shape_key_add(name="Trainer waist and upper torso contour",from_mix=False)
for v,base in zip(body_contour.data,human.data.shape_keys.key_blocks["Basis"].data):
    x,y,z=base.co
    inside=1.-min(1.,max(0.,(abs(x)-.15)/.075))
    waist=exp(-((z-1.04)/.089)**2)
    shoulder=exp(-((z-1.323)/.081)**2)*exp(-((abs(x)-.166)/.083)**2)
    v.co.x-=x*(.061*waist*inside+.039*shoulder)
body_contour.value=1.
rig=HumanService.add_builtin_rig(human,"default",import_weights=True)
rig.name="Maya • reusable full-body rig"
HumanService.set_character_skin(str(next((asset_dir/"skins/young_caucasian_female").glob("*.mhmat"))),
                                human,skin_type="MAKESKIN")
for material in human.data.materials:
    if material and material.use_nodes:
        for node in material.node_tree.nodes:
            if node.type=="BSDF_PRINCIPLED":
                node.inputs["Roughness"].default_value=.50
                node.inputs["Subsurface Weight"].default_value=.06
                node.inputs["Specular IOR Level"].default_value=.31
                nodes,links=material.node_tree.nodes,material.node_tree.links
                coordinate=nodes.new("ShaderNodeTexCoord")
                texture=nodes.new("ShaderNodeTexNoise")
                texture.inputs["Scale"].default_value=820.
                texture.inputs["Detail"].default_value=2.
                links.new(coordinate.outputs["Object"],texture.inputs["Vector"])
                pores=nodes.new("ShaderNodeBump")
                pores.inputs["Strength"].default_value=.17
                pores.inputs["Distance"].default_value=.00024
                links.new(texture.outputs["Fac"],pores.inputs["Height"])
                normal=node.inputs["Normal"]
                if normal.is_linked:
                    links.new(normal.links[0].from_socket,pores.inputs["Normal"])
                links.new(pores.outputs[0],normal)
                color=node.inputs["Base Color"]
                if color.is_linked:
                    links=material.node_tree.links
                    src=color.links[0].from_socket
                    multiply=material.node_tree.nodes.new("ShaderNodeMixRGB")
                    multiply.blend_type="MULTIPLY"
                    multiply.inputs[0].default_value=1.
                    multiply.inputs[2].default_value=(.93,.85,.79,1)
                    links.new(src,multiply.inputs[1])
                    links.new(multiply.outputs[0],color)

# Paint small, soft face-color zones into the rest mesh so they follow its
# expression keys, using the UV skin for the underlying detail.
face_tint=human.data.color_attributes.new(name="Maya face tint",type="FLOAT_COLOR",domain="POINT")
for vertex in human.data.vertices:
    x,y,z=vertex.co
    forward=max(0.,min(1.,(-y-.094)/.050))
    cheek=exp(-((abs(x)-.045)/.017)**2-((z-1.509)/.015)**2)*forward
    lip=exp(-(x/.024)**4-((z-1.468)/.0075)**4)*forward
    face_tint.data[vertex.index].color=(.22*cheek,.37*lip,0.,1.)
for material in human.data.materials:
    if not material or not material.use_nodes:
        continue
    nodes,links=material.node_tree.nodes,material.node_tree.links
    shader=next((n for n in nodes if n.type=="BSDF_PRINCIPLED"),None)
    if not shader or not shader.inputs["Base Color"].is_linked:
        continue
    zones=nodes.new("ShaderNodeVertexColor")
    zones.layer_name=face_tint.name
    channels=nodes.new("ShaderNodeSeparateColor")
    links.new(zones.outputs["Color"],channels.inputs["Color"])
    base=shader.inputs["Base Color"].links[0].from_socket
    for channel,tone in (("Red",(1.045,.66,.62,1)),("Green",(1.02,.58,.56,1))):
        tint=nodes.new("ShaderNodeMixRGB")
        tint.blend_type="MULTIPLY"
        links.new(channels.outputs[channel],tint.inputs[0])
        links.new(base,tint.inputs[1])
        tint.inputs[2].default_value=tone
        base=tint.outputs[0]
    links.new(base,shader.inputs["Base Color"])

def asset(path,kind):
    return HumanService.add_mhclo_asset(str(asset_dir/path),human,asset_type=kind,subdiv_levels=1)

outfits={}
for label,key in OUTFIT_PROXIES.items():
    obj=asset(f"clothes/{key}/{key}.mhclo","Clothes")
    obj["maya_outfit"]=label
    outfits[label]=obj
outfit=outfits[OUTFITS[0]]
shoes=asset("clothes/shoes05/shoes05.mhclo","Clothes")
hair_options={}
for label,key in zip(HAIR_STYLES,("long01","ponytail01")):
    obj=asset(f"hair/{key}/{key}.mhclo","Hair")
    obj["maya_hair_style"]=label
    hair_options[label]=obj
hair=hair_options[HAIR_STYLES[0]]
eyes=asset("eyes/high-poly/high-poly.mhclo","Eyes")
brows=asset("eyebrows/eyebrow004/eyebrow004.mhclo","Eyebrows")
lashes=asset("eyelashes/eyelashes01/eyelashes01.mhclo","Eyelashes")
teeth=asset("teeth/teeth_base/teeth_base.mhclo","Teeth")
tongue=asset("tongue/tongue01/tongue01.mhclo","Tongue")

def color_material(name,rgb,roughness=.65):
    material=bpy.data.materials.new(name)
    material.diffuse_color=(*rgb,1)
    material.use_nodes=True
    shader=material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value=(*rgb,1)
    shader.inputs["Roughness"].default_value=roughness
    return material

# The arches have separate head and jaw weights in the source asset. Keep
# both arches and the tongue independently shaded, with a recessed oral wall.
def tone_asset(obj, tint, roughness, subsurface):
    for mat in obj.data.materials:
        if not mat or not mat.use_nodes:
            continue
        nodes,links=mat.node_tree.nodes,mat.node_tree.links
        for shader in [n for n in nodes if n.type=="BSDF_PRINCIPLED"]:
            shader.inputs["Roughness"].default_value=roughness
            shader.inputs["Subsurface Weight"].default_value=subsurface
            shader.inputs["Specular IOR Level"].default_value=.28
            color=shader.inputs["Base Color"]
            if color.is_linked:
                src=color.links[0].from_socket
                mix=nodes.new("ShaderNodeMixRGB")
                mix.blend_type="MULTIPLY"
                mix.inputs[0].default_value=1.
                mix.inputs[2].default_value=(*tint,1.)
                links.new(src,mix.inputs[1])
                links.new(mix.outputs[0],color)

tone_asset(teeth,(1.0,.96,.88),.36,.035)
for mat in teeth.data.materials:
    if not mat or not mat.use_nodes:
        continue
    nodes,links=mat.node_tree.nodes,mat.node_tree.links
    shader=next((n for n in nodes if n.type=="BSDF_PRINCIPLED"),None)
    if not shader or not shader.inputs["Base Color"].is_linked:
        continue
    tex=shader.inputs["Base Color"].links[0].from_socket
    components=nodes.new("ShaderNodeSeparateColor")
    links.new(tex,components.inputs["Color"])
    red_bias=nodes.new("ShaderNodeMath")
    red_bias.operation="SUBTRACT"
    links.new(components.outputs["Red"],red_bias.inputs[0])
    links.new(components.outputs["Green"],red_bias.inputs[1])
    enamel=nodes.new("ShaderNodeMapRange")
    enamel.inputs["From Min"].default_value=.023
    enamel.inputs["From Max"].default_value=.14
    enamel.inputs["To Min"].default_value=.66
    enamel.inputs["To Max"].default_value=0.
    links.new(red_bias.outputs[0],enamel.inputs["Value"])
    mix=nodes.new("ShaderNodeMixRGB")
    mix.inputs[2].default_value=(.66,.59,.48,1)
    links.new(enamel.outputs[0],mix.inputs[0])
    links.new(tex,mix.inputs[1])
    links.new(mix.outputs[0],shader.inputs["Base Color"])

# Recess both arches behind the lip line and keep the lower lip clear.
jaw_group=teeth.vertex_groups.get("jaw")
if jaw_group:
    for v in teeth.data.vertices:
        lower=sum(g.weight for g in v.groups if g.group==jaw_group.index)
        v.co.y+=.0028+.0011*lower
        v.co.z-=.0013*lower
tone_asset(tongue,(.72,.51,.52),.42,.055)
bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,location=(0,-.074,1.466))
cavity=bpy.context.object
cavity.name="Maya • recessed mouth interior"
cavity.scale=(.025,.038,.020)
bpy.ops.object.transform_apply(location=True,rotation=False,scale=True)
cavity.data.materials.append(color_material("Oral wall",(.032,.006,.009),.77))
for poly in cavity.data.polygons:
    poly.use_smooth=True
head_weight=cavity.vertex_groups.new(name="head")
head_weight.add(list(range(len(cavity.data.vertices))),1.,"REPLACE")
cavity.parent=rig
mouth_mod=cavity.modifiers.new("Follow head","ARMATURE")
mouth_mod.object=rig


def fabric(name,rgb,base,keep_normal=True):
    material=base.copy()
    material.name=name
    nodes,links=material.node_tree.nodes,material.node_tree.links
    shader=next(n for n in nodes if n.type=="BSDF_PRINCIPLED")
    for link in list(shader.inputs["Base Color"].links):
        links.remove(link)
    shader.inputs["Base Color"].default_value=(*rgb,1)
    shader.inputs["Roughness"].default_value=.70
    shader.inputs["Sheen Weight"].default_value=.22
    noise=nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value=525
    noise.inputs["Detail"].default_value=2
    bump=nodes.new("ShaderNodeBump")
    normal=shader.inputs["Normal"]
    for link in list(normal.links):
        source=link.from_socket
        links.remove(link)
        if keep_normal:
            links.new(source,bump.inputs["Normal"])
    links.new(noise.outputs["Fac"],bump.inputs["Height"])
    bump.inputs["Strength"].default_value=.16
    bump.inputs["Distance"].default_value=.00032
    links.new(bump.outputs[0],normal)
    return material

def fit_fabric(outfit,label):
    positions=[outfit.matrix_world@v.co for v in outfit.data.vertices]
    base=outfit.data.materials[0]
    top=fabric(f"{label} | top",(.64,.064,.055),base)
    leggings=fabric(f"{label} | bottom",(.021,.27,.25),base,keep_normal=False)
    outfit.data.materials.clear()
    outfit.data.materials.append(top)
    outfit.data.materials.append(leggings)
    # The sports kit contains separate connected shirt and leggings pieces.
    adj=[[] for _ in positions]
    for edge in outfit.data.edges:
        a,b=edge.vertices
        adj[a].append(b)
        adj[b].append(a)
    part={}
    for i in range(len(positions)):
        if i in part:
            continue
        ids=[i]
        part[i]=i
        for j in ids:
            for k in adj[j]:
                if k not in part:
                    part[k]=i
                    ids.append(k)
        print("Outfit piece",i,len(ids),min(positions[j].z for j in ids),max(positions[j].z for j in ids))
    sizes={}
    for i,g in part.items():
        sizes.setdefault(g,[]).append(positions[i].z)
    split=(min(p.z for p in positions)+max(p.z for p in positions))*.5
    for polygon in outfit.data.polygons:
        values=sizes[part[polygon.vertices[0]]]
        polygon.material_index=int(sum(values)/len(values)<split)
        polygon.use_smooth=True

for label,obj in outfits.items():
    fit_fabric(obj,label)

# Keep the fitted leggings clear of the model and shoe cuffs.
studio=outfits["studio-set"]
for vertex in studio.data.vertices:
    if vertex.co.z < .24:
        vertex.co += vertex.normal*.004
fit_waistband(studio,human)
hide_covered_waist(human)
for vertex in studio.data.vertices:
    x,y,z=vertex.co
    if y<-.06 and 1.14<z<1.32:
        vertex.co+=vertex.normal*(.004*exp(-((z-1.225)/.065)**2))
# The color line follows an interpolated rest-space band, so irregular
# polygon edges cannot create rectangular patches around the waist.
band=studio.data.attributes.new(name="Maya waistband",type="FLOAT",domain="POINT")
for vertex in studio.data.vertices:
    h=vertex.co.z
    amount=max(0.,min(1.,(h-.924)/.012)) if h<1.03 else 0.
    band.data[vertex.index].value=amount*amount*(3-2*amount)
leggings=studio.data.materials[1]
nodes,links=leggings.node_tree.nodes,leggings.node_tree.links
shader=next(n for n in nodes if n.type=="BSDF_PRINCIPLED")
fill=nodes.new("ShaderNodeRGB")
fill.name="Wardrobe base color"
fill.outputs[0].default_value=shader.inputs["Base Color"].default_value
weight=nodes.new("ShaderNodeAttribute")
weight.attribute_name=band.name
waist_mix=nodes.new("ShaderNodeMixRGB")
waist_mix.blend_type="MULTIPLY"
waist_mix.inputs[2].default_value=(.71,.71,.71,1.)
links.new(weight.outputs["Fac"],waist_mix.inputs[0])
links.new(fill.outputs[0],waist_mix.inputs[1])
links.new(waist_mix.outputs[0],shader.inputs["Base Color"])

loose_tip=min(v.co.z for v in hair_options["loose-long"].data.vertices)
tied=hair_options["tied-long"]
tied_tip=min(v.co.z for v in tied.data.vertices)
for vertex in tied.data.vertices:
    x,y,z=vertex.co
    tail_weight=max(0.,min(1.,(y-.045)/.040))
    strand_length=max(0.,min(1.,(1.525-z)/max(.06,1.525-tied_tip)))
    vertex.co.z-=max(0.,tied_tip-loose_tip)*tail_weight*strand_length**1.22
    vertex.co.y+=.034*tail_weight*strand_length
# Preserve fitted hair cards and the packed strand texture from the hair asset.
for label,variant in hair_options.items():
    for mat in variant.data.materials:
        if mat and mat.use_nodes:
            for node in mat.node_tree.nodes:
                if node.type=="BSDF_PRINCIPLED":
                    node.inputs["Roughness"].default_value=.57
                    node.inputs["Specular IOR Level"].default_value=.12
                    color=node.inputs["Base Color"]
                    if color.is_linked:
                        nodes,links=mat.node_tree.nodes,mat.node_tree.links
                        source=color.links[0].from_socket
                        ramp=nodes.new("ShaderNodeValToRGB")
                        ramp.color_ramp.elements[0].position=.026 if label=="loose-long" else .04
                        ramp.color_ramp.elements[0].color=(.012,.004,.003,1)
                        ramp.color_ramp.elements[1].position=.41 if label=="loose-long" else .48
                        ramp.color_ramp.elements[1].color=(.25,.105,.055,1)
                        links.new(source,ramp.inputs[0])
                        links.new(ramp.outputs[0],color)

scene=bpy.context.scene
scene.render.engine="BLENDER_EEVEE_NEXT"
scene.eevee.taa_render_samples=24
scene.world=bpy.data.worlds.new("Studio ambient")
scene.world.use_nodes=True
scene.world.node_tree.nodes["Background"].inputs[0].default_value=(.48,.54,.62,1)
scene.world.node_tree.nodes["Background"].inputs[1].default_value=.27
scene.view_settings.view_transform="AgX"
bpy.context.view_layer.update()
box=[human.matrix_world@Vector(corner) for corner in human.bound_box]
bottom=min((shoes.matrix_world @ v.co).z for v in shoes.data.vertices)
top_z=max(p.z for p in box)
height=top_z-bottom
print("Human bounds",[(min(p[i] for p in box),max(p[i] for p in box)) for i in range(3)])
print("Rig bones",list(rig.pose.bones.keys()))
print("Body orientations",human.rotation_euler[:],human.scale[:],rig.rotation_euler[:],rig.scale[:])

def aim(obj,position):
    obj.rotation_euler=(Vector(position)-obj.location).to_track_quat("-Z","Y").to_euler()

bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,bottom+.007*height))
floor=bpy.context.object
floor.name="Studio backdrop"
floor.data.materials.append(color_material("Slate studio",(.105,.15,.172)))
for name,offset,power,s in (
    ("Large soft key",(-1.35,-2.0,2.1),410.,1.8),
    ("Warm fill",(1.25,-1.3,1.30),105.,1.4),
    ("Hair rim",(1.10,1.05,1.88),300.,1.15),
):
    bpy.ops.object.light_add(type="AREA",location=(offset[0]*height,offset[1]*height,bottom+offset[2]*height))
    light=bpy.context.object
    light.name=name
    scale=height/1.72
    light.data.energy=power*scale**2
    if name=="Warm fill":
        light.data.color=(1.0,.86,.77)
    light.data.shape="DISK"
    light.data.size=s*scale
    aim(light,(0,0,bottom+.74*height))

def camera(name,xyz,target,scale):
    bpy.ops.object.camera_add(location=(xyz[0]*height,xyz[1]*height,bottom+xyz[2]*height))
    obj=bpy.context.object
    obj.name=name
    obj.data.type="ORTHO"
    obj.data.ortho_scale=scale*height
    aim(obj,(0,0,bottom+target*height))
    return obj

front=camera("Full body",(.28,-3.1,.60),.51,1.12)
portrait=camera("Close-up",(.62,-3.1,.95),.894,.31)
profile=camera("Side",(-3.1,-.25,.58),.51,1.12)
scene.camera=front
scene.render.resolution_x=680
scene.render.resolution_y=900
scene.render.resolution_percentage=100
# A restrained smile and independent eyelid, jaw and lip controls.
root=module_dir/"mpfb/data/targets/expression/units/caucasian"
expressions={}
for label,target in (("Open","mouth-open"),
                     ("Round","mouth-pursing"),("Wide","mouth-retraction"),
                     ("Close","mouth-compression"),("Blink L","eye-left-closure"),
                     ("Blink R","eye-right-closure"),("Cheek smile","mouth-upward-retraction"),
                     ("Lower eyelid L","eye-left-slit"),("Lower eyelid R","eye-right-slit"),
                     ("Brow L","eyebrows-left-inner-up"),("Brow R","eyebrows-right-inner-up"),
                     ("Smile part","mouth-part-later")):
    expressions[label]=TargetService.load_target(human,str(root/(target+".target.gz")),name=label)

# Smaller mouth-corner travel and a fuller cheek lift than the stock target.
# Keep the closed-lip shape gentle, then expose a little enamel as jaw opens.
smile_key=human.shape_key_add(name="Smile",from_mix=False)
basis=human.data.shape_keys.key_blocks["Basis"]
for vertex,base in zip(smile_key.data,basis.data):
    x,y,z=base.co
    face_weight=max(0.,min(1.,(-y-.097)/.026))
    corner=exp(-((abs(x)-.019)/.010)**2-((z-1.466)/.011)**2)*face_weight
    cheek=exp(-((abs(x)-.034)/.014)**2-((z-1.482)/.019)**2)*face_weight
    direction=-1 if x<0 else 1
    vertex.co.x+=direction*(.0023*corner+.00085*cheek)
    vertex.co.z+=.0029*corner+.0016*cheek
    vertex.co.y-=.0010*cheek
expressions["Smile"]=smile_key


# Give the ponytail a deform bone separate from the head.
bpy.ops.object.select_all(action="DESELECT")
rig.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode="EDIT")
tail=rig.data.edit_bones.new("ponytail")
tail.head=(0,.068,1.553)
tail.tail=(0,.143,1.210)
tail.parent=rig.data.edit_bones["head"]
bpy.ops.object.mode_set(mode="OBJECT")
for label,hair in hair_options.items():
    scale=.72 if label=="loose-long" else 1.
    group=hair.vertex_groups.get("ponytail") or hair.vertex_groups.new(name="ponytail")
    head_group=hair.vertex_groups.get("head") or hair.vertex_groups.new(name="head")
    for v in hair.data.vertices:
        world=hair.matrix_world@v.co
        w=scale*max(0.,min(1.,(world.y-.032)/.058))*max(0.,min(1.,(1.57-world.z)/.19))
        if w>.005:
            for old in list(v.groups):
                hair.vertex_groups[old.group].remove([v.index])
            group.add([v.index],w,"REPLACE")
            head_group.add([v.index],1-w,"REPLACE")

phones=json.loads((HERE.parent/"trainer-3d/trainer-speech-timing.json").read_text())
def phone_pose(label):
    if label in {"M","B","P"}:
        return (0.,0.,0.,.92)
    if label in {"OW","UW","UH","W","OY"}:
        return (.28,.70,0.,0.)
    if label in {"AA","AE","AH","AO","AW","AY","EH","ER"}:
        return (.65,.06,.14,0.)
    if label in {"IY","IH","EY","Y","S","Z","SH","CH","JH"}:
        return (.22,.04,.47,0.)
    if label=="SIL":
        return (0.,0.,0.,.06)
    return (.13,.07,.13,.08)

def lip_values(t):
    value=[0.,0.,0.,0.]
    total=0.
    for label,start,end in phones:
        distance=max(0.,start-t,t-end)
        if distance<.042:
            w=(1-distance/.042)**2
            total+=w
            for i,target in enumerate(phone_pose(label)):
                value[i]+=w*target
    return [v/max(1.,total) for v in value]

def set_rotation(name,rotation,frame):
    bone=rig.pose.bones[name]
    bone.rotation_mode="XYZ"
    bone.rotation_euler=rotation
    bone.keyframe_insert("rotation_euler",frame=frame,group=name)

def ease(x):
    return x*x*(3-2*x)

def performance(keys,t):
    if t<=keys[0][0]:
        return keys[0][1]
    j=bisect_right(keys,(t,float("inf")))
    if j>=len(keys):
        return keys[-1][1]
    a,va=keys[j-1]
    b,vb=keys[j]
    mix=ease((t-a)/(b-a))
    return va+(vb-va)*mix

HEAD_PITCH=((0,.015),(.46,-.046),(1.12,.036),(2.0,-.015),(2.8,.061),(3.45,-.033),
           (4.03,.006),(4.73,-.061),(5.35,.028),(6.35,.03),(7.1,-.040),(8,.013))
HEAD_TURN=((0,-.035),(.55,-.062),(1.44,.027),(2.49,.018),(3.06,-.074),(3.70,-.01),
          (4.18,.038),(4.93,-.039),(5.58,.029),(6.55,.094),(7.23,.06),(8,-.018))
EYE_TURN=((0,.031),(.33,.018),(.67,-.026),(1.73,.02),(2.82,.042),(3.59,-.032),
          (4.37,.012),(5.47,-.016),(6.46,-.053),(7.14,-.012),(8,.011))

def set_eye(name,yaw,pitch,frame):
    pose=rig.pose.bones[name]
    local=pose.bone.matrix_local.to_quaternion()
    world=Quaternion((0,0,1),yaw)@Quaternion((1,0,0),pitch)
    pose.rotation_mode="QUATERNION"
    pose.rotation_quaternion=local.inverted()@world@local
    pose.keyframe_insert("rotation_quaternion",frame=frame,group=name)

scene.frame_start,scene.frame_end=1,192
scene.render.fps=24
for frame in range(1,193):
    t=(frame-1)/24
    reach=performance(((0,0),(5.94,0),(6.57,.88),(7.10,.95),(7.89,0)),t)
    pitch=performance(HEAD_PITCH,t)
    turn=performance(HEAD_TURN,t)
    opened,rounded,wide,closed=lip_values(t)
    jaw=max(0.,opened*(1-.88*closed))
    for side,sign in (("L",1),("R",-1)):
        bone=rig.pose.bones["upperarm01."+side]
        bone.rotation_mode="QUATERNION"
        initial=bone.bone.tail_local-bone.bone.head_local
        gesture=reach if side=="R" else .015*sin(t*1.8)
        wanted=Vector(((.245+.56*gesture)*sign,-.085-.20*gesture,-.96+.47*gesture))
        local=bone.bone.matrix_local.to_quaternion()
        bone.rotation_quaternion=local.inverted()@initial.rotation_difference(wanted)@local
        bone.keyframe_insert("rotation_quaternion",frame=frame,group=bone.name)
        set_rotation("wrist."+side,(.035+.05*gesture,-.066*sign,.034*sign),frame)
        set_eye("eye."+side,performance(EYE_TURN,t),-.34*pitch+.012,frame)
    set_rotation("head",(pitch,.036*turn,.91*turn),frame)
    set_rotation("spine02",(.012*sin(t*1.7-.25),-.014*turn,.016*reach),frame)
    lag=performance(HEAD_TURN,t-.155)-turn
    set_rotation("ponytail",(.72*lag,.47*lag,-.86*lag+.045*reach),frame)
    soft_grin=performance(((0,.24),(1.1,.10),(3.88,.09),(4.72,.40),(5.15,.78),
                           (5.63,.60),(6.22,.28),(7.30,.56),(8,.38)),t)
    set_rotation("jaw",(.29*jaw+.030*soft_grin*(1-closed),0.,.020*wide-.016*rounded),frame)
    blink=max(max(0.,1-abs(t-mark)/width) for mark,width in
              ((.94,.09),(2.70,.107),(4.37,.106),(6.07,.09),(7.63,.098)))
    expressions["Blink L"].value=blink
    expressions["Blink R"].value=.96*blink
    smile=performance(((0,.64),(.7,.50),(1.1,.56),(2.08,.45),(3.54,.49),(4.38,.64),
                       (5.15,.98),(5.58,.88),(6.22,.62),(7.30,.79),(8,.68)),t)
    expressions["Smile"].value=smile*(1-.19*jaw)
    expressions["Cheek smile"].value=.12*smile
    expressions["Smile part"].value=.14*soft_grin*(1-.75*closed)
    for label,scale in (("Lower eyelid L",.13),("Lower eyelid R",.16)):
        expressions[label].value=smile*scale*(1-blink)
    brow=performance(((0,.09),(.36,.37),(.87,.06),(1.65,.26),(2.75,.07),
                      (3.81,.22),(4.63,.11),(5.00,.31),(5.64,.05),(8,.11)),t)
    expressions["Brow L"].value=brow
    expressions["Brow R"].value=.86*brow
    # Separate jaw travel from the lip outline so the opening does not double.
    for label,value in (("Open",.36*jaw),("Round",rounded),("Wide",wide),("Close",closed)):
        expressions[label].value=value
    for key in expressions.values():
        key.keyframe_insert("value",frame=frame)
scene.frame_set(1)
set_appearance(HAIR_STYLES[0],OUTFITS[0],*PALETTES[0])
bpy.context.preferences.filepaths.save_version=0
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/"maya-trainer-contour-fit.blend"))
for cam,name in ((front,"maya-full-body"),(portrait,"maya-portrait"),(profile,"maya-side")):
    scene.camera=cam
    scene.render.filepath=str(HERE/(name+".png"))
    bpy.ops.render.render(write_still=True)

# Two close shots verify that the oral geometry stays behind the lips.
for frame,label in ((1,"closed"),(85,"speech"),(124,"smile")):
    scene.camera=portrait
    scene.frame_set(frame)
    scene.render.filepath=str(HERE/("maya-mouth-"+label+".png"))
    bpy.ops.render.render(write_still=True)


for index,(style,kit) in enumerate(zip(HAIR_STYLES,OUTFITS)):
    set_appearance(style,kit,*PALETTES[index])
    scene.frame_set(124)
    scene.camera=front
    scene.render.filepath=str(HERE/("maya-wardrobe-"+style+".png"))
    bpy.ops.render.render(write_still=True)
    scene.camera=portrait
    scene.render.filepath=str(HERE/("maya-hair-"+style+".png"))
    bpy.ops.render.render(write_still=True)
