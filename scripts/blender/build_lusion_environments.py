"""Build web-ready corridor, organic portal room, and pre-fractured shards.

The source recording is used only as visual direction. All geometry and
materials in this file are original Echo assets.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


ROOT = Path(parse_args().project_root).resolve()
DESIGN_ROOT = ROOT / "design/3d"
PREVIEW_V01 = DESIGN_ROOT / "previews/lusion-environment-v01"
PREVIEW_V02 = DESIGN_ROOT / "previews/lusion-environment-v02"
PUBLIC_MODELS = ROOT / "public/models"
BLEND_V01 = DESIGN_ROOT / "lusion-environment-blockout-v01.blend"
BLEND_V02 = DESIGN_ROOT / "lusion-environment-refined-v02.blend"
CORRIDOR_GLB = PUBLIC_MODELS / "lusion-corridor-module-v02.glb"
PORTAL_GLB = PUBLIC_MODELS / "lusion-portal-room-v02.glb"
SHARDS_GLB = PUBLIC_MODELS / "lusion-portal-shards-v02.glb"


def clean_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.metaballs,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)
    for collection in list(bpy.data.collections):
        if collection.name != "Collection":
            bpy.data.collections.remove(collection)


def collection(name: str) -> bpy.types.Collection:
    result = bpy.data.collections.get(name)
    if result is None:
        result = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(result)
    return result


def move_to(obj: bpy.types.Object, target: bpy.types.Collection) -> None:
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    target.objects.link(obj)


def material(
    name: str,
    color: tuple[float, float, float, float],
    *,
    metallic: float,
    roughness: float,
    emission: tuple[float, float, float, float] | None = None,
    emission_strength: float = 0.0,
    transmission: float = 0.0,
    alpha: float = 1.0,
) -> bpy.types.Material:
    result = bpy.data.materials.new(name)
    result.use_nodes = True
    principled = result.node_tree.nodes.get("Principled BSDF")
    if principled is None:
        principled = next(
            node
            for node in result.node_tree.nodes
            if node.type == "BSDF_PRINCIPLED"
        )
    principled.inputs["Base Color"].default_value = color
    principled.inputs["Metallic"].default_value = metallic
    principled.inputs["Roughness"].default_value = roughness
    transmission_input = principled.inputs.get("Transmission Weight")
    if transmission_input is not None:
        transmission_input.default_value = transmission
    alpha_input = principled.inputs.get("Alpha")
    if alpha_input is not None:
        alpha_input.default_value = alpha
    if emission is not None:
        emission_input = principled.inputs.get("Emission Color")
        emission_strength_input = principled.inputs.get("Emission Strength")
        if emission_input is not None:
            emission_input.default_value = emission
        if emission_strength_input is not None:
            emission_strength_input.default_value = emission_strength
    result.diffuse_color = color
    result.surface_render_method = "DITHERED" if alpha < 1.0 else "DITHERED"
    return result


def add_box(
    name: str,
    location: tuple[float, float, float],
    dimensions: tuple[float, float, float],
    mat: bpy.types.Material,
    target: bpy.types.Collection,
    *,
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0),
    bevel: float = 0.05,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    move_to(obj, target)
    if bevel > 0:
        modifier = obj.modifiers.new("Edge highlights", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
        modifier.limit_method = "ANGLE"
    return obj


def build_corridor(refined: bool) -> bpy.types.Collection:
    target = collection("WEB_CorridorModule")
    dark = material(
        "Corridor_Mirror",
        (0.018, 0.028, 0.038, 1.0),
        metallic=0.94,
        roughness=0.12 if refined else 0.28,
    )
    glass = material(
        "Corridor_Glass",
        (0.12, 0.33, 0.44, 0.28),
        metallic=0.16,
        roughness=0.08,
        transmission=0.82,
        alpha=0.26,
    )
    cool = material(
        "Corridor_Light_Cool",
        (0.15, 0.82, 1.0, 1.0),
        metallic=0.0,
        roughness=0.22,
        emission=(0.15, 0.82, 1.0, 1.0),
        emission_strength=8.0,
    )
    warm = material(
        "Corridor_Light_Warm",
        (1.0, 0.08, 0.22, 1.0),
        metallic=0.0,
        roughness=0.2,
        emission=(1.0, 0.08, 0.22, 1.0),
        emission_strength=7.0,
    )

    beam = 0.105 if refined else 0.16
    depth = 0.32
    add_box("Corridor_Frame_Top", (0, 0, 2.55), (8.7, depth, beam), dark, target)
    add_box(
        "Corridor_Frame_Bottom", (0, 0, -2.55), (8.7, depth, beam), dark, target
    )
    add_box("Corridor_Frame_Left", (-4.3, 0, 0), (beam, depth, 5.2), dark, target)
    add_box("Corridor_Frame_Right", (4.3, 0, 0), (beam, depth, 5.2), dark, target)

    for index, angle in enumerate((-0.42, -0.21, 0.21, 0.42)):
        side = -1 if index < 2 else 1
        add_box(
            f"Corridor_Brace_{index:02d}",
            (side * (2.0 + (index % 2) * 1.45), 0.02, 0),
            (beam * 0.7, depth * 0.72, 4.8),
            dark,
            target,
            rotation=(0, angle * 0.18, angle),
            bevel=0.035,
        )

    panel_count = 8 if refined else 4
    for index in range(panel_count):
        t = index / max(panel_count - 1, 1)
        side = -1 if index % 2 == 0 else 1
        add_box(
            f"Corridor_Glass_{index:02d}",
            (side * (1.25 + t * 2.55), 0.12 + t * 0.08, (t - 0.5) * 3.7),
            (1.2 + t * 1.4, 0.035, 0.22 + (index % 3) * 0.16),
            glass,
            target,
            rotation=(0.04 * side, 0.1 * side, 0.18 * side),
            bevel=0.018,
        )

    light_count = 14 if refined else 8
    for index in range(light_count):
        side = -1 if index % 2 == 0 else 1
        z = -2.22 + (index % 7) * 0.74
        x = side * (3.85 - (index % 3) * 0.56)
        add_box(
            f"Corridor_Light_{'A' if side < 0 else 'B'}_{index:02d}",
            (x, -0.2 + (index % 4) * 0.09, z),
            (0.58 + (index % 3) * 0.22, 0.055, 0.055),
            cool if side < 0 else warm,
            target,
            rotation=(0.0, 0.0, side * 0.08),
            bevel=0.012,
        )

    rng = random.Random(721 if refined else 220)
    block_count = 26 if refined else 12
    for index in range(block_count):
        side = -1 if rng.random() < 0.5 else 1
        add_box(
            f"Corridor_Reflector_{index:02d}",
            (
                side * rng.uniform(2.4, 4.8),
                rng.uniform(-0.5, 0.62),
                rng.uniform(-2.8, 2.8),
            ),
            (
                rng.uniform(0.15, 0.7),
                rng.uniform(0.12, 0.58),
                rng.uniform(0.12, 0.76),
            ),
            dark,
            target,
            rotation=(
                rng.uniform(-0.15, 0.15),
                rng.uniform(-0.2, 0.2),
                rng.uniform(-0.3, 0.3),
            ),
            bevel=0.04,
        )
    return target


def meta_element(
    meta: bpy.types.MetaBall,
    location: tuple[float, float, float],
    radius: float,
    *,
    stiffness: float = 2.0,
) -> None:
    element = meta.elements.new()
    element.co = location
    element.radius = radius
    element.stiffness = stiffness


def add_irregular_ring(
    name: str,
    location: tuple[float, float, float],
    radii: tuple[float, float],
    plane: str,
    mat: bpy.types.Material,
    target: bpy.types.Collection,
    *,
    phase: float,
    thickness: float,
    segments: int = 56,
) -> bpy.types.Object:
    """Create a single continuous, slightly asymmetric graphic ring."""
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int, int]] = []
    for index in range(segments):
        angle = math.tau * index / segments
        ripple = (
            1
            + math.sin(angle * 3 + phase) * 0.075
            + math.sin(angle * 7 - phase * 0.61) * 0.028
        )
        outer_u = math.cos(angle) * radii[0] * ripple
        outer_v = math.sin(angle) * radii[1] * ripple
        inner_ripple = 1 + math.sin(angle * 2 - phase) * 0.06
        inner_scale = max(0.22, 1 - thickness)
        inner_u = math.cos(angle) * radii[0] * inner_scale * inner_ripple
        inner_v = math.sin(angle) * radii[1] * inner_scale * inner_ripple

        def coordinate(u: float, v: float) -> tuple[float, float, float]:
            if plane == "xy":
                return (u, v, 0)
            if plane == "xz":
                return (u, 0, v)
            return (0, u, v)

        vertices.append(coordinate(outer_u, outer_v))
        vertices.append(coordinate(inner_u, inner_v))
    for index in range(segments):
        next_index = (index + 1) % segments
        faces.append(
            (
                index * 2,
                next_index * 2,
                next_index * 2 + 1,
                index * 2 + 1,
            )
        )
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(mat)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = location
    target.objects.link(obj)
    return obj


def build_portal(refined: bool) -> bpy.types.Collection:
    target = collection("WEB_PortalRoom")
    organic = material(
        "Portal_Organic",
        (0.008, 0.035, 0.78, 1.0),
        metallic=0.18,
        roughness=0.16 if refined else 0.28,
        emission=(0.008, 0.025, 0.56, 1.0),
        emission_strength=1.35 if refined else 0.72,
        transmission=0.08 if refined else 0.02,
    )
    core = material(
        "Portal_Core",
        (0.82, 0.85, 1.0, 1.0),
        metallic=0.02,
        roughness=0.18,
        emission=(0.55, 0.66, 1.0, 1.0),
        emission_strength=5.8,
        transmission=0.18,
        alpha=0.98,
    )
    pattern = material(
        "Portal_Pattern",
        (0.63, 0.66, 0.82, 1.0),
        metallic=0.03,
        roughness=0.28,
        emission=(0.25, 0.31, 0.62, 1.0),
        emission_strength=2.3 if refined else 1.2,
    )

    # The reference room is a smooth architectural tunnel. Its organic
    # character comes from irregular continuous rings, not overlapping blobs.
    room_depth = 9.6 if refined else 6.8
    wall_thickness = 0.16
    add_box(
        "Portal_Room_Floor",
        (0, room_depth * 0.5, -2.72),
        (8.5, room_depth, wall_thickness),
        organic,
        target,
        bevel=0.06,
    )
    add_box(
        "Portal_Room_Ceiling",
        (0, room_depth * 0.5, 2.72),
        (8.5, room_depth, wall_thickness),
        organic,
        target,
        bevel=0.06,
    )
    for side in (-1, 1):
        add_box(
            f"Portal_Room_Wall_{'L' if side < 0 else 'R'}",
            (side * 4.22, room_depth * 0.5, 0),
            (wall_thickness, room_depth, 5.5),
            organic,
            target,
            bevel=0.06,
        )

    rng = random.Random(901 if refined else 114)
    ring_count = 34 if refined else 16
    for index in range(ring_count):
        surface = index % 4
        depth = rng.uniform(0.4, room_depth - 0.4)
        radius_a = rng.uniform(0.38, 1.35)
        radius_b = rng.uniform(0.24, 0.92)
        offset = rng.uniform(-2.9, 2.9)
        if surface == 0:
            location = (offset, depth, -2.625)
            plane = "xy"
            radii = (radius_a, radius_b)
        elif surface == 1:
            location = (offset, depth, 2.625)
            plane = "xy"
            radii = (radius_a, radius_b)
        elif surface == 2:
            location = (-4.125, depth, rng.uniform(-1.9, 1.9))
            plane = "yz"
            radii = (radius_a, radius_b)
        else:
            location = (4.125, depth, rng.uniform(-1.9, 1.9))
            plane = "yz"
            radii = (radius_a, radius_b)
        add_irregular_ring(
            f"Portal_Pattern_{index:02d}",
            location,
            radii,
            plane,
            pattern,
            target,
            phase=rng.uniform(0, math.tau),
            thickness=rng.uniform(0.26, 0.52),
            segments=56 if refined else 36,
        )

    # Repeating luminous side apertures establish the deep perspective and
    # provide the deliberately overexposed white/cyan transition.
    aperture_count = 6 if refined else 3
    for index in range(aperture_count):
        depth = 0.9 + index * ((room_depth - 1.8) / max(aperture_count - 1, 1))
        for side in (-1, 1):
            add_box(
                f"Portal_Aperture_{index:02d}_{'L' if side < 0 else 'R'}",
                (side * 4.105, depth, -0.15),
                (0.035, 0.82, 2.55),
                core,
                target,
                bevel=0.12,
            )

    curve_data = bpy.data.curves.new("Portal_CoreRing_Curve", type="CURVE")
    curve_data.dimensions = "3D"
    curve_data.resolution_u = 2
    curve_data.bevel_depth = 0.085 if refined else 0.12
    curve_data.bevel_resolution = 4
    spline = curve_data.splines.new("POLY")
    count = 128
    spline.points.add(count - 1)
    for index in range(count):
        angle = math.tau * index / count
        spline.points[index].co = (
            math.cos(angle) * 2.05,
            -0.24,
            math.sin(angle) * 2.05,
            1.0,
        )
    spline.use_cyclic_u = True
    ring = bpy.data.objects.new("Portal_CoreRing", curve_data)
    curve_data.materials.append(core)
    target.objects.link(ring)
    bpy.context.view_layer.objects.active = ring
    ring.select_set(True)
    bpy.ops.object.convert(target="MESH")
    ring.select_set(False)

    add_box(
        "Portal_BackReflector",
        (0, room_depth - 0.08, 0.0),
        (5.0, 0.1, 4.6),
        core,
        target,
        bevel=0.14,
    )
    return target


def build_shards(refined: bool) -> bpy.types.Collection:
    target = collection("WEB_PortalShards")
    shard_mat = material(
        "Portal_ShardGlass",
        (0.12, 0.56, 1.0, 0.82),
        metallic=0.18,
        roughness=0.06,
        emission=(0.05, 0.34, 1.0, 1.0),
        emission_strength=2.4,
        transmission=0.66,
        alpha=0.78,
    )
    rng = random.Random(1441 if refined else 449)
    count = 58 if refined else 24
    for index in range(count):
        angle = rng.random() * math.tau
        radius = rng.uniform(0.55, 2.85)
        x = math.cos(angle) * radius
        z = math.sin(angle) * radius * 0.74
        y = rng.uniform(-0.6, 0.8)
        scale = rng.uniform(0.12, 0.48)
        vertices = [
            (-scale * 0.7, -scale * 0.08, -scale),
            (scale * 0.9, scale * 0.12, -scale * 0.35),
            (scale * 0.25, -scale * 0.05, scale * 1.2),
            (-scale * 0.18, scale * 0.28, scale * 0.05),
        ]
        faces = [(0, 1, 2), (0, 3, 1), (1, 3, 2), (2, 3, 0)]
        mesh = bpy.data.meshes.new(f"Portal_Shard_{index:03d}_Mesh")
        mesh.from_pydata(vertices, [], faces)
        mesh.materials.append(shard_mat)
        mesh.update()
        obj = bpy.data.objects.new(f"Portal_Shard_{index:03d}", mesh)
        obj.location = (x, y, z)
        obj.rotation_euler = (
            rng.uniform(-math.pi, math.pi),
            rng.uniform(-math.pi, math.pi),
            rng.uniform(-math.pi, math.pi),
        )
        obj["burst_vector"] = (
            math.cos(angle) * rng.uniform(1.6, 4.8),
            rng.uniform(-0.4, 2.4),
            math.sin(angle) * rng.uniform(1.2, 4.0),
        )
        target.objects.link(obj)
    return target


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def add_preview_rig() -> tuple[bpy.types.Object, bpy.types.Material]:
    preview = collection("PREVIEW")
    clay = material(
        "Preview_Clay",
        (0.42, 0.47, 0.54, 1),
        metallic=0.18,
        roughness=0.48,
    )
    camera_data = bpy.data.cameras.new("PreviewCamera")
    camera = bpy.data.objects.new("PreviewCamera", camera_data)
    camera.data.lens = 56
    preview.objects.link(camera)
    bpy.context.scene.camera = camera
    for name, location, energy, color, size in (
        ("Key", (-4.5, -7.0, 7.5), 1550, (0.62, 0.8, 1.0), 5.5),
        ("Fill", (5.5, -2.0, 1.5), 1100, (0.18, 0.42, 1.0), 4.0),
        ("Rim", (0.0, 6.0, 5.0), 1450, (0.35, 0.16, 1.0), 3.2),
    ):
        light_data = bpy.data.lights.new(name, type="AREA")
        light_data.energy = energy
        light_data.color = color
        light_data.shape = "DISK"
        light_data.size = size
        light = bpy.data.objects.new(name, light_data)
        light.location = location
        look_at(light, Vector((0, 1.5, 0)))
        preview.objects.link(light)
    return camera, clay


VIEWS = {
    "front": ((0.0, -14.0, 0.4), (0.0, 1.3, 0.0)),
    "side": ((12.5, 2.0, 0.8), (0.0, 1.5, 0.0)),
    "back": ((0.0, 14.0, 0.4), (0.0, 1.6, 0.0)),
    "three-quarter": ((9.6, -10.5, 6.8), (0.0, 1.3, 0.0)),
}


def configure_render() -> None:
    scene = bpy.context.scene
    # Blender 5.2 exposes Eevee Next through the BLENDER_EEVEE enum.
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 760
    scene.render.resolution_y = 760
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.view_settings.look = "AgX - Medium High Contrast"
    world = bpy.data.worlds.new("EchoPreviewWorld")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (
        0.002,
        0.004,
        0.012,
        1,
    )
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.16
    scene.world = world


def render_views(
    output_dir: Path,
    modes: tuple[str, ...],
    *,
    include_corridor: bool,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    camera, clay = add_preview_rig()
    configure_render()
    corridor = bpy.data.collections.get("WEB_CorridorModule")
    if corridor:
        corridor.hide_render = not include_corridor
    render_objects = [
        obj
        for collection_name in ("WEB_CorridorModule", "WEB_PortalRoom", "WEB_PortalShards")
        for obj in bpy.data.collections[collection_name].all_objects
        if obj.type == "MESH"
    ]
    slots = {
        obj.name: [slot.material for slot in obj.material_slots] for obj in render_objects
    }
    scene = bpy.context.scene
    for mode in modes:
        scene.render.engine = (
            "BLENDER_WORKBENCH" if mode == "wireframe" else "BLENDER_EEVEE"
        )
        if mode == "wireframe":
            scene.display.shading.light = "STUDIO"
            scene.display.shading.color_type = "SINGLE"
            scene.display.shading.single_color = (0.12, 0.42, 0.82)
            scene.display.shading.show_shadows = True
            scene.display.shading.show_cavity = True
            scene.display.shading.cavity_type = "WORLD"
            for obj in render_objects:
                obj.show_wire = True
                obj.show_all_edges = True
        else:
            for obj in render_objects:
                obj.show_wire = False
            if mode == "clay":
                for obj in render_objects:
                    for slot in obj.material_slots:
                        slot.material = clay
            else:
                for obj in render_objects:
                    original = slots[obj.name]
                    for index, slot in enumerate(obj.material_slots):
                        slot.material = original[index]
        for view_name, (location, target) in VIEWS.items():
            camera.location = location
            look_at(camera, Vector(target))
            scene.render.filepath = str(output_dir / f"{mode}_{view_name}.png")
            bpy.ops.render.render(write_still=True)


def export_collection(target: bpy.types.Collection, filepath: Path) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in target.all_objects:
        if obj.type in {"MESH", "CURVE", "EMPTY"}:
            obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=str(filepath),
        export_format="GLB",
        use_selection=True,
        export_animations=False,
        export_cameras=False,
        export_lights=False,
        export_apply=True,
        export_yup=True,
    )


def report() -> dict[str, object]:
    collections = {}
    for name in ("WEB_CorridorModule", "WEB_PortalRoom", "WEB_PortalShards"):
        target = bpy.data.collections[name]
        mesh_objects = [obj for obj in target.all_objects if obj.type == "MESH"]
        collections[name] = {
            "objects": len(mesh_objects),
            "triangles": sum(
                sum(len(polygon.vertices) - 2 for polygon in obj.data.polygons)
                for obj in mesh_objects
            ),
            "materials": sorted(
                {
                    slot.material.name
                    for obj in mesh_objects
                    for slot in obj.material_slots
                    if slot.material
                }
            ),
            "modifiers": {
                obj.name: [modifier.type for modifier in obj.modifiers]
                for obj in mesh_objects
                if obj.modifiers
            },
        }
    return {
        "blender": bpy.app.version_string,
        "collections": collections,
        "exports": {
            "corridor": str(CORRIDOR_GLB),
            "portal": str(PORTAL_GLB),
            "shards": str(SHARDS_GLB),
        },
        "unresolved_intersections": [
            "Structural corridor reflector blocks intentionally intersect their module frame.",
            "Blue room shell intersections are limited to intentional architectural seams between floor, ceiling, and side walls.",
            "Organic graphic rings are single continuous meshes and sit just above their host surfaces to avoid z-fighting.",
        ],
    }


def build(refined: bool) -> None:
    clean_scene()
    build_corridor(refined)
    build_portal(refined)
    build_shards(refined)


def main() -> None:
    for path in (DESIGN_ROOT, PREVIEW_V01, PREVIEW_V02, PUBLIC_MODELS):
        path.mkdir(parents=True, exist_ok=True)

    build(refined=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_V01))
    render_views(PREVIEW_V01, ("clay",), include_corridor=True)

    build(refined=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_V02))
    render_views(
        PREVIEW_V02,
        ("clay", "wireframe", "material"),
        include_corridor=True,
    )
    export_collection(bpy.data.collections["WEB_CorridorModule"], CORRIDOR_GLB)
    export_collection(bpy.data.collections["WEB_PortalRoom"], PORTAL_GLB)
    export_collection(bpy.data.collections["WEB_PortalShards"], SHARDS_GLB)
    data = report()
    (PREVIEW_V02 / "report.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
