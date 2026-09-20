# Spec: Agent原理及实践 — Part 2 大模型与 Agent 的演进

**Date:** 2026-09-20
**Status:** Draft (pending user review)
**Project:** `agentkit` (Chinese technical book on Agent principles and practice)
**Scope:** Part 2 of 6

---

## 1. 项目背景与分解策略

本书《Agent原理及实践》面向**有编程基础但无 AI/ML 背景的初学者**，以中文 Markdown 写成。整体拆为 6 个 Part，每个 Part 独立走 `brainstorm → spec → plan → 写作` 流程：

| Part | 主题 |
|---|---|
| 1 | 大模型基础（已完成 spec） |
| 2 | 大模型与 Agent 的演进 ← **本 spec** |
| 3 | Agent 原理 |
| 4 | Harness 工程 |
| 5 | Agent 功能实现 |
| 6 | 工业落地 |

本 spec 只覆盖 **Part 2**。其余 Part 在各自 spec 中设计。

### Part 2 的定位

Part 1 解决了"LLM 是什么、怎么训练出来"的问题。Part 2 要回答两个新问题：

1. **LLM 这一路是怎么走到 2026 的？** —— 家族史：BERT → GPT → LLaMA → Qwen / DeepSeek / Claude / Gemini → 推理模型 → 混合架构
2. **Agent 这一路又是怎么走过来的？** —— 50 年演进：Symbolic → Reactive → Cognitive → Hybrid → LLM-based
3. **为什么突然冒出 MCP / A2A 这种协议？** —— 行业从"做模型"走向"做生态"的拐点

按 CLAUDE.md 的写作原则，Part 2 **不**做 LLM 训练数学、不做 Attention 推导（已在 Part 1），也**不**展开 Agent 原理细节（放 Part 3）。Part 2 的角色是"**横向时间线**"——让读者读完后，能在大脑中建立一张 2026 年 LLM 与 Agent 世界的"地图"。

---

## 2. 目标读者与约束

- **读者：** 大学本科以上、会写代码、**已完成 Part 1** 学习的初学者
- **认知前提：** Transformer、Attention、Self-Supervised Pre-training、RLHF 这些概念在 Part 1 已建立。Part 2 在此之上铺历史与现代变体
- **代码：** 比 Part 1 **更少**——历史叙事章节（Ch6-Ch9）以图 + 表为主；仅 Ch10 给出 1 个最小可运行示例
- **总字数：** 25-30k 字（5 章 × 5-6k）。比 Part 1 略多，但**密度更低**（叙述为主）
- **写作原则：** 严格遵守 CLAUDE.md「一·甲」—— 认知负荷 ≤ 3 新概念/段、直觉 → 类比 → 视觉 → 公式、mermaid 紧贴正文

---

## 3. 文件结构

```
agentkit/
├── part-2-大模型与agent的演进/
│   ├── README.md                # Part 2 目录与简介
│   ├── ch06-llm家族编年史.md
│   ├── ch07-现代llm关键变体.md
│   ├── ch08-agent五十年演进.md
│   ├── ch09-协议层mcp与a2a.md
│   └── ch10-从模型到agent.md
└── code/
    └── part-2/
        ├── README.md            # 依赖说明（仅一个示例）
        └── react_loop.py        # Ch10 最小 ReAct 循环示例
```

> Part 2 与 Part 1 的关系：Part 1 末尾已留衔接，本 Part 标题采用 Part 1 末尾规划的"演进篇"定位。

---

## 4. Part 2 五章内容大纲

### Ch6 LLM 家族编年史（~6k 字）

读完应能在脑海中**画出 2017-2026 LLM 时间线**，并指出每个里程碑的开创性意义。

- 6.1 引子：从 Transformer 到"模型即产品"——三个分水岭年（2017 / 2020 / 2023）
- 6.2 三大架构路线：Encoder-only / Decoder-only / Encoder-Decoder
- 6.3 Encoder-only 时代：BERT（2018）与它的继承者（RoBERTa、ALBERT、DeBERTa）
- 6.4 Decoder-only 统一：GPT 系（GPT-1 / GPT-2 / GPT-3 / GPT-3.5 / GPT-4 / GPT-4o / GPT-5 / o 系列）
- 6.5 Encoder-Decoder 路线：T5（2019）与 BART，统一文本到文本的范式
- 6.6 开源浪潮：LLaMA 系（2023.2 起 → Llama 2 → 3 → 3.1 → 4 Scout/Maverick → Meta Superintelligence Labs 2026 转向）
- 6.7 中文 LLM 双雄：Qwen 系（Qwen 2.5 / Qwen 3, 2025.04 hybrid thinking）与 DeepSeek 系（V3 / R1, 2025.01）
- 6.8 闭源前沿：Claude（4.7 Opus）、Gemini（3 Pro）、GPT-5 系列——三家分工
- 6.9 **编年总表（mermaid timeline）**：一张图涵盖 2017-2026 所有里程碑
- 6.10 Part 2 章末小结 + 与 Ch7 衔接

