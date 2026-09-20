# Ch3 Transformer 与注意力

> 一句话简介：从 RNN 的局限讲起，到 self-attention 的直觉，再到 Transformer block 的标准结构，为理解现代 LLM 打地基。

## 本章目标

读完本章你应当能：
- 解释 RNN / LSTM 在长序列上的局限
- 直观描述 self-attention 的工作机制
- 写出 scaled dot-product attention 的公式并解释每一项
- 说出多头注意力的作用
- 解释位置编码的必要性，并比较 Sinusoidal / RoPE / ALiBi
- 画出一个标准 Transformer block 的结构
- 区分 Decoder-only / Encoder-only / Encoder-Decoder 三种架构
- 描述 KV cache 的作用
- 简述 MoE 的稀疏激活思想

## 本章导览

```mermaid
graph TD
    A[输入 token] --> B[Token Embedding]
    B --> C[+ 位置编码]
    C --> D[Transformer Block × N]
    D --> E[输出 Logits]
    subgraph "一个 Transformer Block"
        F[LayerNorm] --> G[Multi-Head Self-Attention]
        G --> H[残差连接]
        H --> I[LayerNorm]
        I --> J[FFN]
        J --> K[残差连接]
    end
```

## 3.1 为什么需要新架构

在 Transformer 出现之前（2017 年之前），处理序列数据的主流架构是 RNN 及其升级版 LSTM / GRU。它们的核心思想是**按时间步递归**：第 $t$ 步的隐藏状态 $h_t$ 由当前输入 $x_t$ 和上一步的隐藏状态 $h_{t-1}$ 计算得到，于是信息像"接力棒"一样沿着时间传递。理论上，这种结构可以捕捉任意长距离的依赖。

但实践暴露了三个棘手问题。**第一，并行性差**。$h_t$ 依赖 $h_{t-1}$，第 $t$ 步必须等第 $t-1$ 步算完，整个序列必须串行计算——在 GPU 这种天生适合并行的硬件上，RNN 的训练效率非常低。**第二，长距离依赖仍然难学**。虽然 LSTM 的门控机制（输入门、遗忘门、输出门）一定程度上缓解了梯度消失，但当序列长度达到几百上千个 token 时，早期 token 的信息仍然会被稀释，模型依然难以捕捉远距离关系。**第三，难以扩展**。RNN 的隐藏状态维度是固定的，无论输入多长，都得压缩进同一个向量；这给信息容量设了硬上限。

正是为了解决这三个问题，Vaswani 等人在 2017 年提出了 **Transformer**（参见本章参考）。它抛弃了递归结构，改用一种叫 **self-attention（自注意力）** 的机制，让序列里**任意两个位置**直接"对话"。这一改动带来两个革命性收益：长距离依赖一步到位（信息传递的路径长度恒定为 1），并且整个序列可以**完全并行**计算（不再有 $h_{t-1}$ → $h_t$ 的依赖）。于是我们看到了今天所有主流 LLM——GPT、LLaMA、Qwen、DeepSeek——清一色都建立在 Transformer 之上。

## 3.2 Self-attention 的直觉

Self-attention 的核心想法可以用一句话概括：**序列里每个位置都要"看一看"其它所有位置，根据相关性重新组合自己的表示**。

设想你在读一个句子："小明借了小王的书，**他**说下周还。" 这里的"他"指代的是谁？人脑会下意识回到上文找"小明"或"小王"，根据语义关系推断。Self-attention 就是让模型做同样的事——它让"他"这个位置的 token 去"询问"句子里所有 token（包括自己），每个被询问的位置给出一个相关性分数（也叫做注意力权重），然后"他"把自己的新表示定义为这些位置的加权平均。

用稍微正式一点的语言：给定一个长度为 $L$ 的序列，self-attention 把每个位置 $i$ 变成一个**新的向量**，这个向量的每一位都是从其它位置"借"来的信息，权重由位置 $i$ 和位置 $j$ 的相关性决定。直观上，这就像一个"软检索"——模型不是从记忆里硬挑一个 token，而是软性地、按权重融合它们。

这种机制有两个非常优雅的性质。**第一，路径长度恒定**。任意两个位置之间只需要一次"询问"就能交换信息，不像 RNN 那样要沿着链一步步传递，序列再长也不会被稀释。**第二，可解释性强**。我们可视化训练后的注意力权重，常常能看到句法结构（主谓关系、指代关系）自动浮现——这在 RNN 时代是不可想象的。Ch4 我们会看到，Transformer 的"理解力"很大程度上就建立在这种"全局可访问 + 软加权"上。

