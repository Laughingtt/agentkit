# Ch19 A2A：让 Agent 之间也能对上话

> 一句话简介：工具是一次调用，委派是一件事——A2A 讲的就是后者。

上一章讲完 MCP，harness 第 4 项职责「**协议接入**」只做了一半。那一半叫"把工具接进来"，这一半叫"**把另一个 Agent 接进来**"。很多人读完两章还是糊的，症结不在术语难，而在**根本没意识到这是两种不同的接法**。本章的第一个责任就是把它讲透。

本章以 **A2A 协议 v1.0** 为准（v1.0.0 于 2026 年 3 月发布，v1.0.1 为当前修订；协议版本号一律写作 `1.0`，补丁号不参与协商）。

## 本章目标

读完本章你应当能：

- 用一句话说清「接一个工具」和「接一个 Agent」差在哪
- 解释 Agent Card 是什么、为什么它必须待在固定地址上
- 复述任务的八个状态，并指出哪一个是 A2A 区别于工具调用的根本原因
- 画出一次完整委派的时序：读自述页 → 派活 → 停下来问人 → 交付
- 判断一个外部能力该做成工具，还是该做成一个 Agent

## 本章导览

左边是本地 harness，虚线框里是通过 A2A 招来的远端 Agent——**框里那台自己还带着一整套 harness。A2A 连的是两个壳，不是一个壳和一个模型。**

```mermaid
graph TD
    U[用户] --> H1[本地 harness]

    subgraph 远端["另一个 Agent 的 harness（你看不见里面）"]
        H2[协议接入]
        L2[它的 Agent 循环]
        H2 --> L2
    end

    H1 -->|读自述页 Agent Card| H2
    H1 -->|派一个任务 Task| H2
    H2 -->|可能反过来问人 input-required| H1
    H2 -->|交付成果 Artifact| H1
    H1 -->|MCP 接工具| T[本地工具]
```

图里已经藏着全章要点：**箭头是双向的、有状态的、可能会折回来。** 上一章的 MCP 箭头只有一根，从 Agent 指向工具，问完就结束。

赶时间只读四处：19.1 的场景、19.3 的一张卡片、19.4 的状态图、19.6 的对比表。

---

## 19.1 先演一遍「没有它会怎样」

### 19.1.1 一个具体场景

你要一份"某项目过去三年验收情况"的报告。你手上有一个**写报告的 Agent**：文笔好、排版好，但它看不见档案库。档案库里有几千份扫描件，需要一个**专精检索的 Agent** 去翻——它知道哪些文件在哪、哪些是正文哪些是附件、同一件事分散在三个年度的附件里。

活儿分给了两个专才。问题来了：**报告 Agent 怎么把活儿派给检索 Agent？**

### 19.1.2 没有协议的日子

按最直觉的办法干：在报告 Agent 里直接写调用。

```text
【手写对接】
response = http_post("https://archive.internal/api/v2/search",
                     {"query": "...", "year_from": 2021, "year_to": 2024})
```

第一天能跑通。**第三天开始出事，而且出的是四类完全不同的事：**

| 出了什么事 | 表面现象 | 真正的病根 |
|---|---|---|
| 检索 Agent 改了接口 | 返回 422，错误信息是一段英文 JSON，模型读不懂也不会重试 | 你把它的**实现**焊死了 |
| 检索 Agent 要反问："A 项目还是 B 项目？" | 请求直接超时——**HTTP 的问-答模型里没有"停下来等"的位** | 你的模型和它的模型不是一回事 |
| 检索 Agent 翻档案要 6 分钟 | 你的连接 30 秒就断了，只剩半截结果 | 你假设了它是**瞬时**的 |
| 检索 Agent 换了底层引擎 | 返回结构全变，报告 Agent 直接崩 | 你没有"能力描述"，只能靠猜 |

请特别注意第二、三行：**它们不是接口没调通，是模型不匹配**——你用"调一个函数"的假设，去对付一个"会自己规划、自己循环、中途可能需要人、需要一段时间"的程序。

于是本章的立论就在这儿：

> **当「工具」需要一个决策、需要一段时间、甚至需要反过来问人时，它就不再是工具了，它是一个 Agent。**

A2A 就是为这句话而生的。它不发明 Agent，只规定**两个都不透明的 Agent 之间怎么说话**——双方都不需要知道对方的模型、框架和内部工具。

### 19.1.3 加上协议之后

