"""Print selected armature bone positions at the start and end of a GLB action."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--action", required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def rounded(values) -> list[float]:
    return [round(float(value), 5) for value in values]


def main() -> None:
    args = parse_args()
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(Path(args.model).resolve()))

    rig = next(obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE")
    action = bpy.data.actions.get(args.action)
    if action is None:
        raise RuntimeError(f"Action not found: {args.action}")

    rig.animation_data_create()
    rig.animation_data.action = action
    frame_start, frame_end = [int(value) for value in action.frame_range]
    report: dict[str, object] = {
        "action": action.name,
        "frame_range": [frame_start, frame_end],
        "frames": {},
    }
    for frame in (frame_start, frame_end):
        bpy.context.scene.frame_set(frame)
        bones = {}
        for name in (
            "clavicle.L",
            "upper_arm.L",
            "forearm.L",
            "hand.L",
            "clavicle.R",
            "upper_arm.R",
            "forearm.R",
            "hand.R",
        ):
            pose_bone = rig.pose.bones[name]
            bones[name] = {
                "head": rounded(pose_bone.head),
                "tail": rounded(pose_bone.tail),
                "rotation_quaternion": rounded(pose_bone.rotation_quaternion),
            }
        report["frames"][str(frame)] = bones

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
