"""Transfer two squats from the CMU Graphics Lab capture to Maya.

Use animations/14_06.fbx from https://huggingface.co/datasets/gbionics/cmu-fbx.
Open maya-trainer-contour-fit.blend in Blender before running this script.
Pass the FBX and frame output directory after Blender's -- separator.
"""

import argparse
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector


def basis(up, right):
    up = up.normalized()
    across = (right - right.project(up)).normalized()
    forward = up.cross(across)
    return Matrix((across, forward, up)).transposed().to_quaternion()


def align(bone, world_rotation):
    """Apply a rest-to-pose rotation in armature space, preserving the joint."""
    current = bone.matrix.to_quaternion()
    matrix = (world_rotation @ current.inverted()).to_matrix().to_4x4() @ bone.matrix
    matrix.translation = bone.head
    bone.matrix = matrix


def swing(bone, rest_direction, target_direction):
    rest_rotation = bone.bone.matrix_local.to_quaternion()
    align(bone, rest_direction.rotation_difference(target_direction) @ rest_rotation)


def knee_target(hip, ankle, pole, upper_length, lower_length):
    direction = (ankle - hip).normalized()
    reach = min((ankle - hip).length, upper_length + lower_length - .0001)
    projection = (upper_length**2 - lower_length**2 + reach**2) / (2 * reach)
    outward = (pole - pole.project(direction)).normalized()
    return hip + direction * projection + outward * math.sqrt(max(0, upper_length**2 - projection**2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("fbx", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--frames", type=int, nargs="*")
    parser.add_argument("--cpu", action="store_true", help="Use Cycles CPU for rendering")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    args.output.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    rig = next(obj for obj in scene.objects if obj.name.startswith("Maya • reusable"))
    # Keep the reusable mesh and its expressions. The original action also
    # contains unrelated coaching gestures, so the squat owns its body pose.
    rig.animation_data_clear()
    bpy.ops.import_scene.fbx(filepath=str(args.fbx))
    source = next(obj for obj in bpy.context.selected_objects if obj.type == "ARMATURE")
    source.hide_render = True
    capture = source.pose.bones
    bones = rig.pose.bones
    rest = lambda name: bones[name].bone.head_local.copy()

    camera = bpy.data.objects["Full body"]
    scene.camera = camera
    camera.location = (-3.1, -5.5, 1.20)
    camera.rotation_euler = (Vector((0, 0, .84)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.ortho_scale = 1.93
    bpy.data.objects["Studio backdrop"].hide_render = True
    scene.render.film_transparent = True
    scene.render.resolution_x = 448
    scene.render.resolution_y = 544
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    if args.cpu:
        scene.render.engine = "CYCLES"
        scene.cycles.device = "CPU"
        scene.cycles.samples = 12
        scene.cycles.use_denoising = True
    else:
        scene.eevee.taa_render_samples = 16

    # Reuse the mesh correction for folded leggings, including sock cuffs.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from posed_cloth import PosedWaistband

    body = next(obj for obj in scene.objects if obj.get("maya_body"))
    leggings = next(obj for obj in scene.objects if obj.get("maya_outfit") == "studio-set")
    pelvis = leggings.vertex_groups.get("root") or leggings.vertex_groups.new(name="root")
    for vertex in leggings.data.vertices:
        z = vertex.co.z
        if .875 < z < 1.0:
            t = min(1., (z - .875) / .081)
            blend = .93 * t * t * (3 - 2 * t)
            weights = {g.group: g.weight for g in vertex.groups}
            for group, weight in weights.items():
                leggings.vertex_groups[group].add([vertex.index], weight * (1 - blend), "REPLACE")
            pelvis_weight = weights.get(pelvis.index, 0.)
            pelvis.add([vertex.index], pelvis_weight * (1 - blend) + blend, "REPLACE")
    waistband = PosedWaistband(body, leggings)
    shoes = next(obj for obj in scene.objects if obj.name.endswith(".shoes05"))
    covered = shoes.vertex_groups.new(name="Cuffs under leggings")
    covered.add([v.index for v in shoes.data.vertices if v.co.z > .125], 1., "REPLACE")
    mask = shoes.modifiers.new("Covered cuffs", "MASK")
    mask.vertex_group = covered.name
    mask.invert_vertex_group = True

    hip_samples = []
    for frame in (254, 257, 260, 263, 266):
        scene.frame_set(frame)
        hip_samples.append(capture["hip"].head.copy())
    baseline = sum(hip_samples, Vector()) / len(hip_samples)
    rest_torso = basis(rest("neck01") - rest("spine04"), rest("upperarm01.L") - rest("upperarm01.R"))
    view = bpy.context.view_layer
    max_slide = 0.
    fps = 30
    # Two consecutive recorded reps. Slow the take slightly to make the
    # movement readable as a coaching demo.
    for index in args.frames if args.frames is not None else range(186):
        sample = 254 + index * .8
        scene.frame_set(int(sample), subframe=sample % 1)
        pos = lambda name: capture[name].head.copy()
        offset = pos("hip") - baseline
        offset = Vector((offset.x * .0075, offset.y * .0095, offset.z * .0048))
        root = bones["root"]
        root.location = root.bone.matrix_local.to_3x3().inverted() @ offset
        view.update()

        torso = basis(pos("neck") - pos("abdomen"), pos("lShldr") - pos("rShldr"))
        spine = bones["spine04"]
        align(spine, torso @ rest_torso.inverted() @ spine.bone.matrix_local.to_quaternion())
        view.update()
        for side, source_side in (("L", "l"), ("R", "r")):
            thigh, shin, foot = (bones[f"{name}.{side}"] for name in ("upperleg01", "lowerleg01", "foot"))
            upper = shin.bone.head_local - thigh.bone.head_local
            lower = foot.bone.head_local - shin.bone.head_local
            ankle = foot.bone.head_local
            hip = thigh.head.copy()
            pole = pos(source_side + "Shin") - pos(source_side + "Thigh")
            # Preserve the capture timing while mapping the knee direction
            # to Maya's narrower, forward-facing foot stance.
            side_sign = 1 if side == "L" else -1
            pole = Vector((.18 * side_sign, -1, 0)) + pole.normalized() * .32
            knee = knee_target(hip, ankle, pole, upper.length, lower.length)
            swing(thigh, upper, knee - hip)
            view.update()
            swing(shin, lower, ankle - knee)
            view.update()
            align(foot, foot.bone.matrix_local.to_quaternion())
            view.update()
            max_slide = max(max_slide, (foot.head - ankle).length)

            arm, forearm, hand = (bones[f"{name}.{side}"] for name in ("upperarm01", "lowerarm01", "wrist"))
            swing(arm, forearm.bone.head_local - arm.bone.head_local,
                  pos(source_side + "ForeArm") - pos(source_side + "Shldr"))
            view.update()
            swing(forearm, hand.bone.head_local - forearm.bone.head_local,
                  pos(source_side + "Hand") - pos(source_side + "ForeArm"))
            view.update()

        waistband.fit(offset, max_correction=.024)
        scene.render.filepath = str(args.output / f"{index:04d}.png")
        bpy.ops.render.render(write_still=True)
    print(f"Maximum ankle drift: {max_slide * 100:.2f} cm at {fps} fps")


if __name__ == "__main__":
    main()