```text
① 读 检索 Agent 的自述页（一个固定地址的 JSON）
   → 知道：它叫"档案检索助手"，会"复杂档案检索"，协议版本 1.0
② 派一句话过去："查一份 2023 年的项目验收档案"
   → 对方回一个任务号，状态"处理中"
③ 对方停下来说："要限定年份范围吗？"
   → 报告 Agent 答："限定 2023 年 1 月到 6 月"，带上那个任务号送回去
④ 对方回"已完成"，附一份成果
```

**报告 Agent 全程不知道对方用什么模型、什么框架、连着什么数据库。** 它只遵守了一套约定——正是 17.4.4 那句"协议的作用不是让熟人之间更方便，而是让互不相识的两端也能对上"。

## 19.2 A2A 是什么

### 19.2.1 白话、类比、小例子

**白话。** A2A 是一种**公开的对话约定**，让两个各自独立、谁也看不见谁的 Agent，能发现彼此、派活给它、看着它干完、必要时中途搭把手，最后取走成果。

**类比。** 接着 17.4.4 的**通用对讲机频率**往下推一步：MCP 解决的是**两端对上频率**——频率统一了，谁都能呼叫谁。但对上频道只够"滴"两下确认在不在。要谈成一件事，还得有三样东西：**对方开机时自报家门**（我叫什么、我会什么、在哪个频道）、**每件事一个工单号**（有进度、有状态、能停下来等你回话）、以及**最后交回来的成果单**。A2A 就是规定这三样东西长什么样。

**小例子。** 一句话派活，加上一句话回话，就是完整的 A2A 交互：

```text
客户端 → 服务端：  { "message": { "role": "ROLE_USER",
                              "parts": [ {"text": "帮我查一份 2023 年的验收档案"} ] } }
服务端 → 客户端：  { "task": { "id": "task-uuid",
                              "status": { "state": "TASK_STATE_INPUT_REQUIRED",
                                          "message": { "role": "ROLE_AGENT",
                                                       "parts": [ {"text":
                                                       "要限定年份范围吗？"} ] } } } }
```

读法：客户端发出**一句话**，服务端回给它的**不是结果，是一个任务**；任务现在停在"等你回话"，并附了一句反问。**注意"任务"这两个字**——它有编号、有状态、能暂停、稍后接着走。这是本章接下来要展开的唯一一个新概念。

### 19.2.2 它到底规定了哪几件事

一个协议只做四件事，A2A 也一样：

| 协议要做的事 | A2A 的答案 | 展开在 |
|---|---|---|
| 我怎么找到你 | 一张固定地址的自述页 | 19.3 |
| 我怎么把活儿派给你 | 一条消息，换回一个任务 | 19.4 |
| 我怎么知道它干到哪了 | 任务有状态，状态会变 | 19.4 |
| 干完了我拿什么 | 成果单独装，不和对话混在一起 | 19.5 |

至于"你怎么想"、"你调什么工具"、"你的模型多大"——**协议一概不问。不问，才有互操作。**

### 19.2.3 一句官方说法，和它的治理

A2A 项目在 v1.0 发布公告里，把它和 MCP 的关系写成一句话：

> **MCP inside agents, A2A between agents.**（MCP 在 Agent 内部，A2A 在 Agent 之间。）

和 19.1 的立论是同一件事的两种说法：一句讲分工，一句讲为什么。19.6 把它展开成一张表。

治理方面：A2A 于 2025 年 6 月由 Linux Foundation 托管，2026 年 8 月并入该基金会旗下的 Agentic AI 基金会（AAIF），成为 Growth Stage 项目；技术指导委员会由 8 家公司的代表组成。到 2026 年 4 月官方宣布有 **150 多家组织**参与。**这些数字都在变，要引用就以官网当日页面为准。**

## 19.3 Agent Card：一个 Agent 怎么介绍自己

### 19.3.1 白话、类比、小例子

**白话。** Agent Card 是一张**自述页**：一个 Agent 在固定地址上公开的一份 JSON 说明书，写着我是谁、我会干什么、从哪儿能派活给我。**别人在派活之前先读它。**

**类比。** 还是对讲机那场戏。无线电有**呼号**——每个电台报出自己是谁，别人一听就知道在跟谁说话。Agent Card 就是 Agent 的呼号，只不过它还附带一张**业务范围表**：我专修发动机，不修机翼，你派错活我当场就能拒。

**小例子。** 一张真实的自述页（字段名与 v1.0 规范一致，值为便于理解而编造）：

