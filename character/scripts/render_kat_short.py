import bpy
from pathlib import Path
root=Path('/Users/asif/Documents/DAZ 3D/kat-blender-short')
s=bpy.context.scene
for name in ('Eye Left','Eye Right'):
 mat=bpy.data.materials.get(name)
 if mat:
  mat.use_nodes=True
  sh=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
  tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(root/'eyes-composite.png'),check_existing=True)
  mat.node_tree.links.new(tex.outputs['Color'],sh.inputs['Base Color'])
for o in bpy.data.objects:
 if o.type=='MESH' and 'Eirgrid' in o.name:
  for mat in o.data.materials:
   if mat and mat.use_nodes:
    sh=next((n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
    if sh:
     for l in list(sh.inputs['Base Color'].links):mat.node_tree.links.remove(l)
     sh.inputs['Base Color'].default_value=(.065,.028,.012,1)
     sh.inputs['Roughness'].default_value=.6
s.render.resolution_x=512;s.render.resolution_y=768;s.cycles.samples=8
s.frame_start=1;s.frame_end=144;s.render.fps=24
s.render.image_settings.file_format='PNG';s.render.filepath=str(root/'frames'/'frame-')
(root/'frames').mkdir(exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(root/'kat-animated.blend'))
bpy.ops.render.render(animation=True)