**Anchor 示例：**
- Mermaid timeline：2017 Transformer → 2018 BERT/GPT-1 → 2019 T5/RoBERTa → 2020 GPT-3 → 2022 ChatGPT/InstructGPT → 2023 LLaMA 1/2 → 2024 Llama 3 → 2025 Qwen3/DeepSeek R1/Llama 4 → 2026 Claude 4.7 / Gemini 3 / Meta 转向 Muse Spark
- 表格：三大架构路线对比（Encoder / Decoder / Enc-Dec）

**为什么这样安排：** Part 1 已经讲过 Transformer 内部；本章把 Transformer 之后的"应用形态"梳理一遍。读者读完应能用一句话回答"为什么 2020 年后几乎所有 LLM 都是 Decoder-only"。

---

### Ch7 现代 LLM 的关键变体（~5.5k 字）

读完应能说出当代 SOTA LLM 的**五个关键标签**（MoE / 推理 / 长上下文 / 多模态 / SSM 混合），并能用一句话解释每个标签的动机。

- 7.1 引子：为什么 2023-2026 的 LLM 看起来"长得不一样"
- 7.2 **MoE（Mixture of Experts）**：稀疏激活的直觉 + 一句话点名 Switch Transformer / Mixtral / DeepSeek-V3 / Qwen3-MoE
- 7.3 **状态空间模型（SSM / Mamba）**：为什么 Transformer 在长序列上"贵"，SSM 的解法
- 7.4 **混合架构**：Jamba（AI21, 2024.03）、Nemotron-H（NVIDIA, 2025）、Falcon-H1（TII）—— 1 个 Attention 配 5-7 个 SSM 是当前共识
- 7.5 **推理模型（Reasoning Model）**：o1（2024.09）→ o3 → R1（2025.01）→ Qwen3 Thinking 模式——"思考更久答更好"
- 7.6 **长上下文与 KV cache**：从 4K → 128K → 1M 的工程战；KV 量化、GQA、MQA
- 7.7 **多模态原生化**：从 CLIP-style 对齐 → Native Multimodal（Gemini / GPT-4o 一体训练）
- 7.8 **现代组件一句话点名**：RMSNorm / SwiGLU / RoPE / ALiBi / YaRN——表格列出，不展开
- 7.9 章节小结：五个标签一张图

**Anchor 示例：**
- Mermaid 思维导图（mindmap）：现代 LLM 变体五大类
- 表格：五大变体对比（动机 / 代表模型 / 何时引入）
- 一张 mermaid `graph LR`：标准 Transformer block → 现代 Transformer block 的对比

**为什么这样安排：** Part 1 §3.10 已经给过现代变体的"一句话预告"，本章兑现。注意**深度**——读者只需要直觉，不需要数学。

---

### Ch8 Agent 五十年演进（~6k 字）

读完应能说出 Agent 演进的**四个阶段**及其代表工作，并能用一句话回答"为什么 2022 年后 Agent 范式被 LLM-based 统治"。

- 8.1 引子：从"会思考的程序"到"会用工具的 LLM"——Agent 不是一个新词
- 8.2 Agent 的工作定义（Wooldridge & Jennings, 1995）：自主性 + 反应性 + 主动性 + 社会性
- 8.3 **Symbolic Agents**（1960s-1990s）：Logic Theorist / General Problem Solver / SHRDLU / 专家系统（MYCIN）—— 规则与逻辑的辉煌
- 8.4 **Reactive Agents**（1980s-2000s）：Rodney Brooks 的"无表示智能"—— subsumption architecture，挑战 Symbolic
- 8.5 **Cognitive / Deliberative Agents**（1990s-2010s）：BDI（Belief-Desire-Intention）模型、SOAR、ACT-R、IRMA
- 8.6 **混合架构**（2000s-2010s）：InteRRaP、TouringMachines—— 分层（reactive 在底层 / deliberative 在上层）
- 8.7 **LLM-based Agents**（2022- ）：ReAct（2022.10, Yao et al.）→ AutoGPT（2023.03）→ Reflexion（2023.03）→ Toolformer（2023.02）→ BabyAGI（2023.03）—— "LLM 当大脑"的新范式
- 8.8 演进图：四条路线的 mermaid `graph TD` 时间线（带高亮：当前主流）
- 8.9 章节小结：四条路线的**通用模式**——perception / memory / planning / action

