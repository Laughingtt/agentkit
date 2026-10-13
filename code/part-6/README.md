# Part 6 示意代码

> ⚠️ **本目录代码仅供阅读对照，不保证可直接运行。**
> 用户明令：**本书全程不执行任何代码文件**。所有代码核查由人工逐行静态推演完成。

## 文件清单

| 文件 | 对应章节 | 作用 |
|---|---|---|
| `langfuse_trace.py` | Ch29 | 一次 Agent 请求的 trace：root span → generation → tool span |
| `eval_pipeline.py` | Ch30 | 最小 LLM-as-judge 评测流水线（数据集 → 裁判 → 分数） |
| `redteam_basic.py` | Ch31 | 红队接入：对抗用例集 + 批量执行 |
| `router_demo.py` | Ch32 | 基于关键词 + 长度的规则路由器，以及四层缓存骨架 |

## 依赖（若你确实想跑）

```bash
pip install "langfuse>=3" openai anthropic opentelemetry-sdk \
            opentelemetry-exporter-otlp promptfoo
```

各文件的具体依赖写在文件头注释里。

## 约定

- 文件头三行：`# runnable: yes|no` / `# depends: <pkg>` / `# usage: python xxx.py`
- 注释用中文，说明**意图**而不是复述语法
- 正文引用代码时保持与本目录文件**逐字一致**（终审会做 md ↔ .py 对账）

## ⚠️ 关于版本与数据的时效性

这一 Part 的代码与正文涉及**大量随时间变化的外部信息**（SDK 版本、属性名、标准条款、平台数据）。写作时必须联网核实并在正文标注"截至本书写作时"，不要把某个具体版本的 API 当成不变的规范。