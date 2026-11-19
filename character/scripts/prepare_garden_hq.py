"""Improve material detail and garden matching; native resolution, no optical flow."""
import bpy,math
from pathlib import Path
from mathutils import Vector
P=Path('/Users/asif/Documents/fitness-garden-demo');s=bpy.context.scene
texroot=Path('/Users/Shared/My DAZ 3D Library/Runtime/Textures/DAZ/Characters/Genesis9/Base/Feminine_01')
for region,tile in [('Head','1001'),('Body','1002'),('Arms','1004'),('Legs','1003')]:
 m=bpy.data.materials.get(region)
 if not m:continue
 n=m.node_tree.nodes;l=m.node_tree.links;sh=next(n for n in n if n.type=='BSDF_PRINCIPLED')
 color=sh.inputs['Base Color'];src=color.links[0].from_socket if color.links else None
 if src:
  tint=n.new('ShaderNodeMixRGB');tint.name='Natural warm skin response';tint.blend_type='MULTIPLY';tint.inputs[0].default_value=1;tint.inputs[2].default_value=(1,.91,.83,1);l.new(src,tint.inputs[1]);l.new(tint.outputs[0],color)
 sh.inputs['Subsurface Weight'].default_value=.075
 sh.inputs['Subsurface Radius'].default_value=(.8,.35,.2)
 if 'Subsurface Scale' in sh.inputs:sh.inputs['Subsurface Scale'].default_value=.012
 sh.inputs['Specular IOR Level'].default_value=.28
 for suffix,kind in [('NM','Normal'),('R','Roughness')]:
  path=texroot/f'G9Feminine01_{region}_{suffix}_{tile}.jpg'
  if not path.exists():continue
  t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(path),check_existing=True);t.image.colorspace_settings.name='Non-Color'
  if kind=='Normal':
   norm=n.new('ShaderNodeNormalMap');norm.inputs['Strength'].default_value=.4;l.new(t.outputs['Color'],norm.inputs['Color']);l.new(norm.outputs[0],sh.inputs['Normal'])
  else:l.new(t.outputs['Color'],sh.inputs['Roughness'])
for o in bpy.data.objects:
 if o.type=='MESH' and any(x in o.name for x in ['Bra_','Pant_']):
  for m in o.data.materials:
   if m and m.use_nodes:
    for sh in m.node_tree.nodes:
     if sh.type=='BSDF_PRINCIPLED':
      sh.inputs['Base Color'].default_value=(.005,.006,.009,1);sh.inputs['Roughness'].default_value=.65;sh.inputs['Specular IOR Level'].default_value=.2
lights=[o for o in s.objects if o.type=='LIGHT']
for i,o in enumerate(lights):
 o.data.energy=[300,80,140][i%3];o.data.color=[(1,.88,.73),(.85,.93,1),(1,.96,.82)][i%3]
s.view_settings.exposure=-.12;s.view_settings.look='AgX - Medium High Contrast'
s.render.engine='BLENDER_EEVEE';s.render.resolution_x=1920;s.render.resolution_y=1080;s.render.resolution_percentage=100
# Preserve timing while increasing actual animation sampling from 12 to 24 fps.
for action in bpy.data.actions:
 curves=[]
 if hasattr(action,'fcurves'):curves=list(action.fcurves)
 else:
  for layer in action.layers:
   for strip in layer.strips:
    for bag in strip.channelbags:curves.extend(bag.fcurves)
 for curve in curves:
  for k in curve.keyframe_points:
   k.co.x=(k.co.x-1)*2+1;k.handle_left.x=(k.handle_left.x-1)*2+1;k.handle_right.x=(k.handle_right.x-1)*2+1
  curve.update()
s.render.fps=24;s.frame_start=1;s.frame_end=1440
s.render.film_transparent=True;s.render.image_settings.color_mode='RGBA'
s.render.filepath=str(P/'frames-hq'/'f-');(P/'frames-hq').mkdir(exist_ok=True)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'garden-workout-hq.blend'),compress=True)
for frame,label in [(277,'standing'),(1045,'floor')]:
 s.frame_set(frame);s.render.filepath=str(P/f'hq-{label}.png');bpy.ops.render.render(write_still=True)
