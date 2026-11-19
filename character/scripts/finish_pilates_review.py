"""Bake restrained native jaw controls, inspect geometry, and render the sample."""
import bpy, json, gzip, math, sys
from pathlib import Path
from mathutils import Quaternion, Vector
from bpy_extras.object_utils import world_to_camera_view

OUT=Path('/Users/asif/Documents/fitness-pilates-review')
s=bpy.context.scene
a=bpy.data.objects['Genesis9']
body=bpy.data.objects['Genesis9.Shape']
# Calibrate the existing review file's sole thickness once, without per-frame lift.
root=bpy.data.objects['Workout motion root']
s.frame_set(1)
offset=max(0,.9022-root.location.z)
if offset>1e-6:
    action=root.animation_data.action
    curves=[]
    if hasattr(action,'fcurves'):curves=list(action.fcurves)
    else:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:curves.extend(bag.fcurves)
    for curve in curves:
        if curve.data_path=='location' and curve.array_index==2:
            for k in curve.keyframe_points:
                k.co.y+=offset;k.handle_left.y+=offset;k.handle_right.y+=offset
            curve.update()
base=Path('/Users/Shared/My DAZ 3D Library/data/DAZ 3D/Genesis 9/Base/Morphs/Daz 3D/FACS')
raw=(base/'facs_bs_JawOpen.dsf').read_bytes()
data=json.loads(gzip.decompress(raw) if raw[:2]==b'\x1f\x8b' else raw)['modifier_library'][0]
key=body.shape_key_add(name='JawOpen',from_mix=False)
basis=body.data.shape_keys.key_blocks['Basis']
for i,v in enumerate(key.data):v.co=basis.data[i].co
for i,x,y,z in data['morph']['deltas']['values']:key.data[i].co+=Vector((x,y,z))
envelope=json.loads((OUT/'speech-envelope.json').read_text())
for frame,amount in enumerate(envelope,1):
    s.frame_set(frame)
    value=.22*amount
    key.value=value
    key.keyframe_insert(data_path='value',frame=frame)
    for formula in data['formulas']:
        target=formula['output'].split('#')[-1]
        name,channel=target.split('?')
        if name not in a.pose.bones or not channel.startswith(('translation/','rotation/')):continue
        axis='xyz'.index(channel[-1])
        coefficient=formula['operations'][1].get('val')
        if coefficient is None:raise RuntimeError('Unsupported native facial formula')
        bone=a.pose.bones[name]
        if channel.startswith('translation/'):
            bone.location[axis]=coefficient*value
            bone.keyframe_insert(data_path='location',frame=frame)
        else:
            vector=[0,0,0];vector[axis]=1
            bone.rotation_quaternion=Quaternion(vector,math.radians(coefficient)*value)
            bone.keyframe_insert(data_path='rotation_quaternion',frame=frame)

qa=[]
deps=bpy.context.evaluated_depsgraph_get()
def approximate_com():
    p=lambda name:a.matrix_world@a.pose.bones[name].head
    center=.081*(p('head')+Vector((0,0,.07)))+.497*p('hip').lerp(p('spine4'),.55)
    segments=[('upperarm','forearm',.028,.436),('forearm','hand',.016,.43),
              ('hand','mid1',.006,.506),('thigh','shin',.10,.433),
              ('shin','foot',.0465,.433),('foot','toes',.0145,.5)]
    return center+sum((mass*p(side+'_'+name).lerp(p(side+'_'+child),ratio)
        for side in ['l','r'] for name,child,mass,ratio in segments),Vector())
def hull(points):
    points=sorted(set(points))
    def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lower=[];upper=[]
    for point in points:
        while len(lower)>=2 and cross(lower[-2],lower[-1],point)<=0:lower.pop()
        lower.append(point)
    for point in reversed(points):
        while len(upper)>=2 and cross(upper[-2],upper[-1],point)<=0:upper.pop()
        upper.append(point)
    return lower[:-1]+upper[:-1]
