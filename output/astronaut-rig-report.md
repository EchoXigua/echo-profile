# Astronaut Rig Inspection Report

生成日期：2026-07-27T10:35:54+08:00

源文件：`/Users/edy/Documents/Echo主页/design/animation-model/astronaut-rigged.glb`

检查工具：Blender 5.2.0 LTS / Blender Python API

检查方式：只读导入到临时场景；未覆盖源 GLB、未删除动画、未修改拓扑。

## 结论摘要

- Armature：`Armature`，共 41 根骨骼。
- 主宇航员由 1 个蒙皮 Mesh 构成；另外发现辅助/非蒙皮 Mesh：`棱角球`。
- 主宇航员尺寸：`[0.31519, 0.43026, 0.99613]`；完整导入场景尺寸：`[1.90212, 2.0, 2.00415]`。
- 主宇航员面数：32,672 faces / 32,672 triangles。
- 完整 GLB 面数：32,752 faces / 32,752 triangles。
- 已有 Action：`NlaTrack`。
- 网页准备风险：源文件包含额外的非蒙皮 Mesh 时，应在正式网页导出副本中明确排除；本次没有删除该对象。
- `Root` 与 `Hip` 的骨骼尾端明显伸出人体轮廓；两者分别影响 0 / 0 个顶点，应结合动作变形继续确认是否需要保留为 deform bone。

## 环境与前端技术栈

- Blender：5.2.0 LTS。
- 项目：Next.js 16.2.6、React 19.2.6、TypeScript 5.9.3。
- 3D：React Three Fiber 9.4.0、Three.js 0.180.0。
- 滚动动画：GSAP 3.13.0 / ScrollTrigger。
- 现有入口：`components/scene/EchoScene.tsx` 使用 `GLTFLoader`、`SkeletonUtils.clone`、`AnimationMixer`，并以滚动进度采样动画。

## 场景、尺寸、坐标与原点

- 场景单位：`METRIC`，长度单位：`METERS`，scale_length：1.0。
- 帧率：24/1.0 = 24 fps。
- Scene 帧范围：1–250。
- 主宇航员 Bounds：min `[-0.14656, -0.22079, 0.00801]`，max `[0.16863, 0.20947, 1.00415]`。
- 完整 GLB Bounds：min `[-0.95106, -1.0, -1.0]`，max `[0.95106, 1.0, 1.00415]`。
- 朝向判断：Blender 导入后为 Z-up。根据左右肢体主要沿 Y 轴展开、头盔面罩朝 +X，判断角色面向 +X；正面相机位于 +X，侧面相机位于 -Y，背面相机位于 -X。GLB 导入对象旋转均记录在下表，未在检查过程中应用变换。

| Mesh Object | 蒙皮 | 顶点 | 三角面 | 尺寸 XYZ | 世界原点 | 材质 |
| --- | --- | ---: | ---: | --- | --- | --- |
| `tripo_node_ff97da5c-fc7f-4555-9e7e-ef4ebebe8783` | 是 | 18,276 | 32,672 | `[0.31519, 0.43026, 0.99613]` | `[0.0, 0.0, 0.0]` | `tripo_mat_ff97da5c-fc7f-4555-9e7e-ef4ebebe8783` |
| `棱角球` | 否 | 42 | 80 | `[1.90212, 2.0, 2.0]` | `[0.0, 0.0, 0.0]` | `无` |

## Armature 与骨骼层级

Armature Object：`Armature`

Armature Location：`[0.0, 0.0, 0.0]`

Armature Rotation (radians)：`[0.0, 0.0, 0.0]`

Armature Scale：`[1.0, 1.0, 1.0]`

