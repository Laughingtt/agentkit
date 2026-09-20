# CLAUDE.md — Agent原理及实践 写作规范

> 本文件是 AI 助手（Claude Code 等）协作写本书时的"项目宪法"。
> 所有写作/重构/PR 必须遵循这里的约定。约定变更须在此文件更新。

## 一、项目目标

一本从原理到实践的中文技术书籍《Agent原理及实践》，以 Markdown 格式保存在本仓库，面向 **有编程基础但无 AI/ML 背景的初学者**。

全书拆为 6 个 Part：

| Part | 主题 |
|---|---|
| 1 | 大模型基础 |
| 2 | 大模型与 Agent 的演进 |
| 3 | Agent 原理 |
| 4 | Harness 工程 |
| 5 | Agent 功能实现 |
| 6 | 工业落地 |

每个 Part 独立走 `brainstorm → spec → plan → 写作` 流程。

### 各 Part 必须覆盖的子主题（参考 2026 主流 Agent 产品）

**基准产品**：Claude Code（Anthropic）、Pi Coding Agent（earendil-works）、OpenAI Codex CLI——三个主流 coding agent CLI。Parts 4-6 应以其设计选择为参照。

**协议栈（2026 已标准化）**：
- **MCP**（Model Context Protocol）—— 工具访问事实标准；2025.12 进入 Linux Foundation AAIF
- **A2A**（Agent-to-Agent）—— 多 Agent 协作标准；2026.04 v1.0，150+ 组织支持
- **x402 / AP2** —— 支付协议
- **AG-UI** —— UI 协议

| Part | 必须覆盖（2026 视角） |
|---|---|
| 1 大模型基础 | AI/ML/DL、Transformer、预训练、SFT、RLHF/对齐（DPO/GRPO/PRM） |
| 2 LLM 与 Agent 演进 | LLM 家族史（BERT/GPT/T5/LLaMA/Qwen/DeepSeek/Jamba/SSM混合…）；Agent 从 Symbolic → Reactive → Cognitive → LLM-based 的演进；MCP/A2A 起源 |
| 3 Agent 原理 | 认知架构（perception/memory/planning/action）；范式（ReAct/Reflexion/Plan-and-Execute/AutoGPT）；混合系统（rules + retriever + 小模型 + 中心 LLM） |
| 4 Harness 工程 | **MCP 客户端/服务端**、Streamable HTTP、A2A、上下文工程、记忆、hooks、permissions、sandbox；参照 Claude Code / Pi / Codex 的 harness 设计 |
| 5 Agent 功能实现 | tool calling、RAG、记忆、规划、多 Agent 协作、code execution；**MCP server 实现**、A2A 集成、x402 集成；**复现 Claude Code / Pi / Codex 的核心特性** |
| 6 工业落地 | 部署、**LLM-native 可观测性（Langfuse/Helicone/Arize Phoenix/OpenLLMetry）**、evaluation（LLM-as-judge、生产环境评测）、security/红队、**模型路由器（Martian/Not Diamond）**、cost control、speculative decoding、EU AI Act 合规、AIUC-1、真实案例 |

### 写作原则：以主流产品为素材，提炼通用要素

**Agent 相关 Part（3-6）的写作方法**：

1. **素材来源**：以 2026 主流产品（Claude Code、Pi、Codex CLI、Antigravity、Goose、Aider、OpenHands、Sourcegraph Amp 等）为观察对象
2. **提取模式**：从这些产品中识别**反复出现的设计决策**——不是某个产品独有的特性
3. **抽象要素**：把模式抽象成框架无关、模型无关、产品无关的通用概念
4. **避免的写法**：
   - 不写"Claude Code 怎么用" / "Pi 的 API 长啥样" 这种产品教程
   - 不引用某个产品的私有命名（如 Claude Code 的 Skill、Pi 的 Lazy Skills 这种产品术语）
   - 不假设读者只用某一个工具
5. **追求的目标**：读完 Part 3-6 后，读者能**独立设计一个 Agent harness / 实现一个 Agent / 评估一个生产 Agent**，而不依赖任何一个特定产品

**判别标准**：一个章节的内容，去掉后换一个产品来描述仍然成立 → 这是通用要素；换一个产品就不成立 → 这是产品特性（应剔除）。

## 二、语言与术语

- **正文语言：** 中文（简体）
- **技术术语首次出现：** `中文名（English term）` 格式，例如 `标记化（Tokenization）`、`自注意力（Self-Attention）`
- **后续使用：** 两种语言任选其一，保持章节内一致
- **代码、命令、文件名、变量名：** 严格英文

## 三、风格基调

- 教程式、朋友式语气；用"读者"、"我们"，**避免**"您"
- 段落 3-6 句为自然段，避免大段独白
- 直觉优先；允许比喻但节制，同一概念不复用同一比喻
- 不学究、不堆砌；尊重读者

## 四、数学与公式