## 3.3 Q/K/V 与 attention 公式

Self-attention 在工程上通过三个矩阵——**Query（查询）、Key（键）、Value（值）**——来实现。这个三元组的命名借鉴了信息检索：你想找东西，先用一个 query 去和所有 key 比对相关性，再按相关性从对应的 value 里取内容。

具体地，给定输入 $X$（形状为 $(L, d)$），我们用三组可学习权重矩阵 $W^Q, W^K, W^V$ 分别做线性投影，得到：

$$Q = X W^Q, \quad K = X W^K, \quad V = X W^V$$

然后套用著名的 **scaled dot-product attention** 公式：

$$\text{Attention}(Q, K, V) = \text{softmax}\!\left(\frac{Q K^\top}{\sqrt{d_k}}\right) V$$

我们逐项拆解：

- **$Q K^\top$**：query 和 key 做矩阵乘，得到形状 $(L, L)$ 的打分矩阵，元素 $(i, j)$ 表示"位置 $i$ 的 query 和位置 $j$ 的 key 有多相关"。相关度越高，分数越大。
- **$\sqrt{d_k}$**：缩放因子。$d_k$ 是 key 的维度。当 $d_k$ 比较大时，$Q K^\top$ 的数值方差也会变大，softmax 会把概率集中到一个位置（梯度变得很小），训练不稳定。除以 $\sqrt{d_k}$ 是为了把分数的方差拉回到 1 附近。
- **softmax**：沿最后一维做 softmax，把打分转换成概率分布——每行加起来等于 1，每个值在 $(0, 1)$ 之间。这就是注意力权重。
- **乘以 $V$**：用注意力权重对 value 做加权平均，得到最终输出——形状仍是 $(L, d)$，但每个位置都融合了全局信息。

这个公式是整个 Transformer 的"心脏"。配套的最小实现见 `code/part-1/attention.py`（3.9 节会进一步解读）。

## 3.4 多头注意力

单头 attention 的表达能力有限——它只能从一个"视角"看序列。比如想让模型同时关注"主谓关系"和"指代关系"，单头就要被迫在这两个模式之间折中。

**多头注意力（Multi-Head Attention, MHA）** 解决了这个问题：把 $Q/K/V$ 分别拆成 $h$ 组（每组维度 $d_k = d / h$），独立做 attention，再把结果拼起来：

$$\text{MultiHead}(Q, K, V) = \text{Concat}(\text{head}_1, \dots, \text{head}_h) W^O$$

其中 $\text{head}_i = \text{Attention}(X W_i^Q, X W_i^K, X W_i^V)$。最后用一个输出投影 $W^O$ 把拼起来的结果再线性映射回去。

直觉上，每个 head 就像一个"专家"，专门负责某一种关系：有的 head 学会追踪主谓一致，有的学会对齐指代词，有的学会聚焦最近的 token，等等。多个 head 并行，最后融合——这是典型的"分而治之"。经验上，多头带来的提升非常稳定，所以现在几乎所有 LLM 都有 16~128 个 head。

需要注意的是，**总参数量和单头差不多**——把一个大矩阵拆成几个小矩阵乘起来，参数量几乎一样。换句话说，多头没有显著增加模型体积，只是把同样的预算"重新分配"到了多个子空间里。这种"花同样的钱，办更多的事"的设计，是 Transformer 一直保持高效的重要原因。

## 3.5 位置编码

Self-attention 有一个隐藏的、但极其关键的弱点：**它对序列顺序不敏感**。把"猫吃鱼"和"鱼吃猫"分别喂给 attention 层，输出会完全一样——因为 attention 只关心"哪些 token 共现"，不关心"谁先谁后"。但语言显然是有顺序的，所以必须显式告诉模型"位置"信息。

这就需要**位置编码（Positional Encoding）**：给每个位置生成一个向量，加到 token embedding 上。Ch3 [原始 Transformer 论文] 用的是**Sinusoidal（正弦）** 编码——用不同频率的 sin/cos 函数生成位置向量：

$$PE_{(pos, 2i)} = \sin(pos / 10000^{2i/d}), \quad PE_{(pos, 2i+1)} = \cos(pos / 10000^{2i/d})$$

