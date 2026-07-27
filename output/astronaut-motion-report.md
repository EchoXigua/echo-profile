# Astronaut Lusion Motion Report

## Output

- Source (read-only): `/Users/edy/Documents/Echo主页/design/animation-model/astronaut-rigged.glb`
- Source SHA-256: `01fbaf77bdd824b8c7c434a3afb1871469e07a6f321d98f1aae80d05122f369d`
- Stage v01: `/Users/edy/Documents/Echo主页/design/animation-model/astronaut-lusion-motion-v01.blend`
- Stage v02: `/Users/edy/Documents/Echo主页/design/animation-model/astronaut-lusion-motion-v02.blend`
- Web GLB: `/Users/edy/Documents/Echo主页/public/models/astronaut-lusion-animated.glb` (12234004 bytes)
- Review renders: `/Users/edy/Documents/Echo主页/output/astronaut-motion-previews`

## Model and rig

- Armature: `Armature` / 41 bones
- Skinned mesh: `tripo_node_ff97da5c-fc7f-4555-9e7e-ef4ebebe8783`
- Vertices: 18,276
- Triangles: 32,672
- Materials: `tripo_mat_ff97da5c-fc7f-4555-9e7e-ef4ebebe8783`
- Modifier stack: `Armature` (ARMATURE, Preserve Volume: True)
- Excluded from derivative export: `棱角球`
- Topology changes: none
- Source overwrite: no

## Animation actions

30 fps. The scroll action is deterministic and designed to be sampled in both
directions. Pointer and click actions are independent layers.

| Action | Frames | Duration |
| --- | ---: | ---: |
| `EchoScrollStory` | 1–361 | 12.000s |
| `EchoPointerWave` | 1–91 | 3.000s |
| `EchoPointerSweep` | 1–91 | 3.000s |
| `EchoPointerClick` | 1–22 | 0.700s |
| `EchoZeroGIdle` | 1–241 | 8.000s |

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
- Live desktop R3F validation completed: forward scroll, reverse scroll,
  pointer-driven reach/sweep and click recoil all return to deterministic poses.
- Browser console validation completed with no warnings or errors.
- Mobile validation was intentionally not included in this phase.
