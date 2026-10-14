# runnable: no
# depends: 无（只用标准库 dataclasses / json / concurrent.futures）
# usage: python multi_agent_crew.py
"""自研极简 Crew：角色 + 任务 + 三种执行形态，不依赖任何编排框架。

这个文件想说明的只有一件事——「角色式」多 Agent 的全部结构就是三样东西：

    角色（Role）    一段固定的身份说明，进每一次模型调用
    任务（Task）    一次要做的事，以及它依赖谁的结果
    编排（Crew）    按什么顺序把任务跑完，失败了怎么办

跑不了是因为 llm 只是一个可调用对象的占位：本书全程不执行代码，
需要你自己把它接到真实模型上。接法见文件末尾的 demo_llm。
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

# llm 就是一个「给它一段提示词、还你一段文字」的函数
LLM = Callable[[str], str]


# ---------- 一、角色：一段每次都要重复的身份说明 ----------

@dataclass
class Role:
    name: str
    goal: str
    backstory: str

    def system_prompt(self) -> str:
        # 关键：角色不是「换个模型」，而是「换个视角」——
        # 三段文本拼起来的提示词，就是这个角色的全部差别。
        return f"你是{self.name}。\n目标：{self.goal}\n背景：{self.backstory}"


# ---------- 二、任务：一次要做的事，以及它等谁 ----------

@dataclass
class Task:
    name: str
    description: str
    expected_output: str
    role: str
    depends_on: List[str] = field(default_factory=list)
    max_retries: int = 1


class TaskFailed(RuntimeError):
    """任务重试用尽仍然失败。它是编排层的信号，不是模型的问题。"""


# ---------- 三、拼提示词：把上游产物接进下游 ----------

def render_prompt(role: Role, task: Task, ctx: Dict[str, str],
                  inputs: Dict[str, str], feedback: str = "") -> str:
    parts = [role.system_prompt(), "", f"任务：{task.description}"]
    if inputs:
        parts.append("原始输入：" + json.dumps(inputs, ensure_ascii=False))
    if ctx:
        # 交接的全部秘密就在这几行：上游的输出，变成下游的输入。
        parts.append("你将收到这些上游产物：")
        for k, v in ctx.items():
            parts.append(f"[来自 {k}]\n{v}")
    if feedback:
        # 重试不是从零重来，而是带着上一轮的批评重来。
        parts.append(f"上一次没能通过，原因如下，请针对性修改：\n{feedback}")
    parts.append(f"交付要求：{task.expected_output}")
    return "\n".join(parts)


# ---------- 四、编排：Crew ----------

class Crew:
    def __init__(self, roles: List[Role], tasks: List[Task],
                 process: str = "sequential", manager: Optional[Role] = None):
        # process 三选一：sequential 顺序 / parallel 分组并行 / hierarchical 分层
        assert process in ("sequential", "parallel", "hierarchical")
        self.roles = {r.name: r for r in roles}
        self.tasks = {t.name: t for t in tasks}
        self.order = list(tasks)                  # 保持声明顺序
        self.process = process
        self.manager = manager
        for t in tasks:                           # 早期校验：依赖必须存在
            for dep in t.depends_on:
                assert dep in self.tasks, f"{t.name} 依赖了不存在的任务 {dep}"

    # 拓扑排序：算出每个任务在第几层（depends_on 最长路径 + 1）
    def _depth(self, name: str, seen: Optional[set] = None) -> int:
        seen = seen or set()
        if name in seen:                          # 环：直接报错，不要让死循环去烧钱
            raise ValueError(f"任务依赖成环，涉及 {name}")
        seen = seen | {name}
        deps = self.tasks[name].depends_on
        return 1 + max([self._depth(d, seen) for d in deps], default=-1)

    def _run_one(self, task: Task, ctx: Dict[str, str],
                 inputs: Dict[str, str], llm: LLM, log: List[str]) -> str:
        role = self.roles[task.role]
        feedback = ""
        for attempt in range(task.max_retries + 1):
            try:
                out = llm(render_prompt(role, task, ctx, inputs, feedback))
            except Exception as exc:              # 模型侧的崩，不该拖垮整组
                feedback = f"{type(exc).__name__}: {exc}"
                log.append(f"[{task.name}] 第 {attempt + 1} 次尝试异常：{feedback}")
                continue
            ctx[task.name] = out                  # 只写入成功的结果
            log.append(f"[{task.name}] 第 {attempt + 1} 次成功，产出 {len(out)} 字")
            return out
        raise TaskFailed(f"任务 {task.name} 重试 {task.max_retries} 次仍失败：{feedback}")

    def kickoff(self, inputs: Dict[str, str], llm: LLM) -> Dict[str, str]:
        ctx: Dict[str, str] = {}
        log: List[str] = []
        log.append(f"流程={self.process}，任务数={len(self.tasks)}")

        if self.process == "hierarchical":
            # 分层：主管先出计划，计划决定后面怎么派活。
            plan = llm(render_prompt(self.manager, Task(
                name="__plan__",
                description="把总目标拆成可交给下属的任务，并指明先后",
                expected_output="每行一个：<任务名>:<承担角色>:<交付物>",
                role=self.manager.name,
            ), ctx, inputs))
            log.append(f"主管计划：{plan}")
            self.order = self._order_from_plan(plan)

        if self.process == "parallel":
            # 并行：同一层的任务互不依赖，可以同时跑。
            layers: Dict[int, List[Task]] = {}
            for name in self.order:
                layers.setdefault(self._depth(name), []).append(self.tasks[name])
            for depth in sorted(layers):
                batch = layers[depth]
                log.append(f"第 {depth} 层并行 {len(batch)} 个任务")
                with ThreadPoolExecutor(max_workers=len(batch)) as pool:
                    futures = [pool.submit(self._run_one, t, ctx, inputs, llm, log)
                               for t in batch]
                    for t, f in zip(batch, futures):
                        f.result()
            return {"outputs": ctx, "log": log}

        # sequential 与 hierarchical 都走这条顺序路径
        for name in self.order:
            self._run_one(self.tasks[name], ctx, inputs, llm, log)
        return {"outputs": ctx, "log": log}

    def _order_from_plan(self, plan: str) -> List[str]:
        # 主管计划里出现的任务名，按它写的顺序重排；没提到的放最后。
        picked = [ln.split(":", 1)[0].strip()
                  for ln in plan.splitlines() if ln.strip()]
        hit = [n for n in picked if n in self.tasks]
        tail = [n for n in self.tasks if n not in hit]
        return hit + tail


# ---------- 五、一个能替换的假模型 ----------

def demo_llm(prompt: str) -> str:
    """占位实现：真实项目里把这里换成调用模型客户端的函数。"""
    return f"[占位输出] 这是一次模拟回答，输入长度 {len(prompt)} 字符。"


if __name__ == "__main__":
    roles = [
        Role("研究员", "找齐材料并标出哪些是事实、哪些是推测",
             "你做过大量文献工作，从不把推测写成事实。"),
        Role("写手", "把材料写成结构清晰的短文",
             "你写东西克制，从不加形容词。"),
        Role("审稿人", "挑出稿子里的逻辑漏洞与无依据的断言",
             "你只提可执行的意见：哪一句、为什么、怎么改。"),
    ]
    tasks = [
        Task("research", "围绕主题收集三条要点", "要点列表，注明来源", "研究员"),
        Task("draft", "把要点写成 300 字短文", "短文正文", "写手",
             depends_on=["research"]),
        Task("review", "挑出稿子里的漏洞", "意见列表", "审稿人",
             depends_on=["draft"], max_retries=2),
    ]
    crew = Crew(roles, tasks, process="sequential")
    result = crew.kickoff({"topic": "多 Agent 的误差放大"}, demo_llm)
    print(json.dumps(result["outputs"], ensure_ascii=False, indent=2))
