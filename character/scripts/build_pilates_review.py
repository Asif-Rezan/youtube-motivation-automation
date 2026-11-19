"""Reference-authored heel-raise review, with locked forefeet and native Daz smile.

This is a kinematic animation sample, not a certified exercise or a physics sim.
Run using Blender --background kat-cmu-mocap-final.blend --python this_file.
"""
import bpy, gzip, json, math, sys
from pathlib import Path
from mathutils import Vector, Quaternion
from bpy_extras.object_utils import world_to_camera_view
sys.path.insert(0,str(Path(__file__).parent))
from rig_repairs import repair_mouth_chain

OUT = Path('/Users/asif/Documents/fitness-pilates-review')
OUT.mkdir(exist_ok=True)
scene = bpy.context.scene
rig = bpy.data.objects['Genesis9']
body = bpy.data.objects['Genesis9.Shape']
repair_mouth_chain(rig,bpy.data.objects['Genesis9Mouth.Shape'])
for obj in bpy.data.objects:
    if obj.animation_data:
        obj.animation_data_clear()
for bone in rig.pose.bones:
    bone.matrix_basis.identity()
    bone.rotation_mode = 'QUATERNION'
root = bpy.data.objects['Workout motion root']
root.location = (0, 0, .9022)
root.rotation_euler = (0, 0, 0)
for mod in body.modifiers:
    if mod.type == 'ARMATURE':
        mod.use_deform_preserve_volume = True
bpy.context.view_layer.update()
rest = {b.name: rig.matrix_world @ b.matrix_local for b in rig.data.bones}
def point(name):
    return rest[name].translation.copy()
def orient(name, delta):
    bone = rig.pose.bones[name]
    world = (delta @ rest[name].to_quaternion()).to_matrix().to_4x4()
    for i in range(3):
        for j in range(3):
            world[i][j] *= .01
    world.translation = rig.matrix_world @ bone.head
    bone.matrix = rig.matrix_world.inverted() @ world
    bpy.context.view_layer.update()

# Native mesh morphs preserve the sculpted lip contour instead of dragging corners.
base = Path('/Users/Shared/My DAZ 3D Library/data/DAZ 3D/Genesis 9/Base')
def read_dsf(path):
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if data[:2] == b'\x1f\x8b' else data)
geom = read_dsf(base/'Genesis9.dsf')['geometry_library'][0]
assert geom['vertices']['count'] == len(body.data.vertices)
assert all(tuple(p[2:]) == tuple(q.vertices) for p,q in zip(geom['polylist']['values'],body.data.polygons)), 'Daz vertex ordering differs'
if not body.data.shape_keys:
    body.shape_key_add(name='Basis', from_mix=False)
def morph(name):
    key = body.data.shape_keys.key_blocks.get(name)
    if key:
        return key
    data = read_dsf(base/'Morphs'/'Daz 3D'/'FACS'/f'facs_bs_{name}.dsf')['modifier_library'][0]['morph']
    assert data['vertex_count'] == len(body.data.vertices)
    key = body.shape_key_add(name=name, from_mix=False)
    basis=body.data.shape_keys.key_blocks['Basis']
    for i,v in enumerate(key.data):
        v.co=basis.data[i].co
    for index, x, y, z in data['deltas']['values']:
        key.data[index].co += Vector((x,y,z))
    return key
smiles = [morph('MouthSmileLeft'), morph('MouthSmileRight')]
blink_keys = [morph('EyeBlinkLeft'), morph('EyeBlinkRight')]
for key in smiles:
    key.value = .22

# Arms hang in a relaxed anatomical position, with a small elbow bend.
arm_deltas = {}
for side, sign in [('l',1),('r',-1)]:
    for name, child, target in [
        (side+'_upperarm',side+'_forearm',Vector((sign*.28,.015,-1))),
        (side+'_forearm',side+'_hand',Vector((sign*.10,-.12,-1))),
        (side+'_hand',side+'_mid1',Vector((sign*.04,-.03,-1))),
    ]:
        arm_deltas[name] = (point(child)-point(name)).rotation_difference(target)