for frame in range(1,289):
    s.frame_set(frame)
    evaluated=body.evaluated_get(deps)
    mesh=evaluated.to_mesh()
    feet=[evaluated.matrix_world@v.co for i,v in enumerate(mesh.vertices) if body.data.vertices[i].co.y<10]
    foot_z=[v.z for v in feet]
    boundary=hull([(v.x,v.y) for v in feet if v.z<min(foot_z)+.003])
    center=approximate_com()
    supported=all((boundary[(i+1)%len(boundary)][0]-point[0])*(center.y-point[1])-
        (boundary[(i+1)%len(boundary)][1]-point[1])*(center.x-point[0])>=-1e-6
        for i,point in enumerate(boundary))
    qa.append({'frame':frame,'lowest_foot_mesh_z_m':min(foot_z),
        'approximate_com':list(center),'support_hull_xy':[list(v) for v in boundary],
        'com_inside_support_hull':supported})
    evaluated.to_mesh_clear()
print('FOOT_GEOMETRY_MIN_M',min(x['lowest_foot_mesh_z_m'] for x in qa),
    'UNSUPPORTED_FRAMES',[x['frame'] for x in qa if not x['com_inside_support_hull']],flush=True)
assert min(x['lowest_foot_mesh_z_m'] for x in qa)>=0,'Foot mesh penetrates the deck'
assert all(x['com_inside_support_hull'] for x in qa),'Approximate COM leaves the support polygon'
for i,row in enumerate(qa):
    center=Vector(row['approximate_com'])
    before=Vector(qa[max(0,i-1)]['approximate_com'])
    after=Vector(qa[min(len(qa)-1,i+1)]['approximate_com'])
    acceleration=(after-2*center+before)*(24**2)
    assert 9.81+acceleration.z>0,'Invalid vertical acceleration'
    zmp=center-acceleration*(center.z/(9.81+acceleration.z))
    boundary=row['support_hull_xy']
    supported=all((boundary[(j+1)%len(boundary)][0]-point[0])*(zmp.y-point[1])-
        (boundary[(j+1)%len(boundary)][1]-point[1])*(zmp.x-point[0])>=-1e-6
        for j,point in enumerate(boundary))
    row.update(approximate_zmp_xy=list(zmp)[:2],zmp_inside_support_hull=supported)
print('DYNAMIC_SUPPORT_FAILURES',[v['frame'] for v in qa if not v['zmp_inside_support_hull']],flush=True)
assert all(v['zmp_inside_support_hull'] for v in qa),'Approximate dynamic balance leaves support'
(OUT/'foot-mesh-review.json').write_text(json.dumps(qa,indent=2))
review=json.loads((OUT/'contact-review.json').read_text())
for row in review['frames']:
    s.frame_set(row['frame'])
    for side,contact in zip(['l','r'],row['contacts']):
        pos=a.matrix_world@a.pose.bones[side+'_toes'].head
        uv=world_to_camera_view(s,s.camera,pos)
        contact['pixel']=[uv.x*1920,(1-uv.y)*1080]
        contact['z']=pos.z
review['sole_calibration_m']=.0022
(OUT/'contact-review.json').write_text(json.dumps(review,indent=2))
s['speech']='Timed voice-amplitude jaw controls plus native Daz corrective morph; not phoneme visemes'
s.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'kat-heel-raise-final.blend'),compress=True)
camera=s.camera
position=camera.location.copy();rotation=camera.rotation_euler.copy();scale=camera.data.ortho_scale
if '--render' not in sys.argv:
    camera.location=(.12,-3,1.58)
    camera.rotation_euler=(Vector((0,0,1.48))-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale=.48
    s.render.resolution_x=s.render.resolution_y=800
    peak=max(range(len(envelope)),key=envelope.__getitem__)+1
    for frame,label in [(44,'blink'),(peak,'talk')]:
        s.frame_set(frame);s.render.filepath=str(OUT/f'face-final-{label}.png');bpy.ops.render.render(write_still=True)
    camera.location=(3,-4,1.6)
    camera.rotation_euler=(Vector((0,0,.86))-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale=3.65
    s.render.resolution_x=1920;s.render.resolution_y=1080
    for frame in [1,61]:
        s.frame_set(frame);s.render.filepath=str(OUT/f'quarter-{frame}.png');bpy.ops.render.render(write_still=True)
else:
    (OUT/'frames').mkdir(exist_ok=True)
    s.render.filepath=str(OUT/'frames'/'f-')
    bpy.ops.render.render(animation=True)
