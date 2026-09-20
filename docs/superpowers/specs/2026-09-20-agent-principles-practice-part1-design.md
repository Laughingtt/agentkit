# Spec: Agent原理及实践 — Part 1 大模型基础

**Date:** 2026-09-20
**Status:** Draft (pending user review)
**Project:** `agentkit` (Chinese technical book on Agent principles and practice)
**Scope:** Part 1 of 6

---

## 1. 项目背景与分解策略

本书《Agent原理及实践》面向**有编程基础但无 AI/ML 背景的初学者**，以中文 Markdown 写成。整体拆为 6 个 Part，每个 Part 独立走 `brainstorm → spec → plan → 写作` 流程：

| Part | 主题 |
|---|---|
| 1 | 大模型基础 ← **本 spec** |
| 2 | 大模型与 Agent 的演进 |
| 3 | Agent 原理 |
| 4 | Harness 工程 |
| 5 | Agent 功能实现 |
| 6 | 工业落地 |

本 spec 只覆盖 **Part 1**。其余 Part 在各自 spec 中设计。

---

## 2. 目标读者与约束

- **读者：** 大学本科以上、会写代码（至少一门主流语言）、但**没有** AI/ML 背景
- **数学策略：** 直觉优先，最少公式。关键公式（attention、loss、KL）必须出现并解释，但**不**做完整数学推导
- **代码：** 少量示意代码 inline 在 markdown 中；带 import 的较完整示例放在 `code/part-1/`
- **语言：** 中文（简体）；技术术语首次出现用 `中文名（English term）` 格式
- **总字数：** 18-22k 字（5 章）
- **风格：** 教程式、朋友式；"读者"、"我们"；段落 3-6 句

---

## 3. 文件结构

```
agentkit/
├── README.md                   # 书籍总目录（已有占位，需扩充）
├── CLAUDE.md                   # 写作规范（已写入）
├── part-1-大模型基础/
│   ├── README.md               # Part 1 目录与简介
│   ├── ch01-ai-ml-dl-概览.md
│   ├── ch02-神经网络与深度学习.md
│   ├── ch03-transformer与注意力.md
│   ├── ch04-预训练与微调.md
│   └── ch05-rlhf与对齐.md
└── code/
    └── part-1/
        ├── README.md           # 依赖说明（PyTorch ≥ 2.0, Transformers ≥ 4.30）
        ├── train_mlp.py        # Ch2 示例
        ├── attention.py        # Ch3 示例
        └── tokenize_demo.py    # Ch4 示例
```

---

## 4. Part 1 五章内容大纲

### Ch1 AI / ML / DL 概览（~3-4k 字）

读完应能描述 LLM 在 AI 整体图谱中的位置。

- 1.1 什么是 AI、ML、DL（定义与谱系）
- 1.2 三大范式：符号主义 / 连接主义 / 统计学习
- 1.3 三大学习划分：监督 / 无监督 / 强化
- 1.4 深度学习为什么崛起：算力 + 数据 + 算法 + 任务
- 1.5 LLM 在 AI 整体图谱中的位置
- 1.6 本书阅读路线

**Anchor 示例：**
- Mermaid AI 谱系图（含 AI / ML / DL / 神经网络 / LLM / VLM 等节点）
- 表格：三种学习方式对比（监督 / 无监督 / 强化）

---

### Ch2 神经网络与深度学习基础（~3-4k 字）

读完应能口述一个简单神经网络的训练流程。

- 2.1 神经元与多层感知机（MLP）
- 2.2 激活函数：ReLU / GELU / Softmax
- 2.3 反向传播的直觉
- 2.4 损失函数：交叉熵 / MSE
- 2.5 优化器演进：SGD → Adam → AdamW
- 2.6 正则化：Dropout / Weight Decay
- 2.7 归一化：BatchNorm / LayerNorm
- 2.8 一个最小的 PyTorch 训练示例

**Anchor 示例：**
- Mermaid MLP 架构图
- 代码：`code/part-1/train_mlp.py`（拟合一个简单函数）

---

### Ch3 Transformer 与注意力（~4.5-5.5k 字）

读完应能解释 self-attention 的工作原理，并描述一个 Transformer block 的结构。

- 3.1 为什么需要新架构：RNN / LSTM 的局限
- 3.2 Self-attention 的直觉
- 3.3 Q/K/V 与 attention 公式（关键公式）
- 3.4 多头注意力
- 3.5 位置编码：Sinusoidal → RoPE → ALiBi
- 3.6 Transformer block：LN → Attention → FFN → 残差
- 3.7 Decoder-only vs Encoder-Decoder
- 3.8 KV cache 直观理解（含 KV cache 量化的提示）
- 3.9 一个最小 attention 示例
- 3.10 **MoE 与现代 Transformer 变体**（新增）
  - 什么是 MoE：稀疏激活的直觉
  - 为什么 MoE：参数 vs 推理成本的解耦
  - 现代组件速览：RMSNorm（去掉均值中心）、SwiGLU（门控 FFN）、GQA（共享 KV 折中）
  - 定位：当代 SOTA 标配，Part 1 只给直觉，Part 2 展开