- `Root` — parent: `None`, deform: `True`, weighted vertices: `0`, head: `[0.01203, 0.01111, 0.0]`, tail: `[-0.53899, 0.01111, 0.0]`
  - `Hip` — parent: `Root`, deform: `True`, weighted vertices: `0`, head: `[0.01203, 0.01111, 0.55102]`, tail: `[-0.37681, -0.01063, 0.94084]`
    - `Pelvis` — parent: `Hip`, deform: `True`, weighted vertices: `0`, head: `[0.01203, 0.01111, 0.55102]`, tail: `[0.0015, 0.00749, 0.6159]`
      - `L_Thigh` — parent: `Pelvis`, deform: `True`, weighted vertices: `0`, head: `[0.0099, 0.07676, 0.54624]`, tail: `[0.05328, 0.10101, 0.30135]`
        - `L_Calf` — parent: `L_Thigh`, deform: `True`, weighted vertices: `0`, head: `[0.05324, 0.10101, 0.30134]`, tail: `[0.05702, 0.13008, 0.05668]`
          - `L_CalfTwist01` — parent: `L_Calf`, deform: `True`, weighted vertices: `1014`, head: `[0.05324, 0.10099, 0.30149]`, tail: `[0.05482, 0.11313, 0.1994]`
            - `L_CalfTwist02` — parent: `L_CalfTwist01`, deform: `True`, weighted vertices: `1283`, head: `[0.05482, 0.11313, 0.1994]`, tail: `[0.05639, 0.12526, 0.09732]`
          - `L_Foot` — parent: `L_Calf`, deform: `True`, weighted vertices: `848`, head: `[0.05705, 0.13009, 0.05669]`, tail: `[0.0879, 0.13347, 0.05328]`
            - `L_ToeBase` — parent: `L_Foot`, deform: `True`, weighted vertices: `685`, head: `[0.0879, 0.13347, 0.05328]`, tail: `[0.11875, 0.13685, 0.04987]`
        - `L_ThighTwist01` — parent: `L_Thigh`, deform: `True`, weighted vertices: `2546`, head: `[0.00988, 0.07674, 0.54636]`, tail: `[0.03157, 0.08887, 0.42391]`
          - `L_ThighTwist02` — parent: `L_ThighTwist01`, deform: `True`, weighted vertices: `1468`, head: `[0.03157, 0.08887, 0.42391]`, tail: `[0.05326, 0.10099, 0.30146]`
      - `R_Thigh` — parent: `Pelvis`, deform: `True`, weighted vertices: `0`, head: `[0.01424, -0.05454, 0.5553]`, tail: `[0.05959, -0.08083, 0.30134]`
        - `R_Calf` — parent: `R_Thigh`, deform: `True`, weighted vertices: `0`, head: `[0.05955, -0.08081, 0.30133]`, tail: `[0.05907, -0.0868, 0.04308]`
          - `R_CalfTwist01` — parent: `R_Calf`, deform: `True`, weighted vertices: `999`, head: `[0.05955, -0.08081, 0.30148]`, tail: `[0.05935, -0.08331, 0.19373]`
            - `R_CalfTwist02` — parent: `R_CalfTwist01`, deform: `True`, weighted vertices: `1289`, head: `[0.05935, -0.08331, 0.19373]`, tail: `[0.05915, -0.08581, 0.08597]`
          - `R_Foot` — parent: `R_Calf`, deform: `True`, weighted vertices: `737`, head: `[0.0591, -0.0868, 0.04308]`, tail: `[0.0866, -0.08439, 0.03763]`
            - `R_ToeBase` — parent: `R_Foot`, deform: `True`, weighted vertices: `735`, head: `[0.0866, -0.08439, 0.03763]`, tail: `[0.11411, -0.08197, 0.03218]`
        - `R_ThighTwist01` — parent: `R_Thigh`, deform: `True`, weighted vertices: `3168`, head: `[0.01422, -0.05453, 0.55543]`, tail: `[0.03689, -0.06767, 0.42844]`
          - `R_ThighTwist02` — parent: `R_ThighTwist01`, deform: `True`, weighted vertices: `1561`, head: `[0.03689, -0.06767, 0.42844]`, tail: `[0.05957, -0.08082, 0.30146]`
    - `Waist` — parent: `Hip`, deform: `True`, weighted vertices: `3359`, head: `[0.01202, 0.0111, 0.55107]`, tail: `[0.00377, 0.00827, 0.60192]`
      - `Spine01` — parent: `Waist`, deform: `True`, weighted vertices: `4872`, head: `[0.00377, 0.00827, 0.60192]`, tail: `[-0.01271, 0.0026, 0.70349]`
        - `Spine02` — parent: `Spine01`, deform: `True`, weighted vertices: `4758`, head: `[-0.01271, 0.0026, 0.70349]`, tail: `[-0.02712, -0.00235, 0.79232]`
          - `L_Clavicle` — parent: `Spine02`, deform: `True`, weighted vertices: `2431`, head: `[-0.02712, 0.01765, 0.79229]`, tail: `[-0.03668, 0.09695, 0.80954]`
            - `L_Upperarm` — parent: `L_Clavicle`, deform: `True`, weighted vertices: `0`, head: `[-0.03669, 0.09698, 0.80938]`, tail: `[-0.04891, 0.16769, 0.6688]`
              - `L_Forearm` — parent: `L_Upperarm`, deform: `True`, weighted vertices: `0`, head: `[-0.04885, 0.1677, 0.6688]`, tail: `[0.00237, 0.24335, 0.53513]`
                - `L_ForearmTwist01` — parent: `L_Forearm`, deform: `True`, weighted vertices: `508`, head: `[-0.04887, 0.16766, 0.66887]`, tail: `[-0.02324, 0.20552, 0.60197]`
                  - `L_ForearmTwist02` — parent: `L_ForearmTwist01`, deform: `True`, weighted vertices: `733`, head: `[-0.02324, 0.20552, 0.60197]`, tail: `[0.00239, 0.24338, 0.53508]`
                - `L_Hand` — parent: `L_Forearm`, deform: `True`, weighted vertices: `1080`, head: `[0.00237, 0.24334, 0.53512]`, tail: `[0.01621, 0.26899, 0.37586]`
              - `L_UpperarmTwist01` — parent: `L_Upperarm`, deform: `True`, weighted vertices: `1756`, head: `[-0.03668, 0.09694, 0.80945]`, tail: `[-0.04279, 0.1323, 0.73916]`
                - `L_UpperarmTwist02` — parent: `L_UpperarmTwist01`, deform: `True`, weighted vertices: `721`, head: `[-0.04279, 0.1323, 0.73916]`, tail: `[-0.04891, 0.16766, 0.66886]`
          - `NeckTwist01` — parent: `Spine02`, deform: `True`, weighted vertices: `407`, head: `[-0.02712, -0.00235, 0.79232]`, tail: `[-0.03154, -0.00387, 0.81955]`
            - `NeckTwist02` — parent: `NeckTwist01`, deform: `True`, weighted vertices: `1649`, head: `[-0.03154, -0.00387, 0.81955]`, tail: `[-0.03391, -0.00468, 0.83413]`
              - `Head` — parent: `NeckTwist02`, deform: `True`, weighted vertices: `2945`, head: `[-0.03391, -0.00468, 0.83413]`, tail: `[-0.03628, -0.00549, 0.84871]`
          - `R_Clavicle` — parent: `Spine02`, deform: `True`, weighted vertices: `3072`, head: `[-0.02712, -0.02235, 0.79229]`, tail: `[-0.02168, -0.10308, 0.80046]`
            - `R_Upperarm` — parent: `R_Clavicle`, deform: `True`, weighted vertices: `0`, head: `[-0.02169, -0.10309, 0.8003]`, tail: `[-0.02327, -0.17675, 0.64841]`
              - `R_Forearm` — parent: `R_Upperarm`, deform: `True`, weighted vertices: `0`, head: `[-0.02322, -0.17676, 0.64841]`, tail: `[0.0217, -0.23632, 0.53513]`
                - `R_ForearmTwist01` — parent: `R_Forearm`, deform: `True`, weighted vertices: `477`, head: `[-0.02324, -0.17673, 0.64847]`, tail: `[-0.00077, -0.20653, 0.59178]`
                  - `R_ForearmTwist02` — parent: `R_ForearmTwist01`, deform: `True`, weighted vertices: `622`, head: `[-0.00077, -0.20653, 0.59178]`, tail: `[0.02171, -0.23634, 0.53509]`
                - `R_Hand` — parent: `R_Forearm`, deform: `True`, weighted vertices: `1151`, head: `[0.0217, -0.23631, 0.53512]`, tail: `[0.05552, -0.24906, 0.40438]`
              - `R_UpperarmTwist01` — parent: `R_Upperarm`, deform: `True`, weighted vertices: `2448`, head: `[-0.02169, -0.10306, 0.80038]`, tail: `[-0.02248, -0.13989, 0.72441]`
                - `R_UpperarmTwist02` — parent: `R_UpperarmTwist01`, deform: `True`, weighted vertices: `741`, head: `[-0.02248, -0.13989, 0.72441]`, tail: `[-0.02327, -0.17673, 0.64845]`

