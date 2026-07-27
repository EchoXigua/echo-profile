"""Author web-ready astronaut actions on a copy of the Tripo rig.

The source GLB is imported read-only. This script writes staged .blend files,
review renders, a derivative GLB, and an animation report.

Run with Blender:
  blender --background --python scripts/blender/author_lusion_astronaut_actions.py -- \
    --input design/animation-model/astronaut-rigged.glb \
    --blend-v01 design/animation-model/astronaut-lusion-motion-v01.blend \
    --blend-v02 design/animation-model/astronaut-lusion-motion-v02.blend \
    --output-glb public/models/astronaut-lusion-animated.glb \
    --preview-dir output/astronaut-motion-previews \
    --report output/astronaut-motion-report.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import bpy
from mathutils import Vector


FPS = 30
STORY_END = 361
POINTER_END = 91
CLICK_END = 22
IDLE_END = 241


@dataclass(frozen=True)
class Pose:
    frame: int
    hand_l: tuple[float, float, float]
    hand_r: tuple[float, float, float]
    foot_l: tuple[float, float, float]
    foot_r: tuple[float, float, float]
    pole_arm_l: tuple[float, float, float]
    pole_arm_r: tuple[float, float, float]
    pole_leg_l: tuple[float, float, float]
    pole_leg_r: tuple[float, float, float]
    waist: tuple[float, float, float] = (0.0, 0.0, 0.0)
    spine: tuple[float, float, float] = (0.0, 0.0, 0.0)
    chest: tuple[float, float, float] = (0.0, 0.0, 0.0)
    head: tuple[float, float, float] = (0.0, 0.0, 0.0)
    hand_rot_l: tuple[float, float, float] = (0.0, 0.0, 0.0)
    hand_rot_r: tuple[float, float, float] = (0.0, 0.0, 0.0)
    foot_rot_l: tuple[float, float, float] = (0.0, 0.0, 0.0)
    foot_rot_r: tuple[float, float, float] = (0.0, 0.0, 0.0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--blend-v01", required=True)
    parser.add_argument("--blend-v02", required=True)
    parser.add_argument("--output-glb", required=True)
    parser.add_argument("--preview-dir", required=True)
    parser.add_argument("--report", required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def reset_scene() -> None:
    bpy.ops.object.mode_set(mode="OBJECT") if bpy.context.object and bpy.context.object.mode != "OBJECT" else None
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in (
        bpy.data.armatures,
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
        bpy.data.actions,
    ):
        for datablock in list(collection):
            collection.remove(datablock)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def import_source(path: Path) -> tuple[bpy.types.Object, bpy.types.Object, list[str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    bpy.ops.import_scene.gltf(filepath=str(path))
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        raise RuntimeError(f"Expected one armature, found {len(armatures)}")
    rig = armatures[0]
    skinned = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH"
        and any(
            modifier.type == "ARMATURE" and modifier.object == rig
            for modifier in obj.modifiers
        )
    ]
    if len(skinned) != 1:
        raise RuntimeError(f"Expected one skinned mesh, found {len(skinned)}")
    mesh = skinned[0]
    excluded: list[str] = []
    for obj in list(bpy.context.scene.objects):
        if obj in {rig, mesh}:
            continue
        orphan_mesh = obj.data if obj.type == "MESH" else None
        if obj.type == "MESH":
            excluded.append(obj.name)
        bpy.data.objects.remove(obj, do_unlink=True)
        if orphan_mesh is not None and orphan_mesh.users == 0:
            bpy.data.meshes.remove(orphan_mesh)

    required = {
        "Root",
        "Pelvis",
        "Waist",
        "Spine01",
        "Spine02",
        "NeckTwist01",
        "Head",
        "L_Clavicle",
        "L_Upperarm",
        "L_Forearm",
        "L_Hand",
        "R_Clavicle",
        "R_Upperarm",
        "R_Forearm",
        "R_Hand",
        "L_Thigh",
        "L_Calf",
        "L_Foot",
        "R_Thigh",
        "R_Calf",
        "R_Foot",
    }
    missing = sorted(required - set(rig.data.bones.keys()))
    if missing:
        raise RuntimeError(f"Missing required bones: {missing}")

    # The source test action is intentionally omitted from this derivative.
    rig.animation_data_clear()
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    return rig, mesh, excluded


def add_controller(
    name: str,
    location: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> bpy.types.Object:
    controller = bpy.data.objects.new(name, None)
    controller.empty_display_type = "SPHERE"
    controller.empty_display_size = 0.025
    controller.location = location
    bpy.context.collection.objects.link(controller)
    return controller


def add_ik(
    rig: bpy.types.Object,
    bone_name: str,
    target: bpy.types.Object,
    pole: bpy.types.Object,
    pole_angle: float,
) -> None:
    constraint = rig.pose.bones[bone_name].constraints.new("IK")
    constraint.name = f"ECHO_IK_{bone_name}"
    constraint.target = target
    constraint.pole_target = pole
    constraint.chain_count = 2
    constraint.use_tail = True
    constraint.pole_angle = pole_angle


def add_copy_rotation(
    rig: bpy.types.Object,
    bone_name: str,
    target: bpy.types.Object,
) -> None:
    constraint = rig.pose.bones[bone_name].constraints.new("COPY_ROTATION")
    constraint.name = f"ECHO_ROT_{bone_name}"
    constraint.target = target
    constraint.owner_space = "LOCAL"
    constraint.target_space = "LOCAL"
    constraint.mix_mode = "REPLACE"


def create_controllers(rig: bpy.types.Object) -> dict[str, bpy.types.Object]:
    controllers = {
        "hand_l": add_controller("CTRL_hand_L", (0.02, 0.24, 0.535)),
        "hand_r": add_controller("CTRL_hand_R", (0.03, -0.235, 0.535)),
        "foot_l": add_controller("CTRL_foot_L", (0.088, 0.133, 0.053)),
        "foot_r": add_controller("CTRL_foot_R", (0.087, -0.084, 0.038)),
        "pole_arm_l": add_controller("CTRL_pole_arm_L", (0.22, 0.42, 0.70)),
        "pole_arm_r": add_controller("CTRL_pole_arm_R", (0.22, -0.42, 0.70)),
        "pole_leg_l": add_controller("CTRL_pole_leg_L", (0.38, 0.11, 0.31)),
        "pole_leg_r": add_controller("CTRL_pole_leg_R", (0.38, -0.08, 0.31)),
        "waist": add_controller("CTRL_rot_Waist"),
        "spine": add_controller("CTRL_rot_Spine01"),
        "chest": add_controller("CTRL_rot_Spine02"),
        "head": add_controller("CTRL_rot_Head"),
        "hand_rot_l": add_controller("CTRL_rot_Hand_L"),
        "hand_rot_r": add_controller("CTRL_rot_Hand_R"),
        "foot_rot_l": add_controller("CTRL_rot_Foot_L"),
        "foot_rot_r": add_controller("CTRL_rot_Foot_R"),
    }
    add_ik(rig, "L_Forearm", controllers["hand_l"], controllers["pole_arm_l"], math.pi / 2)
    add_ik(rig, "R_Forearm", controllers["hand_r"], controllers["pole_arm_r"], -math.pi / 2)
    add_ik(rig, "L_Calf", controllers["foot_l"], controllers["pole_leg_l"], 0.0)
    add_ik(rig, "R_Calf", controllers["foot_r"], controllers["pole_leg_r"], 0.0)
    for bone_name, controller_name in (
        ("Waist", "waist"),
        ("Spine01", "spine"),
        ("Spine02", "chest"),
        ("Head", "head"),
        ("L_Hand", "hand_rot_l"),
        ("R_Hand", "hand_rot_r"),
        ("L_Foot", "foot_rot_l"),
        ("R_Foot", "foot_rot_r"),
    ):
        add_copy_rotation(rig, bone_name, controllers[controller_name])
    return controllers


def key_location(controller: bpy.types.Object, frame: int, value: Iterable[float]) -> None:
    controller.location = tuple(value)
    controller.keyframe_insert(data_path="location", frame=frame)


def key_rotation(controller: bpy.types.Object, frame: int, value: Iterable[float]) -> None:
    controller.rotation_mode = "XYZ"
    controller.rotation_euler = tuple(value)
    controller.keyframe_insert(data_path="rotation_euler", frame=frame)


def set_interpolation(controllers: dict[str, bpy.types.Object]) -> None:
    for controller in controllers.values():
        action = controller.animation_data.action if controller.animation_data else None
        if not action:
            continue
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
        controller.location = (0.0, 0.0, 0.0)
        controller.rotation_mode = "XYZ"
        controller.rotation_euler = (0.0, 0.0, 0.0)


def key_pose(controllers: dict[str, bpy.types.Object], pose: Pose) -> None:
    for name in (
        "hand_l",
        "hand_r",
        "foot_l",
        "foot_r",
        "pole_arm_l",
        "pole_arm_r",
        "pole_leg_l",
        "pole_leg_r",
    ):
        key_location(controllers[name], pose.frame, getattr(pose, name))
    for name in (
        "waist",
        "spine",
        "chest",
        "head",
        "hand_rot_l",
        "hand_rot_r",
        "foot_rot_l",
        "foot_rot_r",
    ):
        key_rotation(controllers[name], pose.frame, getattr(pose, name))


REST = {
    "hand_l": (0.02, 0.243, 0.535),
    "hand_r": (0.022, -0.236, 0.535),
    "foot_l": (0.088, 0.133, 0.053),
    "foot_r": (0.087, -0.084, 0.038),
    "pole_arm_l": (0.22, 0.42, 0.70),
    "pole_arm_r": (0.22, -0.42, 0.70),
    "pole_leg_l": (0.38, 0.11, 0.31),
    "pole_leg_r": (0.38, -0.08, 0.31),
}


def pose(frame: int, **changes: object) -> Pose:
    values: dict[str, object] = {**REST, "frame": frame}
    values.update(changes)
    return Pose(**values)


def story_poses() -> list[Pose]:
    # The timing follows the supplied full recording: forward reach, expanding
    # silhouette, compact tunnel tumble, open blue-portal pose, contact fold,
    # then upright contact state. The web samples this same clip backwards.
    return [
        pose(
            1,
            hand_l=(0.255, 0.17, 0.755),
            hand_r=(0.27, -0.16, 0.74),
            pole_arm_l=(0.16, 0.39, 0.69),
            pole_arm_r=(0.17, -0.39, 0.68),
            spine=(0.02, -0.04, 0.03),
            chest=(0.03, -0.06, 0.05),
            head=(-0.02, -0.05, 0.02),
            hand_rot_l=(0.05, -0.22, -0.08),
            hand_rot_r=(-0.04, 0.20, 0.08),
        ),
        pose(
            50,
            hand_l=(0.31, 0.145, 0.77),
            hand_r=(0.30, -0.14, 0.755),
            pole_arm_l=(0.20, 0.38, 0.72),
            pole_arm_r=(0.20, -0.38, 0.71),
            spine=(0.04, -0.07, 0.04),
            chest=(0.06, -0.10, 0.08),
            head=(-0.02, -0.08, 0.03),
            hand_rot_l=(0.08, -0.28, -0.10),
            hand_rot_r=(-0.06, 0.26, 0.10),
        ),
        pose(
            92,
            hand_l=(0.10, 0.33, 0.83),
            hand_r=(0.12, -0.32, 0.82),
            pole_arm_l=(0.16, 0.46, 0.71),
            pole_arm_r=(0.16, -0.46, 0.71),
            foot_l=(0.10, 0.14, 0.08),
            foot_r=(0.16, -0.10, 0.17),
            spine=(-0.04, 0.06, -0.06),
            chest=(-0.08, 0.10, -0.10),
            head=(0.03, 0.12, -0.04),
            hand_rot_l=(0.0, -0.18, -0.18),
            hand_rot_r=(0.0, 0.18, 0.18),
        ),
        pose(
            136,
            hand_l=(0.15, 0.29, 0.72),
            hand_r=(0.23, -0.15, 0.86),
            foot_l=(0.13, 0.12, 0.14),
            foot_r=(0.20, -0.11, 0.31),
            pole_leg_l=(0.42, 0.13, 0.32),
            pole_leg_r=(0.44, -0.09, 0.42),
            waist=(0.08, -0.08, 0.10),
            spine=(0.10, -0.10, 0.12),
            chest=(0.13, -0.13, 0.15),
            head=(-0.08, -0.11, 0.08),
            foot_rot_r=(0.18, -0.12, 0.02),
        ),
        pose(
            178,
            hand_l=(0.17, 0.075, 0.67),
            hand_r=(0.18, -0.075, 0.65),
            foot_l=(0.25, 0.095, 0.40),
            foot_r=(0.24, -0.09, 0.43),
            pole_arm_l=(0.31, 0.30, 0.66),
            pole_arm_r=(0.31, -0.30, 0.65),
            pole_leg_l=(0.48, 0.18, 0.45),
            pole_leg_r=(0.48, -0.15, 0.46),
            waist=(-0.12, 0.10, -0.08),
            spine=(-0.17, 0.13, -0.10),
            chest=(-0.22, 0.16, -0.13),
            head=(0.15, 0.12, 0.10),
            hand_rot_l=(-0.12, -0.18, 0.12),
            hand_rot_r=(0.10, 0.18, -0.12),
            foot_rot_l=(0.14, 0.08, 0.06),
            foot_rot_r=(-0.12, -0.08, -0.05),
        ),
        pose(
            222,
            hand_l=(0.22, 0.11, 0.61),
            hand_r=(0.13, -0.10, 0.70),
            foot_l=(0.22, 0.14, 0.43),
            foot_r=(0.28, -0.06, 0.35),
            pole_arm_l=(0.34, 0.31, 0.59),
            pole_arm_r=(0.29, -0.30, 0.70),
            pole_leg_l=(0.47, 0.22, 0.46),
            pole_leg_r=(0.52, -0.11, 0.39),
            waist=(0.10, -0.12, 0.14),
            spine=(0.15, -0.16, 0.18),
            chest=(0.19, -0.20, 0.22),
            head=(-0.14, -0.15, 0.10),
            hand_rot_l=(0.13, -0.12, -0.08),
            hand_rot_r=(-0.10, 0.16, 0.12),
            foot_rot_l=(-0.12, 0.08, 0.04),
            foot_rot_r=(0.16, -0.10, -0.03),
        ),
        pose(
            270,
            hand_l=(0.02, 0.405, 0.82),
            hand_r=(0.03, -0.405, 0.83),
            foot_l=(0.09, 0.145, 0.07),
            foot_r=(0.22, -0.10, 0.29),
            pole_arm_l=(0.12, 0.48, 0.70),
            pole_arm_r=(0.12, -0.48, 0.72),
            pole_leg_r=(0.48, -0.10, 0.39),
            waist=(0.02, 0.02, -0.03),
            spine=(0.03, 0.03, -0.04),
            chest=(0.04, 0.04, -0.05),
            head=(-0.02, 0.05, 0.02),
            hand_rot_l=(0.0, -0.12, -0.18),
            hand_rot_r=(0.0, 0.12, 0.18),
            foot_rot_r=(0.14, -0.08, -0.02),
        ),
        pose(
            304,
            hand_l=(-0.015, 0.42, 0.825),
            hand_r=(-0.005, -0.42, 0.82),
            foot_l=(0.085, 0.15, 0.055),
            foot_r=(0.25, -0.09, 0.31),
            pole_arm_l=(0.08, 0.49, 0.72),
            pole_arm_r=(0.08, -0.49, 0.71),
            pole_leg_r=(0.52, -0.10, 0.41),
            chest=(0.0, 0.04, -0.02),
            head=(0.0, 0.07, 0.01),
            hand_rot_l=(0.0, -0.10, -0.22),
            hand_rot_r=(0.0, 0.10, 0.22),
            foot_rot_r=(0.20, -0.10, -0.02),
        ),
        pose(
            326,
            hand_l=(0.255, 0.055, 0.54),
            hand_r=(0.26, -0.055, 0.535),
            foot_l=(0.20, 0.075, 0.30),
            foot_r=(0.21, -0.07, 0.31),
            pole_arm_l=(0.37, 0.26, 0.58),
            pole_arm_r=(0.37, -0.26, 0.57),
            pole_leg_l=(0.46, 0.16, 0.39),
            pole_leg_r=(0.47, -0.14, 0.40),
            waist=(-0.42, 0.0, 0.0),
            spine=(-0.52, 0.0, 0.0),
            chest=(-0.62, 0.0, 0.0),
            head=(-0.10, 0.0, 0.0),
            hand_rot_l=(-0.14, -0.18, 0.08),
            hand_rot_r=(0.14, 0.18, -0.08),
            foot_rot_l=(0.15, 0.04, 0.0),
            foot_rot_r=(0.15, -0.04, 0.0),
        ),
        pose(
            345,
            hand_l=(0.08, 0.21, 0.55),
            hand_r=(0.09, -0.205, 0.55),
            foot_l=(0.10, 0.13, 0.07),
            foot_r=(0.11, -0.085, 0.06),
            waist=(-0.15, 0.0, 0.0),
            spine=(-0.20, 0.0, 0.0),
            chest=(-0.24, 0.0, 0.0),
            head=(0.06, 0.0, 0.0),
        ),
        pose(361),
    ]


def pointer_wave_poses() -> list[Pose]:
    return [
        pose(1),
        pose(
            28,
            hand_r=(0.24, -0.21, 0.70),
            pole_arm_r=(0.28, -0.42, 0.75),
            spine=(0.0, 0.02, 0.015),
            chest=(0.0, 0.04, 0.03),
            head=(0.0, 0.06, 0.02),
            hand_rot_r=(-0.08, 0.12, 0.05),
        ),
        pose(
            58,
            hand_r=(0.16, -0.17, 0.94),
            pole_arm_r=(0.24, -0.36, 0.84),
            spine=(0.0, 0.04, 0.025),
            chest=(0.0, 0.08, 0.05),
            head=(0.0, 0.12, 0.04),
            hand_rot_r=(-0.16, 0.18, 0.10),
        ),
        pose(
            91,
            hand_r=(0.06, -0.12, 1.01),
            pole_arm_r=(0.15, -0.31, 0.90),
            spine=(0.0, 0.05, 0.03),
            chest=(0.0, 0.10, 0.065),
            head=(0.0, 0.15, 0.05),
            hand_rot_r=(-0.24, 0.20, 0.14),
        ),
    ]


def pointer_sweep_poses() -> list[Pose]:
    return [
        pose(
            1,
            hand_r=(0.19, -0.10, 0.60),
            pole_arm_r=(0.28, -0.34, 0.69),
            chest=(0.0, 0.0, 0.09),
            head=(0.0, 0.0, 0.14),
            hand_rot_r=(0.0, 0.08, 0.14),
        ),
        pose(46),
        pose(
            91,
            hand_r=(0.17, -0.31, 0.61),
            pole_arm_r=(0.25, -0.49, 0.68),
            chest=(0.0, 0.0, -0.09),
            head=(0.0, 0.0, -0.14),
            hand_rot_r=(0.0, -0.08, -0.14),
        ),
    ]


def pointer_click_poses() -> list[Pose]:
    return [
        pose(1),
        pose(
            5,
            hand_l=(0.08, 0.22, 0.57),
            hand_r=(0.26, -0.18, 0.73),
            pole_arm_r=(0.33, -0.39, 0.72),
            spine=(-0.035, 0.0, 0.0),
            chest=(-0.07, 0.025, 0.015),
            head=(0.08, 0.04, 0.02),
            hand_rot_r=(-0.12, 0.10, 0.06),
        ),
        pose(
            11,
            hand_l=(0.04, 0.235, 0.55),
            hand_r=(0.18, -0.20, 0.64),
            spine=(0.02, 0.0, 0.0),
            chest=(0.04, 0.0, 0.0),
            head=(-0.04, 0.0, 0.0),
        ),
        pose(22),
    ]


def zero_g_idle_poses() -> list[Pose]:
    return [
        pose(1),
        pose(
            61,
            hand_l=(0.035, 0.247, 0.55),
            hand_r=(0.03, -0.232, 0.525),
            foot_l=(0.10, 0.135, 0.07),
            foot_r=(0.08, -0.088, 0.05),
            spine=(0.015, -0.018, 0.012),
            chest=(0.022, -0.03, 0.018),
            head=(-0.015, -0.038, 0.012),
        ),
        pose(
            121,
            hand_l=(0.015, 0.239, 0.525),
            hand_r=(0.038, -0.245, 0.55),
            foot_l=(0.08, 0.13, 0.045),
            foot_r=(0.10, -0.08, 0.07),
            spine=(-0.012, 0.02, -0.014),
            chest=(-0.02, 0.032, -0.02),
            head=(0.014, 0.04, -0.014),
        ),
        pose(
            181,
            hand_l=(0.03, 0.248, 0.545),
            hand_r=(0.015, -0.23, 0.528),
            foot_l=(0.095, 0.138, 0.065),
            foot_r=(0.082, -0.087, 0.047),
            spine=(0.01, -0.015, 0.01),
            chest=(0.016, -0.025, 0.016),
            head=(-0.012, -0.032, 0.01),
        ),
        pose(241),
    ]


def author_controls(
    controllers: dict[str, bpy.types.Object],
    poses: list[Pose],
) -> tuple[int, int]:
    clear_controller_animation(controllers)
    for authored_pose in poses:
        key_pose(controllers, authored_pose)
    set_interpolation(controllers)
    return poses[0].frame, poses[-1].frame


def reset_pose(rig: bpy.types.Object) -> None:
    for bone in rig.pose.bones:
        bone.matrix_basis.identity()


def bake_action(
    rig: bpy.types.Object,
    name: str,
    frame_start: int,
    frame_end: int,
) -> bpy.types.Action:
    rig.animation_data_clear()
    reset_pose(rig)
    bpy.context.scene.frame_start = frame_start
    bpy.context.scene.frame_end = frame_end
    bpy.context.scene.frame_set(frame_start)
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
        raise RuntimeError(f"Failed to bake {name}")
    action.name = name
    action.use_fake_user = True
    return action


def remove_controllers(
    rig: bpy.types.Object,
    controllers: dict[str, bpy.types.Object],
) -> None:
    for bone in rig.pose.bones:
        for constraint in list(bone.constraints):
            bone.constraints.remove(constraint)
    for controller in controllers.values():
        bpy.data.objects.remove(controller, do_unlink=True)
    reset_pose(rig)


def attach_actions_to_nla(
    rig: bpy.types.Object,
    actions: list[bpy.types.Action],
) -> None:
    rig.animation_data_clear()
    rig.animation_data_create()
    for action in actions:
        track = rig.animation_data.nla_tracks.new()
        track.name = action.name
        start = int(action.frame_range[0])
        strip = track.strips.new(action.name, start, action)
        strip.action_frame_start = action.frame_range[0]
        strip.action_frame_end = action.frame_range[1]
        track.mute = True


def save_blend(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(path))


def configure_render(scene: bpy.types.Scene) -> None:
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 600
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.004, 0.006, 0.01)
    scene.view_settings.look = "AgX - Medium High Contrast"


def add_preview_lights() -> list[bpy.types.Object]:
    result: list[bpy.types.Object] = []
    target = Vector((0.0, 0.0, 0.55))
    for name, location, energy, color, size in (
        ("PreviewKey", (2.8, -2.7, 3.1), 850, (0.90, 0.96, 1.0), 2.2),
        ("PreviewFill", (1.4, 2.8, 1.8), 520, (0.28, 0.62, 1.0), 2.0),
        ("PreviewRim", (-2.6, -0.8, 2.4), 780, (0.42, 1.0, 0.72), 1.8),
    ):
        light_data = bpy.data.lights.new(name, "AREA")
        light_data.energy = energy
        light_data.color = color
        light_data.shape = "DISK"
        light_data.size = size
        light = bpy.data.objects.new(name, light_data)
        light.location = location
        light.rotation_euler = (target - light.location).to_track_quat("-Z", "Y").to_euler()
        bpy.context.collection.objects.link(light)
        result.append(light)
    return result


def add_camera() -> bpy.types.Object:
    data = bpy.data.cameras.new("MotionPreviewCamera")
    data.lens = 64
    camera = bpy.data.objects.new("MotionPreviewCamera", data)
    bpy.context.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    return camera


def aim_camera(
    camera: bpy.types.Object,
    location: tuple[float, float, float],
    target: tuple[float, float, float] = (0.0, 0.0, 0.55),
) -> None:
    camera.location = location
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()


def make_clay_material() -> bpy.types.Material:
    material = bpy.data.materials.new("EchoMotionClay")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    principled = nodes.new("ShaderNodeBsdfPrincipled")
    principled.inputs["Base Color"].default_value = (0.36, 0.42, 0.48, 1.0)
    principled.inputs["Metallic"].default_value = 0.18
    principled.inputs["Roughness"].default_value = 0.58
    links.new(principled.outputs["BSDF"], output.inputs["Surface"])
    return material


def make_wire_material() -> bpy.types.Material:
    material = bpy.data.materials.new("EchoMotionWire")
    material.diffuse_color = (0.08, 0.95, 0.60, 1.0)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (0.08, 1.0, 0.58, 1.0)
    emission.inputs["Strength"].default_value = 2.0
    transparent = nodes.new("ShaderNodeBsdfTransparent")
    wire = nodes.new("ShaderNodeWireframe")
    wire.inputs["Size"].default_value = 0.7
    mix = nodes.new("ShaderNodeMixShader")
    links.new(wire.outputs["Fac"], mix.inputs[0])
    links.new(transparent.outputs["BSDF"], mix.inputs[1])
    links.new(emission.outputs["Emission"], mix.inputs[2])
    links.new(mix.outputs["Shader"], output.inputs["Surface"])
    material.surface_render_method = "DITHERED"
    return material


def assign_action(
    rig: bpy.types.Object,
    action: bpy.types.Action,
    frame: int,
) -> None:
    rig.animation_data_clear()
    rig.animation_data_create()
    rig.animation_data.action = action
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()


def render_previews(
    mesh: bpy.types.Object,
    rig: bpy.types.Object,
    actions: dict[str, bpy.types.Action],
    preview_dir: Path,
) -> None:
    preview_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    configure_render(scene)
    camera = add_camera()
    lights = add_preview_lights()
    original_materials = list(mesh.data.materials)
    clay = make_clay_material()
    wire = make_wire_material()

    assign_action(rig, actions["EchoScrollStory"], 222)
    views = {
        "front": (2.7, 0.0, 0.65),
        "side": (0.0, -2.7, 0.65),
        "back": (-2.7, 0.0, 0.65),
        "three-quarter": (2.15, -2.15, 0.78),
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
        for view_name, camera_location in views.items():
            aim_camera(camera, camera_location)
            scene.render.filepath = str(preview_dir / f"{mode}-{view_name}.png")
            bpy.ops.render.render(write_still=True)

    mesh.data.materials.clear()
    for material in original_materials:
        mesh.data.materials.append(material)
    keyframes = {
        "01-hero-reach": 50,
        "02-open-flight": 92,
        "03-zero-g-tuck": 178,
        "04-tunnel-tumble": 222,
        "05-portal-open": 304,
        "06-contact-fold": 326,
        "07-contact-upright": 361,
    }
    aim_camera(camera, (2.15, -2.15, 0.78))
    for name, frame in keyframes.items():
        assign_action(rig, actions["EchoScrollStory"], frame)
        scene.render.filepath = str(preview_dir / f"key-{name}.png")
        bpy.ops.render.render(write_still=True)
    assign_action(rig, actions["EchoPointerWave"], 91)
    scene.render.filepath = str(preview_dir / "key-08-pointer-reach.png")
    bpy.ops.render.render(write_still=True)

    for obj in [camera, *lights]:
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.materials.remove(clay)
    bpy.data.materials.remove(wire)


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


def mesh_triangles(mesh: bpy.types.Object) -> int:
    mesh.data.calc_loop_triangles()
    return len(mesh.data.loop_triangles)


def write_report(
    path: Path,
    source: Path,
    source_hash: str,
    mesh: bpy.types.Object,
    rig: bpy.types.Object,
    actions: list[bpy.types.Action],
    excluded: list[str],
    blend_v01: Path,
    blend_v02: Path,
    output_glb: Path,
    preview_dir: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    modifiers = [
        f"`{modifier.name}` ({modifier.type}, Preserve Volume: "
        f"{bool(getattr(modifier, 'use_deform_preserve_volume', False))})"
        for modifier in mesh.modifiers
    ]
    materials = [
        f"`{slot.material.name}`"
        for slot in mesh.material_slots
        if slot.material is not None
    ]
    action_rows = "\n".join(
        f"| `{action.name}` | {action.frame_range[0]:.0f}–{action.frame_range[1]:.0f} "
        f"| {(action.frame_range[1] - action.frame_range[0]) / FPS:.3f}s |"
        for action in actions
    )
    text = f"""# Astronaut Lusion Motion Report

