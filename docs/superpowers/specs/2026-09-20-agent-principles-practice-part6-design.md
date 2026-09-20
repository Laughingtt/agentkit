# Spec: Agent原理及实践 — Part 6 工业落地

**Date:** 2026-09-20
**Status:** Draft (pending user review)
**Project:** `agentkit` (Chinese technical book on Agent principles and practice)
**Scope:** Part 6 of 6

---

## 1. 项目背景与分解策略

本书《Agent原理及实践》面向**有编程基础但无 AI/ML 背景的初学者**，以中文 Markdown 写成。整体拆为 6 个 Part，每个 Part 独立走 `brainstorm → spec → plan → 写作` 流程：

| Part | 主题 | 状态 |
|---|---|---|
| 1 | 大模型基础 | 已发布 |
| 2 | 大模型与 Agent 的演进 | 进行中 |
| 3 | Agent 原理 | 进行中 |
| 4 | Harness 工程 | 进行中 |
| 5 | Agent 功能实现 | 进行中 |
| 6 | 工业落地 ← **本 spec** | Draft |

本 spec 只覆盖 **Part 6**，聚焦"在生产环境里把 Agent 跑起来并跑好"。

### Part 6 必须覆盖（CLAUDE.md 规定）

> 部署、**LLM-native 可观测性（Langfuse / Helicone / Arize Phoenix / OpenLLMetry）**、evaluation（LLM-as-judge、生产环境评测）、security/红队、**模型路由器（Martian / Not Diamond）**、cost control、speculative decoding、EU AI Act 合规、AIUC-1、真实案例

---

## 2. 目标读者与约束

- **读者：** 大学本科以上、会写代码（至少一门主流语言）、但**没有** AI/ML 背景
- **核心假设：** 读者已经读完 Part 1-5，对 LLM、Agent、Harness、MCP/A2A 协议有基本概念
- **数学策略：** 直觉优先；cost / latency / 安全相关数据用表格呈现，不堆公式
- **代码：** 少量示意代码 inline；完整示例放 `code/part-6/`（Langfuse 接入、LLM-as-judge、简单 router）
- **语言：** 中文（简体）；技术术语首次出现用 `中文名（English term）` 格式
- **总字数：** 25-30k 字（6 章，每章 ~4-5k）
- **风格：** 教程式、朋友式；面向"想把 Agent 真正上线"的工程师

---

## 3. 文件结构

```
agentkit/
├── part-6-工业落地/
│   ├── README.md               # Part 6 目录与简介
│   ├── ch28-llm-native可观测性.md
│   ├── ch29-evaluation.md
│   ├── ch30-security与红队.md
│   ├── ch31-模型路由器与成本控制.md
│   ├── ch32-合规与标准.md
│   └── ch33-真实案例与小结.md
└── code/
    └── part-6/
        ├── README.md           # 依赖说明（Langfuse ≥ 3.x, OpenTelemetry SDK）
        ├── langfuse_trace.py   # Ch28 示例：单次 LLM 调用的 trace
        ├── eval_pipeline.py    # Ch29 示例：LLM-as-judge 评测
        ├── router_demo.py      # Ch31 示例：基于规则的 router
        └── redteam_basic.py    # Ch30 示例：Promptfoo 接入
```

---

## 4. Part 6 六章内容大纲

### Ch28 LLM-native 可观测性（~4-5k 字）

读完应能在 Agent 上接入 tracing 并回答"这次请求为什么慢、为什么贵"。

- 28.1 可观测性是什么：日志 / 指标 / 追踪（Logs / Metrics / Traces）
- 28.2 为什么 LLM 应用需要"专门"的可观测性：非确定性 + 多步嵌套 + 成本可见性
- 28.3 OpenTelemetry 与 GenAI 语义约定（`gen_ai.*` attributes）
- 28.4 四大主流平台速览（Langfuse / Helicone / Arize Phoenix / OpenLLMetry）
- 28.5 一次 LLM 调用的 trace 长什么样：root span → generation → tool span
- 28.6 用 Langfuse 接入一个最简单的 trace（代码示例）
- 28.7 自托管 vs SaaS：合规、成本、规模的取舍
- 28.8 从 trace 到 dashboard：成本归因、延迟分位、错误率

**Anchor 示例：**
- Mermaid `sequenceDiagram`：一次 Agent 请求的完整 span 嵌套
- 表格：四大平台对比（开源协议 / 自托管 / 嵌套 trace / eval）
- 代码：`code/part-6/langfuse_trace.py`（使用 Langfuse Python SDK + OTel）

---

