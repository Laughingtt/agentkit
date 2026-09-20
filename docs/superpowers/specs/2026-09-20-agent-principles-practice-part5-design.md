# Spec: Agent原理及实践 — Part 5 Agent 功能实现

**Date:** 2026-09-20
**Status:** Draft (pending user review)
**Project:** `agentkit` (Chinese technical book on Agent principles and practice)
**Scope:** Part 5 of 6

---

## 1. 项目背景与分解策略

本书《Agent原理及实践》面向**有编程基础但无 AI/ML 背景的初学者**，以中文 Markdown 写成。整体拆为 6 个 Part：

| Part | 主题 | 状态 |
|---|---|---|
| 1 | 大模型基础 | 已完成 spec |
| 2 | 大模型与 Agent 的演进 | 已完成 spec |
| 3 | Agent 原理 | 待 spec |
| 4 | Harness 工程 | 待 spec |
| 5 | Agent 功能实现 ← **本 spec** | Draft |
| 6 | 工业落地 | 待 spec |

### Part 5 的定位

Part 3 讲了 Agent 的认知架构与范式（"Agent 在想什么"），Part 4 讲了 Harness 工程（"Agent 怎么跑起来"）。Part 5 要回答一个新问题：

> **"一个 Agent 怎么具备实用能力？"** —— tool calling、RAG、记忆、规划、多 Agent 协作、code execution；以及把这些能力封装成 2026 标准协议（MCP / A2A / x402）暴露给世界。

按 CLAUDE.md 的写作原则，Part 5 **不**做原理推导（已在 Part 3），**不**展开 harness 内部细节（已在 Part 4），**不**涉及生产部署与可观测性（放 Part 6）。Part 5 的角色是"**功能积木**"——读完这一 Part，读者应能**独立实现一个具备 tool calling + RAG + 记忆 + 规划 的单 Agent**，并把它**按 MCP / A2A / x402 标准协议打包**，对外提供可复用的能力。

### 与其它 Part 的边界

| 来自 Part | Part 5 复用 | 不复用 |
|---|---|---|
| Part 3（原理） | ReAct / Plan-and-Execute / Reflexion 三范式的接口签名 | 范式的理论动机 |
| Part 4（harness） | while-loop engine、tool registry、context budget 接口 | while-loop 的实现细节、permission 引擎 |

---

## 2. 目标读者与约束

- **读者：** 大学本科以上、会写代码（Python 优先）、**已完成 Part 1-4** 学习的初学者
- **认知前提：** Transformer / RLHF / Agent 认知架构 / ReAct 范式 / Harness 的 while-loop / sandbox 隔离 —— 这些概念已在 Part 1-4 建立
- **代码策略：** **比 Part 1-4 都多**。Part 5 是"实现篇"，每个核心功能必须给出**最小可运行示例**，全部放在 `code/part-5/`
- **总字数：** 35-40k 字（6 章 × 5.5-7k）
- **写作原则：** 严格遵守 CLAUDE.md「一·甲」—— 认知负荷 ≤ 3 新概念/段、直觉 → 类比 → 视觉 → 公式、mermaid 紧贴正文；本 Part 对"实现类"内容特别要求**先流程后代码**（worked-example effect）

---

## 3. 文件结构

```
agentkit/
├── part-5-agent功能实现/
│   ├── README.md                       # Part 5 目录与简介
│   ├── ch22-tool-calling与rag.md       # Tool Calling + RAG
│   ├── ch23-记忆与规划.md              # Memory + Planning
│   ├── ch24-多agent协作.md             # Multi-Agent Collaboration
│   ├── ch25-code-execution.md          # 代码执行沙箱
│   ├── ch26-协议集成.md                # MCP / A2A / x402
│   └── ch27-小结与衔接.md              # Part 5 收束 + 衔接 Part 6
└── code/
    └── part-5/
        ├── README.md                   # 依赖：openai/anthropic/mcp/fastmcp/e2b 等
        ├── tool_calling.py             # Ch22 tool calling 最小循环
        ├── naive_rag.py                # Ch22 Naive RAG 端到端
        ├── agentic_rag.py              # Ch22 Agentic RAG（带 reranker + query rewrite）
        ├── memory_short_term.py        # Ch23 滑动窗口记忆
        ├── memory_long_term.py         # Ch23 三层记忆（KV + vector + relational）
        ├── plan_and_execute.py         # Ch23 Plan-and-Execute with replanning
        ├── multi_agent_crew.py         # Ch24 Crew 风格多 Agent
        ├── multi_agent_langgraph.py    # Ch24 LangGraph 风格状态机
        ├── code_exec_e2b.py            # Ch25 E2B 沙箱执行
        ├── mcp_server.py               # Ch26 FastMCP 服务端（tools + resources + prompts）
        ├── mcp_client.py               # Ch26 FastMCP 客户端
        ├── a2a_server.py               # Ch26 A2A agent card + JSON-RPC 服务端
        ├── a2a_client.py               # Ch26 A2A 客户端（发现 + 任务提交）
        └── x402_demo.py                # Ch26 x402 micropayment 演示
```

