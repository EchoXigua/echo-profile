"""Export a texture-free greybox GLB while preserving the source geometry."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def main() -> None:
    args = parse_args()
    source = Path(args.input).resolve()
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(source))

    grey = bpy.data.materials.new("Echo_Greybox")
    grey.use_nodes = True
    grey.node_tree.nodes.clear()
    output_node = grey.node_tree.nodes.new("ShaderNodeOutputMaterial")
    principled = grey.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
    principled.inputs["Base Color"].default_value = (0.34, 0.37, 0.4, 1.0)
    principled.inputs["Metallic"].default_value = 0.22
    principled.inputs["Roughness"].default_value = 0.68
    grey.node_tree.links.new(principled.outputs["BSDF"], output_node.inputs["Surface"])

    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        obj.data.materials.clear()
        obj.data.materials.append(grey)
        obj.select_set(True)

    for image in list(bpy.data.images):
        bpy.data.images.remove(image)

    bpy.ops.export_scene.gltf(
        filepath=str(output),
        export_format="GLB",
        export_animations=False,
        export_cameras=False,
        export_lights=False,
        export_apply=True,
        export_yup=True,
    )
    print(f"Exported {output} ({output.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