## 主要骨骼识别

映射不是按 Mixamo 名称硬编码；结果综合使用名称语义、层级、局部坐标与左右侧标记。证据不足的项目会保留未识别。

| 目标角色 | 识别骨骼 | 置信度 | 证据 |
| --- | --- | --- | --- |
| Root | `Root` | high | 名称语义得分 10.0；空间位置得分 1.5；左右侧验证得分 0.0；父骨骼 None，层级深度 0；局部 head [0.01203, 0.01111, 0.0]，tail [-0.53899, 0.01111, 0.0] |
| Hips | `Pelvis` | high | 名称语义得分 10.0；空间位置得分 2.0；左右侧验证得分 0.0；父骨骼 Hip，层级深度 2；局部 head [0.01203, 0.01111, 0.55102]，tail [0.0015, 0.00749, 0.6159] |
| Spine | `Spine01` | high | 名称语义得分 10.0；空间位置得分 2.0；左右侧验证得分 0.0；父骨骼 Waist，层级深度 3；局部 head [0.00377, 0.00827, 0.60192]，tail [-0.01271, 0.0026, 0.70349] |
| Chest | `Spine02` | high | 名称语义得分 10.0；空间位置得分 2.0；左右侧验证得分 0.0；父骨骼 Spine01，层级深度 4；局部 head [-0.01271, 0.0026, 0.70349]，tail [-0.02712, -0.00235, 0.79232] |
| Neck | `NeckTwist01` | high | 名称语义得分 7.0；空间位置得分 2.0；左右侧验证得分 0.0；父骨骼 Spine02，层级深度 5；局部 head [-0.02712, -0.00235, 0.79232]，tail [-0.03154, -0.00387, 0.81955] |
| Head | `Head` | high | 名称语义得分 10.0；空间位置得分 2.0；左右侧验证得分 0.0；父骨骼 NeckTwist02，层级深度 7；局部 head [-0.03391, -0.00468, 0.83413]，tail [-0.03628, -0.00549, 0.84871] |
| LeftUpperArm | `L_Upperarm` | high | 名称语义得分 10.0；空间位置得分 2.0；左右侧验证得分 2.0；父骨骼 L_Clavicle，层级深度 6；局部 head [-0.03669, 0.09698, 0.80938]，tail [-0.04891, 0.16769, 0.6688] |
| RightUpperArm | `R_Upperarm` | high | 名称语义得分 10.0；空间位置得分 2.0；左右侧验证得分 2.0；父骨骼 R_Clavicle，层级深度 6；局部 head [-0.02169, -0.10309, 0.8003]，tail [-0.02327, -0.17675, 0.64841] |
| LeftForeArm | `L_Forearm` | high | 名称语义得分 10.0；空间位置得分 2.0；左右侧验证得分 2.0；父骨骼 L_Upperarm，层级深度 7；局部 head [-0.04885, 0.1677, 0.6688]，tail [0.00237, 0.24335, 0.53513] |
| RightForeArm | `R_Forearm` | high | 名称语义得分 10.0；空间位置得分 2.0；左右侧验证得分 2.0；父骨骼 R_Upperarm，层级深度 7；局部 head [-0.02322, -0.17676, 0.64841]，tail [0.0217, -0.23632, 0.53513] |
| LeftHand | `L_Hand` | high | 名称语义得分 10.0；空间位置得分 1.0；左右侧验证得分 2.0；父骨骼 L_Forearm，层级深度 8；局部 head [0.00237, 0.24334, 0.53512]，tail [0.01621, 0.26899, 0.37586] |
| RightHand | `R_Hand` | high | 名称语义得分 10.0；空间位置得分 1.0；左右侧验证得分 2.0；父骨骼 R_Forearm，层级深度 8；局部 head [0.0217, -0.23631, 0.53512]，tail [0.05552, -0.24906, 0.40438] |
| LeftUpperLeg | `L_Thigh` | high | 名称语义得分 10.0；空间位置得分 2.8；左右侧验证得分 2.0；父骨骼 Pelvis，层级深度 3；局部 head [0.0099, 0.07676, 0.54624]，tail [0.05328, 0.10101, 0.30135] |
| RightUpperLeg | `R_Thigh` | high | 名称语义得分 10.0；空间位置得分 2.8；左右侧验证得分 2.0；父骨骼 Pelvis，层级深度 3；局部 head [0.01424, -0.05454, 0.5553]，tail [0.05959, -0.08083, 0.30134] |
| LeftLowerLeg | `L_Calf` | high | 名称语义得分 10.0；空间位置得分 2.8；左右侧验证得分 2.0；父骨骼 L_Thigh，层级深度 4；局部 head [0.05324, 0.10101, 0.30134]，tail [0.05702, 0.13008, 0.05668] |
| RightLowerLeg | `R_Calf` | high | 名称语义得分 10.0；空间位置得分 2.8；左右侧验证得分 2.0；父骨骼 R_Thigh，层级深度 4；局部 head [0.05955, -0.08081, 0.30133]，tail [0.05907, -0.0868, 0.04308] |
| LeftFoot | `L_Foot` | high | 名称语义得分 10.0；空间位置得分 2.8；左右侧验证得分 2.0；父骨骼 L_Calf，层级深度 5；局部 head [0.05705, 0.13009, 0.05669]，tail [0.0879, 0.13347, 0.05328] |
| RightFoot | `R_Foot` | high | 名称语义得分 10.0；空间位置得分 2.8；左右侧验证得分 2.0；父骨骼 R_Calf，层级深度 5；局部 head [0.0591, -0.0868, 0.04308]，tail [0.0866, -0.08439, 0.03763] |

