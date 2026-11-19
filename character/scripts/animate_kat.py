import bpy,math,json,gzip
from urllib.parse import unquote
from pathlib import Path
from mathutils import Vector
out=Path('/Users/asif/Documents/DAZ 3D/kat-blender-short');out.mkdir(exist_ok=True)
s=bpy.context.scene
native=json.loads(gzip.decompress(Path('/Users/asif/Documents/DAZ 3D/Studio/My Library/Scenes/Kat Black Training Outfit v2.duf').read_bytes()))
images={i['id']:i for i in native.get('image_library',[])}
for mat in bpy.data.materials:
 mat.use_nodes=True
 source=next((m for m in native['scene']['materials'] if m.get('id')==mat.name or m.get('id')==mat.name+'-1'),None)
 if not source:continue
 ch=source.get('diffuse',{}).get('channel',{})
 path=ch.get('image_file')
 if not path and ch.get('image'):
  item=images.get(unquote(ch['image'].lstrip('#')),{})
  path=next((v.get('url') for v in item.get('map',[]) if v.get('url')),None)
 shader=next((n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
 if shader and path:
  file=Path('/Users/Shared/My DAZ 3D Library')/unquote(path).lstrip('/')
  if file.exists():
   tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(file),check_existing=True)
   mat.node_tree.links.new(tex.outputs['Color'],shader.inputs['Base Color'])
 if 'EyeMoisture' in mat.name or 'Tear' in mat.name:
  nodes=mat.node_tree.nodes;nodes.clear();a=nodes.new('ShaderNodeBsdfTransparent');b=nodes.new('ShaderNodeOutputMaterial');mat.node_tree.links.new(a.outputs[0],b.inputs['Surface'])
for o in bpy.data.objects:
 if o.type=='MESH':
  o.hide_render=any(x in o.name for x in ('G9BaseShirt','EssentialShorts','ponytail'))
  print('MESH',o.name,'mods',[(m.type,m.object.name if m.type=='ARMATURE' and m.object else '') for m in o.modifiers],flush=True)
  for p in o.data.polygons:p.use_smooth=True
  if not o.hide_render:
   for mat in o.data.materials:
    if not mat or not mat.use_nodes:continue
    for n in mat.node_tree.nodes:
     if n.type=='BSDF_PRINCIPLED':
      n.inputs['Roughness'].default_value=.5
      n.inputs['Metallic'].default_value=0
      if 'Bra_' in o.name or 'Pant_' in o.name:
       for l in list(n.inputs['Base Color'].links):mat.node_tree.links.remove(l)
       n.inputs['Base Color'].default_value=(.013,.015,.022,1)
       n.inputs['Roughness'].default_value=.75
       if 'Emission Strength' in n.inputs:n.inputs['Emission Strength'].default_value=0
arm=bpy.data.objects['Genesis9']
for o in bpy.data.objects:
 if o.type=='MESH' and any(x in o.name for x in ('Eirgrid','Eyes.','Mouth.','Tear.','Eyelashes.','Eyebrow')):
  world=o.matrix_world.copy();o.parent=arm;o.parent_type='BONE';o.parent_bone='head';o.matrix_world=world
# Repeat the same controls for fitted clothing/accessory skeleton branches.
for f in range(1,145):
 t=(f-1)/24
 envelope=math.sin(math.pi*min(1,t/1.4)) if t<1.4 else (1 if t<4.6 else max(0,(6-t)/1.4))
 for b in arm.pose.bones:
  name=b.name.split('.')[0];b.rotation_mode='XYZ'
  if name in ('r_upperarm','r_forearm','r_hand','head'):
   if name=='r_upperarm':b.rotation_euler=(0,0,-.38*envelope)
   elif name=='r_forearm':b.rotation_euler=(0,-1.0*envelope,0)
   elif name=='r_hand':b.rotation_euler=(.20*math.sin(t*8)*envelope,0,0)
   elif name=='head':b.rotation_euler=(.018*math.sin(t*2),.045*math.sin(t*1.5),0)
   else:b.rotation_euler=(0,0,.012*math.sin(t*1.4))
   b.keyframe_insert(data_path='rotation_euler',frame=f)
def aim(o,at):o.rotation_euler=(Vector(at)-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(2.6,-4.8,1.5));cam=bpy.context.object;aim(cam,(0,0,.88));cam.data.type='ORTHO';cam.data.ortho_scale=2.05;s.camera=cam
for loc,power,size in [((2,-3,4),450,4),((-3,-1,2.3),250,3),((0,3,3),500,3)]:
 bpy.ops.object.light_add(type='AREA',location=loc);l=bpy.context.object;l.data.energy=power;l.data.shape='DISK';l.data.size=size;aim(l,(0,0,1))
bpy.ops.mesh.primitive_plane_add(size=200);floor=bpy.context.object
mat=bpy.data.materials.new('Warm studio floor');mat.diffuse_color=(.19,.22,.23,1);floor.data.materials.append(mat)
if not s.world:s.world=bpy.data.worlds.new('Studio World')
s.world.color=(.18,.18,.18)
s.render.engine='CYCLES';s.cycles.samples=16;s.cycles.use_denoising=True
s.render.resolution_x=640;s.render.resolution_y=960;s.render.resolution_percentage=100
s.render.fps=24;s.frame_start=1;s.frame_end=144
s.view_settings.view_transform='AgX';s.frame_set(48)
s.render.image_settings.file_format='PNG';s.render.filepath=str(out/'preview.png')
bpy.ops.wm.save_as_mainfile(filepath=str(out/'kat-animated.blend'))
bpy.ops.render.render(write_still=True)
