# Part 4 示意代码

> ⚠️ **本目录代码仅供阅读对照，不保证可直接运行。**
> 用户明令：**本书全程不执行任何代码文件**。所有代码核查由人工逐行静态推演完成。

## 文件清单

| 文件 | 对应章节 | 作用 |
|---|---|---|
| `mcp_server_min.py` | Ch18 | 最小 MCP server：几个工具 + stdio 启动 |
| `mcp_client_min.py` | Ch18 | 最小 MCP client：列出工具 + 调用一次 |
| `a2a_server_min.py` | Ch19 | 最小 A2A server：Agent Card + 任务执行器 |
| `a2a_client_min.py` | Ch19 | 最小 A2A client：拉卡片 + 发任务 + 收结果 |
| `compaction_demo.py` | Ch20 | 上下文压缩：四种策略的骨架（示意） |
| `hooks_register.py` | Ch21 | 钩子注册：生命周期事件上的确定性回调 |
| `permission_policy.py` | Ch21 | 权限策略：allow / ask / deny 三档判定 |

## 依赖（若你确实想跑）

```bash
pip install "mcp[cli]" a2a-sdk httpx pyyaml fastapi uvicorn
```

各文件的具体依赖写在文件头注释里。

## 约定

- 文件头第一行标注 `# runnable: yes`（可运行）或 `# illustrative only`（仅示意）
- 注释用中文，说明**意图**而不是复述语法
- 正文引用代码时保持与本目录文件**逐字一致**（终审会做 md ↔ .py 对账）