**Anchor 示例：**
- Mermaid Transformer block 架构图
- 代码：`code/part-1/attention.py`（手写 scaled dot-product attention）

---

### Ch4 预训练与微调（~4-5k 字）

读完应能描述 LLM 从数据到可用模型的全流程。

- 4.1 预训练目标：next-token prediction
- 4.2 数据：清洗 / 去重 / 配比
- 4.3 Tokenizer：BPE / WordPiece / SentencePiece
- 4.4 训练基础设施：GPU 集群与并行（DP/TP/PP）
- 4.5 Scaling Law
- 4.6 SFT 数据构造
- 4.7 LoRA / QLoRA 参数高效微调（含 Distillation 一句话提示）
- 4.8 灾难性遗忘
- 4.9 一个 tokenizer 示例

**Anchor 示例：**
- Mermaid 训练流程图（数据 → Tokenize → 预训练 → SFT → 对齐）
- 代码：`code/part-1/tokenize_demo.py`（用 transformers 库 tokenizer）

---

### Ch5 RLHF 与对齐（~4-5k 字）

读完应能解释 RLHF 三步曲与 DPO 的核心思想。

- 5.1 为什么要对齐
- 5.2 RLHF 三步：SFT → RM → PPO（直觉讲法）
- 5.3 奖励模型（Reward Model）
- 5.4 PPO 在 LLM 中的应用（直觉）
- 5.5 DPO：直接偏好优化
- 5.6 其他对齐方法：Constitutional AI / RLAIF
- 5.7 安全与红队
- 5.8 **推理模型与思维链**（新增）
  - o1 / R1 风格："思考更久答更好"
  - 思维链（CoT）是什么
  - 推理时计算 vs 训练时计算
- 5.9 **多模态与延伸**（新增）
  - 多模态是什么：图像 / 音频 / 视频 token
  - 两种思路：CLIP-style 对齐 vs Native Multimodal
  - 多模态对齐的特殊挑战
- 5.10 Part 1 小结 + 与 Part 2 衔接

**Anchor 示例：**
- Mermaid RLHF 循环图（SFT → RM → PPO 反馈环）
- 表格：对齐方法对比（RLHF / DPO / Constitutional AI / RLAIF）

---

## 5. 写作约定（简版，详见 CLAUDE.md）

- 每章模板：标题 → 一句话简介 → 本章目标（3-5 条 bullet）→ 本章导览（mermaid 总览图）→ 子节 → 本章小结 → 本章参考
- Mermaid 仅用四种图：`graph` / `flowchart` / `sequenceDiagram` / `mindmap`
- 复杂关系用表格，不堆 mermaid
- 引用：随文 markdown 链接 + 章末 "本章参考"（分必读论文 / 推荐博客 / 视频课程 三类）
- 代码：中文注释；可运行示例文件头加 `# runnable: yes`
- 跨章引用 `参见 X.3`；跨 Part `(见 Part N ChM)`，**不**复制内容

---

## 6. 完成度与验收标准

### 单章完成标准

- 子节齐全，与大纲一致
- 含本章目标、小结、本章参考
- 含至少 1 个 mermaid + 1 个表格
- 字数在 ±20% 区间内
- 关键概念全覆盖（每章 5-8 个）
- 至少 1 个代码示例（Ch1、Ch5 可豁免示意性代码）

### Part 1 整体验收

- 5 章全部写完
- 总字数 18-22k
- `part-1-大模型基础/README.md` 含目录与一句话简介
- `README.md` 出现 Part 1，标记为 "已发布"
- 所有 mermaid 在 GitHub 渲染无语法错误
- 所有 Python 代码片段对应文件存在于 `code/part-1/`
- 自查通过（placeholder / 内部一致性 / 范围 / 歧义）

### 自查清单

1. **Placeholder 扫描：** 无 TBD / TODO / 占位文本
2. **内部一致性：** 章间不矛盾（术语、概念、数据一致）
3. **范围检查：** 不混入 Part 2-6 内容（agent / harness / 工业落地）
4. **歧义检查：** 每个子节要求无歧义

---

## 7. 显式 Out-of-Scope（Part 1 不涉及）

- Agent 定义、架构、范式 → Part 3
- Harness 设计 → Part 4
- Agent 代码实现 → Part 5
- 工业案例 / 部署 / 监控 → Part 6
- LLM 家族演进史细节（BERT / GPT / T5 / LLaMA 等逐个横评）→ Part 2
- 现代变体详细技术（MoE / GQA / 长上下文 / 量化深入）→ Part 2
- 数学严格证明

---

## 8. 后续流程

1. 本 spec 经用户审阅通过后，进入 `superpowers:writing-plans` 流程
2. writing-plans 输出 Part 1 的实现 plan
3. plan 完成后进入实际写作阶段
4. Part 1 完成后再启动 Part 2 的 brainstorm