# Spec: Agent原理及实践 — Part 3 Agent 原理

**Date:** 2026-10-12
**Status:** Approved（结构与流程已定：6 章 Ch11-Ch16 / 一次成稿 + 每章易读性审查）
**Supersedes:** `2026-09-20-agent-principles-practice-part3-design.md`（v1）
**Project:** `agentkit`（中文技术书《Agent原理及实践》）
**Scope:** Part 3 of 6

---

## 0. v2 相对 v1 的变更摘要

| # | 变更 | 原因 |
|---|---|---|
| 1 | 5 章（Ch11-15，25-30k）→ **6 章（Ch11-16，52-60k）** | v1 遗漏 CLAUDE.md 硬性要求的「混合系统（rules + retriever + 小模型 + 中心 LLM）」；v1 字数低于 Part 1（44.5k）/ Part 2（58k）密度一个档 |
| 2 | **Ch15 混合系统独立成章** | 该主题是「单一大脑」与「多 Agent」之间的中间态，也是通向 Part 6 模型路由的桥，压成一节会写成名词罗列 |
| 3 | **Part 4 顺延 Ch17-22、Part 5 顺延 Ch23-28、Part 6 顺延 Ch29-34** | 章号链条连续性；同时必须逐行重核 Part 4 spec 的跨 Part 交叉引用表（见 §12，该表 5 行中有 3 行原本就指错） |
| 4 | 写作流程定为**一次成稿 + 每章易读性审查**（无 Phase R 重写阶段） | 一·甲 已把表达规范写进宪法，重写阶段的信息损耗不再值得；由每章 brief 的术语三件套清单前置保障 |
| 5 | 每章新增**「与 Part 2 的边界」**一节约束 | Part 2 Ch8/Ch9/Ch10 已交付认知四件套的历史、协议起源、积木清单与 ReAct 循环；Part 3 若重讲即越界 |
| 6 | 研究资料表**逐条重新核实**，3 处数字纠错、3 处引用张冠李戴作废 | v1 的引用表从未经过网络验证（见 §11） |
| 7 | mermaid 白名单改为**六种**（v1 写四种） | 对齐 CLAUDE.md 现行规定 |
| 8 | 新增「不重复 Part 2」与「产品中立」两条硬约束的具体判据 | v1 的 Ch14 大面积点名 LangGraph/AutoGen/CrewAI，与 CLAUDE.md「基准产品 + 概念定义位不出现产品名」冲突 |

---

## 1. Part 3 的任务与边界

**核心任务（CLAUDE.md 规定）**：讲清楚「一个 Agent 内部是什么在运转」——
认知架构的四个组件（感知 / 记忆 / 规划 / 行动）、三大经典范式（ReAct / Reflexion / Plan-and-Execute）、记忆机制的工程取舍、多 Agent 协作的设计选择、混合系统（规则 + 检索 + 小模型 + 中心 LLM）的真实形态。

**与已完成的 Part 1-2 的分工**：

| 已由 Part N 交付 | Part 3 的增量 |
|---|---|
| Part 1：Transformer / 注意力 / 预训练 / 微调 / 对齐 | 不重复任何训练侧内容 |
| Part 2 Ch8：认知四件套的**历史原料**（BDI / SOAR / ACT-R） | 只回顾一句"这四味药今天长什么样"，讲**运行时怎么协作** |
| Part 2 Ch9：MCP / A2A 的**起源与协议层** | 只在需要时一句预告（见 Part 4 Ch19） |
| Part 2 Ch10：五块**积木清单** + 三步 ReAct 循环 + 最小代码 | 讲**装配图**与**范式为什么有效/何时失效**，不重讲循环 |

**克制边界（不写）**：API 调用与 tool function 编码 → Part 5；harness 实现（hooks / permissions / sandbox / 上下文工程工艺）→ Part 4；评估 / 监控 / 成本 / 合规 → Part 6。

---

## 2. 目标读者与约束

