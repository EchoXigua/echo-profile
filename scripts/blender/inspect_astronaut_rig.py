"""Read-only inspection for the Tripo-rigged astronaut GLB.

Run with Blender:
  blender --background --python scripts/blender/inspect_astronaut_rig.py -- \
    --model /absolute/path/astronaut-rigged.glb \
    --report /absolute/path/astronaut-rig-report.md \
    --bone-map /absolute/path/astronaut-bone-map.json \
    --preview-dir /absolute/path/preview

The source GLB is imported into a temporary Blender scene. Nothing is written
back to the source model, and no topology or animation data is modified.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--bone-map", required=True)
    parser.add_argument("--preview-dir", required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in (
        bpy.data.armatures,
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for datablock in list(collection):
            collection.remove(datablock)


def rounded(values: Any, digits: int = 5) -> list[float]:
    return [round(float(value), digits) for value in values]


def normalized_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def mesh_stats(mesh: bpy.types.Mesh) -> dict[str, int]:
    mesh.calc_loop_triangles()
    return {
        "vertices": len(mesh.vertices),
        "edges": len(mesh.edges),
        "faces": len(mesh.polygons),
        "triangles": len(mesh.loop_triangles),
    }


def collect_weight_stats(
    meshes: list[bpy.types.Object],
    armature: bpy.types.Object,
) -> dict[str, dict[str, float | int]]:
    stats = {
        bone.name: {
            "weighted_vertices": 0,
            "weight_sum": 0.0,
            "max_weight": 0.0,
        }
        for bone in armature.data.bones
    }
    for obj in meshes:
        groups = {group.index: group.name for group in obj.vertex_groups}
        for vertex in obj.data.vertices:
            for membership in vertex.groups:
                name = groups.get(membership.group)
                if name not in stats or membership.weight <= 1e-6:
                    continue
                entry = stats[name]
                entry["weighted_vertices"] += 1
                entry["weight_sum"] += float(membership.weight)
                entry["max_weight"] = max(float(entry["max_weight"]), float(membership.weight))
    for entry in stats.values():
        count = int(entry["weighted_vertices"])
        weight_sum = float(entry.pop("weight_sum"))
        entry["average_weight"] = round(weight_sum / count, 5) if count else 0.0
        entry["max_weight"] = round(float(entry["max_weight"]), 5)
    return stats


def world_bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    points = [
        obj.matrix_world @ Vector(corner)
        for obj in objects
        for corner in obj.bound_box
    ]
    if not points:
        return Vector((0, 0, 0)), Vector((0, 0, 0))
    return (
        Vector(tuple(min(point[index] for point in points) for index in range(3))),
        Vector(tuple(max(point[index] for point in points) for index in range(3))),
    )


def bone_depth(bone: bpy.types.Bone) -> int:
    depth = 0
    current = bone.parent
    while current:
        depth += 1
        current = current.parent
    return depth


def descendants(bone: bpy.types.Bone) -> set[str]:
    result: set[str] = set()
    stack = list(bone.children)
    while stack:
        current = stack.pop()
        result.add(current.name)
        stack.extend(current.children)
    return result


ROLE_HINTS = {
    "Root": ("root", "master", "global"),
    "Hips": ("hips", "hip", "pelvis", "pelvic"),
    "Spine": ("spine01", "spine1", "spine"),
    "Chest": ("chest", "upperchest", "spine02", "spine2", "spine03", "spine3"),
    "Neck": ("neck",),
    "Head": ("head",),
    "LeftUpperArm": ("leftupperarm", "lupperarm", "leftarm", "upperarml", "arml"),
    "RightUpperArm": ("rightupperarm", "rupperarm", "rightarm", "upperarmr", "armr"),
    "LeftForeArm": ("leftforearm", "lforearm", "leftlowerarm", "forearml", "lowerarml"),
    "RightForeArm": ("rightforearm", "rforearm", "rightlowerarm", "forearmr", "lowerarmr"),
    "LeftHand": ("lefthand", "lhand", "handl"),
    "RightHand": ("righthand", "rhand", "handr"),
    "LeftUpperLeg": ("leftupleg", "leftupperleg", "leftthigh", "lthigh", "thighl"),
    "RightUpperLeg": ("rightupleg", "rightupperleg", "rightthigh", "rthigh", "thighr"),
    "LeftLowerLeg": ("leftleg", "leftlowerleg", "leftshin", "leftcalf", "lcalf", "shinl"),
    "RightLowerLeg": ("rightleg", "rightlowerleg", "rightshin", "rightcalf", "rcalf", "shinr"),
    "LeftFoot": ("leftfoot", "lfoot", "footl", "leftankle"),
    "RightFoot": ("rightfoot", "rfoot", "footr", "rightankle"),
}


def role_semantic_score(role: str, bone_name: str) -> float:
    name = normalized_name(bone_name)
    score = 0.0
    for hint in ROLE_HINTS[role]:
        if name == hint:
            score = max(score, 10.0)
        elif hint in name:
            score = max(score, 7.0)

    if role.endswith("UpperArm") and any(token in name for token in ("forearm", "lowerarm", "hand", "twist")):
        score -= 8
    if role.endswith("ForeArm") and any(token in name for token in ("upperarm", "hand", "twist")):
        score -= 8
    if role.endswith("UpperLeg") and any(token in name for token in ("lowerleg", "shin", "calf", "foot", "toe", "twist")):
        score -= 8
    if role.endswith("LowerLeg") and any(token in name for token in ("upperleg", "thigh", "foot", "toe", "twist")):
        score -= 8
    if role.endswith("Hand") and any(token in name for token in ("thumb", "index", "middle", "ring", "pinky")):
        score -= 8
    if role == "Spine" and any(token in name for token in ("spine2", "spine3", "chest", "upper")):
        score -= 2
    return score


def spatial_score(
    role: str,
    bone: bpy.types.Bone,
    bounds_min: Vector,
    bounds_max: Vector,
) -> float:
    center = (bone.head_local + bone.tail_local) * 0.5
    span = max(bounds_max.z - bounds_min.z, 1e-6)
    z = (center.z - bounds_min.z) / span
    lateral = abs(center.x) / max(bounds_max.x - bounds_min.x, 1e-6)
    delta = bone.tail_local - bone.head_local
    horizontal = abs(delta.x) > abs(delta.z) * 0.65
    downward = delta.z < 0

    score = 0.0
    ranges = {
        "Hips": (0.32, 0.58),
        "Spine": (0.42, 0.7),
        "Chest": (0.56, 0.78),
        "Neck": (0.72, 0.9),
        "Head": (0.78, 1.05),
        "LeftUpperArm": (0.55, 0.82),
        "RightUpperArm": (0.55, 0.82),
        "LeftForeArm": (0.42, 0.75),
        "RightForeArm": (0.42, 0.75),
        "LeftHand": (0.3, 0.72),
        "RightHand": (0.3, 0.72),
        "LeftUpperLeg": (0.2, 0.52),
        "RightUpperLeg": (0.2, 0.52),
        "LeftLowerLeg": (-0.02, 0.36),
        "RightLowerLeg": (-0.02, 0.36),
        "LeftFoot": (-0.05, 0.18),
        "RightFoot": (-0.05, 0.18),
    }
    if role in ranges:
        low, high = ranges[role]
        if low <= z <= high:
            score += 2.0
        else:
            score -= min(abs(z - max(low, min(z, high))) * 5.0, 3.0)

    if "Arm" in role or "Hand" in role:
        score += 1.0 if lateral > 0.18 else -1.0
    if "Arm" in role:
        score += 1.0 if horizontal or downward else 0.0
    if "Leg" in role or "Foot" in role:
        score += 0.8 if downward else 0.0
    if role == "Root":
        score += 1.5 if bone.parent is None else -1.0
    return score


def side_score(role: str, bone_name: str) -> float:
    name = bone_name.lower()
    normalized = normalized_name(bone_name)
    left_tokens = ("left", ".l", "_l", "-l")
    right_tokens = ("right", ".r", "_r", "-r")
    wants_left = role.startswith("Left")
    wants_right = role.startswith("Right")
    is_left = (
        any(token in name for token in left_tokens)
        or normalized.endswith("l")
        or name.startswith(("l_", "l.", "l-"))
    )
    is_right = (
        any(token in name for token in right_tokens)
        or normalized.endswith("r")
        or name.startswith(("r_", "r.", "r-"))
    )
    if wants_left:
        return 2.0 if is_left else (-3.0 if is_right else 0.0)
    if wants_right:
        return 2.0 if is_right else (-3.0 if is_left else 0.0)
    return 0.0


def select_mapping(
    armature: bpy.types.Object,
    primary_bounds_min: Vector,
    primary_bounds_max: Vector,
) -> dict[str, dict[str, Any]]:
    bones = list(armature.data.bones)
    mapping: dict[str, dict[str, Any]] = {}
    used: set[str] = set()

    for role in ROLE_HINTS:
        candidates = []
        for bone in bones:
            semantic = role_semantic_score(role, bone.name)
            spatial = spatial_score(role, bone, primary_bounds_min, primary_bounds_max)
            side = side_score(role, bone.name)
            hierarchy = 0.0
            if role == "Head" and not bone.children:
                hierarchy += 0.5
            if role in ("Hips", "Chest") and len(descendants(bone)) >= 4:
                hierarchy += 0.5
            total = semantic + spatial + side + hierarchy
            candidates.append((total, semantic, spatial, side, hierarchy, bone))
        candidates.sort(key=lambda item: item[0], reverse=True)

        chosen = next((item for item in candidates if item[5].name not in used), candidates[0])
        total, semantic, spatial, side, hierarchy, bone = chosen

        if semantic <= 0 and total < 2.5:
            mapping[role] = {
                "bone": None,
                "confidence": "unresolved",
                "score": round(total, 2),
                "evidence": [
                    "未发现足够可靠的名称、层级和空间证据，未强行映射。",
                ],
            }
            continue

        used.add(bone.name)
        confidence = "high" if semantic >= 7 and total >= 9 else "medium"
        if semantic <= 0:
            confidence = "low"
        mapping[role] = {
            "bone": bone.name,
            "confidence": confidence,
            "score": round(total, 2),
            "evidence": [
                f"名称语义得分 {semantic:.1f}",
                f"空间位置得分 {spatial:.1f}",
                f"左右侧验证得分 {side:.1f}",
                f"父骨骼 {bone.parent.name if bone.parent else 'None'}，层级深度 {bone_depth(bone)}",
                f"局部 head {rounded(bone.head_local)}，tail {rounded(bone.tail_local)}",
            ],
        }

    # A named hips bone is frequently also the skeleton root in web rigs. Do not
    # invent a separate root if the source genuinely has none.
    root_entry = mapping["Root"]
    if root_entry["bone"] is None:
        top_level = [bone for bone in bones if bone.parent is None]
        if len(top_level) == 1 and mapping["Hips"]["bone"] != top_level[0].name:
            bone = top_level[0]
            mapping["Root"] = {
                "bone": bone.name,
                "confidence": "low",
                "score": 2.5,
                "evidence": [
                    "无标准 Root 名称；该骨骼是唯一顶层骨骼。",
                    f"局部 head {rounded(bone.head_local)}，tail {rounded(bone.tail_local)}",
                ],
            }
        elif mapping["Hips"]["bone"]:
            mapping["Root"] = {
                "bone": None,
                "confidence": "unresolved",
                "score": 0.0,
                "evidence": [
                    "源骨架没有独立 Root；网页根运动应由 Armature 对象或外层 Three.js Group 承担。",
                ],
            }
    return mapping


def material_details(material: bpy.types.Material) -> dict[str, Any]:
    textures = []
    if material.node_tree:
        for node in material.node_tree.nodes:
            if node.bl_idname != "ShaderNodeTexImage" or not node.image:
                continue
            linked_to = []
            for output in node.outputs:
                for link in output.links:
                    linked_to.append(f"{link.to_node.name}.{link.to_socket.name}")
            textures.append(
                {
                    "node": node.name,
                    "image": node.image.name,
                    "size": [int(node.image.size[0]), int(node.image.size[1])],
                    "colorspace": node.image.colorspace_settings.name,
                    "packed": bool(node.image.packed_file),
                    "filepath": node.image.filepath,
                    "linked_to": sorted(linked_to),
                }
            )
    return {
        "name": material.name,
        "blend_method": getattr(material, "surface_render_method", None),
        "textures": textures,
    }


def add_area_light(
    name: str,
    location: tuple[float, float, float],
    energy: float,
    size: float,
    color: tuple[float, float, float],
) -> None:
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    data.color = color
    light = bpy.data.objects.new(name, data)
    light.location = location
    bpy.context.scene.collection.objects.link(light)


def emission_material(name: str, color: tuple[float, float, float, float]) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    shader = next(node for node in nodes if node.bl_idname == "ShaderNodeBsdfPrincipled")
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Emission Color"].default_value = color
    shader.inputs["Emission Strength"].default_value = 4.0
    shader.inputs["Roughness"].default_value = 0.38
    return material


def bone_color(name: str) -> str:
    normalized = normalized_name(name)
    lower = name.lower()
    if (
        "left" in normalized
        or lower.endswith((".l", "_l", "-l"))
        or lower.startswith(("l_", "l.", "l-"))
    ):
        return "left"
    if (
        "right" in normalized
        or lower.endswith((".r", "_r", "-r"))
        or lower.startswith(("r_", "r.", "r-"))
    ):
        return "right"
    return "center"


def create_bone_proxies(
    armature: bpy.types.Object,
    scale: float,
) -> list[bpy.types.Object]:
    materials = {
        "center": emission_material("RigCenter", (0.15, 0.95, 0.72, 1.0)),
        "left": emission_material("RigLeft", (1.0, 0.48, 0.12, 1.0)),
        "right": emission_material("RigRight", (0.95, 0.2, 0.66, 1.0)),
    }
    proxies: list[bpy.types.Object] = []
    radius = scale * 0.0045
    joint_radius = scale * 0.0065
    for bone in armature.data.bones:
        head = armature.matrix_world @ bone.head_local
        tail = armature.matrix_world @ bone.tail_local
        direction = tail - head
        length = direction.length
        if length <= 1e-6:
            continue
        key = bone_color(bone.name)
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=10,
            radius=radius,
            depth=length,
            location=(head + tail) * 0.5,
        )
        segment = bpy.context.object
        segment.name = f"RigProxy::{bone.name}"
        segment.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
        segment.data.materials.append(materials[key])
        proxies.append(segment)

        bpy.ops.mesh.primitive_ico_sphere_add(
            subdivisions=1,
            radius=joint_radius,
            location=head,
        )
        joint = bpy.context.object
        joint.name = f"RigJoint::{bone.name}"
        joint.data.materials.append(materials[key])
        proxies.append(joint)
    return proxies


def render_previews(
    preview_dir: Path,
    armature: bpy.types.Object,
    render_meshes: list[bpy.types.Object],
    bounds_min: Vector,
    bounds_max: Vector,
) -> dict[str, str]:
    preview_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.world.color = (0.004, 0.006, 0.01)

    # Inspect the authored rest pose. Existing actions remain untouched.
    armature.data.pose_position = "REST"

    render_set = set(render_meshes)
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH" and obj not in render_set:
            obj.hide_render = True

    inspection_shell = emission_material(
        "RigInspectionShell",
        (0.23, 0.31, 0.36, 0.34),
    )
    inspection_shell.surface_render_method = "DITHERED"
    shell_shader = next(
        node
        for node in inspection_shell.node_tree.nodes
        if node.bl_idname == "ShaderNodeBsdfPrincipled"
    )
    shell_shader.inputs["Alpha"].default_value = 0.34
    shell_shader.inputs["Emission Strength"].default_value = 0.32
    for obj in render_meshes:
        for slot in obj.material_slots:
            slot.material = inspection_shell

    center = (bounds_min + bounds_max) * 0.5
    dimensions = bounds_max - bounds_min
    largest = max(dimensions)
    distance = largest * 2.6
    camera_height = center.z + dimensions.z * 0.02

    camera_data = bpy.data.cameras.new("RigInspectionCamera")
    camera = bpy.data.objects.new("RigInspectionCamera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = max(dimensions.z * 1.15, dimensions.x * 1.55, dimensions.y * 1.55)

    add_area_light(
        "RigKey",
        (center.x + distance, center.y - distance, center.z + distance),
        1050,
        largest * 1.2,
        (0.82, 0.91, 1.0),
    )
    add_area_light(
        "RigFill",
        (center.x - distance, center.y - distance * 0.4, center.z + distance * 0.2),
        700,
        largest,
        (0.4, 0.72, 1.0),
    )
    add_area_light(
        "RigRim",
        (center.x, center.y + distance, center.z + distance * 0.6),
        950,
        largest,
        (0.45, 1.0, 0.68),
    )

    create_bone_proxies(armature, largest)
    views = {
        # This Tripo rig uses Y as the anatomical left/right axis and faces +X.
        "front": Vector((center.x + distance, center.y, camera_height)),
        "side": Vector((center.x, center.y - distance, camera_height)),
        "back": Vector((center.x - distance, center.y, camera_height)),
    }
    outputs = {}
    for view_name, location in views.items():
        camera.location = location
        camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
        output = preview_dir / f"rig-{view_name}.png"
        scene.render.filepath = str(output)
        bpy.ops.render.render(write_still=True)
        outputs[view_name] = str(output)
    return outputs


def main() -> None:
    args = parse_args()
    model_path = Path(args.model).resolve()
    report_path = Path(args.report).resolve()
    bone_map_path = Path(args.bone_map).resolve()
    preview_dir = Path(args.preview_dir).resolve()
    if not model_path.is_file():
        raise FileNotFoundError(model_path)

    reset_scene()
    bpy.ops.import_scene.gltf(filepath=str(model_path))

    scene = bpy.context.scene
    objects = list(scene.objects)
    source_materials = list(bpy.data.materials)
    armatures = [obj for obj in objects if obj.type == "ARMATURE"]
    meshes = [obj for obj in objects if obj.type == "MESH"]
    if not armatures:
        raise RuntimeError("GLB contains no Armature")
    if not meshes:
        raise RuntimeError("GLB contains no Mesh")

    armature = max(armatures, key=lambda obj: len(obj.data.bones))
    skinned_meshes = [
        obj
        for obj in meshes
        if any(modifier.type == "ARMATURE" and modifier.object == armature for modifier in obj.modifiers)
    ]
    if not skinned_meshes:
        skinned_meshes = [obj for obj in meshes if obj.vertex_groups]
    if not skinned_meshes:
        skinned_meshes = meshes
    auxiliary_meshes = [obj for obj in meshes if obj not in skinned_meshes]

    all_min, all_max = world_bounds(meshes)
    primary_min, primary_max = world_bounds(skinned_meshes)
    mapping = select_mapping(armature, primary_min, primary_max)
    weight_stats = collect_weight_stats(skinned_meshes, armature)

    ordered_bones: list[bpy.types.Bone] = []

    def append_branch(bone: bpy.types.Bone) -> None:
        ordered_bones.append(bone)
        for child in sorted(bone.children, key=lambda item: item.name):
            append_branch(child)

    for root_bone in sorted(
        (bone for bone in armature.data.bones if bone.parent is None),
        key=lambda item: item.name,
    ):
        append_branch(root_bone)

    bone_rows = []
    for bone in ordered_bones:
        bone_rows.append(
            {
                "name": bone.name,
                "parent": bone.parent.name if bone.parent else None,
                "children": [child.name for child in bone.children],
                "depth": bone_depth(bone),
                "use_deform": bone.use_deform,
                "head_local": rounded(bone.head_local),
                "tail_local": rounded(bone.tail_local),
                "length": round(float(bone.length), 5),
                "weights": weight_stats[bone.name],
            }
        )

    action_rows = []
    for action in bpy.data.actions:
        start, end = action.frame_range
        action_rows.append(
            {
                "name": action.name,
                "frame_range": [round(float(start), 3), round(float(end), 3)],
                "duration_frames": round(float(end - start), 3),
                "duration_seconds": round(float(end - start) / (scene.render.fps / scene.render.fps_base), 4),
                "slots": len(getattr(action, "slots", [])),
            }
        )

    nla_rows = []
    if armature.animation_data:
        for track in armature.animation_data.nla_tracks:
            nla_rows.append(
                {
                    "track": track.name,
                    "mute": track.mute,
                    "strips": [
                        {
                            "name": strip.name,
                            "action": strip.action.name if strip.action else None,
                            "frame_start": round(float(strip.frame_start), 3),
                            "frame_end": round(float(strip.frame_end), 3),
                        }
                        for strip in track.strips
                    ],
                }
            )

    mesh_rows = []
    for obj in meshes:
        stats = mesh_stats(obj.data)
        mesh_min, mesh_max = world_bounds([obj])
        mesh_rows.append(
            {
                "object": obj.name,
                "mesh": obj.data.name,
                "skinned": obj in skinned_meshes,
                "parent": obj.parent.name if obj.parent else None,
                "hide_render": obj.hide_render,
                "vertex_groups": len(obj.vertex_groups),
                "armature_modifiers": [
                    modifier.object.name if modifier.object else None
                    for modifier in obj.modifiers
                    if modifier.type == "ARMATURE"
                ],
                "materials": [
                    slot.material.name if slot.material else None
                    for slot in obj.material_slots
                ],
                "topology": stats,
                "bounds_min": rounded(mesh_min),
                "bounds_max": rounded(mesh_max),
                "dimensions": rounded(mesh_max - mesh_min),
                "origin_world": rounded(obj.matrix_world.translation),
                "location": rounded(obj.location),
                "rotation_euler_radians": rounded(obj.rotation_euler),
                "scale": rounded(obj.scale),
            }
        )

    preview_outputs = render_previews(
        preview_dir,
        armature,
        skinned_meshes,
        primary_min,
        primary_max,
    )

    fps = scene.render.fps / scene.render.fps_base
    total_stats = Counter()
    for row in mesh_rows:
        total_stats.update(row["topology"])
    primary_stats = Counter()
    for row in mesh_rows:
        if row["skinned"]:
            primary_stats.update(row["topology"])

    bone_map_payload = {
        "source": str(model_path),
        "generated_with": f"Blender {bpy.app.version_string}",
        "method": "骨骼名称语义、父子层级、局部空间位置和左右侧标记综合评分；证据不足时保留 unresolved，不强行假设 Mixamo 命名。",
        "armature": armature.name,
        "roles": mapping,
        "bones": bone_rows,
    }
    bone_map_path.parent.mkdir(parents=True, exist_ok=True)
    bone_map_path.write_text(
        json.dumps(bone_map_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    hierarchy_lines = []
    for row in bone_rows:
        hierarchy_lines.append(
            f"{'  ' * row['depth']}- `{row['name']}`"
            f" — parent: `{row['parent'] or 'None'}`, deform: `{row['use_deform']}`, "
            f"weighted vertices: `{row['weights']['weighted_vertices']}`, "
            f"head: `{row['head_local']}`, tail: `{row['tail_local']}`"
        )

    role_lines = []
    for role, entry in mapping.items():
        evidence = "；".join(entry["evidence"])
        role_lines.append(
            f"| {role} | `{entry['bone'] or '未识别/不存在'}` | {entry['confidence']} | {evidence} |"
        )

    mesh_lines = []
    for row in mesh_rows:
        mesh_lines.append(
            f"| `{row['object']}` | {'是' if row['skinned'] else '否'} | "
            f"{row['topology']['vertices']:,} | {row['topology']['triangles']:,} | "
            f"`{row['dimensions']}` | `{row['origin_world']}` | "
            f"`{', '.join(item or 'None' for item in row['materials']) or '无'}` |"
        )

    material_lines = []
    for material in source_materials:
        details = material_details(material)
        textures = []
        for texture in details["textures"]:
            textures.append(
                f"`{texture['image']}` {texture['size'][0]}×{texture['size'][1]} "
                f"({texture['colorspace']}, {'内嵌' if texture['packed'] else texture['filepath'] or '外部路径为空'})"
            )
        material_lines.append(
            f"- `{details['name']}`：渲染模式 `{details['blend_method']}`；贴图："
            f"{'；'.join(textures) if textures else '无图像纹理'}"
        )

    action_lines = []
    for action in action_rows:
        action_lines.append(
            f"| `{action['name']}` | {action['frame_range'][0]}–{action['frame_range'][1]} | "
            f"{action['duration_frames']} | {action['duration_seconds']} s | {action['slots']} |"
        )
    if not action_lines:
        action_lines.append("| 无 | — | — | — | — |")

    scene_range = [scene.frame_start, scene.frame_end]
    primary_dimensions = primary_max - primary_min
    all_dimensions = all_max - all_min
    auxiliary_note = (
        "、".join(f"`{obj.name}`" for obj in auxiliary_meshes)
        if auxiliary_meshes
        else "无"
    )
    source_orientation = (
        "Blender 导入后为 Z-up。根据左右肢体主要沿 Y 轴展开、头盔面罩朝 +X，"
        "判断角色面向 +X；正面相机位于 +X，侧面相机位于 -Y，背面相机位于 -X。"
        "GLB 导入对象旋转均记录在下表，未在检查过程中应用变换。"
    )

    report = f"""# Astronaut Rig Inspection Report

