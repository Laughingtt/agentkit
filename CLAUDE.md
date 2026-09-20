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

### 各 Part 必须覆盖的子主题（参考 2025 主流 Agent 书目录）

| Part | 必须覆盖 |
|---|---|
| 1 大模型基础 | AI/ML/DL、Transformer、预训练、SFT、RLHF、对齐 |
| 2 LLM 与 Agent 演进 | LLM 家族史（BERT/GPT/T5/LLaMA/Qwen/DeepSeek…）；Agent 从 Symbolic → Reactive → Cognitive → LLM-based 的演进 |
| 3 Agent 原理 | 认知架构（perception/memory/planning/action）；范式（ReAct/Reflexion/Plan-and-Execute/AutoGPT） |
| 4 Harness 工程 | 工具/MCP（Model Context Protocol）、sandbox、上下文工程、记忆、hooks、permissions |
| 5 Agent 功能实现 | tool calling、RAG、记忆、规划、多 Agent 协作、code execution、MCP 集成 |
| 6 工业落地 | 部署、可观测性、evaluation（LLM-as-judge、benchmark）、security/红队、cost control、真实案例 |

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