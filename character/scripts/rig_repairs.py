"""Repairs for the imported Daz accessory skeletons."""
def repair_mouth_chain(rig, mouth):
    # Tongue bones belong to the imported mouth's duplicate skeleton, even after
    # vertex groups upperteeth/lowerteeth are renamed to the main body bones.
    ancestors=set()
    for group in mouth.vertex_groups:
        bone=rig.pose.bones.get(group.name)
        if bone:
            ancestors.add(bone.name)
            ancestors.update(parent.name for parent in bone.parent_recursive)
    repaired=[]
    for name in ancestors:
        base=name.split('.')[0]
        if base==name or base not in rig.pose.bones:continue
        bone=rig.pose.bones[name]
        constraint=next((c for c in bone.constraints if c.name=='Follow main facial rig'),None)
        if constraint is None:constraint=bone.constraints.new('COPY_TRANSFORMS')
        constraint.name='Follow main facial rig';constraint.target=rig;constraint.subtarget=base
        constraint.target_space='POSE';constraint.owner_space='POSE'
        repaired.append(name)
    return sorted(repaired)