**Anchor 示例：**
- Mermaid `graph TD`：Agent 五十年路线图（Symbolic / Reactive / Cognitive / LLM-based 四分支并行时间线）
- 表格：四个阶段代表工作对比（年代 / 代表论文或系统 / 核心思想 / 局限）
- ASCII 框图：BDI agent 内部循环（信念 ← 感知 / 意图 ← 规划 / 行动 → 环境）

**为什么这样安排：** 这一章是 Part 2 的"历史灵魂"。要让读者明白 Agent 不是 2023 年突然出现的——它有 50 年的思想积淀。LLM-based 是新一波，但 reactive / BDI 的思想（**反应性**、**信念-愿望-意图分层**）仍在当代 Agent 设计里反复出现。

---

### Ch9 协议层的诞生：MCP 与 A2A（~5k 字）

读完应能描述 **MCP 是什么、A2A 是什么、它们为何互补**，能看懂一段 MCP server 的 Python 代码骨架。

- 9.1 引子：为什么 2024 年起突然冒出"协议"这个词？—— 工具碎片化的痛点
- 9.2 **MCP 起源**：2024.11.25 Anthropic 发布；主创 David Soria Parra、Justin Spahr-Summers；灵感来自 LSP（Language Server Protocol）
- 9.3 **MCP 三大原语**：Tools（工具）/ Resources（数据）/ Prompts（提示模板）—— 一句话直觉
- 9.4 **MCP 传输层**：stdio（本地进程）与 Streamable HTTP（远程服务）——为什么 HTTP 不够、要"Streamable"
- 9.5 **MCP 生态时间线**：2025.03 OpenAI 采纳 → 2025.04 Google DeepMind 支持 → 2025.05 Microsoft Windows 原生 → 2025.12.09 捐赠 Linux Foundation AAIF
- 9.6 **A2A 起源**：2025.04.09 Google 发起；目标是跨厂商 / 跨框架的 Agent 协作
- 9.7 **A2A 与 MCP 的关系**：MCP 解决"Agent ↔ 工具"、A2A 解决"Agent ↔ Agent"——互补不竞争
- 9.8 **一句话点名其他协议**：x402（支付）、AP2（代理支付）、AG-UI（UI）—— 表格列出定位
- 9.9 章节小结：协议层 = Agent 时代的"USB-C 时刻"

**Anchor 示例：**
- Mermaid `sequenceDiagram`：MCP 客户端调工具的四步握手（initialize → list tools → call tool → 响应）
- 表格：MCP vs A2A 对比（解决什么问题 / 发起方 / 时间 / 核心抽象）
- Mermaid `graph LR`：协议层全景图（MCP / A2A / x402 / AP2 / AG-UI）

**为什么这样安排：** 这章是 Part 2 与 Part 4（Harness 工程）的桥梁。Part 2 只讲起源与动机，不展开实现细节。Part 4 / 5 会再深入实现。

---

### Ch10 从模型到 Agent：必备的工程组件（~5.5k 字）

读完应能口述一个**最小 Agent 系统**的五个工程组件（context / memory / tool / plan / act），并能阅读一个 50 行的 ReAct 循环示例。

- 10.1 引子：LLM ≠ Agent——LLM 只是"大脑"，Agent 是"大脑 + 身体"
- 10.2 **上下文工程（Context Engineering）**：拼装 system prompt / history / tool result 的艺术
- 10.3 **记忆三层**：短期（in-context）/ 长期（向量库 / 文件）/ 工作记忆（scratchpad）
- 10.4 **工具调用（Tool Calling）**：从 Function Calling（OpenAI 2023.06）到 MCP tools
- 10.5 **RAG 的直觉**：检索 → 拼上下文 → 生成；为什么需要它
- 10.6 **多 Agent 协作**：orchestrator + sub-agent 模式，通信靠消息总线
- 10.7 **代码即工具**：让 Agent 执行 shell / Python 是怎么工作的（简要，Part 5 深入）
- 10.8 **一个最小 ReAct 循环示例**（`code/part-2/react_loop.py`）：
  - Thought → Action → Observation 三步循环
  - 用 Python 字典模拟两个工具（search / calc）
  - 50 行内可运行；不依赖外部 LLM API（用规则模拟 LLM 选择）
- 10.9 Part 2 小结 + 与 Part 3 衔接

