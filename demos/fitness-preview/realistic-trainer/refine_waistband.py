"""Fit the leggings' upper edge to the trainer's current waist surface."""

from collections import Counter
from math import atan2, cos, pi, sin

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def fit_waistband(outfit, body):
    mesh=outfit.data
    edges=Counter(edge for face in mesh.polygons if face.material_index==1 for edge in face.edge_keys)
    border={i for edge,n in edges.items() if n==1 for i in edge if mesh.vertices[i].co.z>.82}
    if len(border)<12:
        raise RuntimeError("Could not identify the top edge of the leggings")
    # Clothing masks would hide the skin underneath the garment. Temporarily
    # expose the fitted torso for raycasting and restore the masks afterward.
    masks=[(m,m.show_viewport) for m in body.modifiers if m.type=="MASK" and m.name.startswith("Delete.")]
    for mod,_ in masks:
        mod.show_viewport=False
    bpy.context.view_layer.update()
    fitted=BVHTree.FromObject(body,bpy.context.evaluated_depsgraph_get())
    for mod,visible in masks:
        mod.show_viewport=visible

    centre_y=-.036
    angles=[]
    for index in border:
        point=mesh.vertices[index].co
        angle=atan2(point.y-centre_y,point.x)
        radial=Vector((cos(angle),sin(angle),0))
        # A soft 8 mm rise at the sides keeps the top from looking ruler-flat.
        z=.963+.005*abs(cos(angle))
        origin=Vector((0,centre_y,z))+radial*.39
        location,_,_,_=fitted.ray_cast(origin,-radial,.38)
        if location is None:
            raise RuntimeError(f"Missed fitted waist at {angle:.2f} rad")
        target=location+radial*(.0055+.006*max(0.,-sin(angle))**2)
        angles.append((angle,point.copy(),target,index))
    for vertex in mesh.vertices:
        if vertex.co.z<.806 or vertex.co.z>1.025:
            continue
        angle=atan2(vertex.co.y-centre_y,vertex.co.x)
        def difference(record):
            return abs((angle-record[0]+pi)%(2*pi)-pi)
        _,base,target,_=min(angles,key=difference)
        if vertex.index not in border and vertex.co.z<=base.z:
            t=max(0.,1.-(base.z-vertex.co.z)/.126)
            t=t*t*(3.-2.*t)
            # Propagate the rise through the upper seam while retaining
            # the original drape lower on the hips.
            vertex.co.z+=t*(target.z-base.z)
            radius=Vector((vertex.co.x,vertex.co.y-centre_y,0))
            if radius.length>0:
                outward=radius.normalized()
                origin=Vector((0,centre_y,vertex.co.z))+outward*.39
                hit,_,_,_=fitted.ray_cast(origin,-outward,.38)
                if hit is not None:
                    clearance=.005+.001*t+.009*max(0.,-outward.y)**2
                    fitted_radius=(hit-Vector((0,centre_y,vertex.co.z))).dot(outward)+clearance
                    blend=max(0.,min(1.,(vertex.co.z-.81)/.095))
                    blend=blend*blend*(3.-2.*blend)
                    # Fit inward as well as outward: the original low-rise
                    # side panels otherwise keep their wider hip radius.
                    desired=radius.length+(fitted_radius-radius.length)*blend
                    vertex.co+=outward*(max(fitted_radius,desired)-radius.length)
    for _,_,target,index in angles:
        mesh.vertices[index].co=target
    mesh.update()
    return len(border)


def hide_covered_waist(body):
    """Prevent the covered torso from clipping a subdivided waistband."""
    modifiers=[(m,m.show_viewport) for m in body.modifiers if m.type in {"MASK","ARMATURE"}]
    for mod,_ in modifiers:
        mod.show_viewport=False
    bpy.context.view_layer.update()
    evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=evaluated.to_mesh()
    indices=[v.index for v in mesh.vertices if .805<v.co.z<.925 and abs(v.co.x)<.226]
    evaluated.to_mesh_clear()
    for mod,enabled in modifiers:
        mod.show_viewport=enabled
    if not indices:
        raise RuntimeError("Could not identify body vertices under the waistband")
    group=body.vertex_groups.new(name="Covered by studio waistband")
    group.add(indices,1.,"REPLACE")
    mod=body.modifiers.new("Maya studio waist occlusion","MASK")
    mod.vertex_group=group.name
    mod.invert_vertex_group=True
