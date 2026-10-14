# runnable: no
# depends: 无（纯标准库）
# usage: python plan_and_execute.py
#
# Ch24 24.9 / 24.10 规划：Plan-and-Execute 的四个接口 + Reflection 的评审循环。
# 本书全程不执行代码，这份文件供逐行阅读。
#
# 这个文件里最重要的一件事不是算法，是「谁不许调模型」：
# judge() 是全链路唯一一处纯代码判据。模型只负责填内容和写清单，
# 「这条路是不是死了」这件事永远不交给模型判断。

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Protocol

# 停滞判据的硬阈值。写死在这里，不交给模型——这类阈值一旦让模型估，
# 它会在无解问题上给出「再试试」并一直试下去，直到超时。
STALL_LIMIT = 3


class EscalationSignal(Enum):
    """升级信号。有限、可枚举、能写成 if —— 这是它能被测试的前提。"""
    RESULT_INVALID = "result_invalid"      # 空值 / 报错 / 形状不对
    PREMISE_BROKEN = "premise_broken"      # 拿到了推翻前提的事实
    STALLED = "stalled"                    # 连续 N 步没有新信息


def judge(obs, stall_count):
    if obs.is_empty or obs.is_error:
        return EscalationSignal.RESULT_INVALID
    if obs.contradicts_plan:
        return EscalationSignal.PREMISE_BROKEN
    if stall_count >= STALL_LIMIT:           # 硬阈值，不交给模型判断
        return EscalationSignal.STALLED
    return None


@dataclass
class Observation:
    """一步执行的结果。执行器只负责产出它，不负责解释它。

    注意 judge() 排在它前面：信号判定不依赖任何数据结构的定义，
    它只读 obs 上的四个布尔。这是为了让「判据」这一层可以被单独测。
    """

    value: object = None
    is_empty: bool = False
    is_error: bool = False
    contradicts_plan: bool = False   # 这一条由工具或校验器标，不由模型说
    summary: str = ""


@dataclass
class Step:
    """清单上的一条。刻意拆成结构体而不是一整句 prompt 字符串：

    「这句话已经用过了」和「这句话真的完成了」是两件事，
    结构体才能让前者被程序判、后者被模型判。
    """

    action: str
    args: dict = field(default_factory=dict)
    note: str = ""          # 重规划时记下来的发现，避免下一轮重犯


class Planner(Protocol):
    def plan(self, goal: str, tools: list[str]) -> list[Step]: ...
    def replan(self, steps: list[Step], obs: Observation,
               signal: EscalationSignal) -> list[Step]: ...


class Executor(Protocol):
    def execute(self, step: Step) -> Observation: ...


@dataclass
class RunResult:
    plan: list[Step]
    results: dict[int, Observation]
    signals: list[EscalationSignal]
    answer: str

    @property
    def model_calls(self) -> int:
        """账单用。20 步机械任务的对照：裸 ReAct 约 21 次，这里约 2 次。"""
        return len(self.signals) + 2


def run(goal: str, tools: list[str], planner: Planner,
        executor: Executor) -> RunResult:
    """主循环。四个接口里只有 execute 是平凡的，难的是 replan 何时触发。

    循环变量刻意只有四个：清单、当前步、结果字典、停滞计数。
    不设「当前计划之外的知识」这种全局缓存——清单本身就是全部状态。
    """
    steps = planner.plan(goal, tools)
    results: dict[int, Observation] = {}
    signals: list[EscalationSignal] = []
    stall_count = 0

    while steps:
        step = steps[0]
        obs = executor.execute(step)
        results[len(results)] = obs
        stall_count = stall_count + 1 if obs.is_empty else 0

        signal = judge(obs, stall_count)
        if signal is not None:
            signals.append(signal)
            # 发现写进备注，否则下一轮重规划会重复犯同一个错。
            step.note = f"{signal.value}: {obs.summary}"
            steps = planner.replan(steps[1:], obs, signal)
            continue          # ← 第一处顺序：回到顶部再判一次

        # 第二处顺序：pop 写在信号检查之后。触发重规划时当前步没被划掉，
        # 因为它可能只是换了参数而不是做完了——留着它重规划器才知道试过了。
        steps.pop(0)

    return RunResult(plan=steps, results=results, signals=signals,
                     answer=finish(steps, results))


def finish(steps: list[Step], results: dict[int, Observation]) -> str:
    """收尾：把结果拼成答案。真实系统里这一步也要调模型，
    但它的输入是已经跑完的事实，不是在途判断。"""
    return "；".join(o.summary for o in results.values() if o.summary)


# ---- Reflection 的两件工具（24.10）----

@dataclass
class Review:
    """评审的输出必须是一个可比较的分数，不是一段评价。

    v2 存在不代表 v2 更好——生成式模型非常容易改 A 的时候弄坏 B。
    没有这个分数，修改循环只会把回退固化成最终产出。
    """

    issues: list[str]
    score: float          # 越高越差：缺陷条数 + 模型自评的加权

    @classmethod
    def from_issues(cls, issues: list[str], self_rating: float = 0.0) -> "Review":
        return cls(issues=issues, score=float(len(issues)) + self_rating)


def revise_once(draft: str, reviewer: Callable[[str], Review],
                reviser: Callable[[str, Review], str],
                accept_better_only: bool = True) -> str:
    """改一版，并且和改之前比分数。

    accept_better_only=True 时分数没下降就丢弃修改稿——两轮必须用同一个
    评审员、同一把尺子，否则比较本身不成立。
    """
    before = reviewer(draft)
    candidate = reviser(draft, before)
    after = reviewer(candidate)
    return candidate if after.score <= before.score else draft