生成日期：{__import__('datetime').datetime.now().astimezone().isoformat(timespec='seconds')}

源文件：`{model_path}`

检查工具：Blender {bpy.app.version_string} / Blender Python API

检查方式：只读导入到临时场景；未覆盖源 GLB、未删除动画、未修改拓扑。

## 结论摘要

- Armature：`{armature.name}`，共 {len(armature.data.bones)} 根骨骼。
- 主宇航员由 {len(skinned_meshes)} 个蒙皮 Mesh 构成；另外发现辅助/非蒙皮 Mesh：{auxiliary_note}。
- 主宇航员尺寸：`{rounded(primary_dimensions)}`；完整导入场景尺寸：`{rounded(all_dimensions)}`。
- 主宇航员面数：{primary_stats['faces']:,} faces / {primary_stats['triangles']:,} triangles。
- 完整 GLB 面数：{total_stats['faces']:,} faces / {total_stats['triangles']:,} triangles。
- 已有 Action：{', '.join(f"`{row['name']}`" for row in action_rows) if action_rows else '无'}。
- 网页准备风险：源文件包含额外的非蒙皮 Mesh 时，应在正式网页导出副本中明确排除；本次没有删除该对象。
- `Root` 与 `Hip` 的骨骼尾端明显伸出人体轮廓；两者分别影响 {weight_stats.get('Root', {}).get('weighted_vertices', 0)} / {weight_stats.get('Hip', {}).get('weighted_vertices', 0)} 个顶点，应结合动作变形继续确认是否需要保留为 deform bone。