### Ch29 Evaluation：让 Agent 的好坏可被衡量（~4-5k 字）

读完应能搭建一条 LLM-as-judge 评测流水线，并在生产环境里持续监控质量。

- 29.1 为什么不能只看"用户没投诉"：质量信号的滞后性
- 29.2 三种评测范式：pointwise / pairwise / reference-based
- 29.3 LLM-as-judge 的直觉：用 LLM 当裁判
- 29.4 四大偏置与对策：position / verbosity / self-preference / agreeableness
- 29.5 主流指标体系：RAGAS（faithfulness / answer relevance / context precision）与 DeepEval
- 29.6 一个最小 LLM-as-judge 评测流水线（代码示例）
- 29.7 离线评测 vs 在线评测：guardrail、A/B、shadow traffic
- 29.8 评测的版本化：rubric 升级 = 评分体系迁移

**Anchor 示例：**
- Mermaid `flowchart`：评测流水线（dataset → candidate → judge → score → dashboard）
- 表格：四种偏置及对策
- 代码：`code/part-6/eval_pipeline.py`（GPT judge Claude 的 cross-family 评测）

---

### Ch30 Security 与红队（~4-5k 字）

读完应能在 Agent 上线前做过一轮结构化红队测试，知道常见攻击类别与防御手段。

- 30.1 为什么 Agent 的攻击面更大：tool calling + 长上下文 + 多步推理
- 30.2 OWASP LLM Top 10 与常见攻击类别：prompt injection / jailbreak / data leakage / over-agency
- 30.3 直接注入 vs 间接注入（从文档/网页注入）
- 30.4 红队工具速览：Promptfoo / PyRIT / Garak 三大框架的取舍
- 30.5 自动化红队的最小可执行流程（代码示例：Promptfoo CLI）
- 30.6 防御层：输入清洗 / 输出过滤 / 工具白名单 / 权限沙箱
- 30.7 持续红队：CI/CD 接入与回归基线
- 30.8 红队不是一次性的：组织、节奏、与产品迭代的耦合

**Anchor 示例：**
- Mermaid `sequenceDiagram`：间接 prompt injection 攻击链
- 表格：OWASP LLM Top 10（2025 版）攻击类别与典型缓解
- 代码：`code/part-6/redteam_basic.py`（Promptfoo config + 一组对抗用例）

---

### Ch31 模型路由器与成本控制（~4-5k 字）

读完应能解释 router 的工作原理，并能在自己的系统里做一版"基于规则的轻量路由"。

- 31.1 为什么需要 router：一个 prompt 不应该都打到最贵的模型
- 31.2 router 的三类策略：规则 / 嵌入相似度 / 元模型（meta-model）
- 31.3 主流 router 速览：Not Diamond / Martian / OpenRouter / 厂商自带 fallback
- 31.4 一个最小 router 设计：难度分级 + 路由表
- 31.5 成本优化的四层缓存：exact / semantic / prompt cache / KV cache
- 31.6 Speculative decoding：直觉、原理、与典型加速比
- 31.7 Continuous batching 与 chunked prefill
- 31.8 一个最小 router 代码示例

**Anchor 示例：**
- Mermaid `flowchart`：router 决策流（query → classify → route → model A/B/C）
- 表格：四类 router 策略对比
- 表格：四层缓存命中率与成本节省区间
- 代码：`code/part-6/router_demo.py`（基于关键词 + 长度的规则 router）

---

### Ch32 合规与标准（~4-5k 字）

读完应能描述 EU AI Act 与 AIUC-1 的核心条款，知道"合规"对工程团队的实质要求。

- 32.1 为什么 Agent 的合规比传统软件复杂：决策不可解释 + 责任主体模糊
- 32.2 EU AI Act 风险分级：unacceptable / high / limited / minimal
- 32.3 GPAI 模型条款：技术文档、训练数据摘要、版权合规
- 32.4 系统性风险阈值（10^25 FLOPs）与额外义务
- 32.5 AIUC-1：第一个专门为 Agent 设计的合规标准
- 32.6 AIUC-1 vs SOC 2 / ISO 42001 / EU AI Act：互补而非替代
- 32.7 一份工程师能用的合规 Checklist（按角色）
- 32.8 合规驱动的工程实践：可追溯日志、prompt 版本化、决策留痕

**Anchor 示例：**
- Mermaid `flowchart`：EU AI Act 风险分级决策树
- 表格：四类风险等级对应的工程义务
- 表格：AIUC-1 / SOC 2 / ISO 42001 / EU AI Act 横向对比

---