> **总计：** 14 个 Python 示例文件 + 1 个 README。比 Part 1（3 个文件）、Part 4（计划 4-5 个文件）明显更多。这是 Part 5 作为"实现篇"的特征。

---

## 4. Part 5 六章内容大纲

### Ch22 Tool Calling 与 RAG（~6.5k 字）

读完应能**独立实现一个支持 tool calling 的 Agent 循环**，并**区分 Naive / Advanced / Agentic 三种 RAG 范式**。

- 22.1 引子：Agent 的"手脚"——为什么没有 tool calling 就没有真正的 Agent
- 22.2 **Tool calling 的协议面**：JSON Schema 描述、OpenAI `tools` vs Anthropic `tools` 字段差异、`tool_choice`（auto / any / none / 指定名字）
- 22.3 **Tool calling 的循环**：Thought → Tool Call → Tool Result → Observation → 下一轮（配 mermaid sequenceDiagram）
- 22.4 **并行 tool 调用**：何时拆开、何时合并；`disable_parallel_tool_use` 的场景
- 22.5 **错误处理与重试**：tool 抛错 → 把错误当 Observation 喂回去 / 重试上限 / 退避
- 22.6 **RAG 的动机**：为什么纯 LLM 不够——幻觉、知识截止、垂直知识
- 22.7 **Naive RAG**：chunk → embed → top-k → prompt 注入（最小可运行）
- 22.8 **Advanced RAG**：query rewrite + reranker + hybrid（BM25 + dense）+ HyDE
- 22.9 **Agentic RAG**：检索本身变成 tool，让 Agent 决定查什么、查几次、如何合并
- 22.10 **向量数据库选型**：Chroma（本地原型）vs Qdrant / Weaviate（生产）vs pgvector（小团队一体化）；一句话点名 Pinecone / Milvus
- 22.11 **三个范式对比表**：成本、延迟、可控性、适用场景
- 22.12 Part 5 章末小结 + 与 Ch23 衔接

**Anchor 示例：**

- **Mermaid sequenceDiagram**：tool calling 时序（user → agent → LLM → tool → result → LLM → ...）
- **Mermaid graph LR**：三种 RAG 范式数据流对比（Naive / Advanced / Agentic）
- **表格**：OpenAI vs Anthropic tool calling 字段差异
- **表格**：三种 RAG 范式在 5 个维度上的对比
- **代码：**
  - `code/part-5/tool_calling.py` —— 最小 tool-calling loop（OpenAI SDK，~80 行，含 JSON Schema）
  - `code/part-5/naive_rag.py` —— Naive RAG 端到端（Chroma + OpenAI embedding）
  - `code/part-5/agentic_rag.py` —— Agentic RAG（retrieve + rerank + answer，retrieval 是 tool）

**为什么这样安排：** Tool calling 是 Agent 的"最基础技能"，RAG 是"垂直知识扩展"。两者放在同一章，因为工程上经常一起实现（"先用 RAG 把知识装进来，再用 tool calling 让 Agent 决定怎么用"）。三种 RAG 范式不平均用力——主推 Agentic RAG（Part 5 视角下唯一可扩展的形态），其余两个给"前置语境"。

---

### Ch23 记忆与规划（~6k 字）

读完应能**独立设计一个三层记忆系统**，并**实现 Plan-and-Execute with replanning**。