- **读者**：会写代码、**没有** AI/ML 背景，已读完 Part 1-2
- **数学策略**：直觉优先；本 Part 几乎不用公式（关心"组件怎么拼"而非"梯度怎么算"）
- **语言**：中文简体；术语首次出现 `中文名（English term）`
- **总字数**：**~111k `wc -m`（6 章）**，均章约 18.5k。⚠️ **2026-10-12 用户裁定**：原验收线 52-60k **作废**——plan 把本 spec §5 的分章区间（Ch11 10-12k、Ch12 12-14k 等，单位均为 `wc -m`）**误整体翻倍**成 [20000,24000] 等，四个写手照此成稿，实测 104k（Ch11-15）+ Ch16 ≈ 111k。Part 3 是全书理论核心，篇幅显著长于 Part 1（44.0k）/ Part 2（58.1k）**属预期**，不再压缩。理由：CLAUDE.md 一·甲的术语三件套、worked-example、"没有它会怎样"起手本身就吃篇幅，砍到 60k 会与"可懂性优先"这条最高优先级原则正面冲突。
- **字数口径**：本 spec 全部字数一律指 **`wc -m` 口径**（与 Part 1/Part 2 plan 一致，约等于中文字数的 2 倍——markdown 语法、英文、空行都被计入）。换算成 Part README 里给读者的中文"字数"时取 `wc -m ÷ 2`
- **分章实测**（`wc -m`，2026-10-12 终稿）：Ch11 21144 / Ch12 25967 / Ch13 19573 / Ch14 19244 / Ch15 18050 / Ch16 收束章
- **风格**：教程式、朋友式；"读者"、"我们"；段落 3-6 句
- **2026 视角**：以 Claude Code / Pi / Codex CLI / Goose / Aider / OpenHands 等为观察对象，**只提炼通用要素**

---

## 3. 文件结构

```
agentkit/
├── README.md
├── CLAUDE.md
├── part-3-agent原理/
│   ├── README.md
│   ├── ch11-agent认知架构.md
│   ├── ch12-三大范式.md
│   ├── ch13-记忆机制.md
│   ├── ch14-多agent协作.md
│   ├── ch15-混合系统.md
│   └── ch16-小结与衔接.md
└── code/
    └── part-3/
        ├── README.md           # 明确：示意代码，Part 5 才给可运行工程示例
        ├── plan_execute.py     # Ch12 Plan-and-Execute 状态机示意
        ├── memory_store.py     # Ch13 记忆的写 / 读 / 忘 示意
        ├── multi_agent_min.py  # Ch14 两 Agent 协作示意
        └── cascade_router.py   # Ch15 级联路由示意
```

**不重复 Part 2 的 `react_loop.py`**——Part 2 Ch10 已交付该文件，Ch12 只回顾其机制。

---

## 4. 三条写作硬约束（写作 agent 必须逐条执行）

### 4.1 术语三件套清单前置

每章的 brief 必须携带一份**本章术语表**，每个术语给出：

| 字段 | 要求 |
|---|---|
| 白话一句话 | 不含任何其他未解释术语 |
| 生活类比 | 读者见过的场景 |
| 具体小例子 | 一个句子 / 一段 token / 一次调用 |

术语裸用（首次出现未完成三件套）= 审查不通过。**清单先行是本 Part 一次成稿路线的主要保险。**

### 4.2 不重复 Part 2

凡 Part 2 已交付的内容（认知四件套历史、协议起源、积木清单、三步循环、五类记忆的基础分类），一律以**一句回顾**起手，直接进入"为什么 / 什么时候"。判据：删掉 Part 3 某节后，Part 2 的对应内容不受影响，且本节讲不出一个新判断 → 该节越界。

### 4.3 产品中立

- **概念定义位**只说通用说法（如"项目说明文件"而非 `CLAUDE.md`、`AGENTS.md`）
- 产品名 / 文件名只出现在**例子位置**，且必须括注说明它是"某家产品的做法之一"
- 判据：删除所有产品名后，本节每一句仍然成立（CLAUDE.md 一·写作原则第 5 条）

---

## 5. 六章内容大纲