### Ch33 真实案例与小结（~4-5k 字）

读完应能讲清楚"别人是怎么踩坑的"，并把 Part 6 的全部要点串成一张行动清单。

- 33.1 案例一：客服 Agent（Klarna：从 700 FTE 到 hybrid 模式的回滚教训）
- 33.2 案例二：代码 Agent（参考 Claude Code / Codex CLI 的 telemetry 实践）
- 33.3 案例三：RAG Agent（一家中型企业的 RAG 召回率优化 + 可观测性接入）
- 33.4 三个案例的共性：可观测先行、灰度发布、保留人类兜底
- 33.5 Part 6 小结 + 全书小结
- 33.6 上线一份 Agent 的 30 天清单
- 33.7 未来 12-24 个月值得关注的方向

**Anchor 示例：**
- 表格：三个案例的指标对比（处理量 / 节省 / 翻车点）
- Mermaid `graph LR`：从 Part 1 到 Part 6 的全书知识地图
- 表格：30 天上线清单（按周划分任务）

---

## 5. 写作约定（简版，详见 CLAUDE.md）

- 每章模板：标题 → 一句话简介 → 本章目标（3-5 条 bullet）→ 本章导览（mermaid 总览图）→ 子节 → 本章小结 → 本章参考
- Mermaid 仅用四种图：`graph` / `flowchart` / `sequenceDiagram` / `mindmap`
- 复杂对比一律用表格，不堆 mermaid
- 引用：随文 markdown 链接 + 章末 "本章参考"（分必读论文 / 推荐博客 / 视频课程 三类）
- 代码：中文注释；可运行示例文件头加 `# runnable: yes`
- 跨章引用 `参见 X.3`；跨 Part `(见 Part N ChM)`，**不**复制内容
- **本 Part 特别强调：** 每章至少 1 个 mermaid + 1 个对比表；Ch28、Ch29、Ch31 的代码示例必须可运行

---

## 6. 完成度与验收标准

### 单章完成标准

- 子节齐全，与大纲一致（6-8 个子节）
- 含本章目标、小结、本章参考
- 含至少 1 个 mermaid + 1 个对比表
- 字数在 ±20% 区间内（每章 4-5k）
- 关键概念全覆盖（每章 5-8 个）
- Ch28 / Ch29 / Ch31 至少 1 个可运行代码示例（`# runnable: yes`）
- Ch30 至少 1 个 Promptfoo/Garak/PyRIT 的接入示意

### Part 6 整体验收

- 6 章全部写完（Ch28-Ch33）
- 总字数 25-30k
- `part-6-工业落地/README.md` 含目录与一句话简介
- `README.md` 出现 Part 6，标记为 "已发布"
- 所有 mermaid 在 GitHub 渲染无语法错误
- 所有 Python 代码片段对应文件存在于 `code/part-6/`
- 自查通过（事实核查 / 链接有效性 / 内部一致性 / 范围 / 风格）
- 写后审查：所有 URL 用 WebFetch 抽样验证；所有 Python 代码统一运行；字数统计

### 自查清单

1. **事实核查：** 引用 Langfuse、Helicone、Phoenix、Not Diamond、EU AI Act、Klarna 等的具体数据必须可验证
2. **链接有效性：** 所有 URL 可访问（WebFetch 抽样）
3. **内部一致性：** 6 章之间不矛盾；与 Part 1-5 不重叠
4. **范围检查：** 不重复 Part 1-5 的内容（Part 1 讲原理、Part 4 讲 harness、Part 5 讲功能实现）
5. **风格检查：** 符合 CLAUDE.md 一·甲 的"初学者可懂性原则"——每个新概念 ≤ 3 个 / 段；公式极少
6. **避免产品教程化：** 不写"Langfuse 怎么用" / "Promptfoo 命令行手册"——只讲通用要素

---

## 7. 显式 Out-of-Scope（Part 6 不涉及）

- Agent 架构原理（认知架构、ReAct、Plan-and-Execute 等）→ Part 3
- Harness 上下文工程、hooks、permissions 设计 → Part 4
- MCP / A2A 协议细节、协议实现 → Part 4-5
- 模型训练、SFT/RLHF 流程 → Part 1
- LLM 家族演进史 → Part 2
- 模型权重选择、A/B 选型的具体评分体系（产品横评）→ Part 6 仅讲方法论
- 自训练 reward model / RLHF on policy → Part 1 / Part 5
- 单个工具的"完整教程"（本书不写 Langfuse 用户手册）
- 数学严格证明

---

## 8. 关键技术决策点

