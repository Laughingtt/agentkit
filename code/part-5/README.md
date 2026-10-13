# Part 5 示意代码

> ⚠️ **本目录代码仅供阅读对照，不保证可直接运行。**
> 用户明令：**本书全程不执行任何代码文件**。所有代码核查由人工逐行静态推演完成。

## 文件清单

| 文件 | 对应章节 | 作用 |
|---|---|---|
| `tool_calling.py` | Ch23 | 工具调用的最小闭环：声明 → 选工具 → 执行 → 回填 |
| `naive_rag.py` | Ch23 | 朴素 RAG：切块 → 向量检索 → 拼提示词 |
| `agentic_rag.py` | Ch23 | Agentic RAG：让模型自己决定检索几轮、何时停 |
| `memory_short_term.py` | Ch24 | 滑动窗口的短期记忆：写入、裁剪、摘要 |
| `memory_long_term.py` | Ch24 | 长期记忆：向量层 + 关系层的读写流水线 |
| `plan_and_execute.py` | Ch24 | Plan-and-Execute：先出计划，再逐步执行与 replan |
| `multi_agent_crew.py` | Ch25 | 顺序/层级协作的最小编排 |
| `multi_agent_langgraph.py` | Ch25 | 图式编排：状态在节点间流转与回环 |
| `code_exec_e2b.py` | Ch26 | 把「执行代码」做成工具：四档隔离的选型与契约 |
| `mcp_server.py` | Ch27 | 手写 MCP server：几个工具 + 启动 |
| `mcp_client.py` | Ch27 | 手写 MCP client：列出工具 + 调用 |
| `a2a_server.py` | Ch27 | 手写 A2A server：Agent Card + 任务执行器 |
| `a2a_client.py` | Ch27 | 手写 A2A client：拉卡片 + 发任务 + 收结果 |
| `x402_demo.py` | Ch27 | x402 支付式工具调用的流程示意 |

## 依赖（若你确实想跑）

```bash
pip install anthropic openai numpy chromadb langchain openai-embeddings
```

各文件的具体依赖写在文件头注释里。

## 约定

- 文件头三行：`# runnable: yes|no` / `# depends: <pkg>` / `# usage: python xxx.py`
- 单文件 ≤ 200 行
- 注释用中文，说明**意图**而不是复述语法
- 正文引用代码时保持与本目录文件**逐字一致**（终审会做 md ↔ .py 对账）