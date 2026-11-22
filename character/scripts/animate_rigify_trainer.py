"""Transfer the preserved Rokoko capture to editable Rigify controls.

Native Daz bone rest offsets preserve skin, clothing and facial deformation.
Legs use non-stretching IK with animated knee poles, not baked deform bones.
"""
import bpy, json, os, math
from pathlib import Path
from mathutils import Matrix, Vector

OUT=Path(os.environ.get('FITNESS_RIGIFY_DIR','/Users/asif/Documents/fitness-rigify-review'))
s=bpy.context.scene; rig=bpy.data.objects['Trainer_Rigify']
a=bpy.data.objects['Genesis9']; source=bpy.data.objects['Rokoko_Baked_Source']
rest={b.name:source.matrix_world@b.matrix_local for b in source.data.bones}
rr={b.name:b.matrix_local.copy() for b in rig.data.bones}
mapping=[('hip','spine'),('pelvis','pelvis.L'),('spine1','spine.001'),('spine2','spine.002'),
         ('spine3','spine.003'),('spine4','spine.003'),('neck1','spine.004'),('neck2','spine.005'),('head','spine.006')]
for side,suffix in [('l','L'),('r','R')]:
    for native,org in [('shoulder','shoulder'),('upperarm','upper_arm'),('forearm','forearm'),
                       ('hand','hand'),('thigh','thigh'),('shin','shin'),('foot','foot'),('toes','toe')]:
        mapping.append((side+'_'+native,org+'.'+suffix))
# Pelvis is the same Daz root orientation; using its asymmetric helper would tilt it.
mapping=[(n,'spine' if n=='pelvis' else o) for n,o in mapping]
for suffix in ['L','R']:
    for name in ['thigh_parent','upper_arm_parent']:
        b=rig.pose.bones[name+'.'+suffix];b['IK_Stretch']=0.0
        b['IK_FK']=0.0 if name=='thigh_parent' else 1.0
    rig.pose.bones['thigh_parent.'+suffix]['pole_vector']=True

def update(): bpy.context.view_layer.update()
def target(native, org):
    return (source.matrix_world@source.pose.bones[native].matrix)@rest[native].inverted()@rr['ORG-'+org]
def orient(ctrl, org, desired):
    update();b=rig.pose.bones[ctrl];current=rig.pose.bones['ORG-'+org].matrix
    q=desired.to_quaternion()@current.to_quaternion().inverted()@b.matrix.to_quaternion()
    m=q.to_matrix().to_4x4();m.translation=b.matrix.translation;b.matrix=m;update()
def key(name,f):
    b=rig.pose.bones[name];b.rotation_mode='QUATERNION'
    for path in ['location','rotation_quaternion','scale']:b.keyframe_insert(data_path=path,frame=f)

controls=['torso','spine_fk','spine_fk.001','spine_fk.002','spine_fk.003','neck','head']
for suffix in ['L','R']:
    controls += [n+'.'+suffix for n in ['shoulder','upper_arm_fk','forearm_fk','hand_fk',
                                      'foot_ik','thigh_ik_target','toe_ik']]
for name in controls:rig.pose.bones[name].rotation_mode='QUATERNION'
errors=[]
for f in range(1,241):
    s.frame_set(f)
    # Reset control pose each frame so no iterative drift accumulates.
    for name in controls:rig.pose.bones[name].matrix_basis.identity()
    update()
    desired=target('hip','spine')
    torso=rig.pose.bones['torso'];m=torso.matrix.copy()
    m.translation += desired.translation-rig.pose.bones['ORG-spine'].head
    torso.matrix=m;update()
    for native,org,ctrl in [('hip','spine','spine_fk'),('spine1','spine.001','spine_fk.001'),
        ('spine2','spine.002','spine_fk.002'),('spine4','spine.003','spine_fk.003'),
        ('neck1','spine.004','neck'),('head','spine.006','head')]:orient(ctrl,org,target(native,org))
    # The hips FK control pivots at its tail. Reconcile root travel after rotation.
    m=torso.matrix.copy();m.translation += desired.translation-rig.pose.bones['ORG-spine'].head
    torso.matrix=m;update()
    for side,suffix in [('l','L'),('r','R')]:
        for native,org,ctrl in [('shoulder','shoulder','shoulder'),('upperarm','upper_arm','upper_arm_fk'),
                                ('forearm','forearm','forearm_fk'),('hand','hand','hand_fk')]:
            orient(ctrl+'.'+suffix,org+'.'+suffix,target(side+'_'+native,org+'.'+suffix))
        foot=target(side+'_foot','foot.'+suffix)
        # Foot control has its own rest axes and origin; solve its rigid delta.
        for _ in range(4):
            update();b=rig.pose.bones['foot_ik.'+suffix]
            delta=foot@rig.pose.bones['ORG-foot.'+suffix].matrix.inverted()
            b.matrix=delta@b.matrix;update()
        h=source.matrix_world@source.pose.bones[side+'_thigh'].head
        k=source.matrix_world@source.pose.bones[side+'_shin'].head
        ankle=source.matrix_world@source.pose.bones[side+'_foot'].head
        axis=(ankle-h).normalized();bend=(k-h)-axis*(k-h).dot(axis)
        if bend.length<.001:bend=Vector((0,-1,0))
        pole=rig.pose.bones['thigh_ik_target.'+suffix];m=pole.matrix.copy()
        m.translation=k+bend.normalized()*.5;pole.matrix=m;update()
        # Re-align ankle after pole update; ball/toes retain captured foot roll.
        b=rig.pose.bones['foot_ik.'+suffix]
        b.matrix=(foot@rig.pose.bones['ORG-foot.'+suffix].matrix.inverted())@b.matrix;update()
        orient('toe_ik.'+suffix,'toe.'+suffix,target(side+'_toes','toe.'+suffix))
        errors.append((rig.pose.bones['ORG-foot.'+suffix].head-foot.translation).length)
    for name in controls:key(name,f)
    if f%40==0:print('RIGIFY_FRAME',f,flush=True)

# Bind the existing Daz deform skeleton through calibrated rest-offset helpers.
helpers=bpy.data.collections.new('Rigify Native Rest Offsets');s.collection.children.link(helpers)
for native,org in mapping:
    helper=bpy.data.objects.new('Rigify offset '+native,None);helpers.objects.link(helper)
    helper.matrix_world=rest[native];helper.hide_render=True;helper.hide_set(True)
    c=helper.constraints.new('CHILD_OF');c.target=rig;c.subtarget='ORG-'+org
    c.inverse_matrix=rr['ORG-'+org].inverted()
    b=a.pose.bones[native]
    c=b.constraints.new('COPY_ROTATION');c.name='Rigify body control';c.target=helper
    c.owner_space='WORLD';c.target_space='WORLD'
    if native=='hip':
        c=b.constraints.new('COPY_LOCATION');c.name='Rigify root travel';c.target=helper
        c.owner_space='WORLD';c.target_space='WORLD'
rig['status']='Rokoko capture on Rigify controls; non-stretching leg IK and animated knee poles'
report={'frames':240,'fps':24,'max_ankle_target_error_m':max(errors),'leg_mode':'IK',
        'stretch':False,'controls_keyed':controls,'review_status':'Requires visual and sole-contact review'}
(OUT/'rigify-motion-review.json').write_text(json.dumps(report,indent=2))
s.frame_set(1);update();bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'kat-rigify-motion.blend'),compress=True)
print('RIGIFY_MOTION_SAVED',report,flush=True)