# Physical joint marker at ball of each foot stays anchored throughout the raise.
toe_rest = {side:point(side+'_toes') for side in ['l','r']}
foot_vectors = {side:point(side+'_toes')-point(side+'_foot') for side in ['l','r']}
metrics=[]
FPS=24
N=288
camera=scene.camera
camera.location=(.48,-5.7,1.65)
def aim(obj, target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
aim(camera,(0,0,.86))
camera.data.type='ORTHO'
camera.data.ortho_scale=3.65
scene.render.engine='BLENDER_EEVEE'
scene.eevee.taa_render_samples=48
scene.render.resolution_x=1920
scene.render.resolution_y=1080
scene.render.resolution_percentage=100
scene.render.fps=FPS
scene.render.image_settings.file_format='PNG'
scene.render.image_settings.color_mode='RGBA'
scene.render.film_transparent=True
scene.frame_start=1
scene.frame_end=N
for f in range(1,N+1):
    scene.frame_set(f)
    t=(f-1)/FPS
    # One deliberately slow cycle; transfer before rise and after heel contact.
    p=max(0,t-1)
    def smooth(x):
        x=max(0,min(1,x)); return x*x*x*(10+x*(-15+6*x))
    rise = smooth((p-1.5)/2) if p<3.5 else 1 if p<4.5 else 1-smooth((p-4.5)/3) if p<7.5 else 0
    transfer=smooth(p/1.5) if p<1.5 else 1 if p<7.5 else 1-smooth((p-7.5)/1.5)
    if t<1 or t>=10: rise=transfer=0
    theta=.42*rise
    q=Quaternion((1,0,0),theta)
    # Move the body over the forefoot support instead of lifting vertically behind it.
    lean=Quaternion((1,0,0),.10*transfer)
    center=Vector((0,0,.9022))
    shift=sum((toe_rest[side]-q@foot_vectors[side]-(center+lean@(point(side+'_foot')-center)) for side in ['l','r']),Vector())/2
    root.location=center+shift
    root.rotation_euler=lean.to_euler()
    for bone in rig.pose.bones:
        if not bone.constraints:
            bone.matrix_basis.identity()
    bpy.context.view_layer.update()
    for name,delta in arm_deltas.items():
        orient(name,lean@delta)
    for side in ['l','r']:
        orient(side+'_foot',q)
        orient(side+'_toes',Quaternion())
    # Tiny respiratory thorax motion; no head bob or exaggerated neck rotation.
    bone=rig.pose.bones['spine4']
    bone.scale=(1+ .0018*math.sin(t*math.tau/4),1,1)
    blink=max(math.exp(-((t-at)/.065)**2) for at in [1.8,5.4,9.3])
    for key in blink_keys:
        key.value=blink
        key.keyframe_insert(data_path='value',frame=f)
    for side in ['l','r']:
        for suffix,angle in [('eyelidupper',50),('eyelidlower',-6)]:
            lid=rig.pose.bones[side+'_'+suffix]
            lid.rotation_quaternion=Quaternion((1,0,0),math.radians(angle)*blink)
            lid.keyframe_insert(data_path='rotation_quaternion',frame=f)
    root.keyframe_insert(data_path='location',frame=f)
    root.keyframe_insert(data_path='rotation_euler',frame=f)
    for name in list(arm_deltas)+['l_foot','r_foot','l_toes','r_toes']:
        rig.pose.bones[name].keyframe_insert(data_path='rotation_quaternion',frame=f)
    bone.keyframe_insert(data_path='scale',frame=f)
    bpy.context.view_layer.update()
    contacts=[]
    for side in ['l','r']:
        pos=rig.matrix_world@rig.pose.bones[side+'_toes'].head
        uv=world_to_camera_view(scene,camera,pos)
        contacts.append({'drift_m':(pos-toe_rest[side]).length,'pixel':[uv.x*1920,(1-uv.y)*1080], 'z':pos.z})
    metrics.append({'frame':f,'angle_deg':math.degrees(theta),'body_lean_deg':math.degrees(.10*transfer),'rise_m':shift.z,'contacts':contacts})
max_drift=max(c['drift_m'] for frame in metrics for c in frame['contacts'])
assert max_drift<.0001, f'Forefoot sliding {max_drift}m'
(OUT/'contact-review.json').write_text(json.dumps({'exercise':'standing-double-heel-raise','method':'Reference-authored joint kinematics; not mocap or rigid-body simulation','qualified_form_review':False,'max_forefoot_marker_drift_m':max_drift,'frames':metrics},indent=2))
scene['exercise']='Standing double heel raise — one slow controlled repetition'
scene['review_status']='Demo only; numerical contact check is not qualified form review'
scene.frame_set(60)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'kat-heel-raise-review.blend'),compress=True)
if '--render' in sys.argv:
    (OUT/'frames').mkdir(exist_ok=True)
    scene.render.filepath=str(OUT/'frames'/'f-')
    bpy.ops.render.render(animation=True)
else:
    for frame in [1,61,131]:
        scene.frame_set(frame)
        scene.render.filepath=str(OUT/f'pose-{frame}.png')
        bpy.ops.render.render(write_still=True)
    camera.location=(.12,-3,1.58)
    aim(camera,(0,0,1.48))
    camera.data.ortho_scale=.48
    scene.render.resolution_x=800
    scene.render.resolution_y=800
    for frame in [1,44]:
        scene.frame_set(frame)
        scene.render.filepath=str(OUT/f'face-{frame}.png')
        bpy.ops.render.render(write_still=True)
    print('CONTACT_DRIFT_METRES',max_drift,flush=True)