- 直觉优先策略：靠文字 + 图 + 类比讲清概念
- 少量关键公式必须出现并解释：attention、loss、KL 散度等
- **不**做完整数学推导
- 公式用 LaTeX（`$...$` 行内、`$$...$$` 行间），GitHub 原生渲染

## 五、代码规范

- 语言：Python 优先（PyTorch / Transformers / NumPy）
- 位置：示意代码 inline 在 markdown；完整示例放 `code/part-N/`
- 文件命名：小写 + 下划线，例如 `train_mlp.py`
- 注释：中文，说明意图而非语法
- 可运行示例：文件头加注释 `# runnable: yes` + 顶部说明依赖
- 不可运行示意：文件头加注释 `# illustrative only`
- 代码块在 markdown 中指定语言：````python`
- 依赖统一在 `code/part-N/README.md` 列出

## 六、图表与 Mermaid

- Mermaid 直接内嵌在 markdown，GitHub 自动渲染
- 仅允许四种图类型：`graph` / `flowchart` / `sequenceDiagram` / `mindmap`
- 复杂关系用**表格**，不用 mermaid
- 节点文字简短（≤ 4 个字 / 词）

## 七、引用与延伸阅读

- 随文链接：参考 [Attention Is All You Need](https://arxiv.org/abs/1706.03762)
- 章末 **本章参考** 分三类：
  1. 必读论文
  2. 推荐博客 / 教程
  3. 视频 / 课程
- **不使用** markdown 脚注语法（GitHub 渲染不完美）

## 八、章节结构模板

每章必须包含：

```markdown
# ChX 章名

> 一句话简介（≤ 30 字）

## 本章目标

读完本章你应当能：
- [可验证能力 1]
- [可验证能力 2]
- ...

## 本章导览

[1 个 mermaid 架构总览图]

## X.1 子节标题

[正文]

## X.2 子节标题

[正文]

...

## 本章小结

- [要点 1]
- [要点 2]
- ...

## 本章参考

### 必读论文
- [标题](url)

### 推荐博客 / 教程
- [标题](url)

### 视频 / 课程
- [标题](url)
```

## 九、跨章与跨 Part 引用

- 章内子节互引：`参见 X.3`
- 跨 Part 引用：`(见 Part N ChM)`，**不**复制内容
- 上 Part 末尾用一节"小结 + 衔接"作为过渡，不展开下一 Part 主题

## 十、文件组织

```
agentkit/
├── README.md
├── CLAUDE.md
├── part-1-大模型基础/
│   ├── README.md
│   ├── ch01-*.md
│   ├── ...
│   └── ch05-*.md
├── part-2-.../
├── ...
└── code/
    └── part-N/
        ├── README.md
        └── *.py
```

## 十一、范围（Out-of-Scope）

- **Part 1 不涉及：** Agent 架构、Harness、工业落地、LLM 家族细节
- **Part 2-6 不重复：** AI/ML 基础、Transformer 训练数学推导
- **全书不涉及：** 数学严格证明、复现论文实验、最新模型逐个横评

## 十二、变更流程

- 修改本文件：直接 commit，commit message 加 `[claude-md]` 前缀
- 修改章节：正常 PR，commit message 写明章号
- 增加新 Part：先更新本文件，再走 brainstorm 流程

## 十三、写作流程规范

### 查证要求（联网搜索为强制项）

写作时遇到任何**不熟悉、有疑问、或不确定时效性**的技术点，必须**联网搜索**确认，禁止凭记忆或猜测。三条硬性目标：

1. **准确性** —— 模型训练数据可能过时或错误；论文标题、作者、年份、方法名必须 100% 正确
2. **真实性** —— 引用的链接、数据、benchmark 分数必须可验证
3. **实时性** —— 领域变化极快（尤其 Agent、LLM），2024 年的判断到 2026 可能已过时

### 触发联网搜索的场景

- 引用某篇论文前 → 确认标题、作者、年份、arXiv 链接
- 提及某个方法/技术 → 确认是否仍是 SOTA、是否有新版本
- 介绍某个产品/工具 → 确认其最新版本、最新功能
- 给出统计数据 → 确认来源与时效
- 使用某个 API/库 → 确认签名、参数、版本要求
- 对任何"我以为是 X，实际可能是 Y"存疑的概念 → 立即搜

### 写后审查（每章/Part 完成后必须执行）

1. **事实核查** —— 每个引用、每个数据、每个方法名都用搜索再次确认
2. **链接有效性** —— 每个 URL 都可访问（用 WebFetch 抽样检查）
3. **内部一致性** —— 术语、概念、数据前后一致；跨章引用都存在
4. **范围检查** —— 未混入 out-of-scope 内容
5. **风格检查** —— 符合本文件规定的语气、术语、格式

审查结果记录到对应 Part 的 report 文件（`.superpowers/sdd/task-N-report.md`），作为任务交付的一部分。