- 23.1 引子：为什么 LLM 的"上下文窗口"不等于"记忆"
- 23.2 **短时记忆（Working Memory）**：context window 里最近 N 轮，滑动窗口 + observation masking
- 23.3 **中时记忆（Hot Memory）**：Redis / Key-Value，TTL 自动过期，存"这一两天还在意"的事实
- 23.4 **长时记忆（Long-Term Memory）**：三层混合
  - 向量层：语义检索（pgvector / Qdrant / Weaviate）
  - 关系层：PostgreSQL，结构化事实 + 行级安全
  - 时序层：可选，Zep/Graphiti 用于"事实会变"的场景
- 23.5 **记忆的写入策略**：always-write / significant-write（让 LLM 判断）/ never-write
- 23.6 **记忆的检索流水线**：user profile 注入 → recency 窗口 → hot memory → semantic search → entity recognition → 拼装
- 23.7 **记忆框架一句话点名**：mem0（bolt-on 通用）、Letta（自编辑式长跑）、Zep（图谱 + 时序）；不展开框架内部
- 23.8 **规划范式回顾**：ReAct / Plan-and-Execute / Reflexion —— Part 3 已经讲原理，本章给**实现接口**
- 23.9 **Plan-and-Execute 实现**：planner（强模型）+ executor（弱模型）+ replan 钩子（fail → 重新规划）
- 23.10 **Reflection 实现**：critic（窄而具体的评判）+ revision loop（防 regression 的对比步骤）
- 23.11 **何时用哪种规划**：ReAct（<10 步）/ Plan-and-Execute（多步研究）/ Reflection（质量优先）
- 23.12 Part 5 章末小结 + 与 Ch24 衔接

**Anchor 示例：**

- **Mermaid graph TD**：三层记忆架构（短时 → 中时 → 长时；长时内部分向量 / 关系 / 时序）
- **Mermaid sequenceDiagram**：Plan-and-Execute 流程（planner → executor → step → replan 触发）
- **表格**：三种规划范式适用场景 + 风险
- **代码：**
  - `code/part-5/memory_short_term.py` —— 滑动窗口 + observation masking
  - `code/part-5/memory_long_term.py` —— 三层记忆（SQLite + pgvector + Redis 可替换接口）
  - `code/part-5/plan_and_execute.py` —— Plan-and-Execute with replanning（强模型 planner + 弱模型 executor）

**为什么这样安排：** 记忆和规划是"Agent 是否能跑长任务"的两个核心。前者解决"它记不记得"，后者解决"它会不会想"。这一章**不**重复 Part 3 的范式动机，**只**给"接口 + 代码"。

---

### Ch24 多 Agent 协作（~6k 字）

读完应能**区分三种多 Agent 架构**，并能独立实现 Crew 风格的角色分工。

- 24.1 引子：单 Agent 的天花板——为什么需要多 Agent
- 24.2 **三种多 Agent 架构**：role-based（Crew）vs graph-based（LangGraph）vs conversation-based（AutoGen）
- 24.3 **角色分工的直觉**：项目经理 / 研究员 / 写手 / 审稿人——为什么拆 4 个比拆 1 个效果好
- 24.4 **Crew 风格实现**：role + goal + backstory + task → 顺序 / 并行 / 分层执行
- 24.5 **LangGraph 风格实现**：把 Agent 当状态机节点，循环就是图遍历
- 24.6 **AutoGen 风格一句话**：对话驱动、双向 messaging；不展开
- 24.7 **通信原语**：消息总线（message bus）/ shared state / 共享文件系统
- 24.8 **冲突解决**：两个 Agent 抢同一份输出 / 投票 / supervisor 仲裁
- 24.9 **失败传播**：一个 Agent 报错如何不拖垮整组——task graph + checkpoint + retry scope
- 24.10 **可观测性要求**：每个 Agent 的 token 用量、步骤数、决策日志（提示在 Part 6 详细展开）
- 24.11 **三种架构对比表**：可控性 / 学习曲线 / 适用场景
- 24.12 Part 5 章末小结 + 与 Ch25 衔接

**Anchor 示例：**