### 决策 1：四大可观测性平台的取舍

**问题：** Langfuse、Helicone、Phoenix、OpenLLMetry 各自定位不同，全讲会变成工具横评。

**决策：**
- **OpenTelemetry / GenAI 语义约定**作为统一底层（标准概念）—— **详讲**
- **Langfuse** 作为"开源 + 自托管 + 嵌套 trace"的代表 —— **重点示例 + 代码**
- **Helicone / Phoenix / OpenLLMetry** 作为对比表呈现 —— **速览**
- 理由：Langfuse 2026 已是最广泛采用的开源 OTel-native 平台（22k+ stars，65M+ SDK installs/month）；其余三家功能有重叠但定位不同，用表格对比即可

### 决策 2：Evaluation 章节不写"Braintrust / LangSmith 接入"

**问题：** 评测平台很多，写全会变成产品横评。

**决策：** 只讲**通用方法论**（三种评测范式 + LLM-as-judge + 四大偏置 + RAGAS 指标），代码示例用通用 OpenAI/Anthropic API 写。Langfuse/Braintrust/LangSmith 在 Part 6 仅作"工具承载"提及，不做教程。

### 决策 3：Security 章节的"红队工具"取舍

**问题：** Promptfoo / PyRIT / Garak / DeepTeam / FuzzyAI 都有定位差异。

**决策：** 三大主流（Promptfoo / PyRIT / Garak）讲定位差异，代码示例用 **Promptfoo**（CLI 上手最快、CI/CD 友好、OWASP 映射直接）。

### 决策 4：Router 章节"自写 vs 用 Not Diamond"

**问题：** Not Diamond / Martian 是 SaaS，自写 router 才是"通用要素"。

**决策：**
- Not Diamond / Martian 作为**外部产品示例**讲清元模型的工作原理（直觉 + 一张 mermaid）
- 代码示例写一个**基于规则的最小 router**（关键词 + 长度）——体现"读者能自己设计 router"而非"读者必须买 SaaS"

### 决策 5：合规章节要不要讲 GDPR / HIPAA

**问题：** GDPR / HIPAA / SOC 2 / ISO 27001 都是常见合规要求。

**决策：**
- **EU AI Act** —— 详讲（CLAUDE.md 强制要求）
- **AIUC-1** —— 详讲（CLAUDE.md 强制要求）
- **SOC 2 / ISO 42001 / ISO 27001 / GDPR** —— 在对比表中点名 + Part 6 Ch32 末尾给一行参考链接
- 不深入展开的理由：CLAUDE.md 已规定本书聚焦"Agent 特异性"问题，传统合规标准应让位给专业资料

---

## 9. 写作流程与依赖

1. 本 spec 经用户审阅通过后，进入 `superpowers:writing-plans` 流程
2. writing-plans 输出 Part 6 的实现 plan（按 Ch28 → Ch33 顺序）
3. 实际写作时严格遵循 CLAUDE.md 一·甲 的初学者可懂性原则
4. 写后审查在 Task 6 整合与终审中统一执行（URL WebFetch 抽样 + 代码运行 + 字数 + 一致性）

### Part 6 内部依赖顺序

```
Ch28 可观测性 ─→ Ch29 Evaluation ─→ Ch30 Security ─→ Ch31 Router/Cost ─→ Ch32 合规 ─→ Ch33 案例
       │              │                  │                  │                 │           │
       └──────────────┴──────────────────┴──────────────────┴─────────────────┴───────────┘
                                            ↓
                                    全书小结 + 30 天清单
```

- Ch28 是"地基"（没有 trace 就没有 eval / 就没有红队基线 / 就没有 cost 归因）
- Ch29 依赖 Ch28（评测数据通常落在 Langfuse/Phoenix）
- Ch30 与 Ch31 可并行（但代码示例建议 Ch30 先做——依赖最小）
- Ch32 是"横切"——与每章都有关联，但放在靠后章节用"汇总视角"讲
- Ch33 收尾：把前 5 章的通用要素在三个真实案例中复现一次

---

## 10. 研究资料来源（联网调研清单，2026-09-20）