```json
{
  "name": "档案检索助手",
  "description": "只做一件事：把一份复杂档案查清楚并交回结论，不写报告。",
  "version": "1.0.0",
  "supportedInterfaces": [
    { "url": "https://archive.example.com", "protocolBinding": "HTTP+JSON",
      "protocolVersion": "1.0" }
  ],
  "capabilities": { "streaming": true, "pushNotifications": false },
  "defaultInputModes":  ["text/plain"],
  "defaultOutputModes": ["text/plain", "application/json"],
  "skills": [
    {
      "id": "archive_lookup",
      "name": "复杂档案检索",
      "description": "给定档案主题与年份范围，检索并汇总成结构化结论。",
      "tags": ["retrieval", "research"],
      "examples": ["查 2023 年 A 项目的三份验收报告"]
    }
  ]
}
```

只有三处要紧：

- **`skills` 是这张卡的正文。** 前面都是格式，`skills` 才是"什么活该派给我"。每条技能有一句 `description` 和一串 `tags`——**这是写给模型读的**，模型靠它决定派不派。所以那句 description 要写"能做什么"，别写"我很好用"。
- **`supportedInterfaces` 告诉你从哪儿接活。** v1.0 把原先分散在顶层的地址和首选传输方式合并成了这个有序数组，**第一个最推荐**。同一个服务可以同时开三种接法，客户端挑一个用。
- **`capabilities` 是它的诚实声明。** 这里写着不支持推送通知，客户端就不该指望它半夜来敲门。

### 19.3.2 为什么非要放在固定地址上

这一步很反直觉：**规定一个大家都能猜到的地址，比提供一个搜索功能有用得多。** 地址固定之后，客户端拿到的就只是一个域名：

```text
GET https://{对方域名}/.well-known/agent-card.json
```

于是接入方**一句配置都不用加**。19.1 那四类故障里的第一类和第四类（实现变了、能力不知道），靠的就是这张卡：对方换了什么引擎不要紧，`skills` 那几行会变；对方不支持哪种接法不要紧，`capabilities` 那几行会变。**变更通过一个公开地址自动传播，不需要挨个通知。**

`/.well-known/` 前缀不是 A2A 独创，来自互联网通用约定（同一套前缀也放 `security.txt` 这类安全声明）。选它的理由很简单：**它让"读说明书"不需要任何鉴权、不需要任何协商**，普通 HTTP 客户端都能读。规范进一步要求这张卡应当**免鉴权**提供——因为客户端还不知道该拿什么凭证来读它，顺序不能倒过来。真正的凭证要求写在卡里的 `securitySchemes` 字段，读完卡才知道。

> ⚠️ **一个必须澄清的路径说法。** 网路上流传着两个地址：`/.well-known/agent.json` 和 `/.well-known/agent-card.json`。**v1.0 规范用的是后者**；本项目早期设计稿里写的 `agent.json` 是更早版本的遗留写法，**已不是当前规范**。本章与配套代码一律用 `agent-card.json`。

最后提一句：卡片还支持**数字签名**（让对方在做任何事之前先验明这张卡确实出自这家公司，跨组织协作的刚需）和**扩展声明**（列出额外支持的私有扩展，将来生态长出新东西不必回头改协议）。这两项本章不展开；你只要知道**卡片不只是自我介绍，还是一份可被机器校验的契约**就够了。

## 19.4 Task：为什么必须有"停下来问人"

### 19.4.1 白话、类比、小例子

**白话。** 任务（Task）是**一件被编号了的活儿**。它不是一次函数调用，它有进度、有历史、会中途停下来向你要信息、最后可能成功也可能失败。A2A 里"派活"的返回值不是结果，是这个任务。

**类比。** 派工单。你把一件活儿填成工单递给另一个班组，对方**不会当场干完递回来**——流程上可能有五个环节，卡在任何一环都可能回头找人："这个编号到底是 A 还是 B？"你补一句，它继续往下走；走到最后一环，工单盖上"完结"章，附上产出物。

**小例子。** 一张停在"等你回话"的工单：

```text
任务号：task-uuid
状态：  等你补信息
对方问：这份档案要限定年份范围吗？给我一个起止年份，我按范围查。
```

**"工单会停在半路"，是 A2A 与上一章那套工具调用最本质的差别。** 工具调用没有半路——你调一个函数，它要么返回一个值，要么抛一个异常，没有"我先歇一会儿，等你回句话"的第三种状态。而现实中的活儿有。

### 19.4.2 八个状态，一张图看完

v1.0 定义了八个状态。按"任务还能不能动"分三组更好记：