- **Mermaid graph LR**：4 角色 Crew 协作（manager → researcher → writer → reviewer）
- **Mermaid graph TD**：LangGraph 状态机示例（plan → code → test → fix → done，循环边）
- **表格**：三种多 Agent 框架对比（CrewAI / LangGraph / AutoGen），含学习曲线 / 适用规模
- **代码：**
  - `code/part-5/multi_agent_crew.py` —— 自研极简 Crew（角色 + 任务 + 顺序执行，~120 行，不依赖 CrewAI）
  - `code/part-5/multi_agent_langgraph.py` —— LangGraph 风格状态机（用纯 Python dict 当 state）

**为什么这样安排：** 多 Agent 是 Part 5 的"中等难度"内容。读者在 Part 3 已经知道协作模式，Part 4 已经知道 harness 怎么跑循环——本章直接给两个最常用形态的实现。**避免**对 CrewAI / LangGraph / AutoGen 任何一个做产品教程；只抽出"模式"。

---

### Ch25 Code Execution（~6k 字）

读完应能**为 Agent 接上一个安全的代码执行沙箱**，并理解"为什么 LLM 不应该直接生成可执行代码"。

- 25.1 引子：Agent 自己写代码并执行——为什么这是 2026 主流 harness 的标配
- 25.2 **为什么需要沙箱**：安全 / 可重放 / 资源限制 / 状态隔离
- 25.3 **沙箱的四个层级**：subprocess（本地进程）→ docker（容器）→ microVM（Firecracker）→ remote API（E2B / Modal）
- 25.4 **subprocess 沙箱**：最简形态，Python `subprocess.run` + resource limits + timeout；适用 trust boundary 内的脚本
- 25.5 **docker 沙箱**：中等隔离，需要 Docker daemon；通用但部署成本
- 25.6 **microVM 沙箱**：Firecracker / gVisor，强隔离；适合生产云端
- 25.7 **远程 API 沙箱**：E2B / Modal / CodeSandbox，按调用计费、无运维；适合 MVP
- 25.8 **代码作为 tool 的设计**：tool "run_python" 接收 `code: str` + 返回 `stdout / stderr / artifacts`；让 LLM 把它当普通 tool 调用
- 25.9 **状态管理**：每个会话一个沙箱实例 / 跨会话复用（昂贵但更接近 REPL 体验）
- 25.10 **典型场景**：数据清洗 / 一次性脚本 / 数学计算 / 文件批量处理
- 25.11 **安全红线**：网络访问控制 / 文件系统挂载 / 输出体积上限 / secret 脱敏
- 25.12 Part 5 章末小结 + 与 Ch26 衔接

**Anchor 示例：**

- **Mermaid graph TD**：沙箱四层级对比（subprocess / docker / microVM / remote API 在隔离强度与运维成本二维平面）
- **Mermaid sequenceDiagram**：Agent 调 `run_python` tool → sandbox exec → 返回结果
- **表格**：四个沙箱层级 × 5 维度（隔离强度 / 启动开销 / 部署复杂度 / 成本 / 适用场景）
- **代码：**
  - `code/part-5/code_exec_e2b.py` —— E2B SDK 最小示例（创建 sandbox → run code → 取 stdout）

**为什么这样安排：** Code execution 是 Part 5"风险最高"的功能——读者一旦把它接到公网 Agent 上，安全事故概率不低。所以这一章**红线**写得比其它章节更明确，**不**给一行"无沙箱执行 LLM 输出"的代码示例。

---

### Ch26 协议集成：MCP / A2A / x402（~7k 字）

读完应能**为本地 Agent 实现一个 MCP server**，**为一个 Agent 暴露 A2A agent card**，并**让一个工具调用走 x402 微支付**。这是 Part 5 全章最贴近"2026 行业标准"的一章。

