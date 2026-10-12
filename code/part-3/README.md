# Part 3 示例代码

依赖：

- Python ≥ 3.10
- 无第三方库（仅标准库）

**本目录所有代码均为示意代码（`# illustrative only`），用于让概念"看得见"，不是可运行的工程实现**；本书不执行这些代码。可运行的工程级实现在 Part 5。

| 文件 | 对应章节 | 说明 |
|---|---|---|
| [`plan_execute.py`](plan_execute.py) | Ch12 | Planner / Executor / Replanner 三段式状态机 |
| [`memory_store.py`](memory_store.py) | Ch13 | 记忆的写入、检索与衰减 |
| [`multi_agent_min.py`](multi_agent_min.py) | Ch14 | researcher → writer 的最小交接 |
| [`cascade_router.py`](cascade_router.py) | Ch15 | 便宜的判断先做、做不了才升级 |