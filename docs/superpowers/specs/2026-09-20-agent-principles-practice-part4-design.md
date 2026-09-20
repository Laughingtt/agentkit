# Spec: Agent原理及实践 — Part 4 Harness 工程

**Date:** 2026-09-20
**Status:** Draft (pending user review)
**Project:** `agentkit` (Chinese technical book on Agent principles and practice)
**Scope:** Part 4 of 6

---

## 1. 项目背景与 Part 4 定位

本书《Agent原理及实践》面向**有编程基础但无 AI/ML 背景的初学者**，以中文 Markdown 写成。整体拆为 6 个 Part，每个 Part 独立走 `brainstorm → spec → plan → 写作` 流程：

| Part | 主题 | 状态 |
|---|---|---|
| 1 | 大模型基础 | 已交付 |
| 2 | 大模型与 Agent 的演进 | spec 待写 |
| 3 | Agent 原理 | spec 待写 |
| 4 | **Harness 工程** | **本 spec** |
| 5 | Agent 功能实现 | spec 待写 |
| 6 | 工业落地 | spec 待写 |

本 spec 只覆盖 **Part 4**。其余 Part 在各自 spec 中设计。

### 1.1 Part 4 在全书的承接关系

- **前置依赖：** Part 3 已讲过"认知架构（perception/memory/planning/action）"、"ReAct/Reflexion/Plan-and-Execute"等范式——Part 4 默认读者已经知道"Agent 在循环里挑工具、调 LLM、产出动作"这件事。
- **本 Part 解决的问题：** 那些在生产环境真正能"跑起来"的 Agent，外面都包了一层叫什么？为什么 2025-2026 主流 Agent 产品（Claude Code、Pi、Codex CLI）的"壳"长得都很像？
- **本 Part 不涉及：** 工具的具体实现细节（→ Part 5）、生产化部署与监控（→ Part 6）、Agent 范式原理（→ Part 3 已讲）。

---

## 2. 目标读者与约束

- **读者：** 大学本科以上、会写代码（至少一门主流语言）、已读完 Part 1-3
- **本 Part 关键约束：** 是工程篇，**代码示例比 Part 1 多**——MCP server、A2A client、hooks 注册都各配一个最小可运行示例
- **语言：** 中文（简体）；技术术语首次出现用 `中文名（English term）` 格式
- **总字数：** 30-35k 字（6 章）
- **风格：** 教程式、朋友式；"读者"、"我们"；段落 3-6 句
- **可懂性：** 严格遵循 CLAUDE.md 一·甲节——每个新概念都要走"直觉 → 类比 → 视觉 → 公式"四步

### 2.1 写作策略：以主流产品为素材，提炼通用要素（CLAUDE.md 第一节）

- **观察对象：** Claude Code（Anthropic）、Pi Coding Agent（earendil-works）、OpenAI Codex CLI，以及 Goose、Aider、Antigravity、Sourcegraph Amp 等
- **提取模式：** 从中识别**反复出现的设计决策**——不是某个产品独有的特性
- **抽象要素：** 把模式抽象成框架无关、模型无关、产品无关的通用概念
- **避免的写法：**
  - 不写 "Claude Code 命令手册" / "Pi 的 SKILL.md 怎么写" 这类产品文档
  - 不引用某个产品的私有命名（Skill、Lazy Skills、Harness、AgentSession 等产品术语）——统一用通用术语
  - 不假设读者只用某一个工具

---

## 3. 文件结构

```
agentkit/
├── part-4-harness工程/
│   ├── README.md               # Part 4 目录与简介
│   ├── ch16-harness导览.md
│   ├── ch17-mcp协议.md
│   ├── ch18-a2a协议.md
│   ├── ch19-上下文工程与记忆.md
│   ├── ch20-hooks-permissions-sandbox.md
│   └── ch21-小结与衔接.md
└── code/
    └── part-4/
        ├── README.md           # 依赖说明（mcp[cli]、a2a-sdk、httpx、PyYAML）
        ├── mcp_server_min.py   # Ch17 最小 MCP server 示例
        ├── mcp_client_min.py   # Ch17 最小 MCP client 示例
        ├── a2a_server_min.py   # Ch18 最小 A2A server 示例
        ├── a2a_client_min.py   # Ch18 最小 A2A client 示例
        ├── hooks_register.py   # Ch20 通用 hooks 注册示例
        ├── permission_policy.py # Ch20 权限策略示例
        └── compaction_demo.py  # Ch19 上下文压缩示意
```