- 26.1 引子：为什么协议化——从"我的 Agent 能用"到"别人也能用我的 Agent"
- 26.2 **协议栈全景**：MCP（Anthropic，2024.11→2025.11→2026.07 三代） / A2A（Google→Linux Foundation, 2026.04 v1.0） / x402（Coinbase, 2025） / AG-UI（CopilotKit, 2026 仍在 draft）
- 26.3 **MCP 的核心抽象**：tools（可调用） / resources（只读数据） / prompts（消息模板） / sampling（服务器反向请求 LLM）
- 26.4 **MCP server 实现（FastMCP）**：`@mcp.tool()` / `@mcp.resource()` / `@mcp.prompt()` 三种装饰器；stdio + Streamable HTTP 两种 transport
- 26.5 **MCP Streamable HTTP 演进**：2024.11-05 HTTP+SSE（已弃）→ 2025-03-26 单端点 Streamable HTTP + session id → 2026-07-28 移除 session；理解"为什么"比记版本号更重要
- 26.6 **MCP 客户端**：用 `MCPClient` 连 server，tools / resources 直接进入 Agent 的 tool registry
- 26.7 **A2A 的核心抽象**：agent card（`/.well-known/agent.json` 描述技能 + endpoint + 鉴权） + task（JSON-RPC over HTTP） + artifact（产物）
- 26.8 **A2A agent card 实现**：写一个最小 agent card（name / description / skills / capabilities）
- 26.9 **A2A server 任务端点**：接受 task → 调度本地 Agent → 返回 artifact
- 26.10 **A2A 客户端**：discovery（拉 agent card）→ 选 skill → submit task → 拉 artifact
- 26.11 **x402 的动机**：HTTP 402 沉睡 30 年 → Agent 经济的微支付需要 → USDC + EIP-3009 + facilitator（Coinbase CDP）
- 26.12 **x402 工作流**：客户端请求 → 收 402 + 支付条款 → 签 USDC → 重试带 payment payload → facilitator 结算
- 26.13 **x402 与 Agent 的结合**：把 `tool calling` 的某个 tool 标记为"按次计费"，被调用时走 x402 流程
- 26.14 **AG-UI 一句话**：Agent ↔ 前端应用的事件流（生命周期 / 文本流 / 工具调用 / 状态快照）；draft 状态，Part 6 再展开
- 26.15 **协议组合实例**：一个 MCP server 同时被本地 + 远端 Agent 调用；远端 Agent 通过 A2A 发现它，部分敏感能力走 x402
- 26.16 Part 5 章末小结 + 与 Ch27 衔接

**Anchor 示例：**

- **Mermaid graph TD**：四大协议在 Agent 系统中的位置（MCP↔工具 / A2A↔Agent / x402↔支付 / AG-UI↔前端）
- **Mermaid sequenceDiagram**：MCP Streamable HTTP 单端点流程（POST 请求 → 响应 JSON 或 SSE）
- **Mermaid sequenceDiagram**：A2A discovery → task submit → artifact 返回
- **Mermaid sequenceDiagram**：x402 401/402 → 签支付 → 200
- **表格**：MCP / A2A / x402 / AG-UI 横向对比（协议层 / 起源 / 标准化机构 / 2026 状态 / 适用场景）
- **代码：**
  - `code/part-5/mcp_server.py` —— FastMCP server（3 个 tool + 1 个 resource + 1 个 prompt，stdio transport）
  - `code/part-5/mcp_client.py` —— 客户端连 server，把 tool 注册到 Agent
  - `code/part-5/a2a_server.py` —— A2A agent card（写在 `/.well-known/agent.json`） + JSON-RPC 任务端点
  - `code/part-5/a2a_client.py` —— 客户端 discovery + task submit
  - `code/part-5/x402_demo.py` —— x402 micropayment 最小演示（client 触发 → server 返回 402 → 签支付 → 重试）

**为什么这样安排：** 这是 Part 5 唯一一章要求"懂协议"。三个协议都不深——MCP 给 server + client 最小骨架，A2A 给 agent card + 一个 task 端点，x402 给 402 重试流程。**不**讲解协议规范的每个字段，**只**给"能让示例跑起来"的最少代码 + 一张图。AG-UI 因仍是 draft，仅作"协议栈全景"中的一行点名。

---

### Ch27 Part 5 小结与衔接 Part 6（~2.5k 字）

读完应能在**一张图上**画出 Part 5 涵盖的"六大功能积木"，并指出 Part 6 将回答的工业落地问题。