这套方案的好处是不需要学习、外推性好；坏处是它表达的是绝对位置，对相对位置关系不直接 —— LLM 已经几乎不用了。

现代 LLM 几乎都用 **RoPE（Rotary Position Embedding，旋转位置编码）**。它的核心思想是：**把 query 和 key 向量在二维子空间里按位置旋转**。具体地，对位置 $m$ 的 query 和位置 $n$ 的 key 做内积，结果会自动包含 $(m-n)$ 这一项——也就是说，RoPE 直接编码的是**相对位置**而不是绝对位置。这套机制数学优雅、效果好，被 LLaMA、Qwen、DeepSeek 等几乎所有主流开源模型采用（论文见本章参考）。

**ALiBi（Attention with Linear Biases）** 走的是另一条路：保持普通 attention 不变，但在打分 $Q K^\top$ 上**加一个与距离成正比的负偏置**。距离越远的两个位置，分数越被压低，注意力权重就越小。ALiBi 不需要额外的位置向量，参数为零；额外参数可学习项为零，但对长度外推（训练用 1024，推理用 4096）的支持非常好。MPT、Falcon 等模型就采用了 ALiBi。

| 方案 | 编码对象 | 是否需要额外参数 | 代表模型 |
|---|---|---|---|
| Sinusoidal | 绝对位置 | 否 | 原始 Transformer |
| RoPE | 相对位置 | 否 | LLaMA / Qwen / DeepSeek |
| ALiBi | 距离偏置 | 否 | MPT / Falcon / BLOOM |

简单记法：**RoPE 是当前主流，ALiBi 适合长上下文外推，老的 Sinusoidal 已被淘汰**。

## 3.6 Transformer block

一个完整的 Transformer block 由两大部分组成：**多头自注意力（Multi-Head Self-Attention）** 和**前馈网络（Feed-Forward Network, FFN）**。两者各包一层 LayerNorm（详见 Ch2）和一条残差连接。

现代 LLM 几乎都用 **Pre-Norm** 结构——把 LayerNorm 放在注意力和 FFN **之前**：

```text
x → LayerNorm → Multi-Head Self-Attention → + → LayerNorm → FFN → + → 输出
|________________________________________________|
                残差连接 1
                |________________________________________________|
                                残差连接 2
```

对应的 PyTorch 风格伪代码：

```python
# 残差连接 1
attn_out = mha(layer_norm_1(x))
x = x + attn_out

# 残差连接 2
ffn_out = ffn(layer_norm_2(x))
x = x + ffn_out
```

为什么要 Pre-Norm 而不是 Post-Norm（BN 时代那种"先注意、后归一化"）？因为 Post-Norm 在深层 Transformer 里会让梯度不稳定，训练时常常要加 learning rate warm-up 等技巧；Pre-Norm 则天然让梯度可以走"残差直路"直接回传，深层训练稳定得多。**所有现代 LLM——GPT、LLaMA、Qwen——都用 Pre-Norm**。

FFN 部分通常是两层全连接，中间一个非线性激活。原始 Transformer 用 ReLU，现代 LLM 普遍用 **SwiGLU**（详见 3.10 节），结构可以理解为：

$$\text{FFN}(x) = W_2 \cdot \sigma(W_1 x) \odot W_3 x$$

两个并联的"门"只算其一会替代，简单一点，主流 LLM 中每个 Transformer block 占总参数约 2/3 是这一块。

最后，整模型就是把同一个 Transformer block **重复堆叠 N 次**（N 通常是 32、80、128 这种数字），中间穿插 LayerNorm 和残差连接。这就是为什么说 "Transformer 是一个深而规整的模型"——它的每一层结构完全相同，只是参数不同。

## 3.7 Decoder-only vs Encoder-Decoder

Transformer 论文（2017 年）描述的是 **Encoder-Decoder** 架构：一个 Encoder 堆叠负责"读懂"输入，一个 Decoder 堆叠负责"生成"输出，中间通过 cross-attention 沟通。这种结构非常适合**翻译、摘要**这种"输入-输出对齐"的 seq2seq 任务。

但 2018 年以后，社区发现了一个更简单的替代：**Decoder-only**——只保留 Decoder 堆叠，让它一次性看完整个 prompt，再一个 token 一个 token 地续写。GPT 系列就是这条路线的代表，事实证明这条路在规模化后效果惊人。今天所有主流大语言模型——GPT、LLaMA、Qwen、DeepSeek、Claude——清一色都是 Decoder-only。