---

## 4. Part 4 六章内容大纲

### Ch16 Harness 导览（~4-5k 字）

读完应能用一段话说清"为什么主流 Agent 产品都长这样"——即 Agent 核心循环 + harness 外壳的分工。

**子节：**

- 16.1 一个朴素的问题：裸 LLM 为什么不能当 Agent 用
- 16.2 什么是 harness：套在 Agent 循环外面的"工程外壳"
- 16.3 主流 coding agent CLI 的横切：Claude Code / Pi / Codex CLI 有什么共同点
- 16.4 Harness 的七大职责（**本章锚点**）：
  1. 工具与权限（tools & permissions）
  2. 执行隔离（isolation / sandbox）
  3. 上下文与记忆（context & memory）
  4. 协议接入（protocol adapters：MCP / A2A / x402）
  5. 生命周期事件（hooks）
  6. 会话与状态（session / state / recordings）
  7. 投递接口（delivery：TUI / CLI / RPC / SDK）
- 16.5 一段话总结：Agent = LLM × harness
- 16.6 全章导览（mermaid 总览图）
- 16.7 Part 4 阅读路线

**Anchor 示例：**

- Mermaid `graph TD`：Agent 核心循环（perception → think → action → observation）外圈包裹 harness 七大职责的层级图
- Mermaid `sequenceDiagram`：用户 → TUI → harness → LLM → tool → 沙箱 → 回到 harness → TUI
- 表格：三个产品（Claude Code / Pi / Codex CLI）的"职责→实现"对照表——只列通用要素，不写产品私有命令

---

### Ch17 MCP 协议（~6-7k 字）

读完应能独立写一个 MCP server，并理解 MCP 在 Harness 中的位置。

**子节：**

- 17.1 为什么需要 MCP：工具调用的标准化困境
- 17.2 MCP 的架构：Host / Client / Server 三角色
- 17.3 四大原语之一：Resource（应用控制、数据提供）
- 17.4 四大原语之二：Tool（模型控制、可执行函数）
- 17.5 四大原语之三：Prompt（用户控制、可复用模板）
- 17.6 四大原语之四：Sampling + Elicitation（客户端能力、2026 新增）
- 17.7 JSON-RPC 2.0 消息结构与一次 `tools/call` 往返
- 17.8 Transport：stdio / Streamable HTTP（替代 SSE）
- 17.9 一个最小可运行的 MCP server（FastMCP 装饰器风格）
- 17.10 一个最小可运行的 MCP client
- 17.11 MCP 在 Harness 里的位置：协议适配器

**Anchor 示例：**

- Mermaid `sequenceDiagram`：host → client → server 之间 `initialize / tools/list / tools/call` 的完整握手（这是全章最核心的图）
- 表格：四大原语对比（控制方 / 类比 / 方法 / 何时调用）
- 表格：stdio vs Streamable HTTP（适用场景 / 优劣 / 典型部署）
- 代码：`code/part-4/mcp_server_min.py`（10 行：3 个工具 + stdio 启动）
- 代码：`code/part-4/mcp_client_min.py`（列出工具 + 调用一次）

---

### Ch18 A2A 协议（~5-6k 字）

读完应能理解"agent 调另一个 agent"和"agent 调一个工具"的本质差异，并能写一个最小 A2A server。

**子节：**

- 18.1 为什么需要 A2A：多 agent 协作的标准化
- 18.2 A2A 与 MCP 的关系：一句话原则（MCP inside，A2A between）
- 18.3 Agent Card：能力自描述（`/.well-known/agent.json`）
- 18.4 Task 生命周期八态：submitted → working → {input-required, auth-required} → {completed, failed, canceled, rejected}
- 18.5 Message / Part / Artifact 三层数据结构
- 18.6 三种交互机制：polling / SSE streaming / push notifications
- 18.7 认证：OAuth 2.0 / JWT / mTLS / API key（v1.0 新增的 JWS 签名）
- 18.8 一个最小可运行的 A2A server（FastAPI 风格）
- 18.9 一个最小可运行的 A2A client（拉取 Agent Card → 发任务 → 收结果）
- 18.10 A2A 在 Harness 里的位置：peer-to-peer 协议

**Anchor 示例：**

