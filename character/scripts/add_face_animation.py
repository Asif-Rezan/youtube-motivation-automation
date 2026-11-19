import bpy,json,math
from pathlib import Path
from mathutils import Vector
P=Path('/Users/asif/Documents/fitness-garden-demo');s=bpy.context.scene;a=bpy.data.objects['Genesis9']
for region in ['Head','Body','Arms','Legs']:
 m=bpy.data.materials.get(region)
 if m:
  tint=m.node_tree.nodes.get('Natural warm skin response')
  if tint:tint.inputs[2].default_value=(1,.98,.95,1)
s.view_settings.exposure=.26
for name in ['Eye Left','Eye Right']:
 m=bpy.data.materials[name];image=bpy.data.images.load('/Users/Shared/My DAZ 3D Library/Runtime/Textures/DAZ/Characters/Genesis9/Base/Eyes/G9_Eyes01_D.jpg',check_existing=True)
 n=m.node_tree.nodes;l=m.node_tree.links;n.clear();out=n.new('ShaderNodeOutputMaterial');sh=n.new('ShaderNodeBsdfPrincipled');t=n.new('ShaderNodeTexImage');t.image=image
 l.new(t.outputs['Color'],sh.inputs['Base Color']);sh.inputs['Alpha'].default_value=1;sh.inputs['Roughness'].default_value=.26;sh.inputs['Specular IOR Level'].default_value=.3;l.new(sh.outputs[0],out.inputs['Surface'])
for name in ['Eyebrows_Primary','Eyebrows_Secondary']:
 m=bpy.data.materials[name];n=m.node_tree.nodes;n.clear();out=n.new('ShaderNodeOutputMaterial');sh=n.new('ShaderNodeBsdfPrincipled');sh.inputs['Base Color'].default_value=(.025,.009,.004,1);sh.inputs['Roughness'].default_value=.85;sh.inputs['Specular IOR Level'].default_value=.15;m.node_tree.links.new(sh.outputs[0],out.inputs['Surface'])
for name in ['Eyelashes Lower','Eyelashes Upper']:
 m=bpy.data.materials[name];n=m.node_tree.nodes;l=m.node_tree.links;image=next((v.image for v in n if v.type=='TEX_IMAGE' and v.image),None);n.clear();out=n.new('ShaderNodeOutputMaterial');sh=n.new('ShaderNodeBsdfPrincipled');sh.inputs['Base Color'].default_value=(.008,.004,.002,1);sh.inputs['Roughness'].default_value=.8
 if image:t=n.new('ShaderNodeTexImage');t.image=image;l.new(t.outputs['Color'],sh.inputs['Alpha'])
 l.new(sh.outputs[0],out.inputs['Surface'])
def solid_material(name,color,rough=.6):
 m=bpy.data.materials[name];n=m.node_tree.nodes;n.clear();out=n.new('ShaderNodeOutputMaterial');sh=n.new('ShaderNodeBsdfPrincipled');sh.inputs['Base Color'].default_value=(*color,1);sh.inputs['Roughness'].default_value=rough;sh.inputs['Specular IOR Level'].default_value=.2;m.node_tree.links.new(sh.outputs[0],out.inputs['Surface'])
solid_material('Mouth Cavity',(.018,.0025,.004))
for name in ['Mouth','Teeth']:
 m=bpy.data.materials[name];n=m.node_tree.nodes;l=m.node_tree.links;n.clear();out=n.new('ShaderNodeOutputMaterial');sh=n.new('ShaderNodeBsdfPrincipled');t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load('/Users/Shared/My DAZ 3D Library/Runtime/Textures/DAZ/Characters/Genesis9/Base/Genesis9_Mouth_D_1001.jpg',check_existing=True)
 shade=n.new('ShaderNodeMixRGB');shade.blend_type='MULTIPLY';shade.inputs[0].default_value=1;shade.inputs[2].default_value=(.55,.48,.43,1);l.new(t.outputs['Color'],shade.inputs[1]);l.new(shade.outputs[0],sh.inputs['Base Color']);sh.inputs['Roughness'].default_value=.48;sh.inputs['Specular IOR Level'].default_value=.15;l.new(sh.outputs[0],out.inputs['Surface'])
 if name=='Teeth':
  # Recessed posterior surfaces must not shine as brightly as front enamel.
  co=n.new('ShaderNodeTexCoord');xyz=n.new('ShaderNodeSeparateXYZ');l.new(co.outputs['Generated'],xyz.inputs[0])
  sub=n.new('ShaderNodeMath');sub.operation='SUBTRACT';sub.inputs[1].default_value=.5;l.new(xyz.outputs['X'],sub.inputs[0])
  ab=n.new('ShaderNodeMath');ab.operation='ABSOLUTE';l.new(sub.outputs[0],ab.inputs[0])
  ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.15;ramp.color_ramp.elements[0].color=(1,1,1,1);ramp.color_ramp.elements[1].position=.36;ramp.color_ramp.elements[1].color=(.045,.045,.045,1);l.new(ab.outputs[0],ramp.inputs[0])
  mul=n.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1;l.new(shade.outputs[0],mul.inputs[1]);l.new(ramp.outputs[0],mul.inputs[2]);l.new(mul.outputs[0],sh.inputs['Base Color'])
