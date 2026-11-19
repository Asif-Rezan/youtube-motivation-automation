"""Use the official free Rokoko retargeter on a clean metre-scale Daz proxy.

The proxy protects the original character's meshes/accessory rig from destructive
armature transform application. Only rotations and root travel are baked back.
"""
import bpy,sys,ssl,json,importlib,math
from pathlib import Path
from mathutils import Vector,Matrix
from bpy.props import PointerProperty,BoolProperty,EnumProperty,CollectionProperty
P=Path('/Users/asif/Documents/fitness-rokoko-review');P.mkdir(exist_ok=True)
addons=Path(bpy.utils.user_resource('SCRIPTS',path='addons'))
sys.path.insert(0,str(addons));original_ssl=ssl._create_default_https_context
addon=importlib.import_module('rokoko_studio_live')
# Offline retargeting requires no account, streaming or login libraries.
ssl._create_default_https_context=original_ssl
for cls in [addon.panels.retargeting.BoneListItem,addon.operators.retargeting.RetargetAnimation]:
    bpy.utils.register_class(cls)
bpy.types.Scene.rsl_retargeting_armature_source=PointerProperty(type=bpy.types.Object)
bpy.types.Scene.rsl_retargeting_armature_target=PointerProperty(type=bpy.types.Object)
bpy.types.Scene.rsl_retargeting_auto_scaling=BoolProperty(default=False)
bpy.types.Scene.rsl_retargeting_use_pose=EnumProperty(items=[('REST','Rest',''),('CURRENT','Current','')])
bpy.types.Scene.rsl_retargeting_bone_list=CollectionProperty(type=addon.panels.retargeting.BoneListItem)
addon.core.detection_manager.load_detection_lists()
s=bpy.context.scene;a=bpy.data.objects['Genesis9'];raw=bpy.data.objects['36_02'];N=240
mapping=[('Hips','hip'),('Hips','pelvis'),('LowerBack','spine1'),('Spine','spine2'),
         ('Spine1','spine3'),('Spine1','spine4'),('Neck','neck1'),('Neck1','neck2'),('Head','head')]
for side,source in [('l','Left'),('r','Right')]:
    for target,suffix in [('shoulder','Shoulder'),('upperarm','Arm'),('forearm','ForeArm'),('hand','Hand'),
        ('thigh','UpLeg'),('shin','Leg'),('foot','Foot'),('toes','ToeBase')]:mapping.append((source+suffix,side+'_'+target))
body=bpy.data.objects['Genesis9.Shape'];rest={b.name:a.matrix_world@b.matrix_local for b in a.data.bones}
rp=lambda name:rest[name].translation.copy()
leg=(rp('l_shin')-rp('l_thigh')).length+(rp('l_foot')-rp('l_shin')).length
rawleg=(raw.data.bones['LeftLeg'].head_local-raw.data.bones['LeftUpLeg'].head_local).length+(raw.data.bones['LeftFoot'].head_local-raw.data.bones['LeftLeg'].head_local).length
scale=leg/rawleg
capture=[]
for f in [1]+[2+round((.25+i/24)*120) for i in range(N)]:
    s.frame_set(f)
    capture.append({b.name:{'basis':b.matrix_basis.copy(),'position':raw.matrix_world@b.head} for b in raw.pose.bones})
hips=[row['Hips']['position']*scale for row in capture[1:]]
center=Vector(((min(p.x for p in hips)+max(p.x for p in hips))/2,(min(p.y for p in hips)+max(p.y for p in hips))/2,0))
source=raw.copy();source.data=raw.data.copy();source.animation_data_clear();source.name='Rokoko source 24fps';s.collection.objects.link(source)
source.matrix_world=Matrix.Scale(scale,4)@raw.matrix_world;source.location-=center;source.hide_render=True
for index,row in enumerate(capture):
    for bone in source.pose.bones:
        bone.rotation_mode='QUATERNION';bone.matrix_basis=row[bone.name]['basis']
        bone.keyframe_insert(data_path='rotation_quaternion',frame=index)
        if bone.name=='Hips':bone.keyframe_insert(data_path='location',frame=index)