完整机器可读映射见：`/Users/edy/Documents/Echo主页/output/astronaut-bone-map.json`。

## 材质与贴图

- `tripo_mat_ff97da5c-fc7f-4555-9e7e-ef4ebebe8783`：渲染模式 `DITHERED`；贴图：`astronaut-rigged_glb_basecolor` 2048×2048 (sRGB, 内嵌)；`astronaut-rigged_glb_rm` 2048×2048 (Non-Color, 内嵌)；`astronaut-rigged_glb_normal` 2048×2048 (Non-Color, 内嵌)

## Animation Actions

| Action | 帧范围 | 时长帧数 | 时长秒数 | Slots |
| --- | ---: | ---: | ---: | ---: |
| `NlaTrack` | 1.0–62.0 | 61.0 | 2.5417 s | 1 |

NLA 数据：

```json
[
  {
    "track": "NlaTrack",
    "mute": true,
    "strips": [
      {
        "name": "NlaTrack",
        "action": "NlaTrack",
        "frame_start": 1.0,
        "frame_end": 62.0
      }
    ]
  }
]
```

注意：当前 Action 的视觉语义需要结合逐帧预览确认。检查报告只记录源文件中的真实名称和时间范围，不把测试动作重命名为最终动作。
用户已说明当前 Action 是“害怕”测试动作，后续最终动作清单不应复用该语义。

