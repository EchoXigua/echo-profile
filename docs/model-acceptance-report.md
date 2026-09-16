# 宇航员与空间站 GLB 模型历史验收报告


> 本文下方保存 2026-07-27 灰模与初版绑定阶段的历史记录，不代表当前页面已经通过完整验收。2026-09-16 整理时，已核对当前页面使用 `public/models/astronaut-lusion-animated.glb`，而非下文旧版 `astronaut-rigged.glb`；当前场景也已包含自定义 Shader 和后期效果。旧版宇航员网页导出物归档到本地 `design/archive/models/`，不随网站发布。四视图与动作截图仅本地保留，不随 Git 提交。

当前动画源文件在 `design/animation-model/`，当前走廊与传送门源文件在 `design/3d/lusion-environment-*.blend`。已有动画导出报告见 [`../output/astronaut-lusion-export-report.json`](../output/astronaut-lusion-export-report.json)；环境模型历史统计见 [`model-reports/lusion-environment-v02.json`](model-reports/lusion-environment-v02.json)。这些统计来自已有报告，本次整理没有重新执行 Blender 渲染验收。

验收日期：2026-07-27
检查环境：Blender 5.2.0 LTS / `scripts/blender/inspect_glb.py`
验收范围：`design/raw-model/astronaut/`、`design/raw-model/space-station/` 内的 PBR 与 shaded GLB，以及网页灰模导出物。

## 验收结论

| 模型 | 灰模阶段 | 正式模型阶段 | 结论 |
| --- | --- | --- | --- |
| 宇航员 | 可用于路径、镜头叙事和滚动驱动的骨骼姿态 | 已补齐 20 根骨骼与两条动作；开放边界和全身极限姿态仍需源文件复核 | 当前网页动作验收通过，通用角色资产有条件通过 |
| 空间站 | 可用于整模路径、旋转和构图占位 | 存在 2 个退化面；开放边界和潜在相交需要源文件复核 | 灰模通过，正式验收待修复 |

本次没有改写用户的 PBR/shaded 源 GLB 和已有工作 `.blend`。宇航员在新的分阶段文件 `astronaut_rig_work_v01.blend`、`astronaut_rig_work_v02.blend` 中完成绑定和 refinement；网页正式加载 `astronaut-rigged.glb`，原有灰模文件仍保留。

## 资产清单

| 资产 | 文件大小 | 顶点 | 三角面 | 材质 / 贴图 |
| --- | ---: | ---: | ---: | --- |
| 宇航员 PBR | 11,943,456 B | 18,276 | 32,672 | 1 个材质；Base Color、Metallic/Roughness、Normal，均为 2048² |
| 宇航员 shaded | 5,659,888 B | 18,276 | 32,672 | 1 个材质；1 张 2048² 烘焙贴图 |
| 空间站 PBR | 13,446,316 B | 19,574 | 36,387 | 1 个材质；Base Color、Metallic/Roughness、Normal，均为 2048² |
| 空间站 shaded | 5,508,804 B | 19,574 | 36,387 | 1 个材质；1 张 2048² 烘焙贴图 |
| 宇航员网页灰模 | 782,124 B | 18,276 | 32,672 | 1 个无贴图灰模材质 |
| 宇航员骨骼版 | 5,824,724 B | 18,276 | 32,672 | 1 个 shaded 材质；20 根骨骼；2 条动作 |
| 空间站网页灰模 | 845,956 B | 19,574 | 36,387 | 1 个无贴图灰模材质 |

PBR 与 shaded 版本的几何、包围盒和拓扑统计一致，区别只在材质表达与文件体积。

## 结构与动画

- 两份原始模型均为单 Mesh、单材质、单位缩放，导入后没有残留 Camera、Light 或 Modifier。
- 原始模型没有 Armature、Action、Shape Key；新骨骼版宇航员包含 20 根骨骼，其中 19 根为变形骨骼。
- `EchoScrollStory` 为 0–449 帧，覆盖抬臂、转身、飞行和收束姿态；`EchoPointerWave` 为 0–59 帧，覆盖左臂抬起、上身和头部轻微跟随。
- 网页使用滚动归一化进度直接采样 `EchoScrollStory`，因此向下和向上滚动都能按同一动作轨道正放/倒放；Contact 阶段只采样 `EchoPointerWave` 的上半身骨骼，避免无关腿部权重影响站立轮廓。
- 空间站也是整模结构，不能独立驱动舱段或端点。
- GLB 原点位于模型底部；宇航员高度约 1.8984，空间站高度约 1.9000。网页已通过父级 Group 做居中和缩放，不修改资产本身。

## 拓扑检查