## Output

- Source (read-only): `{source}`
- Source SHA-256: `{source_hash}`
- Stage v01: `{blend_v01}`
- Stage v02: `{blend_v02}`
- Web GLB: `{output_glb}` ({output_glb.stat().st_size} bytes)
- Review renders: `{preview_dir}`

## Model and rig

- Armature: `{rig.name}` / {len(rig.data.bones)} bones
- Skinned mesh: `{mesh.name}`
- Vertices: {len(mesh.data.vertices):,}
- Triangles: {mesh_triangles(mesh):,}
- Materials: {", ".join(materials) if materials else "none"}
- Modifier stack: {"; ".join(modifiers) if modifiers else "none"}
- Excluded from derivative export: {", ".join(f"`{name}`" for name in excluded) if excluded else "none"}
- Topology changes: none
- Source overwrite: no

## Animation actions

30 fps. The scroll action is deterministic and designed to be sampled in both
directions. Pointer and click actions are independent layers.

| Action | Frames | Duration |
| --- | ---: | ---: |
{action_rows}

- `EchoScrollStory`: hero reach → open flight → compact tunnel tumble → portal
  expansion → contact fold → upright contact.
- `EchoPointerWave`: vertical right-arm reach driven by pointer Y/activity.
- `EchoPointerSweep`: horizontal right-arm/head tracking driven by pointer X.
- `EchoPointerClick`: short recoil and recovery triggered on pointer down.
- `EchoZeroGIdle`: eight-second seamless low-amplitude zero-gravity breathing
  and limb drift.

