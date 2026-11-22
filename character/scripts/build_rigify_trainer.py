"""Generate a fitted Rigify control rig without replacing the Daz facial rig.

Run in Blender with kat-rokoko-walk-v1.blend open. Output is a separate scene.
"""
import bpy, importlib, json, os
from pathlib import Path
from mathutils import Vector

OUT = Path(os.environ.get('FITNESS_RIGIFY_DIR', '/Users/asif/Documents/fitness-rigify-review'))
OUT.mkdir(parents=True, exist_ok=True)
import rigify
bpy.ops.preferences.addon_enable(module='rigify')
from rigify.metarigs.Basic import basic_human

s = bpy.context.scene
a = bpy.data.objects['Genesis9']
s.frame_set(1)
rest = {b.name: a.matrix_world @ b.matrix_local for b in a.data.bones}
def p(n): return rest[n].translation.copy()

# Independent animated reference prevents a target -> source dependency cycle.
source = a.copy()
source.data = a.data.copy()
source.name = 'Rokoko_Baked_Source'
s.collection.objects.link(source)
source.hide_render = True
source.hide_set(True)

bpy.ops.object.select_all(action='DESELECT')
meta = bpy.data.objects.new('Trainer_Metarig', bpy.data.armatures.new('Trainer_Metarig'))
s.collection.objects.link(meta)
meta.select_set(True)
bpy.context.view_layer.objects.active = meta
basic_human.create(meta)
if meta.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.mode_set(mode='EDIT')
eb = meta.data.edit_bones
def fit(n, head, tail):
    b = eb[n]
    b.use_connect = False
    b.head, b.tail = head, tail
    b.roll = 0

# Seven anatomical spine segments; Daz's arbitrary bone tails are not used.
chain = ['hip', 'spine1', 'spine2', 'spine4', 'neck1', 'neck2', 'head']
for i, n in enumerate(chain):
    fit('spine' + ('.%03d' % i if i else ''), p(n), p(chain[i+1]) if i < 6 else p('head') + Vector((0,0,.17)))
for side, suffix in [('l','L'), ('r','R')]:
    for name, start, end in [('thigh','thigh','shin'), ('shin','shin','foot'), ('foot','foot','toes'),
                             ('shoulder','shoulder','upperarm'), ('upper_arm','upperarm','forearm'),
                             ('forearm','forearm','hand'), ('hand','hand','mid1')]:
        fit(name+'.'+suffix, p(side+'_'+start), p(side+'_'+end))
    toe = p(side+'_toes')
    fit('toe.'+suffix, toe, toe+Vector((0,-.065,0)))
    heel = p(side+'_foot'); heel.y += .025; heel.z = .002
    fit('heel.02.'+suffix, heel+Vector((-.035,0,0)), heel+Vector((.035,0,0)))
    fit('pelvis.'+suffix, p('hip'), p(side+'_thigh'))
    # Decorative breast controls are unnecessary: native body shape stays intact.
    eb.remove(eb['breast.'+suffix])
for i in [1,2,3,5,6]:
    eb['spine.%03d' % i].use_connect = True
for suffix in ['L','R']:
    for name in ['shin','foot','toe','forearm','hand']:
        eb[name+'.'+suffix].use_connect = True
bpy.ops.object.mode_set(mode='OBJECT')
meta.pose.bones['spine'].rigify_parameters.make_fk_controls = True
bpy.ops.pose.rigify_generate()
rig = bpy.context.object
rig.name = 'Trainer_Rigify'
rig.show_in_front = True
meta.hide_render = True
meta.hide_set(True)
report = {b.name: {'parent': b.parent.name if b.parent else None,
                  'properties': {k: str(b[k]) for k in b.keys()}}
          for b in rig.pose.bones if not b.name.startswith(('ORG-','MCH-','DEF-'))}
(OUT/'rigify-controls.json').write_text(json.dumps(report, indent=2))
rig['motion_source'] = 'Official Rokoko offline retarget bake, preserved as Rokoko_Baked_Source'
rig['status'] = 'Generated fitted control rig; motion transfer and IK review pending'
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'kat-rigify-controls.blend'), compress=True)
print('RIGIFY_GENERATED', len(rig.pose.bones), flush=True)