- Mermaid `stateDiagram-v2`：Task 生命周期八态的状态机（这是全章最核心的图）
- Mermaid `sequenceDiagram`：A2A client → A2A server：发现 Agent Card → sendMessage → SSE 流式回 artifact
- 表格：A2A vs MCP 维度对比（层 / 对称性 / 记忆共享 / 典型场景）
- 代码：`code/part-4/a2a_server_min.py`（30 行：AgentCard + Executor + FastAPI 启动）
- 代码：`code/part-4/a2a_client_min.py`（15 行：A2AClient 拉卡片 + 调一次）

---

### Ch19 上下文工程与记忆（~6-7k 字）

读完应能解释"上下文工程"是什么、能说出几种常见压缩策略、能区分"上下文管理"和"记忆系统"。

**子节：**

- 19.1 一个朴素的问题：为什么"上下文窗口变大"还不够
- 19.2 上下文工程（context engineering）的定义（Anthropic 2025.09）
- 19.3 注意力预算（attention budget）的直觉
- 19.4 系统提示的"恰到好处区"：不要太死板、不要太模糊
- 19.5 上下文压缩（compaction）的四种策略：
  - 滑动窗口（sliding window）
  - 摘要压缩（summarization）
  - 检查点（checkpoint / branch_summary）
  - 子 agent 隔离（subagent fresh context）
- 19.6 记忆的三层模型：工作记忆 / 会话记忆 / 长期记忆
- 19.7 会话状态的设计：线性日志 vs JSONL 树（带 parentId / fork）
- 19.8 跨模型上下文移交：把 Anthropic 私有字段、Cohere、Google 的差异屏蔽掉
- 19.9 上下文工程的常见反模式
- 19.10 一个上下文压缩示意代码（**非可运行，仅展示策略骨架**）

**Anchor 示例：**

- Mermaid `graph LR`：四种压缩策略的对比（输入 → 策略 → 输出）
- 表格：四层记忆的对比（生命周期 / 存储 / 谁来写 / 谁来读）
- ASCII 图：会话树的结构（id / parentId / branch_summary / checkpoint）
- 代码：`code/part-4/compaction_demo.py`（示意：`def compact(messages, budget)` 伪实现，3-4 个策略分支）

---

### Ch20 Hooks / Permissions / Sandbox（~6-7k 字）

读完应能解释 harness 是怎么"管住"Agent 的——即 prompt 是软约束、harness 是硬约束。

**子节：**

- 20.1 一个朴素的问题：模型说了不等于做了——为什么需要 hook
- 20.2 三层防御模型：
  - **Layer 1 权限闸门**（permission gate）：deny-by-default + allow/ask/deny 三档
  - **Layer 2 沙箱**（sandbox）：OS 级原语（Seatbelt / Landlock / seccomp）优于容器
  - **Layer 3 hooks**：在生命周期事件点上跑确定性的脚本
- 20.3 Hooks：pre-tool / post-tool / pre-edit / post-edit / session-start / session-end
- 20.4 Hook 的输入输出协议：stdin JSON + exit code（0 / 2 / 其他）
- 20.5 Permissions 策略：规则文件语法（allow / deny / ask + 通配符）
- 20.6 命令解析：为什么 AST 优于字符串匹配（防 `git status && curl evil.sh`）
- 20.7 Sandbox 的三档：read-only / workspace-write / full-access（跨产品通用命名）
- 20.8 网络隔离：默认 deny、per-operation 授权
- 20.9 子 agent 隔离：fresh-context reviewer / maker-checker 模式
- 20.10 一个 hooks 注册的最小代码
- 20.11 一个权限策略的最小代码

**Anchor 示例：**

- Mermaid `graph TD`：三层防御模型（permission gate → sandbox → hooks）
- 表格：三层防御的对比（作用层 / 时机 / 谁来配 / 失效成本）
- Mermaid `sequenceDiagram`：bash 命令经过 AST 解析 → 权限策略匹配 → sandbox 执行 → hook 收尾
- 代码：`code/part-4/hooks_register.py`（10-15 行：装饰器风格注册 pre-tool / post-tool 回调）
- 代码：`code/part-4/permission_policy.py`（15 行：YAML/JSON 规则 + 三档判定函数）

---

### Ch21 小结与衔接（~3-4k 字）

读完应对 Part 4 有一个 30 秒回顾，并对接 Part 5 形成清晰期待。

