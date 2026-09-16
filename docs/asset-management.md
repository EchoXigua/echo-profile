# 资产与验收产物管理

## 纳入版本控制

- `public/`：页面实际使用的交付素材，以及此前保留的公共资源。
- `design/3d/*.blend`、`design/animation-model/`：可编辑源文件与分阶段版本；保留 blockout、绑定、refinement 阶段，自动备份 `.blend1` 不提交。
- `design/raw-model/astronaut/`、`design/raw-model/space-station/`：原始 GLB 与配套 emissive 贴图，供重新导出及材质修复使用。
- `design/source-assets/`：可继续编辑或衍生的贴纸源图，不直接部署。
- `scripts/blender/`、`docs/` 与 `output/` 根目录已有的文本报告：生成工具、验收结论、模型统计及未解决问题。

## 仅在本地保留

- `design/3d/previews/`：Clay、线框、材质和动作验收截图。
- `design/qa/`、`design/reference/`：参考截图与设计对照材料。
- `output/` 的子目录：录屏抽帧、浏览器截图、接触表和临时调试产物。
- `design/raw-model/*.zip`：已解压模型的重复压缩包。
- `design/archive/`：当前页面不再使用的中间导出物。本次归档了旧版 `astronaut-greybox.glb` 和 `astronaut-rigged.glb`。

以上本地产物通过 `.gitignore` 忽略；已有跟踪的预览图停止跟踪，仍存在的本地文件保留。新克隆不会包含这些截图，验收报告里的本地截图路径用于说明生成位置，不保证可直接打开。

截图不入库不等于免验收。建模变更仍须按 `AGENTS.md` 生成四角度预览、检查并完成 refinement，提交时保留文字结论和必要统计。环境模型可通过 `scripts/blender/build_lusion_environments.py --project-root`（在 Blender 中运行）重新生成；脚本会重写指定的分阶段环境源文件、预览与 GLB，运行前应保存手工改动。
