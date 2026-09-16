"""Rig the Echo astronaut, author scroll/pointer actions, render QA previews, and export GLB.

This script intentionally creates new staged files. It never overwrites the
user's existing astronaut_work_v01.blend or source GLBs.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--blend-v01", required=True)
    parser.add_argument("--blend-v02", required=True)
    parser.add_argument("--output-glb", required=True)
    parser.add_argument("--preview-dir", required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def clean_scene() -> None:
    bpy.ops.object.mode_set(mode="OBJECT") if bpy.context.object and bpy.context.object.mode != "OBJECT" else None
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (
        bpy.data.armatures,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for datablock in list(datablocks):
            datablocks.remove(datablock)


def import_astronaut(source: Path) -> bpy.types.Object:
    bpy.ops.import_scene.gltf(filepath=str(source))
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if len(meshes) != 1:
        raise RuntimeError(f"Expected one mesh, found {len(meshes)}")
    mesh = meshes[0]
    mesh.name = "EchoAstronaut"
    mesh.data.name = "EchoAstronautMesh"
    bpy.context.view_layer.objects.active = mesh
    mesh.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return mesh


def add_edit_bone(
    armature: bpy.types.Object,
    name: str,
    head: tuple[float, float, float],
    tail: tuple[float, float, float],
    parent: str | None = None,
    connected: bool = False,
    deform: bool = True,
) -> bpy.types.EditBone:
    bone = armature.data.edit_bones.new(name)
    bone.head = head
    bone.tail = tail
    bone.use_deform = deform
    if parent:
        bone.parent = armature.data.edit_bones[parent]
        bone.use_connect = connected
    return bone


def create_armature() -> bpy.types.Object:
    data = bpy.data.armatures.new("EchoAstronautRig")
    rig = bpy.data.objects.new("EchoAstronautRig", data)
    bpy.context.collection.objects.link(rig)
    rig.show_in_front = True
    rig.data.display_type = "OCTAHEDRAL"
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")

    add_edit_bone(rig, "root", (0, 0, 0.88), (0, 0, 1.00), deform=False)
    add_edit_bone(rig, "hips", (0, 0, 0.88), (0, 0, 1.04), "root")
    add_edit_bone(rig, "spine", (0, 0, 1.04), (0, 0, 1.30), "hips", connected=True)
    add_edit_bone(rig, "chest", (0, 0, 1.30), (0, 0, 1.49), "spine", connected=True)
    add_edit_bone(rig, "neck", (0, 0, 1.49), (0, 0, 1.61), "chest", connected=True)
    add_edit_bone(rig, "head", (0, 0, 1.61), (0, 0, 1.86), "neck", connected=True)

    for side, sign in (("L", 1.0), ("R", -1.0)):
        add_edit_bone(
            rig,
            f"clavicle.{side}",
            (0.06 * sign, 0, 1.45),
            (0.29 * sign, 0, 1.43),
            "chest",
        )
        add_edit_bone(
            rig,
            f"upper_arm.{side}",
            (0.29 * sign, 0, 1.43),
            (0.42 * sign, 0, 1.22),
            f"clavicle.{side}",
            connected=True,
        )
        add_edit_bone(
            rig,
            f"forearm.{side}",
            (0.42 * sign, 0, 1.22),
            (0.48 * sign, 0, 1.00),
            f"upper_arm.{side}",
            connected=True,
        )
        add_edit_bone(
            rig,
            f"hand.{side}",
            (0.48 * sign, 0, 1.00),
            (0.50 * sign, -0.01, 0.82),
            f"forearm.{side}",
            connected=True,
        )
        add_edit_bone(
            rig,
            f"thigh.{side}",
            (0.17 * sign, 0, 0.92),
            (0.18 * sign, 0, 0.56),
            "hips",
        )
        add_edit_bone(
            rig,
            f"shin.{side}",
            (0.18 * sign, 0, 0.56),
            (0.18 * sign, 0, 0.17),
            f"thigh.{side}",
            connected=True,
        )
        add_edit_bone(
            rig,
            f"foot.{side}",
            (0.18 * sign, 0, 0.17),
            (0.18 * sign, -0.16, 0.055),
            f"shin.{side}",
            connected=True,
        )

    bpy.ops.object.mode_set(mode="OBJECT")
    return rig


def smoothstep(edge0: float, edge1: float, value: float) -> float:
    if edge0 == edge1:
        return float(value >= edge1)
    t = max(0.0, min(1.0, (value - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def normalize(weights: dict[str, float]) -> dict[str, float]:
    positive = {name: weight for name, weight in weights.items() if weight > 1e-5}
    total = sum(positive.values())
    if total <= 1e-8:
        return {"hips": 1.0}
    return {name: weight / total for name, weight in positive.items()}


def weights_for_vertex(co: Vector) -> dict[str, float]:
    x, _, z = co
    ax = abs(x)

    # Arms and hands. The shoulder band deliberately blends into the chest.
    if ax > 0.255 and 0.73 < z < 1.54:
        side = "L" if x > 0 else "R"
        weights: dict[str, float] = {}
        if z >= 1.28:
            upper = smoothstep(1.28, 1.42, z)
            weights[f"upper_arm.{side}"] = 0.72 + upper * 0.18
            weights[f"clavicle.{side}"] = 0.18
            weights["chest"] = max(0.0, 0.22 - upper * 0.18)
        elif z >= 1.13:
            fore = smoothstep(1.13, 1.28, z)
            weights[f"forearm.{side}"] = 0.62 * (1 - fore)
            weights[f"upper_arm.{side}"] = 0.38 + 0.62 * fore
        elif z >= 0.93:
            hand_blend = 1 - smoothstep(0.93, 1.04, z)
            weights[f"forearm.{side}"] = 1 - hand_blend * 0.5
            weights[f"hand.{side}"] = hand_blend * 0.5
        else:
            weights[f"hand.{side}"] = 1.0
        return normalize(weights)

    # Helmet and neck.
    if z >= 1.57:
        neck_mix = 1 - smoothstep(1.57, 1.66, z)
        return normalize({"head": 1.0 - neck_mix * 0.35, "neck": neck_mix * 0.35})

    # Torso, backpack, and pelvis.
    if z >= 0.91 and ax < 0.40:
        if z >= 1.43:
            return normalize({"chest": 0.58, "neck": 0.42})
        if z >= 1.24:
            chest_mix = smoothstep(1.24, 1.38, z)
            return normalize({"spine": 1.0 - chest_mix, "chest": chest_mix})
        if z >= 1.03:
            spine_mix = smoothstep(1.03, 1.18, z)
            return normalize({"hips": 1.0 - spine_mix, "spine": spine_mix})
        return {"hips": 1.0}

    # Legs and boots.
    side = "L" if x >= 0 else "R"
    if z >= 0.63:
        return normalize({f"thigh.{side}": 0.88, "hips": 0.12})
    if z >= 0.49:
        shin_mix = 1 - smoothstep(0.49, 0.63, z)
        return normalize(
            {
                f"thigh.{side}": 1.0 - shin_mix * 0.58,
                f"shin.{side}": shin_mix * 0.58,
            }
        )
    if z >= 0.15:
        foot_mix = 1 - smoothstep(0.15, 0.25, z)
        return normalize(
            {
                f"shin.{side}": 1.0 - foot_mix * 0.45,
                f"foot.{side}": foot_mix * 0.45,
            }
        )
    return {f"foot.{side}": 1.0}


def bind_mesh(mesh: bpy.types.Object, rig: bpy.types.Object) -> None:
    deform_bones = [bone.name for bone in rig.data.bones if bone.use_deform]
    groups = {name: mesh.vertex_groups.new(name=name) for name in deform_bones}
    for vertex in mesh.data.vertices:
        for name, weight in weights_for_vertex(vertex.co).items():
            if name in groups:
                groups[name].add([vertex.index], weight, "REPLACE")

    modifier = mesh.modifiers.new("EchoAstronautArmature", "ARMATURE")
    modifier.object = rig
    modifier.use_deform_preserve_volume = False
    mesh.parent = rig


def add_controller(name: str, location: tuple[float, float, float]) -> bpy.types.Object:
    controller = bpy.data.objects.new(name, None)
    controller.empty_display_type = "SPHERE"
    controller.empty_display_size = 0.045
    controller.location = location
    bpy.context.collection.objects.link(controller)
    return controller


def add_ik(
    rig: bpy.types.Object,
    bone_name: str,
    target: bpy.types.Object,
    pole: bpy.types.Object,
    chain_count: int = 2,
) -> None:
    pose_bone = rig.pose.bones[bone_name]
    constraint = pose_bone.constraints.new("IK")
    constraint.name = f"IK_{bone_name}"
    constraint.target = target
    constraint.pole_target = pole
    constraint.chain_count = chain_count
    constraint.use_tail = True
    constraint.pole_angle = math.pi / 2


def add_rotation_controller(
    rig: bpy.types.Object,
    bone_name: str,
    controller: bpy.types.Object,
) -> None:
    constraint = rig.pose.bones[bone_name].constraints.new("COPY_ROTATION")
    constraint.name = f"ROT_{bone_name}"
    constraint.target = controller
    constraint.owner_space = "LOCAL"
    constraint.target_space = "LOCAL"


def create_controllers(rig: bpy.types.Object) -> dict[str, bpy.types.Object]:
    controllers = {
        "hand.L": add_controller("CTRL_hand.L", (0.48, 0, 1.00)),
        "hand.R": add_controller("CTRL_hand.R", (-0.48, 0, 1.00)),
        "foot.L": add_controller("CTRL_foot.L", (0.18, 0, 0.17)),
        "foot.R": add_controller("CTRL_foot.R", (-0.18, 0, 0.17)),
        "pole_arm.L": add_controller("CTRL_pole_arm.L", (0.72, -0.42, 1.22)),
        "pole_arm.R": add_controller("CTRL_pole_arm.R", (-0.72, -0.42, 1.22)),
        "pole_leg.L": add_controller("CTRL_pole_leg.L", (0.28, -0.55, 0.56)),
        "pole_leg.R": add_controller("CTRL_pole_leg.R", (-0.28, -0.55, 0.56)),
        "spine": add_controller("CTRL_spine", (0, 0, 1.18)),
        "chest": add_controller("CTRL_chest", (0, 0, 1.38)),
        "head": add_controller("CTRL_head", (0, 0, 1.72)),
    }
    add_ik(rig, "forearm.L", controllers["hand.L"], controllers["pole_arm.L"])
    add_ik(rig, "forearm.R", controllers["hand.R"], controllers["pole_arm.R"])
    add_ik(rig, "shin.L", controllers["foot.L"], controllers["pole_leg.L"])
    add_ik(rig, "shin.R", controllers["foot.R"], controllers["pole_leg.R"])
    add_rotation_controller(rig, "spine", controllers["spine"])
    add_rotation_controller(rig, "chest", controllers["chest"])
    add_rotation_controller(rig, "head", controllers["head"])
    return controllers


def key_location(
    controller: bpy.types.Object,
    frame: int,
    value: tuple[float, float, float],
) -> None:
    controller.location = value
    controller.keyframe_insert(data_path="location", frame=frame)


def key_rotation(
    controller: bpy.types.Object,
    frame: int,
    value: tuple[float, float, float],
) -> None:
    controller.rotation_mode = "XYZ"
    controller.rotation_euler = value
    controller.keyframe_insert(data_path="rotation_euler", frame=frame)


def set_controller_interpolation(controllers: dict[str, bpy.types.Object]) -> None:
    for controller in controllers.values():
        action = controller.animation_data.action if controller.animation_data else None
        if not action:
            continue
        # Blender 5.2 stores freshly keyed curves in layered action channel
        # bags instead of exposing Action.fcurves. Default interpolation is
        # already Bezier, so older versions receive auto-clamped handles while
        # the layered-action path safely keeps Blender's defaults.
        fcurves = getattr(action, "fcurves", None)
        if fcurves is None:
            continue
        for fcurve in fcurves:
            for point in fcurve.keyframe_points:
                point.interpolation = "BEZIER"
                point.handle_left_type = "AUTO_CLAMPED"
                point.handle_right_type = "AUTO_CLAMPED"


def clear_controller_animation(controllers: dict[str, bpy.types.Object]) -> None:
    for controller in controllers.values():
        controller.animation_data_clear()
        controller.location = (0, 0, 0)
        controller.rotation_euler = (0, 0, 0)


def author_scroll_controls(controllers: dict[str, bpy.types.Object]) -> tuple[int, int]:
    poses = [
        # frame, left hand, right hand, left foot, right foot
        (
            1,
            (0.68, -0.16, 1.60),
            (-0.68, -0.16, 1.58),
            (0.18, 0.00, 0.17),
            (-0.18, 0.00, 0.17),
        ),
        (
            82,
            (0.58, -0.22, 1.47),
            (-0.52, -0.20, 1.32),
            (0.20, 0.06, 0.20),
            (-0.19, 0.02, 0.18),
        ),
        (
            154,
            (0.42, -0.32, 1.31),
            (-0.34, -0.34, 1.43),
            (0.26, 0.22, 0.41),
            (-0.26, 0.12, 0.50),
        ),
        (
            236,
            (0.54, -0.26, 1.10),
            (-0.43, -0.30, 1.49),
            (0.31, 0.17, 0.48),
            (-0.22, 0.26, 0.38),
        ),
        (
            318,
            (0.69, -0.15, 1.57),
            (-0.66, -0.15, 1.55),
            (0.20, 0.04, 0.20),
            (-0.20, 0.04, 0.20),
        ),
        (
            392,
            (0.50, -0.06, 1.08),
            (-0.49, -0.05, 1.06),
            (0.18, 0.00, 0.17),
            (-0.18, 0.00, 0.17),
        ),
        (
            450,
            (0.48, 0.00, 1.00),
            (-0.48, 0.00, 1.00),
            (0.18, 0.00, 0.17),
            (-0.18, 0.00, 0.17),
        ),
    ]
    for frame, hand_l, hand_r, foot_l, foot_r in poses:
        key_location(controllers["hand.L"], frame, hand_l)
        key_location(controllers["hand.R"], frame, hand_r)
        key_location(controllers["foot.L"], frame, foot_l)
        key_location(controllers["foot.R"], frame, foot_r)

    body_rotations = [
        (1, (0.00, 0.00, 0.00), (0.00, 0.00, 0.00), (0.00, 0.00, 0.00)),
        (82, (0.08, -0.04, 0.04), (0.05, -0.10, 0.08), (0.02, -0.14, 0.02)),
        (154, (-0.18, 0.08, -0.12), (-0.28, 0.12, -0.16), (0.12, 0.10, -0.08)),
        (236, (0.14, -0.10, 0.13), (0.22, -0.16, 0.20), (-0.10, -0.12, 0.11)),
        (318, (0.04, 0.03, -0.04), (0.06, 0.04, -0.06), (0.02, 0.04, -0.03)),
        (392, (0.00, 0.00, 0.00), (0.00, 0.00, 0.00), (0.00, 0.00, 0.00)),
        (450, (0.00, 0.00, 0.00), (0.00, 0.00, 0.00), (0.00, 0.00, 0.00)),
    ]
    for frame, spine, chest, head in body_rotations:
        key_rotation(controllers["spine"], frame, spine)
        key_rotation(controllers["chest"], frame, chest)
        key_rotation(controllers["head"], frame, head)

    set_controller_interpolation(controllers)
    return 1, 450


def author_pointer_controls(controllers: dict[str, bpy.types.Object]) -> tuple[int, int]:
    # Pointer progress 0 -> neutral, 1 -> raised hand. The web layer scrubs this
    # clip with damped pointer input, reproducing the reference's elastic wave.
    for frame, hand_l, hand_r in (
        (1, (0.48, 0.00, 1.00), (-0.48, 0.00, 1.00)),
        (30, (0.58, -0.10, 1.32), (-0.48, 0.00, 1.00)),
        (60, (0.62, -0.12, 1.73), (-0.48, 0.00, 1.00)),
    ):
        key_location(controllers["hand.L"], frame, hand_l)
        key_location(controllers["hand.R"], frame, hand_r)
        key_location(controllers["foot.L"], frame, (0.18, 0.00, 0.17))
        key_location(controllers["foot.R"], frame, (-0.18, 0.00, 0.17))

    for frame, spine, chest, head in (
        (1, (0, 0, 0), (0, 0, 0), (0, 0, 0)),
        (30, (0, 0.02, -0.02), (0.01, 0.04, -0.04), (0, 0.06, -0.02)),
        (60, (0, 0.05, -0.04), (0.02, 0.08, -0.08), (0, 0.12, -0.04)),
    ):
        key_rotation(controllers["spine"], frame, spine)
        key_rotation(controllers["chest"], frame, chest)
        key_rotation(controllers["head"], frame, head)

    set_controller_interpolation(controllers)
    return 1, 60


def bake_action(
    rig: bpy.types.Object,
    name: str,
    frame_start: int,
    frame_end: int,
) -> bpy.types.Action:
    rig.animation_data_clear()
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.pose.select_all(action="SELECT")
    bpy.ops.nla.bake(
        frame_start=frame_start,
        frame_end=frame_end,
        step=1,
        only_selected=True,
        visual_keying=True,
        clear_constraints=False,
        clear_parents=False,
        use_current_action=False,
        clean_curves=True,
        bake_types={"POSE"},
    )
    bpy.ops.object.mode_set(mode="OBJECT")
    action = rig.animation_data.action
    if action is None:
        raise RuntimeError(f"Blender failed to bake {name}")
    action.name = name
    action.use_fake_user = True
    return action


def remove_controllers(
    rig: bpy.types.Object,
    controllers: dict[str, bpy.types.Object],
) -> None:
    for pose_bone in rig.pose.bones:
        for constraint in list(pose_bone.constraints):
            pose_bone.constraints.remove(constraint)
    for controller in controllers.values():
        bpy.data.objects.remove(controller, do_unlink=True)


def attach_actions_to_nla(
    rig: bpy.types.Object,
    actions: list[bpy.types.Action],
) -> None:
    rig.animation_data_clear()
    rig.animation_data_create()
    for action in actions:
        track = rig.animation_data.nla_tracks.new()
        track.name = action.name
        strip = track.strips.new(action.name, int(action.frame_range[0]), action)
        strip.action_frame_start = action.frame_range[0]
        strip.action_frame_end = action.frame_range[1]
        track.mute = True


def save_staged_blend(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(path))


def refine_deformation(mesh: bpy.types.Object) -> None:
    modifier = next(
        (candidate for candidate in mesh.modifiers if candidate.type == "ARMATURE"),
        None,
    )
    if modifier is None:
        raise RuntimeError("Armature modifier missing during refinement")
    modifier.use_deform_preserve_volume = True


def configure_render(scene: bpy.types.Scene) -> None:
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.008, 0.012, 0.016)
    scene.view_settings.look = "AgX - Medium High Contrast"


def add_preview_lights() -> list[bpy.types.Object]:
    lights: list[bpy.types.Object] = []
    for name, location, energy, color, size in (
        ("Key", (3.4, -4.0, 5.1), 1000, (0.92, 0.98, 1.0), 3.0),
        ("Fill", (-3.0, -2.2, 2.7), 650, (0.45, 0.82, 1.0), 2.6),
        ("Rim", (2.0, 2.5, 4.0), 950, (0.48, 1.0, 0.74), 2.2),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.color = color
        data.shape = "DISK"
        data.size = size
        obj = bpy.data.objects.new(name, data)
        obj.location = location
        bpy.context.collection.objects.link(obj)
        direction = Vector((0, 0, 1.0)) - obj.location
        obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        lights.append(obj)
    return lights


def create_preview_camera() -> bpy.types.Object:
    data = bpy.data.cameras.new("PreviewCamera")
    data.lens = 58
    obj = bpy.data.objects.new("PreviewCamera", data)
    bpy.context.collection.objects.link(obj)
    bpy.context.scene.camera = obj
    return obj


def aim_camera(camera: bpy.types.Object, location: tuple[float, float, float]) -> None:
    camera.location = location
    direction = Vector((0, 0, 1.08)) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def make_clay_material() -> bpy.types.Material:
    material = bpy.data.materials.new("RigPreviewClay")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    principled = nodes.new("ShaderNodeBsdfPrincipled")
    principled.inputs["Base Color"].default_value = (0.52, 0.57, 0.61, 1)
    principled.inputs["Metallic"].default_value = 0.12
    principled.inputs["Roughness"].default_value = 0.62
    links.new(principled.outputs["BSDF"], output.inputs["Surface"])
    return material


def make_wire_material() -> bpy.types.Material:
    material = bpy.data.materials.new("RigPreviewWire")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (0.35, 1.0, 0.74, 1)
    emission.inputs["Strength"].default_value = 2.4
    wire = nodes.new("ShaderNodeWireframe")
    wire.inputs["Size"].default_value = 0.75
    transparent = nodes.new("ShaderNodeBsdfTransparent")
    mix = nodes.new("ShaderNodeMixShader")
    links.new(wire.outputs["Fac"], mix.inputs[0])
    links.new(transparent.outputs["BSDF"], mix.inputs[1])
    links.new(emission.outputs["Emission"], mix.inputs[2])
    links.new(mix.outputs["Shader"], output.inputs["Surface"])
    material.surface_render_method = "DITHERED"
    return material


def render_previews(
    mesh: bpy.types.Object,
    rig: bpy.types.Object,
    scroll_action: bpy.types.Action,
    preview_dir: Path,
) -> None:
    preview_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    configure_render(scene)
    lights = add_preview_lights()
    camera = create_preview_camera()

    rig.animation_data_clear()
    rig.animation_data_create()
    rig.animation_data.action = scroll_action
    scene.frame_start = 1
    scene.frame_end = 450
    scene.frame_set(236)

    original_materials = list(mesh.data.materials)
    clay = make_clay_material()
    wire = make_wire_material()
    views = {
        "front": (0.0, -4.2, 1.34),
        "three-quarter": (3.0, -3.1, 1.48),
        "side": (4.4, 0.0, 1.34),
        "back": (0.0, 4.2, 1.34),
    }

    for mode, replacement in (
        ("material", None),
        ("clay", clay),
        ("wireframe", wire),
    ):
        mesh.data.materials.clear()
        if replacement is None:
            for material in original_materials:
                mesh.data.materials.append(material)
        else:
            mesh.data.materials.append(replacement)

        for view, position in views.items():
            aim_camera(camera, position)
            scene.render.filepath = str(preview_dir / f"{mode}_{view}.png")
            bpy.ops.render.render(write_still=True)

    mesh.data.materials.clear()
    for material in original_materials:
        mesh.data.materials.append(material)
    for obj in [camera, *lights]:
        bpy.data.objects.remove(obj, do_unlink=True)


def export_glb(
    mesh: bpy.types.Object,
    rig: bpy.types.Object,
    actions: list[bpy.types.Action],
    output: Path,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    attach_actions_to_nla(rig, actions)
    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    kwargs = {
        "filepath": str(output),
        "export_format": "GLB",
        "use_selection": True,
        "export_animations": True,
        "export_cameras": False,
        "export_lights": False,
        "export_yup": True,
    }
    try:
        bpy.ops.export_scene.gltf(
            **kwargs,
            export_animation_mode="ACTIONS",
            export_anim_slide_to_zero=True,
        )
    except TypeError:
        bpy.ops.export_scene.gltf(**kwargs)


def write_report(
    mesh: bpy.types.Object,
    rig: bpy.types.Object,
    actions: list[bpy.types.Action],
    output_glb: Path,
    preview_dir: Path,
) -> None:
    report = {
        "mesh": mesh.name,
        "vertices": len(mesh.data.vertices),
        "triangles": sum(len(poly.vertices) - 2 for poly in mesh.data.polygons),
        "armature": rig.name,
        "deform_bones": [bone.name for bone in rig.data.bones if bone.use_deform],
        "actions": [
            {
                "name": action.name,
                "frame_start": float(action.frame_range[0]),
                "frame_end": float(action.frame_range[1]),
            }
            for action in actions
        ],
        "modifier_stack": [
            {
                "name": modifier.name,
                "type": modifier.type,
                "preserve_volume": bool(
                    getattr(modifier, "use_deform_preserve_volume", False)
                ),
            }
            for modifier in mesh.modifiers
        ],
        "materials": [slot.material.name for slot in mesh.material_slots if slot.material],
        "output_glb": str(output_glb),
        "output_glb_bytes": output_glb.stat().st_size if output_glb.exists() else None,
        "known_limitations": [
            "Source mesh is fully triangulated; shoulder, elbow, hip, and knee deformation use manually authored smooth weights.",
            "Reference-site optical distortion and proprietary background assets are not embedded in this GLB.",
        ],
    }
    (preview_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    source = Path(args.input).resolve()
    blend_v01 = Path(args.blend_v01).resolve()
    blend_v02 = Path(args.blend_v02).resolve()
    output_glb = Path(args.output_glb).resolve()
    preview_dir = Path(args.preview_dir).resolve()

    clean_scene()
    mesh = import_astronaut(source)
    rig = create_armature()
    bind_mesh(mesh, rig)
    controllers = create_controllers(rig)

    scroll_start, scroll_end = author_scroll_controls(controllers)
    scroll_action = bake_action(rig, "EchoScrollStory", scroll_start, scroll_end)

    clear_controller_animation(controllers)
    pointer_start, pointer_end = author_pointer_controls(controllers)
    pointer_action = bake_action(rig, "EchoPointerWave", pointer_start, pointer_end)
    actions = [scroll_action, pointer_action]

    remove_controllers(rig, controllers)
    attach_actions_to_nla(rig, actions)
    save_staged_blend(blend_v01)

    refine_deformation(mesh)
    render_previews(mesh, rig, scroll_action, preview_dir)
    attach_actions_to_nla(rig, actions)
    save_staged_blend(blend_v02)
    export_glb(mesh, rig, actions, output_glb)
    write_report(mesh, rig, actions, output_glb, preview_dir)

    print(
        json.dumps(
            {
                "blend_v01": str(blend_v01),
                "blend_v02": str(blend_v02),
                "output_glb": str(output_glb),
                "preview_dir": str(preview_dir),
                "actions": [action.name for action in actions],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