### Ch11 Agent 认知架构：四件套怎么协作（10-12k）

**本章问题**：Part 2 给了积木清单，本章给装配图——一个 Agent 跑起来时，这四块积木如何传递信息、在哪些点做决策。

| 节 | 内容 | 边界提示 |
|---|---|---|
| 11.1 | 单步解剖：一个 Agent 收到一句话后的 60 秒（问题驱动的失败现场起手） | 不重述 Part 2 Ch10 的积木清单 |
| 11.2 | **感知**：把异构输入（文字 / 图片 / 工具返回 / 环境事件）归一成模型读得懂的一种格式 | 举例用"翻译四种语言" |
| 11.3 | **行动**：工具调用的原子性与幂等；为什么"读操作"可以放心重试而"写操作"不能 | 副作用边界；Part 6 安全预告一句 |
| 11.4 | **记忆**：五分类（工作 / 情节 / 语义 / 程序性 / 长期）的**直觉**，明确"机制与工程取舍留 Ch13" | 只给分类直觉与一句话动机 |
| 11.5 | **规划**：什么时候该先拆计划、什么时候不该（子目标链、过度规划的代价） | 展开在 Ch12 |
| 11.6 | **四件套的协作循环**：一次完整循环 + 循环上的三个岔路口（继续 / 换招 / 求助人类） | Mermaid 主图 |
| 11.7 | 三代语言 Agent 的代差（CoALA 的 Generation A / B / C） | 一页篇幅，不展开成历史课 |
| 11.8 | 思维跃迁：从"调用一次 LLM"到"运行一个 Agent" | 收束 |

**Anchor**：`graph LR` 四件套数据流主图；`sequenceDiagram` 单步交互；表格（组件 / 职责 / 常见实现 / Part 4-5 衔接）。
**与 Part 2 边界**：Part 2 Ch8 的 BDI 回顾一句；Part 2 Ch10 的五块积木不重列。

---

### Ch12 三大范式：ReAct / Reflexion / Plan-and-Execute（12-14k）

**本章问题**：同一个循环，凭什么有的系统先想后做，有的边做边想，做错了还能改？三种范式的分界线在哪？

| 节 | 内容 | 边界提示 |
|---|---|---|
| 12.1 | **ReAct 为什么有效**：想-做-看如何把"猜"换成"查"；可解释性与抗幻觉的机制 | 三步循环 Part 2 已给，此处**只讲机制与代价**；`react_loop.py` 只回顾 |
| 12.1.3 | ReAct 的代价：token 成本随轮次线性涨、长链路漂移、什么时候会绕圈打转 | 新内容，v1 缺 |
| 12.2 | **Reflexion**：把失败写进下一轮的开场白——"反思"是留痕不是重训参数 | 与 ReAct 的区别：当下推理 vs 跨轮留痕 |
| 12.3 | **Plan-and-Execute 谱系**：BabyAGI / AutoGPT 起源 → Planner / Executor / Replanner → ReWOO（解耦推理与观察）与 LLMCompiler（并行化） | 两个子范式的已核实数字见 §11 |
| 12.4 | 三范式对比表（假设 / 步骤 / 优势 / 局限 / 典型场景） | |
| 12.5 | 选择指南：拿到一个任务怎么选（决策树） | |
| 12.6 | 两个常见误用：把 ReAct 当银弹；把"反思"误当成"训练" | v1 缺，本书读者极易混淆 |

**Anchor**：`sequenceDiagram`（ReAct 三步）+ `graph TD`（Plan-and-Execute 状态机）+ 两张对比表 + `plan_execute.py`。

---

### Ch13 记忆机制（9-11k）

**本章问题**：上下文窗口有限，Agent 怎么记住过去？更麻烦的是——它该记住什么、忘掉什么？

