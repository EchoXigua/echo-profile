# Echo Core 3D 模型

Echo Core 是个人主页的主视觉装置，用同一个结构承载前端工程、AI 协作研发和项目案例三条叙事线。它不是机器人、AI 大脑或通用发光球，而是一枚可拆解、可重组的界面核心。

## 文件

- Blender 源文件：`design/3d/echo-core-v1.blend`
- 网页模型：`public/models/echo-core-v1.glb`
- 建模脚本：`scripts/blender/create_echo_core.py`
- 本地生成预览图（Git 不跟踪）：`design/3d/previews/echo-core-v1-hero.png`

## 可动画结构

- `GRP_Core`：中心能量体和晶格框架，表达判断力与产品意识。
- `GRP_Shell`：14 块界面外壳，表达前端体验和工程基础。
- `GRP_Orbits`：三条回声轨道，表达输入、推理和交付闭环。
- `GRP_Nodes`：12 个信号节点，表达模型、工具、数据与多端系统。
- `GRP_InterfaceDetails`：界面刻度细节。

网页只负责滚动状态、部件变换、颜色、发光和轻量粒子；Blender 文件不烘焙整段页面动画。

## 建议的滚动状态

1. Hero：结构聚合，缓慢呼吸，轨道低速差动。
2. About：外壳向对角开口方向展开，露出核心。
3. AI Engineering：轨道和节点建立输入到验证再到交付的路径。
4. LeanMate：核心偏薄荷绿，运动节奏更柔和。
5. Voya：轨道偏蓝，节点形成路线与城市信号。
6. Contact：结构重新聚合，向外释放一次回声波。

## 性能边界

当前网页模型约 1.2 万三角面，桌面和移动端可共用。移动端继续限制像素比；减少动态效果开启时保留完整模型但停止持续旋转和呼吸。