- 27.1 引子：Part 5 走完一遍——你手里有了哪些积木
- 27.2 **Part 5 功能总览图**：tool calling + RAG + memory + planning + multi-agent + code execution + 协议层（MCP / A2A / x402）
- 27.3 **可复现的"70% 主流产品特性"自检**：对照 Claude Code / Pi / Codex 三者核心特性，本 Part 给出"是否已实现"的清单
- 27.4 **从"能跑"到"能上线"的缺口**：错误率 / 成本 / 安全 / 可观测性 / 合规——这些是 Part 6 的范畴
- 27.5 **与 Part 6 的衔接**：LLM-native 可观测性（Langfuse / Helicone / Arize Phoenix / OpenLLMetry）、evaluation（LLM-as-judge）、model router、EU AI Act / AIUC-1 合规、真实案例
- 27.6 **写给读者的两个练习**：① 给自己的本地 Agent 加一个 MCP server；② 让两个 Agent 通过 A2A 互派任务

**Anchor 示例：**

- **Mermaid graph TD**：Part 5 功能全景（六大积木 + 协议层 + 与 harness 的关系）
- **表格**：Claude Code / Pi / Codex 核心特性 × Part 5 已实现项（30+ 行 × 4 列）
- **代码：** 无（本章为收束，不引入新代码）

---

## 5. 写作约定（简版，详见 CLAUDE.md）

- 每章模板：标题 → 一句话简介 → 本章目标（3-5 条 bullet）→ 本章导览（mermaid 总览图）→ 子节 → 本章小结 → 本章参考
- Mermaid 仅用四种图：`graph` / `flowchart` / `sequenceDiagram` / `mindmap`
- 复杂关系用表格，不堆 mermaid
- 引用：随文 markdown 链接 + 章末 "本章参考"（分必读论文 / 推荐博客 / 视频课程 三类）
- 代码：中文注释；可运行示例文件头加 `# runnable: yes`；不可运行示意文件头加 `# illustrative only`
- **本 Part 代码规范特别要求**：
  - 完整示例文件 ≤ 200 行（除少数例外）
  - 每个 `.py` 文件顶部 3 行注释：`# runnable: yes / no`、`# depends: <pkg>`、`# usage: python xxx.py`
  - 所有外部依赖统一列在 `code/part-5/README.md`，按章节分组
- 跨章引用 `参见 22.3`；跨 Part `(见 Part 3 Ch12)`，**不**复制内容

---

## 6. 完成度与验收标准

### 单章完成标准

- 子节齐全，与大纲一致（Ch22: 12 节 / Ch23: 12 节 / Ch24: 12 节 / Ch25: 12 节 / Ch26: 16 节 / Ch27: 6 节）
- 含本章目标、小结、本章参考
- 含至少 1 个 mermaid + 1 个表格
- 字数在 ±20% 区间内
- 关键概念全覆盖（每章 6-10 个）
- 至少 1 个代码示例（Ch27 可豁免）

### Part 5 整体验收

- 6 章全部写完
- 总字数 35-40k（Ch22 6.5k / Ch23 6k / Ch24 6k / Ch25 6k / Ch26 7k / Ch27 2.5k）
- `part-5-agent功能实现/README.md` 含目录与一句话简介
- `README.md` 出现 Part 5，标记为 "已发布"
- 所有 mermaid 在 GitHub 渲染无语法错误
- 14 个 Python 示例文件全部存在于 `code/part-5/`（含 README）
- 所有 `runnable: yes` 示例在本地能跑（Task 6 终审时统一验证）
- 自查通过（placeholder / 内部一致性 / 范围 / 歧义）

### 自查清单

1. **Placeholder 扫描：** 无 TBD / TODO / 占位文本
2. **内部一致性：** 章间不矛盾（术语、概念、数据一致）；与 Part 3-4 衔接正确
3. **范围检查：** 不混入 Part 4 harness 内部实现 / Part 6 工业落地细节
4. **歧义检查：** 每个子节要求无歧义；协议字段引用必须给出版本号
5. **代码可运行性：** 14 个示例文件至少抽样 50% 在本地能跑通；跑不通的必须在文件头标注原因

---

## 7. 显式 Out-of-Scope（Part 5 不涉及）

- Agent 认知架构、范式的理论动机 → Part 3
- Harness while-loop / sandbox 引擎 / permissions 内部实现 → Part 4
- 工业部署 / 可观测性平台 / evaluation / security 红队 → Part 6
- 任何具体 LLM（Claude / GPT / Gemini / Qwen）的私有 SDK 细节
- 任何商业向量数据库的产品评测（只做"如何选"）
- CrewAI / LangGraph / AutoGen 等框架的私有 API 深入（只抽模式）
- 数学严格证明 / 论文实验复现