| 节 | 内容 |
|---|---|
| 13.1 | 窗口有限这件事本身，逼出了什么设计（问题驱动起手） |
| 13.2 | 五类记忆 → 工程载体映射（工作记忆 / 情节 / 语义 / 程序性 / 长期持久） |
| 13.3 | **三个决策**：写什么、何时读、何时忘（衰减评分、容量上限、定期合并） |
| 13.4 | MemGPT：把上下文当虚拟内存分页（主上下文 + 外部上下文 + 自驱换页） |
| 13.5 | **记忆是攻击面**：写进去的东西下一轮会被当指令读（预告 Part 6 红队） |
| 13.6 | Part 4 衔接：harness 的上下文工程如何把记忆做成产品能力（→ Part 4 Ch20） |

**边界**：harness 的压缩 / 裁剪实现工艺属 Part 4 Ch20，本章只讲机制与取舍。
**Anchor**：`mindmap` 五类记忆载体 + 表格（五类 / 实现 / 失效模式）+ `memory_store.py`。

---

### Ch14 多 Agent 协作（9-11k）

**本章问题**：什么时候一个人干完就行，什么时候要分给多人？多 Agent 的代价是什么？

| 节 | 内容 |
|---|---|
| 14.1 | **先反着讲**：单 Agent 优先的四种情形（任务可线性分解、上下文可控、调试要求高、预算紧） |
| 14.2 | 多 Agent 的三个真实动机：专精化、上下文隔离、并行 |
| 14.3 | 四种协作拓扑：流水线 / 层级 / 群聊 / 群体，各配一个生活类比 |
| 14.4 | **误差放大**：为什么"加更多 Agent"不等于更强（失败分类法：指令理解、角色混淆、消息丢失、过早终止等） |
| 14.5 | 工程取舍：共享状态、上下文传递方式、身份与权限（A2A 协议细节 → Part 4 Ch19） |
| 14.6 | 最小两 Agent 示例（`multi_agent_min.py`） |

**边界**：框架产品（LangGraph / AutoGen / CrewAI 等）只在例子位点名，且不给版本与维护状态断言（时效性强，留 Task 6 核实或不写）。
**Anchor**：`graph TD` 四种拓扑 + `sequenceDiagram` 两 Agent + 两张表 + `multi_agent_min.py`。

---

### Ch15 混合系统：规则 + 检索 + 小模型 + 中心 LLM（9-11k）【v2 新增】

**本章问题**：不是所有活都该由最贵的大脑来干。一个"好"的 Agent 系统，往往不是一个大模型，而是几类部件各司其职。

| 节 | 内容 |
|---|---|
| 15.1 | 问题现场：一次典型的日常任务里，80% 的判断其实很便宜 |
| 15.2 | **四个部件各管什么**：规则守边界（确定、必须每次执行）／检索供事实（不在参数里的知识）／小模型干粗活（分类、抽取、改写）／中心 LLM 兜底复杂判断 |
| 15.3 | **路由**：什么时候升级到中心 LLM（级联：便宜模型先试，不够格再升级；升级信号有哪些） |
| 15.4 | 收益账与失败模式（成本 / 延迟 / 稳定性 / 可调试性）——**两个方向都要讲** |
| 15.5 | 通往 Part 6：模型路由、cost control 与 speculative decoding 的预告 |

**Anchor**：`graph TD` 四部件分工 + `stateDiagram-v2` 级联路由状态迁移（退出条件 = 升级信号）+ 表格（部件 / 擅长 / 失效模式）+ `cascade_router.py`。

---

### Ch16 收束与 Part 4 衔接（3-4k）

- 16.1 一张装配图回顾（四件套 + 三范式 + 五记忆 + 系统形态）
- 16.2 一张决策图：拿到任务先问三个问题（要多大的脑？要记多少东西？要不要拆给别人？）
- 16.3 关键陷阱：多 Agent 万能解、ReAct 银弹、记忆越多越好
- 16.4 Part 4 衔接：组件已清楚，但组件本身不会组网——上下文工程、工具协议、权限与沙箱是 Part 4 的正题

**Anchor**：`graph TD` Part 3 → Part 4 → Part 5 概念衔接。

---

## 6. 代码示例规划

Part 3 代码量显著少于 Part 1，目标「读完立刻懂概念」，不追求工程完整。