**Encoder-only** 是另一条路，代表是 BERT。它的目标是"理解"输入文本（比如做分类、检索、问答），不需要生成新内容，所以只保留了 Encoder 堆叠。它通常用**掩码语言模型（MLM）** 训练——把句子里某些词遮住，让模型猜回来。今天 Encoder-only 仍然广泛用在**检索增强（RAG）** 和**嵌入模型** 里。

| 架构 | 输入 → 输出 | 注意力掩码 | 代表模型 | 典型任务 |
|---|---|---|---|---|
| Decoder-only | 单向（自回归） | causal mask | GPT / LLaMA / Qwen | 文本生成、对话 |
| Encoder-only | 双向理解 | 无 mask | BERT / RoBERTa | 分类、检索、嵌入 |
| Encoder-Decoder | 输入编码 → 输出生成 | 编码无掩码 / 解码 causal + cross | T5 / BART | 翻译、摘要 |

**掩码（mask）** 是这三个架构的关键区别。Decoder-only 在算 attention 时，必须**遮住未来的位置**——位置 $i$ 只能看到位置 $\leq i$ 的 token，不能"偷看"答案。这是用 **causal mask**（一个上三角为 $-\infty$ 的矩阵）实现的：把不允许看的位置在 softmax 之前设为 $-\infty$，softmax 后概率就是 0。Encoder-only 双向都能看，所以不需要 mask。Encoder-Decoder 的解码器部分既要 causal mask（看不到未来），又要 cross-attention 去看编码器的输出。

简单记法：**生成用 Decoder-only，理解用 Encoder-only，翻译用 Encoder-Decoder**。本书后续章节默认关注 Decoder-only LLM。

## 3.8 KV cache 直观理解

LLM 推理时是**自回归**的——生成第 $t$ 个 token 时，需要把前 $t-1$ 个 token 重新过一遍 attention 层。在朴素的实现里，这意味着每生成一个 token 都要重算所有历史 token 的 K 和 V。序列一长，计算量就爆炸式增长。

**KV cache** 解决了这个问题。它的核心想法很朴素：**历史 token 的 K/V 在第一次算完后缓存下来，下次生成新 token 时直接复用**，不用重算。

具体来说，自回归生成的每一步：
1. 把新 token 的 query 算出来（这没法缓存，因为每次新 token 都不同）；
2. 用这个 query 和**已经缓存的历史 K/V**算 attention，得到当前步的输出；
3. 把当前新 token 的 K/V 追加进缓存，供下一步使用。

这样一来，生成第 $t$ 个 token 的计算量从 $O(t)$ 降到 $O(1)$（只算当前步），整个序列的总计算量从 $O(L^2)$ 降到 $O(L)$。代价是**显存占用增加**——需要把每个 Transformer 层、所有历史 token 的 K 和 V 都存起来。对于一个 32 层、40k 上下文、每层 8 个 KV head、head dim 128 的模型，KV cache 的显存占用是 $32 \times 40000 \times 8 \times 128 \times 2 \text{ bytes} \approx 2.5 \text{ GB}$——已经不能忽视了。

正因为 KV cache 成了长上下文推理的瓶颈，3.10 节要介绍的 **GQA**（分组查询注意力）才变得非常重要——它通过让多个 query head 共享同一组 K/V，把 KV cache 直接砍掉几倍。**理解 KV cache 是理解现代 LLM 推理优化的起点**。

## 3.9 一个最小 attention 示例

理论讲完了，我们用一个最小可运行的 PyTorch 代码把 3.3 节的公式真正跑一遍。完整代码在 `code/part-1/attention.py`，核心函数 `scaled_dot_product_attention` 只有 4 行有效计算：

```python
def scaled_dot_product_attention(query, key, value):
    d_k = query.size(-1)
    scores = torch.matmul(query, key.transpose(-2, -1)) / (d_k ** 0.5)
    attn = F.softmax(scores, dim=-1)
    output = torch.matmul(attn, value)
    return output, attn
```

它精确对应公式 $\text{softmax}(Q K^\top / \sqrt{d_k}) V$，**没有省略任何一项**。我们逐行看：

