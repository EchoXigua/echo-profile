# 回声主页 — AI 协作规范

## 项目定位

这是 Echo 的独立个人主页，用于求职、工作合作、AI 能力展示与精选个人作品介绍。

- 不把页面写成团队、公司、工作室或平台介绍。
- 不修改或替代 `byecho.cn`；完整项目详情通过外链跳转。
- 所有能力描述必须能由真实项目、实现或验证过程支撑。
- 不使用虚构用户数量、客户评价、效率百分比或无法核实的成果。

## 内容主线

核心定位为 `Frontend Engineer / AI Full-Stack Builder`。

页面叙事围绕：

1. 前端体验与工程基础。
2. 向 AI 应用全栈方向的发展。
3. Codex、Claude、Kimi 等 AI 协作研发方式。
4. 瘦搭 LeanMate 与漫游 Voya 两个真实项目案例。
5. 求职与工作合作入口。

## 技术原则

- 使用 Next.js、React、TypeScript。
- 3D 使用 React Three Fiber / Three.js，滚动叙事使用 GSAP。
- 页面核心内容必须保留在可访问的 DOM 中，不能只存在于 Canvas。
- 桌面端提供完整 3D 体验，移动端降低几何复杂度和像素比。
- 尊重 `prefers-reduced-motion`，减少动画时仍能完整阅读内容。
- 当前不引入数据库、鉴权、上传或不必要的服务端状态。

## 目录约定

- `components/scene/`：3D 场景、动画状态、性能降级。
- `components/sections/`：页面内容区块。
- `content/`：个人介绍、能力、项目与导航数据。
- `public/projects/`：经过授权的项目展示素材。
- `public/resume/`：公开简历文件。
- `docs/`：设计决策、内容边界和验收说明。

## 验证

- 完成页面改动后至少运行 `pnpm build`。
- 结构或内容变更后运行 `pnpm test`。
- 交互和动画改动需要检查键盘、触摸、移动端和减少动态效果。