| 文件 | 用途 | 章 | 规模 |
|---|---|---|---|
| `plan_execute.py` | Planner / Executor / Replanner 状态机（纯 Python dict 模拟 State） | Ch12 | ≤ 80 行 |
| `memory_store.py` | 记忆的写入 / 检索 / 衰减三段示意 | Ch13 | ≤ 80 行 |
| `multi_agent_min.py` | researcher + writer 两 Agent 消息传递 | Ch14 | ≤ 80 行 |
| `cascade_router.py` | 小模型先试 → 不够格升级中心 LLM | Ch15 | ≤ 80 行 |
| `README.md` | 明确全部为示意代码；Part 5 才给可运行工程示例 | — | — |

约束：
- 文件头 `# illustrative only`
- 中文注释，只说意图
- **不依赖** LangChain / LangGraph 等外部框架（避免把外部 API 当成"概念本身"）
- **零执行**（用户长期禁令：本书所有代码不运行）。Task 6 只做**静态推演**，推演结果须与章节描述逐字一致

---

## 7. 写作与审查约定

- 章模板：标题 → 一句话简介 → 本章目标 → 本章导览 → 子节 → 本章小结 → 本章参考
- **mermaid 六种**：`graph` / `flowchart` / `sequenceDiagram` / `mindmap` / `timeline` / `stateDiagram-v2`
- 章末参考三类：必读论文 / 推荐博客·教程 / 视频·课程（无论文的章可写「必读」，CLAUDE.md §七 已允许）
- 跨章 `参见 X.3`；跨 Part `(见 Part N ChM)`，不复制内容
- **每节开头先演一次"没有它会怎样"**（Part 2 Phase R 验证有效的写法）

### 审查顺序（CLAUDE.md 一·甲）

| 阶段 | 审什么 | 不审什么 |
|---|---|---|
| 每章写完 | **仅易读性**：一·甲 检查清单、术语三件套是否到位、能否一句话转述、类比是否贴切 | 事实、链接、代码运行 |
| Task 6 终审 | 事实核查、链接有效性、字数、内部一致性、范围、风格、代码静态推演 | — |

**Task 6 的网络降级预案**（本环境已实测）：WebSearch 返回空、WebFetch 域名校验失败、arxiv API 会限流。可用通道 = `arxiv.org/abs/<id>`（逐条 sleep）、`api.crossref.org`、`api.github.com`、`raw.githubusercontent.com`、`linuxfoundation.org/press`、`anthropic.com`、`qwenlm.github.io`、`modelcontextprotocol.io`。不可达项一律进「浏览器抽验清单」，**不得凭印象改写事实**。

---

## 8. 完成度与验收标准

**单章**：子节齐全；本章目标 / 小结 / 参考三件套齐；≥1 mermaid + ≥1 表格；字数落在本 spec 给的区间；术语三件套清单 100% 落地；每节有"没有它会怎样"起手。

**Part 3 整体**：
- 6 章写完，总字数 52-60k
- `part-3-agent原理/README.md` 含目录与一句话简介
- 顶层 `README.md` 标 Part 3 ✅ 已发布（Task 6 时翻转）
- 四个示意代码文件存在于 `code/part-3/`，均 `# illustrative only`
- Task 6 终审通过（事实 / 链接 / 字数 / 一致性 / 范围 / 风格 / 静态推演）

**自查清单**：无 placeholder；章间术语与数据一致；不混入 Part 1/2/4/5/6 范围；产品名删除后章节仍成立。

---

## 9. 显式 Out-of-Scope

Transformer 训练数学 → Part 1；LLM 家族史与 Agent 五十年史 → Part 2；harness 实现（hooks / permissions / sandbox / 上下文工程工艺）→ Part 4；tool calling / RAG / MCP server 编码 → Part 5；监控 / 评测 / 成本 / 合规 → Part 6；数学证明、模型逐个横评。

---

## 10. 后续流程

1. 本 spec 经用户审阅通过
2. `superpowers:writing-plans` 输出 Part 3 实施 plan（每章一个任务，含术语三件套清单的产出方式）
3. 按 plan 执行：每章写作 → 易读性审查 → 定点修复 → commit
4. Task 6 终审 → README 翻转 → commit + push