| 分组 | 状态 | 白话 |
|---|---|---|
| **在途** | `submitted` 已接单 | 我收到了，还没开工 |
| | `working` 处理中 | 正在干 |
| **中断** | `input-required` 等你补信息 | **停下来，要你回一句才能继续** |
| | `auth-required` 等你授权 | 停下来，缺凭证 |
| **终结** | `completed` 完成 | 干成了，成果在后面 |
| | `failed` 失败 | 干了，干砸了 |
| | `canceled` 已取消 | 还没干完就停了 |
| | `rejected` 已拒绝 | 我不接这个活（当场就能拒） |

`rejected` 值得单独说一句：它和 `failed` 不是一回事。**`failed` 是我试了但没成，`rejected` 是我压根不接。** 一个专精档案检索的 Agent 收到"帮我写一封辞职信"，正确反应是当场拒绝，而不是硬着头皮去试、试完报个错。

```mermaid
stateDiagram-v2
    [*] --> submitted: 派活
    submitted --> working: 开工
    working --> input-required: 发现缺信息
    input-required --> working: 补齐了
    working --> auth-required: 缺凭证
    auth-required --> working: 凭证到位
    working --> completed: 干完
    working --> failed: 干砸了
    working --> canceled: 被叫停
    submitted --> rejected: 当场不接
    working --> rejected: 中途判定不接

    completed --> [*]
    failed --> [*]
    canceled --> [*]
    rejected --> [*]
```

四个终结状态都是**终点**：任务进了这些状态就不能再往里递消息了，规范规定这时要报 `UnsupportedOperationError`。这和职责六「会话与状态」是一回事——**能回放的事才叫会话，能被后续消息改写的状态才叫活的。**

### 19.4.3 重点：把 `input-required` 单独拿出来看

回到 Ch17 17.3 那张时序图。它当时画了一条分支，只在旁边标了四个字：

```text
    else 需要人点头
        H->>I: 请求授权
        U-->>H: 同意 / 拒绝
    end
```

**那一条分支就是 `input-required`。** 在工具调用的世界里，人点头发生在**壳内部**——本地 harness 拦下模型的一个危险动作，问的是"我这次用户"。而在 A2A 里，人点头可以发生在**另一台机器上的另一个 Agent 内部**：它说"我需要一个起止年份"，这句话要**穿过网络、回到委派方**。

这个差别看着像技术细节，其实是能力上的分水岭：

- **停下来问人的是对方，不是你。** 你甚至可以把自己的 Agent 关掉，等对方那边的人类答完，再回来接着收。
- **人可以在网络的另一端。** 19.2 那句"两个都不透明的 Agent"，在 `input-required` 上体现得最彻底：你连对方问的是什么问题，都是通过一段 JSON 才知道的。
- **这让长任务变得可能。** 19.1 那类"跑六分钟"的活儿，不再是一次超长的 HTTP 请求，而是一串**可以跨越任意长时间的对话**。

因此本章给你一条实用判据：

> **如果你要接的那个外部能力，说不出"它会中途停下来问什么"，那它多半是个工具，用 MCP 就行，不用上 A2A。**

## 19.5 一次完整的任务流转

19.1 我们用文字演过一遍，现在画出来。

```mermaid
sequenceDiagram
    participant C as 委派方 client
    participant R as 检索 Agent server

    C->>R: GET /.well-known/agent-card.json
    R-->>C: 自述页（会什么、从哪儿接活）
    C->>R: POST /message:send 说一句话
    R-->>C: 任务 task-uuid，状态 input-required
    C->>R: POST /message:send 带上 taskId 回一句
    R-->>C: 状态 completed，附一份成果 artifact
```

五个来回，没有一次是"我调你一下你返回结果"。**第 3、4 步之间可以隔三小时**——如果对方是在等一个真人回答的话。

### 19.5.1 递过去的和递回来的，各是什么

协议里有两个容器，初学者一定要分清：

| 容器 | 装什么 | 生命周期 |
|---|---|---|
| **消息（Message）** | 双方说的话。"我要查档案" / "要限定年份吗" | 一次性，读完就过去 |
| **成果（Artifact）** | 干完的产出：一份报告、一个结论、几段结构化数据 | 挂在任务上，可反复取 |

分开的理由和 Ch17 的会话留痕是同一个：**过程中的对话和最终交付物不是一回事。** 把它们混在一处，你就说不出"这轮任务到底交付了什么"。服务端还给每份成果一个独立编号，这样流式返回时可以一段一段追加（"先给你目录，再给你正文"）。