1. **`torch.matmul(query, key.transpose(-2, -1))`**：算 $Q K^\top$。张量形状从 `(batch, seq, d)` 变成 `(batch, seq, seq)`——也就是"每个位置对每个位置的分数"。
2. **`/(d_k ** 0.5)`**：除以 $\sqrt{d_k}$，把分数方差拉回 1 附近，避免 softmax 进入饱和区。
3. **`F.softmax(scores, dim=-1)`**：沿最后一个维度做 softmax。每行变成"和为 1 的概率分布"——这就是注意力权重。
4. **`torch.matmul(attn, value)`**：用注意力权重对 V 加权求和，得到最终输出。

配套的 `main()` 函数用 `torch.manual_seed(0)` 固定随机种子，生成 shape `(2, 4, 8)` 的随机 Q/K/V，调用 attention，打印输出形状 `(2, 4, 8)` 和注意力权重形状 `(2, 4, 4)`。最后两个 `assert` 做了两件事：

- **验证 softmax 行和为 1**——这是 softmax 的不变量，理论上每行必须严格等于 1（数值误差容忍 `1e-5`）；
- **验证输出形状正确**——`(batch, seq_len, d)`，没有多余或缺失的维度。

直接运行 `python code/part-1/attention.py`，应当看到：

```text
output shape: (2, 4, 8)
attn shape:   (2, 4, 4)
OK：注意力权重行和为 1，输出形状正确
```

退出码为 0。这个例子虽然只有 30 行，但**它就是工业级 Transformer 库（PyTorch `F.scaled_dot_product_attention`、FlashAttention）的数学骨架**——真正的大模型只是把它批量化、加了多头、加了 causal mask。理解了它，你就理解了 Ch4 LLM 实现中 attention 那一块的核心代码。

## 3.10 MoE 与现代 Transformer 变体

标准 Transformer 块已经 8 年了，期间涌现出一系列"小改动、大收益"的变体。下面四个概念是现代 LLM 的**标配**——你会在 LLaMA-3、Qwen-3、DeepSeek-V3、Mixtral 等所有前沿模型里见到它们。

**MoE（Mixture of Experts，混合专家）** 是一种"稀疏激活"架构。传统的 FFN 是一个大块参数，每次推理都要算完它；MoE 则把它拆成 $E$ 个（典型 $E=8, 16, 64, 256$）"专家"网络，外加一个**路由器（Router）**。路由器对每个 token 计算一个分数，决定它**走哪几个专家**（通常取 top-2 或 top-4）。结果是：模型总参数可以非常大（数千亿甚至上万亿），但每个 token 只激活一小部分专家，**推理成本几乎和激活的专家数成正比，而不是和总参数成正比**。DeepSeek-V2、Mixtral 8x7B、GPT-4 都采用了 MoE。

**RMSNorm（Root Mean Square Layer Normalization）** 是 LayerNorm 的简化版。它去掉了均值中心化这一步，只做缩放：

$$\text{RMSNorm}(x) = \gamma \odot \frac{x}{\sqrt{\text{mean}(x^2) + \epsilon}}$$

直觉上，Transformer 的激活分布通常已经接近 0 均值，再减去均值这一步冗余但又不算便宜。RMSNorm 把这一步砍掉，**计算更快、显存更省**，效果和 LayerNorm 几乎打平。LLaMA、Qwen 都用 RMSNorm。

**SwiGLU** 是一种门控激活函数。它把 FFN 里的 ReLU/GELU 换成"Swish 门 × 线性门"的形式：

$$\text{FFN}_{\text{SwiGLU}}(x) = W_2 \cdot (\text{Swish}(W_1 x) \odot W_3 x)$$

直觉上：两条并行的线性变换 $W_1 x$ 和 $W_3 x$，其中一条过 Swish 激活后作为"门控"，按元素乘到另一条上。这套机制在 GLU 论文里就有，PaLM 和 LLaMA 把它定型为现代 LLM 的标配——实践表明它比单纯 GELU 性能好 1~2 个百分点。

**GQA（Grouped-Query Attention，分组查询注意力）** 是 MHA 的"瘦身版"。MHA 里每个 query head 都有自己的 K/V；MQA（Multi-Query Attention）让所有 query head **共享同一组** K/V——推理时 KV cache 最小，但质量有明显损失。GQA 是折中：把 query head 分成 $g$ 组，**每组共享一组 K/V**。$g = h$ 就是标准 MHA，$g = 1$ 就是 MQA，$g = 8$ 是 LLaMA-2/3、Qwen 的常用配置。质量几乎不损，KV cache 比 MHA 小 $g$ 倍，是今天所有追求长上下文 LLM 的标配。

