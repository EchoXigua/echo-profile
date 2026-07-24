# 回声主页

Echo 的独立个人主页项目，用于求职、工作合作、AI 能力展示与精选个人项目介绍。

## 项目边界

- 本项目只介绍 Echo 本人，不替代 `byecho.cn`。
- 瘦搭与漫游在本项目中作为能力案例展示，完整产品内容链接到 `byecho.cn`。
- 当前阶段不需要数据库、登录、上传或其他持久化能力。

## 技术基础

- Next.js / React / TypeScript
- React Three Fiber / Three.js
- GSAP
- vinext / Cloudflare Workers 兼容构建

## 目录

```text
app/                  页面入口与全局样式
components/layout/    导航与页面框架
components/scene/     3D 场景与滚动叙事
components/sections/  内容区块
content/              个人介绍、能力与项目数据
docs/                 设计与实现约束
lib/                  站点配置
public/               项目图片与简历
tests/                服务端渲染验证
types/                内容类型
```

## 本地开发

```bash
pnpm install
pnpm dev
```

## 验证

```bash
pnpm check
```

## 当前状态

基础架构已建立，并包含一个可运行的 3D 场景占位。最终视觉、滚动动画、项目素材、联系方式、简历和正式域名将在后续阶段完善。