**子节：**

- 21.1 全 Part 回顾：harness 是什么、解决什么、不解决什么
- 21.2 三大协议在 harness 中的角色再回顾：MCP / A2A / x402
- 21.3 跨产品的通用决策清单（10 条）：deny-by-default / OS 沙箱优于容器 / hook 是确定性的 / 提示是软约束 / 子 agent 隔离 / 命令 AST / 工具宁少毋滥 / 会话可恢复 / 上下文压缩是策略不是机械 / 网络默认 deny
- 21.4 常见误用与失败模式
- 21.5 衔接 Part 5：接下来讲怎么"实现"——Harness 给的 API 怎么变成一个能跑的 Agent
- 21.6 Part 4 本章参考

**Anchor 示例：**

- 表格：通用决策清单（决策 / 理由 / 反模式）
- 一段结尾式总结（200-300 字），把 harness 的工程价值浓缩成一句话

---

## 5. 写作约定（简版，详见 CLAUDE.md）

- 每章模板：标题 → 一句话简介 → 本章目标（3-5 条 bullet）→ 本章导览（mermaid 总览图）→ 子节 → 本章小结 → 本章参考
- Mermaid 仅用四种图：`graph` / `flowchart` / `sequenceDiagram` / `mindmap` / `stateDiagram-v2`（仅 Ch18 用一次）
- 复杂关系用表格，不堆 mermaid
- 引用：随文 markdown 链接 + 章末"本章参考"（分必读论文 / 推荐博客 / 视频课程 三类）
- 代码：中文注释；可运行示例文件头加 `# runnable: yes`
- 跨章引用 `参见 X.3`；跨 Part `(见 Part N ChM)`，**不**复制内容
- **本 Part 特别约定：**
  - 所有 API 示例代码必须配一段"运行这条代码会发生什么"的直觉叙述
  - 不出现产品私有命令名（如 `claude `、`pi `、`codex ` 后面跟的特定子命令）作为正文展开对象——只作为"在某个产品里是这样实现的"一句话提及

---

## 6. 完成度与验收标准

### 单章完成标准

- 子节齐全，与大纲一致
- 含本章目标、小结、本章参考
- 含至少 1 个 mermaid + 1 个表格
- 字数在 ±20% 区间内
- 关键概念全覆盖（每章 5-8 个）
- Ch17/Ch18/Ch20 必须有可运行代码示例（其他章示意性即可）

### Part 4 整体验收

- 6 章全部写完
- 总字数 30-35k
- `part-4-harness工程/README.md` 含目录与一句话简介
- `README.md` 出现 Part 4，标记为 "已发布"
- 所有 mermaid 在 GitHub 渲染无语法错误
- 所有 Python 代码片段对应文件存在于 `code/part-4/` 且至少关键文件可运行（`mcp_server_min.py`、`a2a_server_min.py`、`hooks_register.py`）
- 自查通过：placeholder / 内部一致性 / 范围 / 歧义 / **不出现产品私有术语**

### 自查清单

1. **Placeholder 扫描：** 无 TBD / TODO / 占位文本
2. **内部一致性：** 章间不矛盾（术语、概念、数据一致）；跨章引用都存在
3. **范围检查：** 不混入 Part 1-3 内容（不重新讲 transformer、不重复讲 ReAct 范式），不混入 Part 5（tool calling 内部实现）、不混入 Part 6（部署/监控）
4. **歧义检查：** 每个子节要求无歧义
5. **产品术语检查：** 全文搜索 `Skill / Lazy Skills / AgentSession / Harness / Hook / Permission / Sandbox` 等词，确认它们只作为通用概念使用，不绑定到任何具体产品的私有实现细节

---

## 7. 显式 Out-of-Scope（Part 4 不涉及）

- LLM 基础（Transformer / attention / 预训练）→ Part 1 已讲
- Agent 范式（ReAct / Reflexion / Plan-and-Execute）→ Part 3 已讲
- LLM 家族演进史 → Part 2
- 工具的具体实现（tool calling 协议底层、JSON schema 校验、RAG 实现）→ Part 5
- 工业级部署、监控、可观测性、评测 → Part 6
- 商业 / 商业模式分析
- 产品对比横评（"X 比 Y 好在哪"）
- 任何产品的私有命令手册（"如何用 Claude Code 做 X"）

---

## 8. 与其他 Part 的衔接清单

