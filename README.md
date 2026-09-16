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
- Next.js 静态导出 / Nginx 自托管

## 环境要求

- Node.js `>=20.9.0`
- pnpm `10.34.5`

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
corepack enable
pnpm install
pnpm dev
```

## 验证

```bash
pnpm check
```

## 构建与部署

```bash
pnpm build
```

构建结果位于 `out/`，可以直接交给 Nginx、Caddy 或其他静态文件服务器托管。自有服务器部署示例见 [`docs/deployment.md`](docs/deployment.md)。

## 当前状态

六阶段滚动页面已建立：Hero、About、Engineering、LeanMate、Voya、Contact 共用一个 React Three Fiber 场景。宇航员骨骼动作、独立镜头路径、空间站状态和 DOM 文案随滚动同步；场景包含走廊、传送门、碎片与联系区贴纸，并使用自定义 Shader 和 Bloom 等后期效果。当前仍需完成移动端性能与交互验收。

项目使用标准 Next.js 静态导出，不依赖 Cloudflare Workers 或常驻 Node.js 服务。模型历史验收及当前资产说明见 [`docs/model-acceptance-report.md`](docs/model-acceptance-report.md)，源文件与本地产物的管理规则见 [`docs/asset-management.md`](docs/asset-management.md)。
