import type { Capability } from "@/types/content";

export const capabilities: Capability[] = [
  {
    title: "AI 协作研发",
    description: "使用 Codex、Claude、Kimi 完成需求拆解、实现、审查、测试和文档沉淀。",
    tags: ["Codex", "Claude", "Kimi", "Context Engineering"],
  },
  {
    title: "AI 应用工程",
    description: "把大模型能力接入真实产品，处理结构化输出、流式交互、任务状态与失败降级。",
    tags: ["LLM Provider", "Structured Output", "SSE", "Fallback"],
  },
  {
    title: "全栈产品交付",
    description: "从前端体验延伸到跨端客户端、后端接口、数据存储和部署验证。",
    tags: ["React", "SwiftUI", "Spring Boot", "NestJS"],
  },
  {
    title: "质量与可信度",
    description: "通过规则校验、评测集、来源说明和用户确认，让 AI 结果保持可核对、可修改。",
    tags: ["Evaluation", "Testing", "Trust UX", "Guardrails"],
  },
];