| 衔接点 | Part 4 引用 | Part N 内容 |
|---|---|---|
| 为什么 harness 是必要的 | 16.1 | Part 3 Ch9（认知架构） |
| MCP 是怎么进入 Agent 循环的 | 17.11 | Part 5 Ch23（tool calling） |
| A2A 任务的并发模式 | 18.4 | Part 5 Ch26（多 Agent 协作） |
| 上下文压缩的具体实现 | 19.5 | Part 5 Ch24（记忆） |
| sandbox 的 OS 原语 | 20.7 | Part 6 Ch28（安全/红队） |
| 协议栈全景图 | 21.2 | Part 5 Ch22（协议接入） |

---

## 9. 后续流程

1. 本 spec 经用户审阅通过后，进入 `superpowers:writing-plans` 流程
2. writing-plans 输出 Part 4 的实现 plan
3. plan 完成后进入实际写作阶段
4. Part 4 完成后再启动 Part 5 的 brainstorm

---

## 附录 A：研究资料来源

### A.1 MCP 协议

- [MCP 规范（2026-07-28 版）](https://modelcontextprotocol.io/specification/2026-07-28/) — 最新版，标记了 Sampling / Logging 的废弃状态
- [MCP 架构总览](https://modelcontextprotocol.io/docs/learn) — Host / Client / Server 三角色权威解释
- [MCP Transport 规范](https://modelcontextprotocol.io/docs/concepts/transports) — Streamable HTTP 替代 SSE 的官方说明
- [Spring AI - MCP Streamable HTTP Support](https://spring.io/blog/2025/05/01/spring-ai-mcp-streamable-http-support/) — Streamable HTTP 实战分析
- [LangChain - Migrating to Streamable HTTP](https://docs.langchain.com/mcp/streamable-http-migration) — 迁移指南
- [Stainless - Implementing MCP Streamable HTTP in Python](https://www.stainless.com/blog/implementing-mcp-streamable-http-servers-in-python) — Python 实现细节

### A.2 MCP SDK

- [FastMCP Quickstart](https://fastmcp.wiki/en/v2/getting-started/quickstart) — 高层 API 入口
- [FastMCP 2026 实战指南](https://www.danilchenko.dev/posts/fastmcp-mcp-server) — 当前版本 v4.0.3
- [dev.to - Build Your First MCP Server in 15 Minutes](https://dev.to/gentic_news/build-your-first-mcp-server-in-15-minutes-with-pythons-fastmcp-1g17) — 入门示例
- [juejin - MCP 自定义服务器开发入门指南](https://juejin.cn/post/7682986422115926059) — 中文 FastMCP 教程

### A.3 A2A 协议

- [A2A 协议官网](https://a2a-protocol.org) — 规范与教程总入口
- [A2A Python Quickstart](https://a2a-protocol.org/v1.0.1/tutorials/python) — 官方 SDK 教程
- [a2aproject/a2a-python](https://github.com/a2aproject/a2a-python) — 官方 Python SDK（PyPI 包名 `a2a-sdk`）
- [a2aproject/a2a-samples](https://github.com/a2aproject/a2a-samples) — 官方样例代码库
- [stacka2a.dev - A2A Python SDK Guide](https://stacka2a.dev/blog/a2a-python-sdk-guide) — 社区教程
- [writetosudeepto/python-a2a](https://github.com/writetosudeepto/python-a2a) — 装饰器风格高层库
- [腾讯云 - A2A 协议落地实践](https://cloud.tencent.com/developer/article/2740824) — 中文实战案例

### A.4 三个主流产品架构

- [openai/codex GitHub](https://github.com/openai/codex) — Codex CLI 官方仓库
- [openai/codex docs/architecture.md](https://github.com/openai/codex/blob/main/docs/architecture.md) — TUI+server / TUI+exec / Approval / Sandbox / Memory 五大子系统
- [Codex CLI 开发者文档](https://developers.openai.com/codex/cli) — Approval policies (untrusted / on-failure / on-request / never) + Sandbox modes (read-only / workspace-write / danger-full-access)
- [earendil-works/pi](https://github.com/earendil-works/pi) — Pi Coding Agent 仓库
- [Pi - Core Architecture DeepWiki](https://deepwiki.com/earendil-works/pi/2-core-architecture) — pi-ai / pi-agent-core / pi-tui / pi-coding-agent 四层包结构
- [Pi - The Coding Agent Built Around What It Won't Do](https://www.rushis.com/pi-the-coding-agent-built-around-what-it-wont-do/) — 设计哲学（最小化、~1K token system prompt）
- [Pi Coding Agent Review: Minimal, Hackable AI Coding CLI](https://dev.to/rosgluk/pi-coding-agent-review-minimal-hackable-ai-coding-cli-4ge8) — 极简主义解读
- [Claude Code Hooks 官方文档](https://docs.anthropic.com/en/docs/claude-code/hooks) — PreToolUse / PostToolUse 等事件定义
- [Claude Code Hooks 完整指南](https://claude.com/blog/how-to-configure-hooks) — 配置实战

### A.5 上下文工程

- [Anthropic - Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) — 2025.09 发布的权威博客（核心引用源）
- [Towards AI - Context Engineering Explained](https://pub.towardsai.net/context-engineering-explained-the-anthropic-guide-thats-changing-how-developers-developers-work-with-ai-40fae176a18d) — 大众化解读
- [腾讯 - Anthropic 发布 AI Agent 上下文工程指南](https://new.qq.com/rain/a/20251001A020C900) — 中文报道
- [Anthropic - Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) — 2024 早期的 agent 设计基础文

### A.6 Harness 工程综合参考

- [akshit.dev - Agent Harness Guardrails](https://www.akshit.dev/posts/agent-harness-guardrails-permissions-sandboxes-hooks) — 三层防御（权限/沙箱/hooks）最相关
- [nxcode.io - What Is Harness Engineering 2026](https://www.nxcode.io/resources/news/what-is-harness-engineering-complete-guide-2026) — 2026 视角综述
- [AI Technology Radar - Harness Engineering](https://ai-radar.aoe.com/architecture-pattern/harness_engineering) — 两种隔离哲学对比
- [llm-stack-book 8.3 - Harness Engineering: Building a Coding Agent](https://prakashkagitha.github.io/llm-stack-book/08-agents-harness/03-harness-coding-agent.html) — 包含 Python 实战代码
- [spd.tech - Agent Harness Engineering](https://spd.tech/artificial-intelligence/agent-harness-engineering) — hooks / sandboxing / HITL 分类清晰
- [dev.to - The Agent Harness as Infrastructure](https://dev.to/devtocash/the-agent-harness-as-infrastructure-least-privilege-guardrails-and-blast-radius-19f2) — "CLAUDE.md = runbook" 等基础设施类比

### A.7 协议栈全景（MCP / A2A / x402 / AP2）

- [x402 / AP2 解析](https://www.coinsdo.com/zh-TW/blog/x402-ap2-agent-payment-protocols-explained) — 四大协议层次对照
- [openfort.io - x402 and Agent-to-Agent Payments](https://www.openfort.io/blog/x402-agentic-payments) — x402 机制详解
- [aiwiki - Agent Payments Protocol (AP2)](https://aiwiki.ai/wiki/agent_payments_protocol) — AP2 Mandates 概念
- [AP2 协议规范](https://agentpaymentsprotocol.info/docs/introduction) — 官方介绍

---

## 附录 B：关键决策点（写作期需复审）

1. **"harness" 是否使用作为通用术语：** 在英文文献中已经是事实通用词；中文采用"Harness（外壳/外层工程）"格式首现，后续可单用"harness"。
2. **不绑定产品命名：** 章节里只能写"某个产品叫 X 实现"，不写"在 Claude Code 中，命令是 X"。例子都用通用语法。
3. **MCP 章节定位：** 必须以"协议"为主、"SDK 用法"为辅；不能变成 FastMCP 教程。
4. **A2A 章节定位：** 必须以"peer-to-peer 协作协议"为主，不展开企业内部多 agent 编排（→ Part 5）。
5. **上下文工程 vs 记忆：** 严格区分——上下文工程是"如何裁剪 prompt 给模型"，记忆是"如何持久化"；Part 4 偏前者，Part 5 偏后者。
6. **Hooks / Permissions / Sandbox：** 三个概念必须分开成章下三节，不能合并讲；否则读者分不清"hook 是事件、permission 是规则、sandbox 是隔离"。
7. **x402 / AP2：** Part 4 只在 Ch21 末尾以"协议栈全景图"一句话提及，不展开；实现细节给 Part 6 工业落地。