## Deformation and web notes

- The Tripo control bones carry zero direct vertex weights; their twist children
  deform the mesh. All delivered actions are baked onto the existing hierarchy.
- Armature modifiers use Preserve Volume in v02 and the exported derivative.
- No finger bones or corrective shape keys exist, so hand articulation and
  extreme shoulder/hip corrections are limited by the source rig.
- Global travel, scale and camera paths remain in React Three Fiber. They are not
  baked into the skeleton, allowing the same Action to reverse cleanly.
- The source test/fear Action `NlaTrack` remains in the source GLB but is omitted
  from the derivative web export by design.

## Review

- Material, clay and wireframe renders are provided from front, side, back and
  three-quarter views at the compact flight pose.
- Eight key-pose renders cover the authored scroll arc and pointer reach.
- Remaining acceptance item after this offline pass: visual comparison in the
  live R3F scene against the supplied recording.
"""
    path.write_text(text, encoding="utf-8")


def main() -> None:
    args = parse_args()
    source = Path(args.input).resolve()
    blend_v01 = Path(args.blend_v01).resolve()
    blend_v02 = Path(args.blend_v02).resolve()
    output_glb = Path(args.output_glb).resolve()
    preview_dir = Path(args.preview_dir).resolve()
    report = Path(args.report).resolve()
    source_hash = sha256(source)

    reset_scene()
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.render.fps_base = 1.0
    rig, mesh, excluded = import_source(source)
    controllers = create_controllers(rig)

    action_specs = (
        ("EchoScrollStory", story_poses()),
        ("EchoPointerWave", pointer_wave_poses()),
        ("EchoPointerSweep", pointer_sweep_poses()),
        ("EchoPointerClick", pointer_click_poses()),
        ("EchoZeroGIdle", zero_g_idle_poses()),
    )
    actions: dict[str, bpy.types.Action] = {}
    for name, poses in action_specs:
        frame_start, frame_end = author_controls(controllers, poses)
        actions[name] = bake_action(rig, name, frame_start, frame_end)

    remove_controllers(rig, controllers)
    action_list = list(actions.values())
    attach_actions_to_nla(rig, action_list)
    if not blend_v01.exists():
        save_blend(blend_v01)

    armature_modifier = next(
        (
            modifier
            for modifier in mesh.modifiers
            if modifier.type == "ARMATURE" and modifier.object == rig
        ),
        None,
    )
    if armature_modifier is None:
        raise RuntimeError("Skinned mesh lost its armature modifier")
    armature_modifier.use_deform_preserve_volume = True

    render_previews(mesh, rig, actions, preview_dir)
    attach_actions_to_nla(rig, action_list)
    save_blend(blend_v02)
    export_glb(mesh, rig, action_list, output_glb)
    write_report(
        report,
        source,
        source_hash,
        mesh,
        rig,
        action_list,
        excluded,
        blend_v01,
        blend_v02,
        output_glb,
        preview_dir,
    )
    print(
        json.dumps(
            {
                "source": str(source),
                "blend_v01": str(blend_v01),
                "blend_v02": str(blend_v02),
                "output_glb": str(output_glb),
                "report": str(report),
                "preview_dir": str(preview_dir),
                "actions": list(actions.keys()),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