---

## 8. 后续流程

1. 本 spec 经用户审阅通过后，进入 `superpowers:writing-plans` 流程
2. writing-plans 输出 Part 5 的实现 plan（含每章 task 拆分）
3. plan 完成后进入实际写作阶段
4. 写作期间严格遵守 CLAUDE.md「十三 · 验证的批量执行」——单章只做最小自查，完整审查在 Task 6 终审统一执行

---

## 9. 研究资料来源（联网搜索汇总，本 spec 共完成 12 次定向搜索）

| # | 主题 | 关键发现 |
|---|---|---|
| 1 | OpenAI / Anthropic tool calling 格式 2026 | tool_choice 四种取值（auto/any/none/tool）；Anthropic 默认并行；`disable_parallel_tool_use` 控制 |
| 2 | Naive / Advanced / Agentic RAG 2026 | 三范式成为业界共识；Agentic RAG 把 retrieve 做成 tool 让 Agent 决定 |
| 3 | 向量数据库 2026 | Chroma（本地）/ pgvector（小团队一体化）/ Qdrant·Weaviate（生产）；Pinecone / Milvus 一句话点名 |
| 4 | 多 Agent 框架 2026 | CrewAI 重易用 / LangGraph 重控制 / AutoGen 重研究；**模式抽取而非产品教程** |
| 5 | Code Execution 沙箱 2026 | E2B（专用）/ Modal（多用途）/ CodeSandbox（前端）；**四层级框架**：subprocess → docker → microVM → remote API |
| 6 | MCP server 实现 | FastMCP `@tool`/`@resource`/`@prompt` 三装饰器；stdio + Streamable HTTP；`mcp[cli]` 安装 |
| 7 | A2A agent card / 客户端 | agent card（`/.well-known/agent.json`）+ JSON-RPC over HTTP；2026.04 v1.0 进入 Linux Foundation |
| 8 | x402 支付协议 | HTTP 402 + USDC + EIP-3009 + facilitator；Coinbase CDP 官方支持；agentic commerce 关键基建 |
| 9 | Claude Code / Pi / Codex 核心特性 | "harness 而非 model 决定编码 Agent 表现"；9 大组件：loop / context / skills / sub-agents / hooks / session / prompt / permissions |
| 10 | AG-UI 协议 | 仍在 draft；事件流 16 类；与 MCP / A2A 并列 2026 协议栈 |
| 11 | Agent 记忆架构 2026 | 三层（KV+pgvector+Postgres）成为企业默认；mem0/Letta/Zep 三种风格路线 |
| 12 | MCP Streamable HTTP 演进 | 2024.11 HTTP+SSE 弃；2025.03.26 单端点 + session；2026.07.28 进一步精简 |

> 本 spec 写作严格基于联网搜索结果**+** 项目内部知识，**不**凭模型记忆单方判断。

---

## 10. 关键决策点（草案级，待用户审阅）

1. **章节数量 6 章：** Ch22-Ch27，Ch27 为收束章。这是 CLAUDE.md 默认的"5-6 章"上限。**不**用 5 章强行合并 Ch27 进 Ch26，避免 Part 5 收尾太突兀。
2. **代码量 14 个 .py：** 比 Part 1-4 都多。这是 Part 5 作为"实现篇"的本质要求——每个核心功能必须有最小可运行示例。**不**为控制篇幅而删代码示例。
3. **三大 RAG 范式不平均用力：** 主推 Agentic RAG（Part 5 视角下唯一可扩展的形态），Naive / Advanced 作为"前置语境"。**不**展开三种范式的完整对比矩阵。
4. **协议章（Ch26）重在"能跑"，不在"全规范"：** MCP / A2A / x402 三个协议各给最小可运行示例 + 一张时序图。**不**逐字段讲协议规范；AG-UI 因仍在 draft 只作"协议栈全景"一行点名。
5. **可复现主流产品特性 70%：** Ch27 给一张表，列出 Claude Code / Pi / Codex 的核心特性并标注 Part 5 是否已实现。**不**写"Claude Code 怎么用"这种产品教程。