## 骨骼检查图

- 正面：`/Users/edy/Documents/Echo主页/output/preview/rig-front.png`
- 侧面：`/Users/edy/Documents/Echo主页/output/preview/rig-side.png`
- 背面：`/Users/edy/Documents/Echo主页/output/preview/rig-back.png`

橙色为 Left 命名骨骼，粉色为 Right 命名骨骼，绿色为中轴或未带左右标记的骨骼。预览使用 Rest Pose；源动画未被删除或修改。

## Three.js / React Three Fiber 准备建议

1. 保留源 GLB 作为只读母版，在新的网页导出副本中处理额外非蒙皮 Mesh、动作命名和压缩。
2. 确认是否需要独立 Root。若骨架只有 Hips 顶层骨骼，网页根运动应由外层 Group 承担，避免把路径位移烘焙进 Hips。
3. 将测试用 Action 与最终动作分开命名；后续建议至少输出 `ZeroG_Idle`、`Fly`、`Turn`、`Reach`、`Wave` 等独立 Action。
4. GLB 导出后必须重新导入检查：骨骼数量、Action 名称、帧范围、贴图、辅助 Mesh 和 bind pose。
5. 当前模型无 Shape Key 时，肩、髋等极限姿态的穿模只能依赖权重、硬质件单骨骼绑定或后续 corrective 方案解决。