| 技术 | 主要收益 | 代表模型 |
|---|---|---|
| MoE | 大参数 + 低推理成本 | Mixtral, DeepSeek-V2/V3, GPT-4 |
| RMSNorm | 比 LayerNorm 更快更省 | LLaMA, Qwen |
| SwiGLU | 优于 ReLU/GELU | PaLM, LLaMA, Qwen |
| GQA | KV cache 缩小 $g$ 倍 | LLaMA-2/3, Qwen-2/3 |

这四个改动背后有一个共同的设计哲学：**用更聪明的方法用好每一 FLOP、每一字节显存**，而不是单纯堆参数。在 Part 2 里我们会看到，它们和 FlashAttention、paged attention、量化推理一起，构成了"现代 LLM 推理栈"的全部关键构件。本章不再深入，**细节留给 Part 2**。

## 本章小结

- **RNN 的局限**：长距离依赖被稀释、训练难并行、扩展性差；Transformer 用 self-attention 一次解决。
- **Self-attention 直觉**：每个位置"询问"序列所有位置，按相关性加权融合，得到融合全局信息的新表示。
- **核心公式**：$\text{Attention}(Q, K, V) = \text{softmax}(Q K^\top / \sqrt{d_k}) V$；$Q/K/V$ 由输入分别投影得到，$\sqrt{d_k}$ 是稳定 softmax 的关键。
- **多头注意力**：把 Q/K/V 拆成多组并行算 attention，让不同 head 学不同模式，几乎不增加参数量。
- **位置编码**：必须显式注入顺序信息。RoPE 编码相对位置（主流）、ALiBi 加距离偏置（适合长上下文）、Sinusoidal 已淘汰。
- **Transformer block**：Pre-Norm + Multi-Head Self-Attention + 残差 + FFN + 残差，重复堆叠 N 次；现代 LLM 几乎都用 Pre-Norm。
- **三类架构**：Decoder-only（生成，主流）、Encoder-only（理解/检索）、Encoder-Decoder（翻译/摘要）；区别在于注意力掩码。
- **KV cache**：自回归推理时缓存历史 K/V，生成从 $O(L^2)$ 降到 $O(L)$ 计算量；长上下文的显存瓶颈。
- **现代变体**：MoE（稀疏激活）、RMSNorm（去掉均值中心）、SwiGLU（门控激活）、GQA（共享 K/V）——这些都是前沿 LLM 的标配。

## 本章参考

### 必读论文

- [Attention Is All You Need (Vaswani et al., 2017)](https://arxiv.org/abs/1706.03762) — Transformer 的开山之作，提出 self-attention 和 Encoder-Decoder 架构。
- [RoFormer: Enhanced Transformer with Rotary Position Embedding (Su et al., 2021)](https://arxiv.org/abs/2104.09864) — RoPE 论文，把旋转矩阵引入位置编码，成为 LLaMA/Qwen/DeepSeek 的标配。
- [GQA: Training Generalized Multi-Query Transformer Models from Multi-Head Checkpoints (Ainslie et al., 2023)](https://arxiv.org/abs/2305.13245) — GQA 论文，给出从 MHA checkpoint 蒸馏到 GQA 的实用方法。
- [Mixtral of Experts (Jiang et al., 2024)](https://arxiv.org/abs/2401.04088) — Mixtral 8x7B 报告，展示了稀疏 MoE 在开源 LLM 中的可行路径。

### 推荐博客 / 教程

- [The Illustrated Transformer (Jay Alammar)](https://jalammar.github.io/illustrated-transformer/) — 图解 Transformer 经典之作，把 Q/K/V、注意力、Encoder/Decoder 讲得非常直观。
- [Llama 3 架构组件：RMSNorm / SwiGLU / GQA / RoPE 解读](https://kdopen.com/blog-3/llm-architecture-components-rmsnorm-swiglu-gqa-rope-explained) — 把现代 LLM 四大组件拆开讲清楚的中文好文。

### 视频 / 课程

- [Andrej Karpathy "Let's build GPT"](https://www.youtube.com/watch?v=kCc8FmEb1nY) — 从零手写 GPT 的视频教程，看完对 decoder-only Transformer 的训练与采样会有具象认识。