**Anchor 示例：**
- Mermaid `flowchart LR`：Agent 五组件（Context / Memory / Tool / Plan / Act）数据流
- ASCII 框图：ReAct 循环的 Thought-Action-Observation 三步
- 代码：`code/part-2/react_loop.py`（最小可运行示例）

**为什么这样安排：** Part 2 的"压轴章"，给读者一个具体的"Agent 长什么样"——避免前 4 章纯历史让读者空虚。Part 3 会从原理层深入，Part 5 会从工程实现层深入，本章是它们的预告。

---

## 5. 写作约定（简版，详见 CLAUDE.md）

- 每章模板：标题 → 一句话简介 → 本章目标（3-5 条 bullet）→ 本章导览（mermaid 总览图）→ 子节 → 本章小结 → 本章参考
- Mermaid 仅用四种图：`graph` / `flowchart` / `sequenceDiagram` / `mindmap` / `timeline`（新增）
- 复杂关系用表格，不堆 mermaid
- 引用：随文 markdown 链接 + 章末 "本章参考"（分必读论文 / 推荐博客 / 视频课程 三类）
- 代码：仅 Ch10 一个示例；中文注释；文件头加 `# runnable: yes`
- 跨章引用 `参见 X.3`；跨 Part `(见 Part N ChM)`，**不**复制内容
- 历史内容务必**联网核查**年份与论文标题——读者对"AI 史"细节敏感

---

## 6. 完成度与验收标准

### 单章完成标准

- 子节齐全，与大纲一致
- 含本章目标、小结、本章参考
- 含至少 1 个 mermaid + 1 个表格
- 字数在 ±20% 区间内
- 关键概念全覆盖（每章 5-8 个）
- Ch6/Ch7/Ch8/Ch9 可无代码；Ch10 必须含 1 个可运行代码示例

### Part 2 整体验收

- 5 章全部写完
- 总字数 25-30k（**5 章合计**，比 Part 1 略多）
- `part-2-大模型与agent的演进/README.md` 含目录与一句话简介
- `README.md` 出现 Part 2，标记为 "已发布"
- 所有 mermaid 在 GitHub 渲染无语法错误
- `code/part-2/react_loop.py` 可运行
- 自查通过（placeholder / 内部一致性 / 范围 / 歧义）

### 自查清单

1. **Placeholder 扫描：** 无 TBD / TODO / 占位文本
2. **内部一致性：** 章节之间不矛盾（年份、模型名、术语一致）
3. **范围检查：** 不混入 Part 3-6 内容（不展开 Agent 原理细节、不展开 Harness 实现）
4. **历史核查：** 论文发表年份、模型发布日期、协议发布日期**全部联网核对**
5. **术语统一：** 同一英文术语在首次出现用"中文名（English term）"，后续保持一致
6. **与 Part 1 衔接：** Part 1 末尾 Ch5.10 提到的"演进篇"在 Part 2 开头呼应

---

## 7. 显式 Out-of-Scope（Part 2 不涉及）

- Transformer / Attention 数学推导 → Part 1
- RLHF / DPO / 对齐技术细节 → Part 1
- Agent 原理细节（ReAct 算法完整描述、AutoGPT 内部状态机、Reflexion 反思机制实现）→ Part 3
- Harness 架构、hooks、permissions、sandbox → Part 4
- MCP server 完整实现、Agent SDK 代码 → Part 5
- 工业落地、监控、评估、合规 → Part 6
- LLM 训练数学 / GPU 集群 / 分布式训练 → Part 1（提过即止）
- 数学严格证明、复现论文实验
- **逐个横评**所有 LLM（如每个模型跑全部 benchmark 对比表）—— Part 2 只取**模式抽象**

---

## 8. 后续流程

1. 本 spec 经用户审阅通过后，进入 `superpowers:writing-plans` 流程
2. writing-plans 输出 Part 2 的实现 plan
3. plan 完成后进入实际写作阶段
4. Part 2 完成后再启动 Part 3 的 brainstorm

---

## 研究资料来源（联网搜索汇总）

