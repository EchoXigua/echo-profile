"""Build the first Echo Core white-model scene.

The scene is intentionally split into stable, named parts so the website can
drive transforms, color and motion without relying on baked Blender animation.
"""

from __future__ import annotations

import math
from pathlib import Path

import bpy
from mathutils import Euler, Vector


ROOT = Path(args["project_root"]).resolve()
BLEND_PATH = ROOT / "design/3d/echo-core-v1.blend"
GLB_PATH = ROOT / "public/models/echo-core-v1.glb"


def clean_scene() -> None:
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
            if datablock.users == 0:
                datablocks.remove(datablock)

    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)


def make_collection(name: str) -> bpy.types.Collection:
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    return collection


def move_to_collection(
    obj: bpy.types.Object, collection: bpy.types.Collection
) -> bpy.types.Object:
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    collection.objects.link(obj)
    return obj


def make_material(
    name: str,
    base_color: tuple[float, float, float, float],
    *,
    metallic: float = 0.0,
    roughness: float = 0.5,
    emission: tuple[float, float, float, float] | None = None,
    emission_strength: float = 0.0,
) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    principled = next(
        (
            node
            for node in material.node_tree.nodes
            if node.type == "BSDF_PRINCIPLED"
        ),
        None,
    )
    if principled is None:
        principled = material.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
    principled.inputs["Base Color"].default_value = base_color
    principled.inputs["Metallic"].default_value = metallic
    principled.inputs["Roughness"].default_value = roughness

    if emission is not None:
        emission_input = principled.inputs.get("Emission Color") or principled.inputs.get(
            "Emission"
        )
        strength_input = principled.inputs.get("Emission Strength")
        if emission_input is not None:
            emission_input.default_value = emission
        if strength_input is not None:
            strength_input.default_value = emission_strength

    return material