消息正文又切成一小块一小块（协议里叫 Part）：可以是纯文字、可以是文件、也可以是一段结构化数据。**一行 `parts: [{"text": "..."}]` 里的那个 `{"text": ...}` 就是一个 Part。** 这是本章最后一个新概念，后面代码里还会再遇到。

### 19.5.2 等结果的三种办法

| 办法 | 怎么做的 | 什么时候选它 |
|---|---|---|
| **轮询** | 过一会儿问一次"到哪了" | 最简单，够用，示例代码就用它 |
| **流式订阅** | 挂一条长连接，对方边干边推 | 想在终端上实时看到进度 |
| **回调** | 留个地址，干完它来敲门 | 客户端不在线，或活儿特别长 |

选哪个，跟你 harness 第 7 项「投递接口」是同一类决策：**取决于人是怎么看进度的**，跟 Agent 本身怎么干活无关。详见 17.4.7。

## 19.6 A2A 与 MCP 怎么分工

上一章已经讲过 MCP 的原语和传输，这里不重复，只回答"什么时候用哪个"。

| 维度 | MCP（Ch18） | A2A（本章） |
|---|---|---|
| 连的是 | **工具**——给一个 Agent 加工具 | **Agent**——让两个 Agent 协作 |
| 谁去找谁 | 通常是 Agent 去找工具 | 一方把**任务**交给另一方 |
| 产物 | 工具的调用与返回 | 一个**有生命周期的任务** |
| 能否中途问人 | 不能（问人发生在本地壳里） | **能**，`input-required` |
| 耗时 | 通常毫秒级 | 可能几秒到几小时 |
| 对方是否不透明 | 工具的说明书是公开的 schema | **对方内部一律不透明**，这是设计目标 |
| 典型场景 | 读文件、查数据库、跑测试 | 专精检索、法务审阅、跨部门协作 |

按顺序问自己三个问题，答到"是"就停：

1. **它需要自己做判断吗？** —— 只是执行一条明确指令 → 工具（MCP）。
2. **它中途可能需要反问我吗？** —— 会停、会要参数、会要授权 → Agent（A2A）。
3. **它是另一个团队写的、我改不动也不该改吗？** —— 是 → Agent（A2A），因为不透明正是它的卖点。

**最后补一句最容易忽略的：两者不是二选一，几乎总是一起用。** 官方那句"MCP 在 Agent 内部，A2A 在 Agent 之间"说的就是这个结构——**远端那个 Agent 的外壳内部，很可能正用 MCP 接着一堆工具。**

```mermaid
graph TD
    U[用户] --> A[编排 Agent 的 harness]
    A -->|A2A 派活| B[检索 Agent 的 harness]
    B -->|MCP 接工具| D1[向量库]
    B -->|MCP 接工具| D2[OCR]
    B -->|MCP 接工具| D3[文件系统]
```

图里那一格 `B` 就是全部重点：**A2A 管 A 和 B 之间那一层，B 内部怎么接工具是 B 自己的事。**

## 19.7 最小服务端与客户端

### 19.7.1 一个能被人委派的 Agent（服务端）