### LLM 家族系
- [Llama 4 - AI Wiki](https://aiwiki.ai/wiki/llama_4)
- [Llama (language model) - Wikipedia](https://en.wikipedia.com/wiki/Llama_2)
- [Open Weights - AI Wiki](https://aiwiki.ai/wiki/open_weights)
- [Class Leading, Open-Source AI: Download Llama](https://developer.meta.com/ai/llama-downloads/)
- [Qwen3: Think Deeper, Act Faster - Alibaba Cloud](https://qwenlm.github.io)
- [Qwen3 Technical Report - ArXiv](https://arxiv.org)
- [Hugging Face Releases Qwen3 - huggingface.co](https://huggingface.co)
- [Qwen3 Arrives - DataCamp](https://datacamp.com)
- [DeepSeek V3.2 Release - GitHub](https://github.com/deepseek-ai/DeepSeek-V3.2)
- [DeepSeek V3.2 model card - Hugging Face](https://huggingface.co/deepseek-ai/DeepSeek-V3.2-Exp)
- [DeepSeek-V3.2 official documentation](https://deepseek-ai.github.io/DeepSeek-V3.2/)
- [DeepSeek-R1 Release 2025/01/20](https://api-docs.deepseek.com/news/news250120)
- [DeepSeek V3.2-Exp: The Quiet Rise of Sparse Attention](https://medium.com/@kalabouillon/deepseek-v3-2-exp-the-quiet-rise-of-sparse-attention-2025-11-6b5c3fbc04e9)

### 闭源前沿模型
- GPT-5 / o3 / o4-mini 模型族（2025-2026 时间线，由 OpenRouter / OpenAI 官方汇总）
- Claude 4.7 Opus（2026.02 发布）、Gemini 3 Pro（2025 末发布）
- 主流三强（Anthropic / Google / OpenAI）2026 分工

### Agent 范式演进
- Wooldridge & Jennings (1995) "Intelligent Agents: Theory and Practice" - Agent 工作定义原始论文
- Brooks (1991) "Intelligence Without Representation" - Reactive AI 经典
- ReAct 论文 (Yao et al., 2022.10) - LLM-based Agent 起点
- AutoGPT / BabyAGI / Reflexion (2023.03) - LLM-based Agent 浪潮

### MCP / A2A 协议
- [Model Context Protocol - Wikipedia](https://en.wikipedia.com/wiki/Model_Context_Protocol)
- [Model Context Protocol 中文百科](https://baike.baidu.com/item/MCP/65540620)
- [Announcing the Agent2Agent Protocol (A2A) - Google Developers Blog](https://developers.googleblog.com)
- [A2A GitHub Repository](https://github.com/google/A2A)
- [Google Cloud Blog: Announcing A2A](https://cloud.google.com)
- MCP 时间线：2024.11.25 发布 → 2025.03 OpenAI → 2025.04 Google → 2025.05 Microsoft → 2025.12.09 Linux Foundation AAIF
- A2A 时间线：2025.04.09 Google 发布；2026.04 v1.0

### SSM / Mamba / 混合架构
- [Mamba-Transformer Hybrids - Vinayak Ajyothi](https://vinayakajyothi.com/blog/papers-2026-03-12-mamba-transformer-hybrids)
- [Mamba-3, Jamba 1.5, and Nemotron-H - Best AI Web](https://www.bestaiweb.ai/mamba-3-jamba-1-5-and-nemotron-h-how-state-space-models-are-rewiring-long-context-ai-in-2026)
- [What Is a State Space Model - Best AI Web](https://www.bestaiweb.ai/what-is-a-state-space-model-and-how-selective-ssms-replace-quadratic-attention)
- [Mamba Wiki](https://aiwiki.ai/wiki/mamba)
- Jamba 1.0（2024.03）→ 1.5 Mini/Large → 1.6/1.7
- Nemotron-H 47B（NVIDIA, 2025）：92% 注意力层替换为 Mamba-2
- Falcon-H1（TII, 2025）：0.5B - 34B，262K 上下文
- Mamba-3（2026.03 ICLR）

---

## 9. 关键设计决策（summary for review）

1. **5 章而非 6 章** —— 把"协议层"作为单独一章（Ch9），把"Agent 五十年"作为单独一章（Ch8），把"现代变体"作为单独一章（Ch7），把"LLM 家族"作为 Ch6，把"工程组件预告"作为 Ch10。比 Part 1 多一章是因为 Part 2 叙事性更强、需要更多章节来组织历史脉络
2. **每章字数 5-6k 而非 3-4k** —— 历史叙事天然更长，但密度更低（少公式、少代码）
3. **代码极少** —— 只有 Ch10 一个最小 ReAct 循环示例；其余章节以图、表、叙事为主
4. **每个新概念 ≤ 3 个/段** —— 即使写"2026 现状"也不堆砌（MoE / SSM / 推理模型等各有专章，但每个章节内部严格控制密度）
5. **Ch9 MCP / A2A 作为桥梁章** —— 不展开协议实现细节，只讲起源与生态时间线；为 Part 4 / 5 做铺垫
6. **历史必联网核查** —— 论文年份、模型发布日期、协议时间线**全部**联网核对（已记录 8+ 次搜索结果）