def add_empty(
    name: str,
    parent: bpy.types.Object | None,
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    empty = bpy.data.objects.new(name, None)
    empty.empty_display_type = "PLAIN_AXES"
    empty.empty_display_size = 0.32
    empty.parent = parent
    collection.objects.link(empty)
    return empty


def add_ico(
    name: str,
    radius: float,
    subdivisions: int,
    material: bpy.types.Material,
    parent: bpy.types.Object,
    collection: bpy.types.Collection,
    *,
    location: Vector = Vector((0.0, 0.0, 0.0)),
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_ico_sphere_add(
        subdivisions=subdivisions,
        radius=radius,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    obj.data.materials.append(material)
    obj.parent = parent
    move_to_collection(obj, collection)
    return obj


def sphere_point(radius: float, latitude: float, longitude: float) -> Vector:
    lat = math.radians(latitude)
    lon = math.radians(longitude)
    return Vector(
        (
            radius * math.cos(lat) * math.cos(lon),
            radius * math.cos(lat) * math.sin(lon),
            radius * math.sin(lat),
        )
    )


def add_shell_panel(
    *,
    name: str,
    latitude: float,
    longitude: float,
    lat_span: float,
    lon_span: float,
    radius: float,
    thickness: float,
    material: bpy.types.Material,
    parent: bpy.types.Object,
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    lat_min = latitude - lat_span / 2
    lat_max = latitude + lat_span / 2
    lon_min = longitude - lon_span / 2
    lon_max = longitude + lon_span / 2

    outer = [
        sphere_point(radius, lat_min, lon_min),
        sphere_point(radius, lat_min, lon_max),
        sphere_point(radius, lat_max, lon_max),
        sphere_point(radius, lat_max, lon_min),
    ]
    inner_radius = radius - thickness
    inner = [
        sphere_point(inner_radius, lat_min, lon_min),
        sphere_point(inner_radius, lat_min, lon_max),
        sphere_point(inner_radius, lat_max, lon_max),
        sphere_point(inner_radius, lat_max, lon_min),
    ]

    vertices = outer + inner
    faces = [
        (0, 1, 2, 3),
        (7, 6, 5, 4),
        (0, 4, 5, 1),
        (1, 5, 6, 2),
        (2, 6, 7, 3),
        (3, 7, 4, 0),
    ]

    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(material)
    mesh.update()

    panel = bpy.data.objects.new(name, mesh)
    panel.parent = parent
    panel["echo_role"] = "shell_panel"
    collection.objects.link(panel)

    bevel = panel.modifiers.new("Soft bevel", "BEVEL")
    bevel.width = 0.035
    bevel.segments = 2
    bevel.limit_method = "ANGLE"
    bpy.context.view_layer.objects.active = panel
    panel.select_set(True)
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    panel.select_set(False)
    return panel


def orbit_point(
    semi_major: float,
    semi_minor: float,
    rotation: tuple[float, float, float],
    t: float,
) -> Vector:
    point = Vector(
        (
            semi_major * math.cos(t),
            semi_minor * math.sin(t),
            0.0,
        )
    )
    return Euler(rotation, "XYZ").to_matrix() @ point


def add_orbit(
    *,
    name: str,
    semi_major: float,
    semi_minor: float,
    rotation: tuple[float, float, float],
    material: bpy.types.Material,
    parent: bpy.types.Object,
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    curve_data = bpy.data.curves.new(f"{name}_Curve", type="CURVE")
    curve_data.dimensions = "3D"
    curve_data.resolution_u = 1
    curve_data.bevel_depth = 0.022
    curve_data.bevel_resolution = 3
    curve_data.resolution_u = 12

    spline = curve_data.splines.new("POLY")
    segments = 128
    spline.points.add(segments - 1)
    for index in range(segments):
        point = orbit_point(
            semi_major,
            semi_minor,
            rotation,
            math.tau * index / segments,
        )
        spline.points[index].co = (*point, 1.0)
    spline.use_cyclic_u = True

    orbit = bpy.data.objects.new(name, curve_data)
    orbit.parent = parent
    orbit["echo_role"] = "orbit"
    curve_data.materials.append(material)
    collection.objects.link(orbit)

    bpy.context.view_layer.objects.active = orbit
    orbit.select_set(True)
    bpy.ops.object.convert(target="MESH")
    orbit = bpy.context.object
    orbit.name = name
    orbit.data.name = f"{name}_Mesh"
    orbit.select_set(False)
    return orbit


def add_beveled_box(
    *,
    name: str,
    location: Vector,
    scale: tuple[float, float, float],
    normal: Vector,
    material: bpy.types.Material,
    parent: bpy.types.Object,
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    obj.scale = scale
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = Vector((0.0, 0.0, 1.0)).rotation_difference(
        normal.normalized()
    )
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    bevel = obj.modifiers.new("Detail bevel", "BEVEL")
    bevel.width = 0.03
    bevel.segments = 2
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=bevel.name)

    obj.data.materials.append(material)
    obj.parent = parent
    obj["echo_role"] = "interface_detail"
    move_to_collection(obj, collection)
    return obj


def add_area_light(
    name: str,
    location: tuple[float, float, float],
    energy: float,
    size: float,
    color: tuple[float, float, float],
    target: Vector,
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    light_data = bpy.data.lights.new(name=f"{name}_Data", type="AREA")
    light_data.energy = energy
    light_data.shape = "DISK"
    light_data.size = size
    light_data.color = color
    light = bpy.data.objects.new(name, light_data)
    light.location = location
    light.rotation_euler = (target - light.location).to_track_quat("-Z", "Y").to_euler()
    collection.objects.link(light)
    return light


def add_camera(
    location: tuple[float, float, float],
    target: Vector,
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    camera_data = bpy.data.cameras.new("EchoCore_Camera_Data")
    camera_data.lens = 58
    camera_data.sensor_width = 36
    camera = bpy.data.objects.new("EchoCore_Camera", camera_data)
    camera.location = location
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    collection.objects.link(camera)
    bpy.context.scene.camera = camera
    return camera


def configure_scene() -> None:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 1200
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False

    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.003, 0.005, 0.009, 1.0)
    background.inputs["Strength"].default_value = 0.28

    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass

def build_scene() -> dict[str, object]:
    clean_scene()
    export_collection = make_collection("MODEL_EXPORT")
    preview_collection = make_collection("_PREVIEW")

    shell_material = make_material(
        "M_WhiteModel_Shell",
        (0.32, 0.38, 0.44, 1.0),
        metallic=0.72,
        roughness=0.24,
    )
    shell_detail_material = make_material(
        "M_WhiteModel_Detail",
        (0.68, 0.78, 0.82, 1.0),
        metallic=0.28,
        roughness=0.22,
        emission=(0.18, 0.52, 0.56, 1.0),
        emission_strength=1.1,
    )
    orbit_material = make_material(
        "M_WhiteModel_Orbit",
        (0.11, 0.15, 0.19, 1.0),
        metallic=0.82,
        roughness=0.2,
    )
    energy_material = make_material(
        "M_WhiteModel_Energy",
        (0.28, 0.82, 0.82, 1.0),
        metallic=0.05,
        roughness=0.18,
        emission=(0.08, 0.95, 0.88, 1.0),
        emission_strength=4.0,
    )
    frame_material = make_material(
        "M_WhiteModel_CoreFrame",
        (0.72, 0.84, 0.86, 1.0),
        metallic=0.7,
        roughness=0.18,
        emission=(0.12, 0.42, 0.45, 1.0),
        emission_strength=0.55,
    )

    root = add_empty("Echo_Core_Root", None, export_collection)
    root["asset_name"] = "Echo Core"
    root["asset_version"] = "1.0-white-model"
    core_group = add_empty("GRP_Core", root, export_collection)
    shell_group = add_empty("GRP_Shell", root, export_collection)
    orbit_group = add_empty("GRP_Orbits", root, export_collection)
    node_group = add_empty("GRP_Nodes", root, export_collection)
    detail_group = add_empty("GRP_InterfaceDetails", root, export_collection)

    core_energy = add_ico(
        "Core_Energy",
        0.82,
        3,
        energy_material,
        core_group,
        export_collection,
    )
    core_energy.scale = (1.0, 0.92, 1.08)
    core_energy.rotation_euler = (
        math.radians(8),
        math.radians(-17),
        math.radians(12),
    )
    core_energy["echo_role"] = "energy_core"

    core_frame = add_ico(
        "Core_Frame",
        1.12,
        2,
        frame_material,
        core_group,
        export_collection,
    )
    core_frame.scale = (1.0, 0.92, 1.08)
    core_frame.rotation_euler = (
        math.radians(8),
        math.radians(-17),
        math.radians(12),
    )
    wireframe = core_frame.modifiers.new("Crystalline frame", "WIREFRAME")
    wireframe.thickness = 0.026
    wireframe.use_replace = True
    bpy.context.view_layer.objects.active = core_frame
    core_frame.select_set(True)
    bpy.ops.object.modifier_apply(modifier=wireframe.name)
    core_frame.select_set(False)
    core_frame["echo_role"] = "core_frame"

    bands = (
        (53.0, 4, 2.0, 25.0, 62.0),
        (21.0, 5, 18.0, 26.0, 54.0),
        (-14.0, 5, -18.0, 26.0, 54.0),
        (-47.0, 4, 43.0, 25.0, 62.0),
    )
    panel_count = 0
    for latitude, count, offset, lat_span, lon_span in bands:
        gap_longitude = -45.0 + latitude * 0.52
        longitude_values = [offset + 360.0 * index / count for index in range(count)]
        gap_index = min(
            range(count),
            key=lambda index: abs(
                ((longitude_values[index] - gap_longitude + 180.0) % 360.0) - 180.0
            ),
        )
        for index, longitude in enumerate(longitude_values):
            if index == gap_index:
                continue
            panel_count += 1
            radius = 1.84 + 0.025 * math.sin(math.radians(longitude * 2.0))
            add_shell_panel(
                name=f"Shell_Panel_{panel_count:02d}",
                latitude=latitude,
                longitude=longitude,
                lat_span=lat_span,
                lon_span=lon_span,
                radius=radius,
                thickness=0.13,
                material=shell_material,
                parent=shell_group,
                collection=export_collection,
            )

    orbit_specs = (
        (
            "Orbit_01",
            2.55,
            1.56,
            (math.radians(66), math.radians(3), math.radians(-22)),
        ),
        (
            "Orbit_02",
            2.42,
            1.72,
            (math.radians(12), math.radians(61), math.radians(24)),
        ),
        (
            "Orbit_03",
            2.66,
            1.44,
            (math.radians(-34), math.radians(18), math.radians(77)),
        ),
    )

    for name, semi_major, semi_minor, rotation in orbit_specs:
        add_orbit(
            name=name,
            semi_major=semi_major,
            semi_minor=semi_minor,
            rotation=rotation,
            material=orbit_material,
            parent=orbit_group,
            collection=export_collection,
        )

    node_count = 0
    node_parameters = (
        (0, 0.10),
        (0, 0.68),
        (0, 1.34),
        (0, 1.92),
        (1, 0.28),
        (1, 0.92),
        (1, 1.55),
        (1, 2.15),
        (2, 0.04),
        (2, 0.76),
        (2, 1.44),
        (2, 2.05),
    )
    for orbit_index, cycle in node_parameters:
        _, semi_major, semi_minor, rotation = orbit_specs[orbit_index]
        location = orbit_point(semi_major, semi_minor, rotation, math.tau * cycle)
        node_count += 1
        node = add_ico(
            f"Node_{node_count:02d}",
            0.11 if node_count in {2, 6, 11} else 0.072,
            2,
            shell_detail_material if node_count in {2, 6, 11} else frame_material,
            node_group,
            export_collection,
            location=location,
        )
        node["echo_role"] = "signal_node"

    detail_positions = (
        (27.0, 82.0, (0.24, 0.045, 0.035)),
        (5.0, 128.0, (0.17, 0.035, 0.028)),
        (-31.0, 8.0, (0.22, 0.04, 0.032)),
        (-24.0, 154.0, (0.15, 0.032, 0.026)),
    )
    for index, (latitude, longitude, scale) in enumerate(detail_positions, start=1):
        normal = sphere_point(1.0, latitude, longitude)
        location = sphere_point(1.925, latitude, longitude)
        add_beveled_box(
            name=f"Interface_Tick_{index:02d}",
            location=location,
            scale=scale,
            normal=normal,
            material=shell_detail_material,
            parent=detail_group,
            collection=export_collection,
        )

    floor_material = make_material(
        "M_Preview_Floor",
        (0.012, 0.018, 0.026, 1.0),
        metallic=0.05,
        roughness=0.32,
    )
    bpy.ops.mesh.primitive_plane_add(size=24.0, location=(0.0, 0.0, -2.7))
    floor = bpy.context.object
    floor.name = "_PREVIEW_Floor"
    floor.data.materials.append(floor_material)
    move_to_collection(floor, preview_collection)

    target = Vector((0.0, 0.0, 0.08))
    add_camera((6.8, -6.8, 4.55), target, preview_collection)
    add_area_light(
        "_PREVIEW_Key",
        (4.2, -4.8, 6.8),
        1250,
        4.2,
        (0.74, 0.91, 1.0),
        target,
        preview_collection,
    )
    add_area_light(
        "_PREVIEW_Fill",
        (-4.8, -1.5, 2.3),
        820,
        5.5,
        (0.32, 0.48, 0.68),
        target,
        preview_collection,
    )
    add_area_light(
        "_PREVIEW_Rim",
        (1.8, 5.2, 5.6),
        1550,
        3.2,
        (0.18, 0.95, 0.82),
        target,
        preview_collection,
    )

    configure_scene()

    BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
    GLB_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))

    bpy.ops.object.select_all(action="DESELECT")
    export_objects = list(export_collection.objects)
    for obj in export_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.gltf(
        filepath=str(GLB_PATH),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
    )
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))

    mesh_objects = [
        obj for obj in export_collection.objects if obj.type == "MESH"
    ]
    triangle_count = sum(
        len(obj.data.loop_triangles)
        if obj.data.loop_triangles
        else len(obj.data.polygons) * 2
        for obj in mesh_objects
    )
    return {
        "blend_path": str(BLEND_PATH),
        "glb_path": str(GLB_PATH),
        "panel_count": panel_count,
        "node_count": node_count,
        "export_object_count": len(export_objects),
        "mesh_object_count": len(mesh_objects),
        "estimated_triangle_count": triangle_count,
    }


__result__ = build_scene()