```python
# illustrative only
"""
最小 A2A 服务端（HTTP+JSON 绑定，只用标准库）

演示一个"能被人委派的 Agent"最少的四件事：放自述页、接单、停下来反问、交付成果。
依赖：Python 3.9+ 标准库。运行：python3 a2a_server_min.py
协议依据：A2A v1.0（协议版本号写作 "1.0"）。
教学示意：未做鉴权、超时重试，任务存在内存里进程一挂就没，不要搬去生产。
"""

import json
import re
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

BASE = "http://127.0.0.1:9000"
A2A_VERSION = "1.0"
JSON_MEDIA = "application/a2a+json"

# 任务表。真实系统该落库——关键是进度要能被后来的人查回来，
# 而不是只活在一次函数调用里。这正是 harness 第六项职责要的留痕。
TASKS = {}

# 教学用流水账，不是协议字段：协议只规定状态怎么变，不规定你怎么记。
LOG = []


def now():
    """协议要求 ISO 8601、UTC、毫秒精度。"""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def build_agent_card():
    """对外的自述页。发现地址被规范定死，调用方拿到域名就能找到你。"""
    return {
        "name": "档案检索助手",
        "description": "只做一件事：把一份复杂档案查清楚并交回结论，不写报告。",
        "version": "1.0.0",
        "supportedInterfaces": [
            {"url": BASE, "protocolBinding": "HTTP+JSON", "protocolVersion": A2A_VERSION}
        ],
        "capabilities": {"streaming": False, "pushNotifications": False},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "skills": [
            {
                "id": "archive_lookup",
                "name": "复杂档案检索",
                "description": "给定档案主题与年份范围，检索并汇总成结构化结论。",
                "tags": ["retrieval", "research"],
                "examples": ["查 2023 年 A 项目的三份验收报告"],
            }
        ],
    }


def start_task(request_text):
    """接单。返回一个"处理中"的任务，此时还没问任何问题。"""
    task = {
        "id": str(uuid.uuid4()),
        "contextId": str(uuid.uuid4()),
        "status": {"state": "TASK_STATE_WORKING", "timestamp": now()},
    }
    TASKS[task["id"]] = task
    LOG.append({"task": task["id"], "event": "submitted", "text": request_text})
    return task


def ask_back(task, question):
    """把任务停在"等你回话"上。

    这是 A2A 与工具调用最本质的差别：对方不是一个函数，
    是一个会中途停下来、要人补一句才能继续的独立程序。
    """
    task["status"] = {
        "state": "TASK_STATE_INPUT_REQUIRED",
        "message": {"role": "ROLE_AGENT", "parts": [{"text": question}]},
        "timestamp": now(),
    }
    LOG.append({"task": task["id"], "event": "input-required"})


def deliver(task, answer):
    """交付成果。产出物用 artifact 装，和过程中的对话分开存放。"""
    task["status"] = {"state": "TASK_STATE_COMPLETED", "timestamp": now()}
    task["artifacts"] = [
        {"artifactId": str(uuid.uuid4()), "name": "检索结论", "parts": [{"text": answer}]}
    ]
    LOG.append({"task": task["id"], "event": "completed"})


class Handler(BaseHTTPRequestHandler):
    def _reply(self, code, body, media=JSON_MEDIA):
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", media)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _not_found(self):
        # 协议规定错误响应用 problem+json，不是随便一个 JSON
        self._reply(404, {"title": "Not Found", "status": 404}, "application/problem+json")

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/.well-known/agent-card.json":
            self._reply(200, build_agent_card())
            return
        matched = re.fullmatch(r"/tasks/([0-9a-fA-F-]+)", path)
        if matched:
            task = TASKS.get(matched.group(1))
            self._reply(200, {"task": task}) if task else self._not_found()
            return
        self._not_found()

    def do_POST(self):
        if self.path.split("?")[0] != "/message:send":
            self._not_found()
            return
        # 真实实现必须在这里校验 A2A-Version 请求头，版本对不上要退回错误
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length) or b"{}")
        message = payload.get("message", {})
        text = "".join(p.get("text", "") for p in message.get("parts", []))
        task_id = message.get("taskId")

        if task_id is None:
            # 第一轮：接单开工。真实系统在这里会真去翻档案，耗时若干秒。
            task = start_task(text)
            ask_back(task, "这份档案要限定年份范围吗？给我一个起止年份，我按范围查。")
        else:
            # 第二轮：带上 taskId 回话，等于在原来那件事上接着往下走
            task = TASKS.get(task_id)
            if task is None:
                self._not_found()
                return
            LOG.append({"task": task_id, "event": "resumed", "text": text})
            deliver(task, "已按「{}」检索完毕，命中 3 份相关文件。".format(text))
        self._reply(200, {"task": task})


if __name__ == "__main__":
    print("A2A 示例服务端已启动：{}".format(BASE))
    print("自述页：{}/.well-known/agent-card.json".format(BASE))
    HTTPServer(("127.0.0.1", 9000), Handler).serve_forever()
```

三个地方值得停下来看：

- **`do_GET` 的第一个分支就是 19.3 那张自述页**，无参数、无鉴权，拿到域名就能读。
- **`do_POST` 的分岔点只有一个：这次消息带没带 `taskId`。** 带了就接着原来那件事说，没带就是新开一件事。**整个 A2A 的会话逻辑，就是这一个字段。**
- **`LOG` 不在协议里。** 它是第 6 项「会话与状态」要的留痕——**协议只规定状态怎么变，不规定你怎么记。**

### 19.7.2 委派的那一方（客户端）

