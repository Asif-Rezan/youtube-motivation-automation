"""Correct the upper leggings against the posed torso before rendering."""

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def smooth(value):
    value=max(0.,min(1.,value))
    return value*value*(3-2*value)


class PosedWaistband:
    def __init__(self, body, leggings):
        self.body=body
        self.leggings=leggings
        self.body_masks=[m for m in body.modifiers if m.type=="MASK" and m.name.startswith(("Delete.","Maya studio"))]
        rest_height=leggings.data.attributes.new(name="Waist fit rest height",type="FLOAT",domain="POINT")
        for v in leggings.data.vertices:
            rest_height.data[v.index].value=v.co.z if v.co.z<1.023 else 0.
        mesh=bpy.data.meshes.new("Temporary evaluated workout garments")
        self.proxy=bpy.data.objects.new("Maya • pose-fitted workout outfit",mesh)
        bpy.context.scene.collection.objects.link(self.proxy)
        # Keep Blender's native render evaluation for shirt sleeves.
        top=leggings.vertex_groups.new(name="Render original shirt only")
        top.add([v.index for v in leggings.data.vertices if v.co.z>1.023],1.,"REPLACE")
        shirt_only=leggings.modifiers.new("Render original shirt only","MASK")
        shirt_only.vertex_group=top.name
        shirt_only.show_viewport=False
        shirt_only.show_render=True

    def fit(self, root_shift):
        # Resolve the collision against the deformed skin rather than
        # comparing the rest mesh or tinting visible skin green.
        original=[m.show_viewport for m in self.body_masks]
        for m in self.body_masks:
            m.show_viewport=False
        bpy.context.view_layer.update()
        depsgraph=bpy.context.evaluated_depsgraph_get()
        skin=BVHTree.FromObject(self.body,depsgraph)
        leggings=self.leggings.evaluated_get(depsgraph)
        mesh=bpy.data.meshes.new_from_object(leggings,preserve_all_data_layers=True,depsgraph=depsgraph)
        self.proxy.matrix_world=self.leggings.matrix_world
        # The evaluated viewport mesh is used only for the fitted leggings.
        editable=bmesh.new()
        editable.from_mesh(mesh)
        for face in list(editable.faces):
            if face.material_index==0:
                editable.faces.remove(face)
        unused=[v for v in editable.verts if not v.link_faces]
        if unused:
            bmesh.ops.delete(editable,geom=unused,context="VERTS")
        editable.to_mesh(mesh)
        editable.free()
        for m,enabled in zip(self.body_masks,original):
            m.show_viewport=enabled
        rest=mesh.attributes["Waist fit rest height"].data
        for vertex in mesh.vertices:
            rest_z=rest[vertex.index].value
            strength=smooth((rest_z-.803)/.076)
            if strength<.001:
                continue
            x,y,z=vertex.co
            center=Vector((root_shift.x,root_shift.y-.040,z))
            outward=Vector((x-center.x,y-center.y,0))
            radius=outward.length
            if radius<.015:
                continue
            outward/=radius
            hit,_,_,_=skin.ray_cast(center+outward*.34,-outward,.333)
            if hit is None:
                continue
            envelope=(hit-center).dot(outward)
            # Hold a little room on the back and front where the pelvis flexes.
            safe=envelope+.006+.006*abs(outward.y)
            correction=max(0.,safe-radius)
            if correction>0:
                vertex.co+=outward*(correction*strength)
        prior=self.proxy.data
        self.proxy.data=mesh
        bpy.data.meshes.remove(prior)
        mesh.update()
        bpy.context.view_layer.update()