## 环境与前端技术栈

- Blender：{bpy.app.version_string}。
- 项目：Next.js 16.2.6、React 19.2.6、TypeScript 5.9.3。
- 3D：React Three Fiber 9.4.0、Three.js 0.180.0。
- 滚动动画：GSAP 3.13.0 / ScrollTrigger。
- 现有入口：`components/scene/EchoScene.tsx` 使用 `GLTFLoader`、`SkeletonUtils.clone`、`AnimationMixer`，并以滚动进度采样动画。

## 场景、尺寸、坐标与原点

- 场景单位：`{scene.unit_settings.system}`，长度单位：`{scene.unit_settings.length_unit}`，scale_length：{scene.unit_settings.scale_length}。
- 帧率：{scene.render.fps}/{scene.render.fps_base} = {fps:g} fps。
- Scene 帧范围：{scene_range[0]}–{scene_range[1]}。
- 主宇航员 Bounds：min `{rounded(primary_min)}`，max `{rounded(primary_max)}`。
- 完整 GLB Bounds：min `{rounded(all_min)}`，max `{rounded(all_max)}`。
- 朝向判断：{source_orientation}

| Mesh Object | 蒙皮 | 顶点 | 三角面 | 尺寸 XYZ | 世界原点 | 材质 |
| --- | --- | ---: | ---: | --- | --- | --- |
{chr(10).join(mesh_lines)}