```python
# illustrative only
"""
最小 A2A 客户端（只用标准库）

演示委派一方的三步：读自述页 → 派一个任务 → 顺着任务状态走到终态。
依赖：Python 3.9+ 标准库。先启动 a2a_server_min.py，再 python3 a2a_client_min.py
协议依据：A2A v1.0（协议版本号写作 "1.0"）。
教学示意：未做鉴权、超时重试与证书校验，不要搬去生产。
"""

import json
import uuid
import urllib.request

BASE = "http://127.0.0.1:9000"
A2A_VERSION = "1.0"
JSON_MEDIA = "application/a2a+json"

# 这两组是本章的核心：任务要么停在"还要你补一句"，要么已经落地了。
INTERRUPTED = {"TASK_STATE_INPUT_REQUIRED", "TASK_STATE_AUTH_REQUIRED"}
TERMINAL = {"TASK_STATE_COMPLETED", "TASK_STATE_FAILED",
            "TASK_STATE_CANCELED", "TASK_STATE_REJECTED"}


def request(method, path, body=None):
    """发一次协议请求。真实实现还要加超时、重试与鉴权头。"""
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", JSON_MEDIA)
    # A2A-Version 从 v1.0 起必填：对方升级之后，两端才知道在讲哪一版
    req.add_header("A2A-Version", A2A_VERSION)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def discover():
    """第 1 步：先读自述页，看它会什么、从哪儿接活，别急着派。"""
    card = request("GET", "/.well-known/agent-card.json")
    print("找到 Agent：{}（{}）".format(card["name"], card["version"]))
    print("  简介：{}".format(card["description"]))
    for skill in card["skills"]:
        print("  技能：{} — {}".format(skill["name"], skill["description"]))
    for iface in card["supportedInterfaces"]:
        print("  接口：{} {}（协议 {}）".format(
            iface["protocolBinding"], iface["url"], iface["protocolVersion"]))


def send(text, task_id=None):
    """派一句话。带 task_id 就是"接着那件事说"，不带就是"新开一件事"。"""
    message = {"role": "ROLE_USER", "parts": [{"text": text}],
               "messageId": str(uuid.uuid4())}
    if task_id:
        message["taskId"] = task_id
    return request("POST", "/message:send", {"message": message})["task"]


def main():
    discover()
    print("\n派活：查一份 2023 年的项目验收档案")
    task = send("帮我查一份 2023 年的项目验收档案")
    task_id = task["id"]

    # 整个客户端的主循环就是这个 while：追着任务状态走，
    # 遇到"停下来问人"就补一句再送回去，遇到终态就收工。
    while True:
        state = task["status"]["state"]
        print("  状态：{}".format(state))
        if state in TERMINAL:
            break
        if state in INTERRUPTED:
            question = task["status"]["message"]["parts"][0]["text"]
            print("  它反问：{}".format(question))
            task = send("限定 2023 年 1 月到 6 月", task_id)
            continue
        # 还在干活：协议给了三种等结果的办法，这里用最简单的轮询。
        # 另外两种是流式订阅（边干边收）和回调（干完它来敲门）。
        task = request("GET", "/tasks/{}".format(task_id))["task"]

    for artifact in task.get("artifacts", []):
        print("交付物[{}]：{}".format(artifact["name"], artifact["parts"][0]["text"]))


if __name__ == "__main__":
    main()
```

**整个客户端的主循环就是那个 `while`，一共三种分支**：到终态就收工；对方在问你就答了再送回去；还在干活就等一会儿再看。**A2A 的客户端逻辑，本质上就是一个状态机。**

### 19.7.3 跑起来会看到什么

```text
找到 Agent：档案检索助手（1.0.0）
  简介：只做一件事：把一份复杂档案查清楚并交回结论，不写报告。
  技能：复杂档案检索 — 给定档案主题与年份范围，检索并汇总成结构化结论。
  接口：HTTP+JSON http://127.0.0.1:9000（协议 1.0）

派活：查一份 2023 年的项目验收档案
  状态：TASK_STATE_INPUT_REQUIRED
  它反问：这份档案要限定年份范围吗？给我一个起止年份，我按范围查。
  状态：TASK_STATE_COMPLETED
交付物[检索结论]：已按「限定 2023 年 1 月到 6 月」检索完毕，命中 3 份相关文件。
```

**这一屏输出里，`input-required` 那一行是全章最值钱的一行。** 19.1 那四类故障里的第二类——"对方要反过来问"——在这一屏里被彻底解决了，而解决它的东西，是对方状态上的两个词加一段 JSON。

## 19.8 A2A 在 harness 里的位置

回到 17.4 那一格。harness 第 4 项职责「**协议接入**」的白话是"用公开协议把外部工具接进来"，Ch18 和 Ch19 正好各占一半：

```text
职责四 协议接入
├── 接工具    ← Ch18：给对方暴露一个函数，毫秒级返回，不需要中途问你
└── 接 Agent  ← Ch19（本）：给对方暴露一个独立程序，能派活、能中途问你、能跑很久
```

