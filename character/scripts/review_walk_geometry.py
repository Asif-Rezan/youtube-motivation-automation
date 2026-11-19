"""Fix mouth accessory inheritance and measure the walking sole contacts."""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector,Quaternion

sys.path.insert(0,str(Path(__file__).parent))
from rig_repairs import repair_mouth_chain
P=Path('/Users/asif/Documents/fitness-walk-review');s=bpy.context.scene;a=bpy.data.objects['Genesis9'];body=bpy.data.objects['Genesis9.Shape']
print('MOUTH_CHAINS_REPAIRED',repair_mouth_chain(a,bpy.data.objects['Genesis9Mouth.Shape']),flush=True)
qa=[];deps=bpy.context.evaluated_depsgraph_get()
for f in range(1,241):
    s.frame_set(f);ev=body.evaluated_get(deps);mesh=ev.to_mesh()
    feet={side:[] for side in ['l','r']}
    for i,v in enumerate(mesh.vertices):
        original=body.data.vertices[i].co
        if original.y<10:feet['l' if original.x>0 else 'r'].append((ev.matrix_world@v.co).z)
    qa.append({'frame':f,'sole_min_z_m':{side:min(v) for side,v in feet.items()}})
    ev.to_mesh_clear()
print('SOLE_MIN_Z_M',{side:min(v['sole_min_z_m'][side] for v in qa) for side in ['l','r']},flush=True)
(P/'sole-review.json').write_text(json.dumps(qa,indent=2))
s.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(P/'kat-continuous-walk-final.blend'),compress=True)
for f in [1,48,96,144,192,240]:
    s.frame_set(f);s.render.filepath=str(P/f'fixed-{f}.png');bpy.ops.render.render(write_still=True)
