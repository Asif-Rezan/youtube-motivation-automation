"""Measure actual heel/toe skin geometry at representative right-foot phases."""
import bpy,json,os
from pathlib import Path
P=Path(os.environ.get('FITNESS_REVIEW_DIR','/Users/asif/Documents/fitness-rokoko-review'))
s=bpy.context.scene;body=bpy.data.objects['Genesis9.Shape'];deps=bpy.context.evaluated_depsgraph_get()
regions={
    'heel':[v.index for v in body.data.vertices if v.co.x<0 and v.co.y<4 and v.co.z< -3],
    'toe':[v.index for v in body.data.vertices if v.co.x<0 and v.co.y<4 and v.co.z>8],
}
report=[]
for frame,phase in [(14,'heel strike'),(23,'flat stance'),(35,'toe off')]:
    s.frame_set(frame);obj=body.evaluated_get(deps);mesh=obj.to_mesh()
    heights={name:min((obj.matrix_world@mesh.vertices[i].co).z for i in ids) for name,ids in regions.items()}
    obj.to_mesh_clear();report.append({'frame':frame,'phase':phase,'height_m':heights})
print('HEEL_TOE_GEOMETRY',report,flush=True)
assert report[0]['height_m']['toe']>report[0]['height_m']['heel']+.005,'Heel strike does not lift toes'
assert abs(report[1]['height_m']['toe']-report[1]['height_m']['heel'])<.008,'Stance sole is not flat'
assert report[2]['height_m']['heel']>report[2]['height_m']['toe']+.01,'Toe off does not lift heel'
(P/'heel-toe-contact-review.json').write_text(json.dumps(report,indent=2))