**为什么这两件事放在同一项职责下？** 因为它们受同一组约束：都需要一份公开约定让互不相识的两端对上，都需要把外部能力的接口从内部实现里剥开，都需要能力声明与鉴权信息，也都要在它出事时查得出是谁接的。**换了协议，不换那套工程。**

也正因如此，A2A 引入了几个上一章没有的问题，而它们**每一个都对应着七大职责里的某一项**：

| A2A 带来的问题 | 归到哪项职责 | 去哪一章 |
|---|---|---|
| 派出去的活儿在对方机器上跑，出事怎么办 | 2 执行隔离 | Part 4 Ch21 |
| 中途冒出"要授权"的状态，谁来点这个头 | 1 工具与权限 | Part 4 Ch21 |
| 对方反问时，我这边该递哪些上下文过去 | 3 上下文与记忆 | Part 4 Ch20 |
| 任务状态是给对方看的，界面怎么呈现 | 7 投递接口 | 见 17.4.7 |

**本章到此只做一件事：讲清楚第 4 项职责的另一半。** 企业里怎么编排一群 Agent，见 Part 5。

## 本章小结

- 工具是一次调用，委派是一件事。当一个外部能力**需要自己做判断、需要一段时间、甚至需要反过来问人**，它就不再是工具，它是一个 Agent——这就是 A2A 存在的全部理由。
- A2A 只规定四个动作：怎么找到对方、怎么派活、怎么知道进度、怎么取成果。**它一概不问对方用什么模型、什么框架、什么工具。不问，才有互操作。**
- **Agent Card** 是固定地址 `/.well-known/agent-card.json` 上的一张自述页，`skills` 是它的正文。定死地址的价值是：调用方拿到域名就能接入，零配置，且对方的变更会通过这个地址自动传播。
- **任务（Task）**有八个状态：`submitted` / `working` / `input-required` / `auth-required` / `completed` / `failed` / `canceled` / `rejected`。其中 `input-required` 是 A2A 与工具调用最本质的差别——**它能让对方停下来问人，隔任意长时间再接着做。**
- **消息装过程，成果装交付**，两者分开，成果才有独立编号才能反复取。
- 分工一句话：**MCP 在 Agent 内部，A2A 在 Agent 之间。** 判据三条：它要自己做判断吗？它中途会反问我吗？它是别人写的、我改不动吗？
- A2A 与 MCP 共处第 4 项职责「协议接入」之下，是它的另一半，不是它的替代品。

## 与 Ch20 的衔接

把活儿派出去之后，一个新问题立刻冒出来：**派过去的那句话里，我该带多少自己的上下文过去？** 带少了对方接不住，带多了既烧钱又稀释注意力。这就是下一章的主题——上下文工程（见 Part 4 Ch20）。

## 本章参考

### 必读

本章全部协议事实以官方规范为准。以下是本章实际访问并逐条核对的页面：

- [A2A 协议官方站点](https://a2a-protocol.org)——规范与教程总入口。
- [A2A v1.0.0 规范全文](https://a2a-protocol.org/v1.0.0/specification/)——本章的 Agent Card 路径（§8.2）、任务状态（§4.1.3）、AgentCard 字段（§4.4.1）、AgentSkill 字段（§4.4.5）、HTTP 绑定路径（§5.3）、多轮交互示例（§6.3）均引自此页。
- [What's New in A2A Protocol v1.0](https://github.com/a2aproject/A2A/blob/v1.0.1/docs/whats-new-v1.md)——v0.3 到 v1.0 的逐项变更，含 `supportedInterfaces` 的合并与 `protocolVersion` 的下沉。
- [A2A v1.0 发布公告](https://github.com/a2aproject/A2A/blob/v1.0.1/docs/announcing-1.0.md)——"MCP inside agents, A2A between agents" 一句的出处。

### 推荐博客 / 教程

- [Agent Discovery 专题](https://github.com/a2aproject/A2A/blob/v1.0.1/docs/topics/agent-discovery.md)——三种发现方式与自述页的缓存、安全注意事项。
- [a2a-python SDK](https://github.com/a2aproject/a2a-python)——官方 Python SDK。本章示例为了不引入手册依赖，只用标准库手写。

### 视频 / 课程

本章无推荐视频。官方站点另附 [SDK 快速上手教程](https://github.com/a2aproject/A2A/tree/v1.0.1/docs/tutorials)，适合动手时对照。
