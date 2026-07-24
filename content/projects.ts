import type { FeaturedProject } from "@/types/content";

export const projects: FeaturedProject[] = [
  {
    slug: "leanmate",
    name: "瘦搭 LeanMate",
    stage: "V1.2 持续开发",
    tone: "leanmate",
    description:
      "专注减脂场景的饮食与体重记录 App，通过低成本记录、AI 辅助识别和及时反馈，帮助用户形成可持续的记录习惯。",
    tags: ["Kimi 多模态", "SwiftUI", "Spring Boot", "SSE"],
    href: "https://byecho.cn/projects/leanmate",
  },
  {
    slug: "voya",
    name: "漫游 Voya",
    stage: "MVP 联调与质量验证",
    tone: "voya",
    description:
      "面向国内自由行用户的 AI 行程规划产品，把自然语言旅行需求转化为可编辑、可验证、可执行的结构化行程。",
    tags: ["LLM Evaluation", "SwiftUI", "NestJS", "POI & Route"],
    href: "https://byecho.cn/projects/roam",
  },
];