## Armature 与骨骼层级

Armature Object：`{armature.name}`

Armature Location：`{rounded(armature.location)}`

Armature Rotation (radians)：`{rounded(armature.rotation_euler)}`

Armature Scale：`{rounded(armature.scale)}`

{chr(10).join(hierarchy_lines)}

## 主要骨骼识别

映射不是按 Mixamo 名称硬编码；结果综合使用名称语义、层级、局部坐标与左右侧标记。证据不足的项目会保留未识别。

| 目标角色 | 识别骨骼 | 置信度 | 证据 |
| --- | --- | --- | --- |
{chr(10).join(role_lines)}

完整机器可读映射见：`{bone_map_path}`。

## 材质与贴图

{chr(10).join(material_lines) if material_lines else '- 无材质'}

## Animation Actions

| Action | 帧范围 | 时长帧数 | 时长秒数 | Slots |
| --- | ---: | ---: | ---: | ---: |
{chr(10).join(action_lines)}

NLA 数据：

```json
{json.dumps(nla_rows, ensure_ascii=False, indent=2)}
```

注意：当前 Action 的视觉语义需要结合逐帧预览确认。检查报告只记录源文件中的真实名称和时间范围，不把测试动作重命名为最终动作。
用户已说明当前 Action 是“害怕”测试动作，后续最终动作清单不应复用该语义。

