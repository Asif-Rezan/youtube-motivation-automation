import bpy
from io_scene_fbx import import_fbx
original_link = import_fbx.FbxImportHelperNode.link_hierarchy
def link_valid_skin_bindings(self, *args):
    # Daz exports stale associations for hidden fitted items. Keep only
    # associations that actually include this armature's FBX bind matrices.
    if self.is_armature and self.meshes:
        self.meshes = {m for m in self.meshes if self in m.armature_setup}
    return original_link(self, *args)
import_fbx.FbxImportHelperNode.link_hierarchy = link_valid_skin_bindings
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath='/Users/asif/Documents/DAZ 3D/kat-outfit-trainer.fbx')
for o in bpy.data.objects:
 print('OBJECT',o.name,o.type,tuple(round(x,3) for x in o.dimensions))
 if o.type=='ARMATURE':print('BONES',','.join(b.name for b in o.data.bones))
bpy.ops.wm.save_as_mainfile(filepath='/Users/asif/Documents/DAZ 3D/trainer-import.blend')