| 检查项 | 宇航员 | 空间站 |
| --- | ---: | ---: |
| 边界边 | 3,764 | 2,719 |
| 多于两面共边 | 0 | 0 |
| 退化面 | 0 | 2 |

解释：

- 没有检测到多于两面共边，未发现典型的非流形分叉。
- 两个模型都有较多开放边界。结合四视图，外轮廓连续、可正常着色，但自动检查无法证明内部没有壳体相交或重叠表面。
- 空间站的 2 个退化面不会阻塞本轮灰模，但应在正式导出前定位并清理。
- 宇航员虽然是单 Mesh，但当前结果不足以证明所有可见有机曲面都满足“连续拓扑、无重叠 primitive assembly”的正式标准；需要在源 `.blend` 中继续做内部穿插和壳体检查。
- 骨骼版保留原始三角化拓扑，通过手工空间分区权重和 Armature `Preserve Volume` 完成当前动作。肩肘变形满足本页镜头距离；髋膝不建议直接扩展到大幅步态或深蹲。

## 材质与贴图

- PBR GLB 的基础材质通道完整，四视图中白色宇航服、黑色关节、深色空间站和小型发光细节均能正常辨认。
- 压缩包中的 `texture_emissive.png` 没有被两份 GLB 内部材质引用。若正式版需要发光舷窗或界面灯，需要在源材质中明确连接并重新导出。
- shaded 版体积更小，但烘焙结果不适合后续独立调节金属度、粗糙度和法线。
- 空间站网页灰模继续使用标准 `MeshStandardMaterial`；宇航员骨骼版保留 shaded 贴图。当前场景没有引入复杂自定义 Shader。

## 四视图证据

每个模型都生成了材质、Clay 和 Wireframe 三组四视图（front、three-quarter、side、back）：

- 宇航员：`design/3d/previews/model-acceptance/astronaut/`
- 空间站：`design/3d/previews/model-acceptance/space-station/`

代表性预览：

- 宇航员材质：`material_three-quarter.png`
- 宇航员线框：`wireframe_three-quarter.png`
- 空间站材质：`material_three-quarter.png`
- 空间站线框：`wireframe_three-quarter.png`
- 宇航员骨骼 refinement：`design/3d/previews/astronaut-rig-v02/`

视觉检查结果：

- 宇航员正面、侧面、背面和三分之四视角轮廓完整，背包、头盔、手部与足部没有出现明显缺面。
- 宇航员布线密度较均匀，但全身三角化，不利于后续骨骼变形；若要做关节动画，需要重新拓扑或至少分区权重验证。
- 骨骼版已输出 material / clay / wireframe 的 front、three-quarter、side、back 四视图，并在第一版绑定后开启 Preserve Volume 完成一次 refinement pass。
- 空间站的 C 形主体、端点与内外壁在四视图中可辨认，侧视厚度存在，没有退化成平面。
- 线框显示空间站整体密度偏高且细节分布较均匀；灰模阶段可接受，移动端正式版仍建议评估 LOD。

## 网页导出验证

网页灰模文件：

- `public/models/astronaut-greybox.glb`
- `public/models/astronaut-rigged.glb`
- `public/models/space-station-greybox.glb`

导出后重新导入 Blender 检查：

- 宇航员仍为 18,276 顶点 / 32,672 三角面。
- 骨骼版 GLB 的 glTF mesh table 仍为 1 个渲染 Mesh；回读后可恢复 20 根骨骼以及 `EchoScrollStory`、`EchoPointerWave` 两条 Action。
- 空间站仍为 19,574 顶点 / 36,387 三角面。
- 包围盒、原点、对象数量和拓扑风险与源 shaded GLB 一致。
- 两个灰模文件均无贴图、无动画、无相机、无灯光；骨骼版保留 1 张 shaded 贴图和两条动画，不包含相机、灯光或控制器。

网页导出相当于本轮的交付优化 refinement pass；它解决了灰模首屏体积和材质复杂度问题，但没有修改源模型拓扑，因此不能替代正式模型的几何修复。

## 正式模型关闭条件

1. 在 `space_station_work_v01.blend` 中定位并移除 2 个退化面。
2. 在两个工作 `.blend` 中检查开放边界、内部壳体相交和可见表面穿插。
3. 若将宇航员用于本页之外的大幅全身动作，继续优化髋膝、肩肘权重，必要时为关节区域重拓扑；当前两条网页动作不受此项阻塞。
4. 将 emissive 贴图真正接入材质，或从交付包移除未使用文件。
5. 后续移动端工作启动时再评估 LOD；本轮按用户要求只验收桌面端。
6. 修复后重新输出 material / clay / wireframe 四视图，并完成一次基于预览的几何 refinement pass。