for name,thickness in [('G9EyebrowFibers.Shape',.006),('Genesis9Eyelashes.Shape',.003)]:
 o=bpy.data.objects[name];m=o.modifiers.new('Visible natural hair thickness','SOLIDIFY');m.thickness=thickness;m.offset=0
# Bind facial accessories to corresponding skin bones rather than rigid head parenting.
a.data.pose_position='REST';bpy.context.view_layer.update()
for name in ['Genesis9Mouth.Shape','Genesis9Eyelashes.Shape','G9EyebrowFibers.Shape']:
 o=bpy.data.objects[name];w=o.matrix_world.copy();o.parent=a;o.parent_type='OBJECT';o.matrix_world=w
 for g in o.vertex_groups:g.name=g.name.split('.')[0]
 if not any(m.type=='ARMATURE' for m in o.modifiers):m=o.modifiers.new('Facial skinning','ARMATURE');m.object=a;m.use_deform_preserve_volume=True
a.data.pose_position='POSE';bpy.context.view_layer.update()
envelope=json.loads((P/'voice-envelope.json').read_text())
blinks=[2,5.7,9.6,13.9,18.1,22.4,26.8,30.7,35.2,39,43.5,47.8,52.1,56.3,59.2]
for frame,amount in enumerate(envelope,1):
 t=(frame-1)/24
 blink=max(math.exp(-((t-b)/.075)**2) for b in blinks)
 for side in ['l','r']:
  b=a.pose.bones[side+'_eyelidupper'];b.location=(0,-.85*blink,-.10*blink);b.keyframe_insert(data_path='location',frame=frame)
  b=a.pose.bones[side+'_eyelidlower'];b.location=(0,.20*blink,0);b.keyframe_insert(data_path='location',frame=frame)
 jaw=a.pose.bones['lowerjaw'];jaw.rotation_mode='XYZ';jaw.rotation_euler.x=.10*amount;jaw.keyframe_insert(data_path='rotation_euler',frame=frame)
 for name in ['l_liplower','r_liplower','liplowermiddle']:
  b=a.pose.bones.get(name)
  if b:b.location.y=-.15*amount;b.keyframe_insert(data_path='location',frame=frame)
 for side in ['l','r']:
  b=a.pose.bones[side+'_lipcorner'];b.location.y=.32+.04*amount;b.location.x=(.13 if side=='l' else -.13);b.keyframe_insert(data_path='location',frame=frame)
  cheek=a.pose.bones.get(side+'_cheek')
  if cheek:cheek.location.y=.10;cheek.keyframe_insert(data_path='location',frame=frame)
s.eevee.taa_render_samples=16
s['face_animation']='Timed blink bones and audio-amplitude-driven jaw/lower lip; approximate speech animation, not phoneme-level lip sync.'
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'garden-workout-face-hq.blend'),compress=True)
# Close-up previews reveal eye and mouth defects before full render.
cam=s.camera;old=cam.matrix_world.copy();scale=cam.data.ortho_scale
cam.location=(0,-4,1.50);cam.rotation_euler=(Vector((0,0,1.49))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=.62
for frame,label in [(25,'talking'),(49,'blink'),(170,'eyes-open')]:
 s.frame_set(frame);s.render.filepath=str(P/f'face-{label}.png');bpy.ops.render.render(write_still=True)
cam.matrix_world=old;cam.data.ortho_scale=scale