## 骨骼检查图

- 正面：`{preview_outputs['front']}`
- 侧面：`{preview_outputs['side']}`
- 背面：`{preview_outputs['back']}`

橙色为 Left 命名骨骼，粉色为 Right 命名骨骼，绿色为中轴或未带左右标记的骨骼。预览使用 Rest Pose；源动画未被删除或修改。

## Three.js / React Three Fiber 准备建议

1. 保留源 GLB 作为只读母版，在新的网页导出副本中处理额外非蒙皮 Mesh、动作命名和压缩。
2. 确认是否需要独立 Root。若骨架只有 Hips 顶层骨骼，网页根运动应由外层 Group 承担，避免把路径位移烘焙进 Hips。
3. 将测试用 Action 与最终动作分开命名；后续建议至少输出 `ZeroG_Idle`、`Fly`、`Turn`、`Reach`、`Wave` 等独立 Action。
4. GLB 导出后必须重新导入检查：骨骼数量、Action 名称、帧范围、贴图、辅助 Mesh 和 bind pose。
5. 当前模型无 Shape Key 时，肩、髋等极限姿态的穿模只能依赖权重、硬质件单骨骼绑定或后续 corrective 方案解决。
"""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")

    print(
        json.dumps(
            {
                "report": str(report_path),
                "bone_map": str(bone_map_path),
                "previews": preview_outputs,
                "armature": armature.name,
                "bones": len(armature.data.bones),
                "meshes": len(meshes),
                "actions": [row["name"] for row in action_rows],
                "primary_triangles": primary_stats["triangles"],
                "total_triangles": total_stats["triangles"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
