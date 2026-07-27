"""Inspect a GLB and optionally render deterministic acceptance previews.

Run with Blender:
  blender --background --python scripts/blender/inspect_glb.py -- \
    --model /absolute/path/model.glb \
    --output /absolute/path/report.json \
    --preview-dir /absolute/path/previews
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--preview-dir")
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for datablock in list(datablocks):
            datablocks.remove(datablock)


def rounded(values, digits: int = 5) -> list[float]:
    return [round(float(value), digits) for value in values]


def mesh_topology(mesh: bpy.types.Mesh) -> dict[str, int]:
    mesh.calc_loop_triangles()
    edge_faces: Counter[tuple[int, int]] = Counter()
    degenerate_faces = 0

    for polygon in mesh.polygons:
        vertices = polygon.vertices
        if polygon.area <= 1e-12:
            degenerate_faces += 1
        for index, vertex in enumerate(vertices):
            pair = tuple(sorted((vertex, vertices[(index + 1) % len(vertices)])))
            edge_faces[pair] += 1

    return {
        "vertices": len(mesh.vertices),
        "edges": len(mesh.edges),
        "faces": len(mesh.polygons),
        "triangles": len(mesh.loop_triangles),
        "boundary_edges": sum(count == 1 for count in edge_faces.values()),
        "non_manifold_edges": sum(count > 2 for count in edge_faces.values()),
        "degenerate_faces": degenerate_faces,
    }


def collect_bounds(mesh_objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    points = [
        obj.matrix_world @ Vector(corner)
        for obj in mesh_objects
        for corner in obj.bound_box
    ]
    return (
        Vector((min(point.x for point in points), min(point.y for point in points), min(point.z for point in points))),
        Vector((max(point.x for point in points), max(point.y for point in points), max(point.z for point in points))),
    )


def inspect_model(model_path: Path) -> tuple[dict, list[bpy.types.Object], Vector, Vector]:
    bpy.ops.import_scene.gltf(filepath=str(model_path))
    # Blender's glTF importer can create hidden rig-display helpers inside the
    # reserved glTF_not_exported collection. They are not GLB payload meshes and
    # must not be counted as model topology during round-trip validation.
    objects = [
        obj
        for obj in bpy.context.scene.objects
        if not any(
            collection.name == "glTF_not_exported"
            for collection in obj.users_collection
        )
    ]
    mesh_objects = [obj for obj in objects if obj.type == "MESH"]
    if not mesh_objects:
        raise RuntimeError(f"No mesh objects found in {model_path}")

    bounds_min, bounds_max = collect_bounds(mesh_objects)
    dimensions = bounds_max - bounds_min
    topology = [mesh_topology(obj.data) for obj in mesh_objects]
    modifiers = [
        {
            "object": obj.name,
            "name": modifier.name,
            "type": modifier.type,
        }
        for obj in mesh_objects
        for modifier in obj.modifiers
    ]

    materials = []
    for material in bpy.data.materials:
        materials.append(
            {
                "name": material.name,
                "use_nodes": material.use_nodes,
                "surface_render_method": getattr(material, "surface_render_method", None),
                "node_types": (
                    sorted({node.bl_idname for node in material.node_tree.nodes})
                    if material.use_nodes and material.node_tree
                    else []
                ),
            }
        )

    images = []
    for image in bpy.data.images:
        images.append(
            {
                "name": image.name,
                "size": [int(image.size[0]), int(image.size[1])],
                "source": image.source,
                "packed": bool(image.packed_file),
                "filepath": image.filepath,
                "colorspace": image.colorspace_settings.name,
            }
        )

    actions = []
    for action in bpy.data.actions:
        actions.append(
            {
                "name": action.name,
                "frame_range": rounded(action.frame_range, 3),
                "slots": len(getattr(action, "slots", [])),
            }
        )

    armatures = [
        {
            "name": obj.name,
            "bones": len(obj.data.bones),
        }
        for obj in objects
        if obj.type == "ARMATURE"
    ]

    mesh_details = []
    for obj, mesh_stats in zip(mesh_objects, topology, strict=True):
        mesh_details.append(
            {
                "name": obj.name,
                "mesh": obj.data.name,
                "topology": mesh_stats,
                "material_slots": [slot.material.name if slot.material else None for slot in obj.material_slots],
                "location": rounded(obj.location),
                "rotation_euler": rounded(obj.rotation_euler),
                "scale": rounded(obj.scale),
                "dimensions": rounded(obj.dimensions),
                "shape_keys": (
                    len(obj.data.shape_keys.key_blocks)
                    if obj.data.shape_keys and obj.data.shape_keys.key_blocks
                    else 0
                ),
            }
        )

    report = {
        "source": str(model_path),
        "file_size_bytes": model_path.stat().st_size,
        "blender_version": bpy.app.version_string,
        "scene": {
            "objects": len(objects),
            "object_types": dict(sorted(Counter(obj.type for obj in objects).items())),
            "mesh_objects": len(mesh_objects),
            "bounds_min": rounded(bounds_min),
            "bounds_max": rounded(bounds_max),
            "dimensions": rounded(dimensions),
        },
        "totals": {
            key: sum(item[key] for item in topology)
            for key in (
                "vertices",
                "edges",
                "faces",
                "triangles",
                "boundary_edges",
                "non_manifold_edges",
                "degenerate_faces",
            )
        },
        "meshes": mesh_details,
        "materials": materials,
        "images": images,
        "armatures": armatures,
        "actions": actions,
        "modifiers": modifiers,
        "cameras": [obj.name for obj in objects if obj.type == "CAMERA"],
        "lights": [obj.name for obj in objects if obj.type == "LIGHT"],
    }
    return report, mesh_objects, bounds_min, bounds_max


def build_override_material(name: str, mode: str, wire_size: float) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    shader.inputs["Roughness"].default_value = 0.82
    shader.inputs["Metallic"].default_value = 0.0

    if mode == "clay":
        shader.inputs["Base Color"].default_value = (0.58, 0.61, 0.64, 1.0)
        links.new(shader.outputs["BSDF"], output.inputs["Surface"])
        return material

    wire = nodes.new("ShaderNodeWireframe")
    wire.inputs["Size"].default_value = wire_size
    dark = nodes.new("ShaderNodeBsdfPrincipled")
    dark.inputs["Base Color"].default_value = (0.025, 0.03, 0.04, 1.0)
    dark.inputs["Roughness"].default_value = 0.88
    line = nodes.new("ShaderNodeEmission")
    line.inputs["Color"].default_value = (0.28, 0.95, 0.72, 1.0)
    line.inputs["Strength"].default_value = 1.8
    mix = nodes.new("ShaderNodeMixShader")
    links.new(wire.outputs["Fac"], mix.inputs[0])
    links.new(dark.outputs["BSDF"], mix.inputs[1])
    links.new(line.outputs["Emission"], mix.inputs[2])
    links.new(mix.outputs["Shader"], output.inputs["Surface"])
    return material


def add_area_light(name: str, location: tuple[float, float, float], energy: float, size: float, color: tuple[float, float, float]) -> None:
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    data.color = color
    light = bpy.data.objects.new(name, data)
    light.location = location
    bpy.context.scene.collection.objects.link(light)


def render_previews(
    preview_dir: Path,
    mesh_objects: list[bpy.types.Object],
    bounds_min: Vector,
    bounds_max: Vector,
) -> None:
    preview_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.world.color = (0.008, 0.01, 0.015)

    center = (bounds_min + bounds_max) / 2
    dimensions = bounds_max - bounds_min
    largest = max(dimensions)
    distance = largest * 2.25
    camera_height = center.z + dimensions.z * 0.08

    camera_data = bpy.data.cameras.new("AcceptanceCamera")
    camera = bpy.data.objects.new("AcceptanceCamera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = largest * 1.28

    light_scale = max(largest, 1.0)
    add_area_light(
        "Key",
        (center.x + distance, center.y - distance, center.z + distance),
        900.0,
        light_scale,
        (0.82, 0.91, 1.0),
    )
    add_area_light(
        "Fill",
        (center.x - distance, center.y - distance * 0.35, center.z + distance * 0.2),
        560.0,
        light_scale * 0.8,
        (0.45, 0.72, 1.0),
    )
    add_area_light(
        "Rim",
        (center.x, center.y + distance, center.z + distance * 0.75),
        720.0,
        light_scale * 0.7,
        (0.55, 1.0, 0.73),
    )

    views = {
        "front": Vector((center.x, center.y - distance, camera_height)),
        "three-quarter": Vector((center.x + distance * 0.72, center.y - distance * 0.72, camera_height + dimensions.z * 0.12)),
        "side": Vector((center.x + distance, center.y, camera_height)),
        "back": Vector((center.x, center.y + distance, camera_height)),
    }
    clay = build_override_material("AcceptanceClay", "clay", largest * 0.001)
    wire = build_override_material("AcceptanceWire", "wire", largest * 0.0012)

    for mode, override in (("material", None), ("clay", clay), ("wireframe", wire)):
        scene.view_layers[0].material_override = override
        for view_name, location in views.items():
            camera.location = location
            camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
            scene.render.filepath = str(preview_dir / f"{mode}_{view_name}.png")
            bpy.ops.render.render(write_still=True)

    scene.view_layers[0].material_override = None


def main() -> None:
    args = parse_args()
    model_path = Path(args.model).resolve()
    output_path = Path(args.output).resolve()
    reset_scene()
    report, mesh_objects, bounds_min, bounds_max = inspect_model(model_path)

    if args.preview_dir:
        preview_dir = Path(args.preview_dir).resolve()
        render_previews(preview_dir, mesh_objects, bounds_min, bounds_max)
        report["preview_dir"] = str(preview_dir)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"report": str(output_path), "triangles": report["totals"]["triangles"]}))


if __name__ == "__main__":
    main()
