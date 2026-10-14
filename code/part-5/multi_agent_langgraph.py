# runnable: no
# depends: 无（只用标准库 json / typing）
# usage: python multi_agent_langgraph.py
"""自研极简图式编排：把 Agent 当状态机节点，循环就是图上的一条回边。

和 multi_agent_crew.py 的区别只有一句话：
角色式把「谁在什么时候干什么」写死在一份任务清单里；
图式把状态显式地摊开，让「下一步去哪个节点」变成一次可判定的转移。

这里刻意用最笨的实现——状态就是一个普通 dict，节点就是一个函数，
边就是两个 if。这样你读完之后，换到任何一个真框架上都能对上号。
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional

State = Dict[str, Any]
Node = Callable[[State], State]

# 一次节点执行之后的现场快照，就是这里的数据形状
INITIAL: State = {
    "task": "",            # 用户的原始要求
    "plan": "",            # 规划节点写进来的步骤清单
    "code": "",            # 编码节点写进来的产物
    "test_report": "",     # 检查节点写进来的结论
    "attempts": 0,         # 循环已经转了几圈——这是唯一的循环计数器
    "history": [],         # 每一步的 (节点名, 摘要)，相当于黑匣子
    "status": "pending",   # pending / done / failed
}


def _record(state: State, node: str, summary: str) -> State:
    state["history"].append((node, summary[:80]))
    return state


# ---------- 节点：每个节点只做一件事，读 state 改 state ----------

def node_plan(state: State, llm) -> State:
    """规划：把一句需求拆成可执行的步骤。"""
    out = llm(f"任务：{state['task']}\n请拆成 2-4 步，每行一步。")
    state["plan"] = out
    return _record(state, "plan", out)


def node_code(state: State, llm) -> State:
    """实现：按计划产出东西。第一轮参考计划，之后参考检查意见。"""
    hint = state["plan"] if state["attempts"] == 0 else state["test_report"]
    out = llm(f"任务：{state['task']}\n计划：{state['plan']}\n"
              f"上一轮意见：{hint}\n请产出。")
    state["code"] = out
    return _record(state, "code", out)


def node_check(state: State, llm) -> State:
    """检查：只回答通过 / 不通过，以及不通过的原因。"""
    out = llm(f"检查这份产出：\n{state['code']}\n只回答 PASS 或 FAIL 加一句原因。")
    state["test_report"] = out
    return _record(state, "check", out)


def node_finish(state: State, llm) -> State:
    """收尾：把最终产出放进结果字段，终结循环。"""
    state["status"] = "done" if state["test_report"].startswith("PASS") else "failed"
    return _record(state, "finish", state["status"])


# ---------- 边：决定下一步去哪个节点 ----------

NODES: Dict[str, Node] = {
    "plan": node_plan,
    "code": node_code,
    "check": node_check,
    "finish": node_finish,
}

# 静态边：绝大多数时候，图是这么走的
STATIC_EDGES = {
    "start": "plan",
    "plan": "code",
    "check": "finish",      # 默认走收尾；要回头得靠动态边推翻它
}

MAX_ATTEMPTS = 3            # 循环硬上限：回环必须有刹车


def route(state: State) -> str:
    """动态边：这张表的返回值就是下一个节点名。

    循环就是这里的一个分支——check 不通过且没超次数，就退回 code 重来。
    """
    if state["status"] != "pending":
        return "finish"
    if state["test_report"].startswith("PASS"):
        return "finish"
    if state["attempts"] >= MAX_ATTEMPTS:
        return "finish"
    return "code"


def run(initial: State, llm: Callable[[str], str],
        checkpoint: Optional[Callable[[str, State], None]] = None,
        max_steps: int = 12) -> State:
    """图遍历：状态机就是一个 while 循环加一张转移表。"""
    state = dict(initial)
    state["history"] = list(initial.get("history", []))
    node = "plan"
    steps = 0

    while steps < max_steps:                       # 第二道刹车：总步数上限
        target = route(state) if node == "check" else STATIC_EDGES.get(node)
        if target is None:
            raise ValueError(f"节点 {node} 没有出边，图写死了")

        if node == "check" and target == "code":
            state["attempts"] += 1                 # 唯一一处状态自增
            state["plan"] = state["plan"]          # 计划不变：改的是产出，不是目标

        state = NODES[node](state, llm)
        steps += 1
        if checkpoint:                             # 每个节点后存一次快照
            checkpoint(node, state)
        node = target

    state["status"] = "done" if state["status"] == "pending" else state["status"]
    return state


# ---------- 检查点：状态存一份，重启从最近一份接着跑 ----------

class FileCheckpoint:
    """把每次快照写成一个 JSON 文件，文件名带步数方便事后回看。"""

    def __init__(self, prefix: str = "run"):
        self.prefix = prefix
        self.saved: List[str] = []

    def __call__(self, node: str, state: State) -> None:
        path = f"{self.prefix}.{len(self.saved):02d}.{node}.json"
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({k: v for k, v in state.items()}, fh,
                      ensure_ascii=False, indent=2)
        self.saved.append(path)


def resume_from(path: str) -> State:
    """从一份快照恢复。恢复时只恢复状态，不恢复调用栈——这正是重试范围可控的原因。"""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ---------- 占位模型：真实项目里把这里换成真的客户端 ----------

def demo_llm(prompt: str) -> str:
    return f"[占位输出] 输入 {len(prompt)} 字符"


if __name__ == "__main__":
    ckpt = FileCheckpoint("graph_demo")
    result = run({"task": "写一个贪心排序", **INITIAL}, demo_llm, ckpt)
    print(json.dumps({"status": result["status"],
                      "attempts": result["attempts"],
                      "history": result["history"]},
                     ensure_ascii=False, indent=2))
    print("检查点文件：", ckpt.saved)
