"""Choose hair, outfit and independent fabric colors on the packed Maya rig."""
import bpy

HAIR_STYLES=("loose-long","tied-long")
OUTFITS=("studio-set","training-set")
PALETTES=(
    ("#ef554a","#009b91"),
    ("#cf3976","#4b233d"),
    ("#b952d3","#243957"),
    ("#e9ad56","#2c356e"),
    ("#635ac8","#bc554a"),
)


def linear_color(hex_value):
    raw=hex_value.removeprefix("#")
    if len(raw)!=6:
        raise ValueError("Expected a six-digit fabric color")
    srgb=[int(raw[i:i+2],16)/255 for i in (0,2,4)]
    return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in srgb)+(1.,)


def set_appearance(hair_style, outfit_name, top_hex, bottom_hex):
    if hair_style not in HAIR_STYLES or outfit_name not in OUTFITS:
        raise ValueError("Unknown Maya hair style or outfit")
    colors=(linear_color(top_hex),linear_color(bottom_hex))
    chosen=None
    for obj in bpy.data.objects:
        if "maya_hair_style" in obj:
            visible=obj["maya_hair_style"]==hair_style
            obj.hide_render=not visible
            obj.hide_set(not visible)
        elif "maya_outfit" in obj:
            visible=obj["maya_outfit"]==outfit_name
            obj.hide_render=not visible
            obj.hide_set(not visible)
            if visible:
                chosen=obj
        if obj.get("maya_body"):
            for mod in obj.modifiers:
                if mod.name=="Maya studio waist occlusion":
                    mod.show_render=outfit_name=="studio-set"
                    mod.show_viewport=mod.show_render
                if mod.type=="MASK" and mod.name.startswith("Delete.female_"):
                    visible=mod.name==f"Delete.{OUTFIT_PROXIES[outfit_name]}"
                    mod.show_render=visible
                    mod.show_viewport=visible
    if chosen is None:
        raise RuntimeError("The selected wardrobe mesh is missing from the Blender file")
    for material,color in zip(chosen.data.materials,colors):
        nodes=material.node_tree.nodes
        fabric_color=nodes.get("Wardrobe base color")
        if fabric_color:
            fabric_color.outputs[0].default_value=color
        else:
            shader=next(n for n in nodes if n.type=="BSDF_PRINCIPLED")
            shader.inputs["Base Color"].default_value=color
        material.diffuse_color=color
    bpy.context.scene["maya_appearance"]=f"{hair_style}, {outfit_name}, {top_hex}, {bottom_hex}"


OUTFIT_PROXIES=dict(zip(OUTFITS,("female_sportsuit01","female_casualsuit02")))


def appearance_for_episode(episode_number):
    """Stable cycling by ordinal; consecutive episodes change hair and outfit."""
    if episode_number<1:
        raise ValueError("Episode number must start at one")
    i=episode_number-1
    return HAIR_STYLES[i%len(HAIR_STYLES)],OUTFITS[i%len(OUTFITS)],*PALETTES[i%len(PALETTES)]