---

## 11. 研究资料（已逐条网络核实，2026-10-12）

### 11.1 arXiv 论文（标题经 `arxiv.org/abs/<id>` 逐条核对，7/7 吻合）

| arXiv ID | 标题（逐字） | 用途 |
|---|---|---|
| 2210.03629 | ReAct: Synergizing Reasoning and Acting in Language Models | Ch12 ReAct |
| 2303.11366 | Reflexion: Language Agents with Verbal Reinforcement Learning | Ch12 Reflexion |
| 2305.18323 | ReWOO: Decoupling Reasoning from Observations for Efficient Augmented Language Models | Ch12 ReWOO |
| 2312.04511 | An LLM Compiler for Parallel Function Calling | Ch12 LLMCompiler |
| 2310.08560 | MemGPT: Towards LLMs as Operating Systems | Ch13 |
| 2309.02427 | Cognitive Architectures for Language Agents（CoALA） | Ch11 |
| 2503.13657 | Why Do Multi-Agent LLM Systems Fail? | Ch14 失败模式 |

### 11.2 已核实的数字（**写作 agent 可直接使用**）

| 数字 | 出处 | 原文依据 |
|---|---|---|
| ReAct 在 ALFWorld / WebShop 上绝对成功率 +34% / +10% | 2210.03629 摘要 | "outperforms ... by an absolute success rate of 34% and 10% respectively, while being prompted with only one or two in-context examples" |
| ReAct 抑制幻觉与误差传播 | 2210.03629 摘要 | "overcomes issues of hallucination and error propagation ... interacting with a simple Wikipedia API" |
| ReWOO token 效率 5×、HotpotQA +4% 准确率 | 2305.18323 摘要 | "achieves 5x token efficiency and 4% accuracy improvement on HotpotQA" |
| ReWOO 把 175B GPT3.5 的推理能力卸载进 7B LLaMA | 2305.18323 摘要 | "offloads reasoning ability from 175B GPT3.5 into 7B LLaMA" |
| LLMCompiler 延迟最高 3.7×、成本最高省 6.7×、准确率最高 ~9% | 2312.04511 摘要 | "consistent latency speedup of up to 3.7x, cost savings of up to 6.7x, and accuracy improvement of up to ~9% compared to ReAct" |
| LLMCompiler 三组件：Planner / Task Fetching Unit / Executor | 2312.04511 摘要 | 三组件命名逐字 |

ReAct 项目页：`https://react-lm.github.io`（摘要中给出）；LLMCompiler 代码：`https://github.com/SqueezeAILab/LLMCompiler`（摘要中给出）。

### 11.3 v1 遗留错误（**禁止再用**）

| v1 写法 | 实际 |
|---|---|
| `arxiv.org/abs/2503.09957` = MAST 失败分类法 | 该 ID 实为《Using Causal Inference to Explore Government Policy Impact on Computer Usage》——**张冠李戴** |
| `arxiv.org/abs/2509.15307` = Why Do Multi-Agent LLM Systems Fail to Improve at Scale? | 该 ID 实为一篇天体物理论文——**张冠李戴** |
| `2502.10679`（曾作为上面第一篇的候选修正） | 实为正则化共形热流数学论文——**作废**；正确引用是 `2503.13657`（见 11.1） |
| ReWOO「调用次数减少 ~40%」 | 实为 **token 效率 5×**（见 11.2） |
| LLMCompiler「并行化提速 ~3.6×」 | 实为 **最高 3.7×**（见 11.2） |
| ReAct「HotpotQA 幻觉 56% → 6%」 | **摘要未含此数**（该数字源自论文正文的 CoT 对比表）。章节如需引用，必须先核对正文，否则改用摘要级的表述（用已核实的 ALFWorld/WebShop 数字） |

### 11.4 待 Task 6 核实的链接与断言