proxy=bpy.data.objects.new('Rokoko clean Daz proxy',a.data.copy());s.collection.objects.link(proxy);proxy.hide_render=True
proxy.data.transform(a.matrix_world);proxy.matrix_world=Matrix.Identity(4)
bpy.ops.object.select_all(action='DESELECT');proxy.select_set(True);bpy.context.view_layer.objects.active=proxy
bpy.ops.object.mode_set(mode='EDIT')
keep={target for _,target in mapping}
for name in list(keep):
    bone=proxy.data.edit_bones[name]
    while bone.parent:keep.add(bone.parent.name);bone=bone.parent
for bone in list(proxy.data.edit_bones):
    if bone.name not in keep:proxy.data.edit_bones.remove(bone)
bpy.ops.object.mode_set(mode='POSE')
for bone in proxy.pose.bones:bone.rotation_mode='QUATERNION';bone.matrix_basis.identity()
bpy.context.view_layer.update()
for side,name in [('l','Left'),('r','Right')]:
    for target,child,sn,sc in [('upperarm','forearm','Arm','ForeArm'),('forearm','hand','ForeArm','Hand'),('hand','mid1','Hand','HandIndex1')]:
        n=side+'_'+target;c=side+'_'+child
        native=(rp(c)-rp(n)).normalized();desired=(capture[0][name+sc]['position']-capture[0][name+sn]['position']).normalized()
        q=native.rotation_difference(desired)@rest[n].to_quaternion();w=q.to_matrix().to_4x4();w.translation=proxy.pose.bones[n].head
        proxy.pose.bones[n].matrix=w;bpy.context.view_layer.update()
bpy.ops.pose.armature_apply(selected=False);bpy.ops.object.mode_set(mode='OBJECT')
s.frame_set(0)
s.rsl_retargeting_armature_source=source;s.rsl_retargeting_armature_target=proxy
s.rsl_retargeting_auto_scaling=False;s.rsl_retargeting_use_pose='CURRENT'
for sn,tn in mapping:
    item=s.rsl_retargeting_bone_list.add();item.bone_name_source=sn;item.bone_name_target=tn
(P/'bone-map.json').write_text(json.dumps(mapping,indent=2))
print('ROKOKO_RETARGET_START',len(mapping),bpy.app.version_string,flush=True)
result=bpy.ops.rsl.retarget_animation()
print('ROKOKO_RETARGET_RESULT',result,flush=True)
assert result=={'FINISHED'}

# Bake the official result onto the original scale-preserving deform skeleton.
if a.animation_data:a.animation_data_clear()
for b in a.pose.bones:
    if not b.constraints:b.matrix_basis.identity()
bpy.ops.object.select_all(action='DESELECT');a.select_set(True);bpy.context.view_layer.objects.active=a
bpy.ops.object.mode_set(mode='POSE')
for b in a.pose.bones:b.select=False
for _,name in mapping:
    b=a.pose.bones[name];b.select=True
    c=b.constraints.new('COPY_ROTATION');c.name='Rokoko proxy rotation';c.target=proxy;c.subtarget=name;c.target_space='WORLD';c.owner_space='WORLD'
    if name=='hip':
        c=b.constraints.new('COPY_LOCATION');c.name='Rokoko proxy root';c.target=proxy;c.subtarget=name;c.target_space='WORLD';c.owner_space='WORLD'
bpy.ops.nla.bake(frame_start=1,frame_end=N,step=1,only_selected=True,visual_keying=True,clear_constraints=True,use_current_action=False,bake_types={'POSE'})
bpy.ops.object.mode_set(mode='OBJECT')
s.camera.animation_data_clear();s.camera.location=(.2,-6,1.65);s.camera.rotation_euler=(Vector((0,0,.85))-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.ortho_scale=4.2
s.frame_start=1;s.frame_end=N;s.render.fps=24;s.eevee.taa_render_samples=32
s['retargeter']='Official Rokoko Studio Live Blender 1.4.4 offline retargeting, clean native-proportion proxy, baked to original Daz rig.'
s.frame_set(1);bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'kat-rokoko-retarget.blend'),compress=True)
for f in [1,48,96,144,192,240]:
    s.frame_set(f);s.render.filepath=str(P/f'rokoko-{f}.png');bpy.ops.render.render(write_still=True)