### 可观测性
- [Langfuse Documentation](https://langfuse.com) — OpenTelemetry Backed LLM Observability
- [Langfuse OpenTelemetry Integration](https://langfuse.com/docs/opentelemetry/example-opentelemetry-collector) — OTel collector 配置
- [Helicone 2026 Review](https://aisotools.com/blog/helicone-review-2026) — Proxy 模式 + Mintlify 收购后的维护模式状态
- [Arize Phoenix GitHub](https://github.com/arize-ai/phoenix) — OpenInference 标准 + Phoenix 平台
- [OpenTelemetry GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/) — `gen_ai.*` 属性标准
- [OpenTelemetry GenAI Agent Spans](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/) — Agent span 属性定义

### Evaluation
- [LLM-as-Judge 2026 — DeepEval Blog](https://deepeval.com/blog/llm-as-a-judge) — Pairwise / 四类偏置 / 校准协议
- [LLM-as-Judge Agent Evaluation 2026](https://agentmarketcap.ai/blog/2026/04/11/llm-as-judge-agent-output-evaluation-2026) — Agent 场景的 LLM-as-judge 实践
- [RAGAS GitHub](https://github.com/explodinggradients/ragas) — Faithfulness / Answer Relevance / Context Precision
- [DeepEval GitHub](https://github.com/confident-ai/deepeval) — 评测框架
- [RAGAS vs DeepEval Comparison](https://www.confident-ai.com/blog/ragas-vs-deepeval) — 框架对比

### Security / Red Team
- [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/) — LLM01-LLM10
- [Microsoft AI Red Team Top 10 Risks for 2026](https://www.darkreading.com/cybersecurity-operations/microsoft-ai-red-team-lays-out-top-10-risks-for-2026) — Microsoft 视角
- [Promptfoo vs PyRIT vs Garak Comparison](https://www.promptfoo.dev/blog/top-5-open-source-ai-red-teaming-tools-2025/) — 三大红队框架对比
- [The Complete LLM Red Teaming Guide 2025](https://www.penligent.ai/the-complete-llm-red-teaming-guide-best-practices-in-2025/) — 红队方法论

### Router / Cost Control
- [Not Diamond](https://www.notdiamond.ai/) — Meta-model 路由
- [Martian LLM Router](https://martian.ai/llm-router) — 实时性能路由
- [Batching and Caching Strategies for LLM Inference](https://mljourney.com/batching-and-caching-strategies-for-high-throughput-llm-inference/) — 缓存 + 批处理策略
- [Speculative Decoding 综述](https://mljourney.com/batching-and-caching-strategies-for-high-throughput-llm-inference/) — EAGLE-3 / Medusa / Lookahead

### 合规与标准
- [EU AI Act Timeline](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai) — 2025-08 GPAI Code of Practice 发布
- [AIUC-1 Standard](https://www.aiucstandard.com/) — AI Agent 合规标准
- [AIUC-1 2026 Roadmap](https://www.aiucstandard.com/blog/aiuc-1-2026-roadmap) — 2026 合规路径
- [AIUC-1 vs SOC 2 vs ISO 42001 vs EU AI Act](https://www.aiucstandard.com/blog/aiuc-1-vs-other-standards) — 标准横向对比

### 真实案例
- [Klarna AI Assistant Case Study](https://www.klarna.com/international/press/klarna-ai-assistant-handles-two-thirds-of-customer-service-chats-in-its-first-month/) — 原始公关稿
- [Why Klarna Walked Back Its AI-Only Strategy](https://blog.doshby.com/?p=485/) — 2025-05 回滚事件
- [Klarna AI 30 Days Breakdown](https://twig.so/blog/ai-powered-dispute-resolution-klarna) — 复盘分析

---

## 11. 字数与时间估算

| 章节 | 章节名 | 字数估算 | 重点难度 |
|---|---|---|---|
| Ch28 | LLM-native 可观测性 | 4.5k | 中（OTel 概念首次出现） |
| Ch29 | Evaluation | 4.5k | 中（LLM-as-judge 偏置部分需细致） |
| Ch30 | Security 与红队 | 4.5k | 中高（OWASP 10 条需简练） |
| Ch31 | 模型路由器与成本控制 | 4.5k | 中（router + speculative decoding 概念多） |
| Ch32 | 合规与标准 | 4.0k | 中（条款多但应避免变成法条翻译） |
| Ch33 | 真实案例与小结 | 4.5k | 低（综合回顾） |
| **合计** | — | **~26.5k** | — |

### 时间估算

- 单章写作（含代码示例 + mermaid）：1.5-2 小时
- 6 章合计写作：~10-12 小时
- 写后审查（Task 6）：2-3 小时
- **总计：~15 小时**

---

## 12. 后续流程

1. 本 spec 经用户审阅通过后，进入 `superpowers:writing-plans` 流程
2. writing-plans 输出 Part 6 的实现 plan（按章拆分 task）
3. plan 完成后进入实际写作阶段
4. Part 6 是全书最后一 Part；完成后启动"全书整合与终审"