- `https://blog.langchain.com/plan-and-execute/`、`langchain-ai.github.io/langgraph/...`（langchain-ai.github.io 域名近年疑有迁移，**引用前先测**；不通则删该链接，不凭印象替换）
- `https://research.memgpt.ai`（MemGPT 项目页）
- AutoGen / CrewAI / LangGraph 的 2026 年维护状态——**除非核实，否则不写**
- v1 引用的 `moltbook.com` 对比文——来源可疑，**弃用**

---

## 12. 连锁修改（Part 4 / Part 5 / Part 6 spec 章号顺延）

| Part | v1 章号 | v2 章号 | 影响面 |
|---|---|---|---|
| Part 3 | Ch11-15 | **Ch11-16**（+Ch15 混合系统、Ch16 收束） | 本 spec |
| Part 4 | Ch16-21 | **Ch17-22** | ~90 处子节号 + 跨 Part 引用表 5 行 |
| Part 5 | Ch22-27 | **Ch23-28** | ~80 处子节号 + 文件树注释 |
| Part 6 | Ch28-33 | **Ch29-34** | 6 个章标题 + 内部引用 |

**必须逐行重核的既有错误**（Part 4 spec 跨 Part 交叉引用表，5 行中 3 行原本就指错，与顺延无关）：

| 行内容 | 原写 | 顺延后应为 | 判定 |
|---|---|---|---|
| MCP 是怎么进入 Agent 循环的 | 17.11 → Part 5 Ch23（tool calling） | 18.11 → Part 5 **Ch23** | ✓ 恰好对上 |
| A2A 任务的并发模式 | 18.4 → Part 5 Ch26（多 Agent 协作） | 19.4 → Part 5 **Ch25** | ✗ 原本就错（多 Agent 是 Ch24→25，不是 Ch26） |
| 上下文压缩的具体实现 | 19.5 → Part 5 Ch24（记忆） | 20.5 → Part 5 **Ch24** | ✓ 恰好对上 |
| sandbox 的 OS 原语 | 20.7 → Part 6 Ch28（安全/红队） | 21.7 → Part 6 **Ch31** | ✗ 原本就错（安全/红队是 Ch30→31，Ch28 是可观测性） |
| 协议栈全景图 | 21.2 → Part 5 Ch22（协议接入） | 22.2 → Part 5 **Ch27** | ✗ 原本就错（协议集成是 Ch26→27） |

**改写时的陷阱**：这些 spec 里混有 `25.09`、`26.07`、`24.11` 这类**版本日期**（如 "2025.09"）。任何正则必须带"数字前无数字"守卫（`(?<![\d.])`），否则会把日期改坏。**禁止裸 `sed s/25\./26\./g` 之类操作。**

**Part 3 中引用后文章号时**：Part 4 = Ch17-22、Part 5 = Ch23-28、Part 6 = Ch29-34（以顺延后的各 Part spec 为准）。

---

## 13. 关键决策点（写给 reviewer）

1. **6 章而非 5 章**：为让「混合系统」有独立位置（CLAUDE.md 硬性要求），代价是 Part 4/5/6 章号全部顺延，且必须逐行重核三份 spec 的交叉引用（见 §12）。
2. **一次成稿而非 Phase R 两段式**：一·甲 已把表达规范前置到宪法 + 每章 brief 强制携带术语三件套清单；重写阶段的信息损耗（返工、被重写的观点丢失）不再划算。
3. **Ch12 只讲范式的机制与失效，不重讲循环**：三步循环与 `react_loop.py` 是 Part 2 的交付物。
4. **Ch14 先反着讲**（单 Agent 优先），因为读者最常见的误用就是无脑上多 Agent。
5. **Ch15 用 `stateDiagram-v2`**：级联路由的本质是状态迁移（够格 → 交付；不够格 → 升级），比流程图更贴切；这也是六种图型里此前从未用过的一种，正好验证规范。
6. **代码零执行**：本书所有示例代码不运行，Task 6 只做静态推演。
7. **不写框架维护状态**：AutoGen / CrewAI 等的版本与维护状态时效性极强，核实不到就不写。