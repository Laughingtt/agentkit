# runnable: no
# depends: 无（纯标准库）
# usage: python memory_short_term.py
#
# Ch24 24.2 短时记忆：滑动窗口 + 观察遮罩。本书全程不执行代码，这份文件供逐行阅读。
#
# 短时记忆要解决的不是"记什么"，而是"窗口什么时候停"。它是一个对象，
# 不是 Ch20 里那个孤零零的 N。窗口对象只记三样东西：条目、预算、驱逐策略。
#
# 本文件刻意不 import 任何第三方库：窗口逻辑是外壳的一部分，
# 不该依赖任何一个向量库或检索库——换掉记忆后端不该改这个文件。

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

# 条目的三种 kind。分开的原因是：观察遮罩只对 observation 生效，
# 对 question 和 answer 生效会毁掉它们（下一节讲为什么）。
QUESTION = "question"
ANSWER = "answer"
OBSERVATION = "observation"


@dataclass
class Item:
    """窗口里的一条东西。

    kind 决定它走不走观察遮罩；
    payload 放原文（走遮罩之前）或处理后的文本（走遮罩之后）；
    handle 是取回句柄——大块内容被压缩后，句柄是把它完整取回来的唯一途径。
    """

    kind: str
    payload: str
    handle: str | None = None
    dropped_from_window: bool = False  # 已经离开窗口但还没被上层处理


@dataclass
class MaskPolicy:
    """观察遮罩的策略。三个字段对应正文 24.2 的三种处理手法。"""

    head_lines: int = 3      # 截断：留头几行
    tail_lines: int = 2      # 截断：留尾几行
    max_chars: int = 400     # 留头尾之后仍超长的，再压到这么多字
    normalize_failures: bool = True   # 归一：把五花八门的失败收敛成有限几种


@dataclass
class SlidingWindow:
    """滑动窗口。

    规则一句话：一直丢最旧的，直到回到预算内。
    唯一不能动的例外是第一条——那一行通常是用户的任务原话，
    丢了它，后面所有步骤都不知道自己在为谁干活。
    """

    budget: int
    items: list[Item] = field(default_factory=list)
    policy: MaskPolicy = field(default_factory=MaskPolicy)
    masked_count: int = 0

    # ---- 预算 ----

    def used(self) -> int:
        """当前占了几条。

        按条目数算，不按字符数。不同条目长度能差三个数量级
        （一句"好的"对上十万行日志），按字符数就得给每种条目定权重，
        权重还得随模型改 tokenize 方式而重写。按条目数是最稳的。
        """
        return len(self.items)

    # ---- 观察遮罩 ----

    def mask(self, item: Item) -> Item:
        """观察遮罩：工具吐回来的东西，先自己处理一遍再进历史。

        三种处理：
        1) 截断——留头尾、丢中间。留尾是必要的，很多错误信息在中后段。
        2) 归一——把失败收敛成有限几种形状，否则信号层认不出来。
        3) 结构化——抠出下一步真正要用的字段，其余留一个句柄。
        """
        lines = item.payload.splitlines()
        if len(lines) <= self.policy.head_lines + self.policy.tail_lines:
            text = item.payload
        else:
            head = lines[: self.policy.head_lines]
            tail = lines[-self.policy.tail_lines :]
            text = "\n".join(head + [f"  ...（省略 {len(lines) - len(head) - len(tail)} 行）"] + tail)

        if len(text) > self.policy.max_chars:
            text = text[: self.policy.max_chars] + " …（更早的内容见句柄）"

        if self.policy.normalize_failures and self._looks_like_failure(text):
            text = self._normalize_failure(text)

        self.masked_count += 1
        return Item(kind=item.kind, payload=text, handle=item.handle)

    def _looks_like_failure(self, text: str) -> bool:
        """极简的失败识别。真实系统里应该由工具自己的返回结构决定，
        而不是靠匹配字符串——这里只保留形状，判据交给工具层。"""
        head = text[:200].lower()
        return any(k in head for k in ("error", "traceback", "失败", "超时", "denied"))

    def _normalize_failure(self, text: str) -> str:
        """归一：把失败收敛成同一个形状。

        这一步是记忆和规划咬合的地方：历史里的失败长得一样，
        24.9 的信号层才判得出 RESULT_INVALID。收敛得越干净，
        升级信号的误判率越低。
        """
        kind = "未知失败"
        if "denied" in text.lower() or "权限" in text:
            kind = "权限不足"
        elif "超时" in text or "timeout" in text.lower():
            kind = "超时"
        return f"[失败：{kind}] {text[:120]}"

    # ---- 入队与驱逐 ----

    def append(self, item: Item) -> list[Item]:
        """追加一条，然后驱逐到预算内。返回被驱逐的条目。

        顺序很重要：遮罩发生在入队之前。窗口里永远不会出现
        没遮罩过的大块输出——不是"应该遮罩"，是压根没机会不遮罩。
        """
        if item.kind == OBSERVATION:
            item = self.mask(item)
        self.items.append(item)
        return self.evict()

    def evict(self) -> list[Item]:
        """驱逐：一直丢最旧的直到回到预算内；第一条永远不丢。

        「第一条不丢」不是优化是保底——那一行通常是用户的任务原话，
        丢了它，后面所有步骤都不知道自己在为谁干活。
        """
        dropped = []
        while self.used() > self.budget and len(self.items) > 1:
            dropped.append(self.items.pop(1))
        return dropped

    # ---- 给上层看 ----

    def render(self) -> list[dict[str, Any]]:
        """渲染成消息列表，交给 Part 4 Ch20 的装配管线。

        刻意不在这里做拼接和裁剪——那是 Ch20 20.3 的职责，
        本窗口只负责"手上有什么"。
        """
        return [
            {"role": "user" if it.kind == QUESTION else "assistant",
             "content": it.payload}
            for it in self.items
            if it.kind in (QUESTION, ANSWER)
        ] + [{"role": "user", "content": f"工具结果：{it.payload}"}
             for it in self.items if it.kind == OBSERVATION]


def demo() -> None:
    """把 24.2 那个预算 4 条的演法跑一遍。

    重点看第 5 轮：超预算时被丢掉的正好是 Q1——任务原点，
    这是滑窗最朴素也最危险的行为。正文给的补救是给第一条留保留位。
    """
    win = SlidingWindow(budget=4)
    win.append(Item(QUESTION, "这酒店要提前三天订"))
    win.append(Item(OBSERVATION, "查询返回 3 条结果\n" + "候选 A\n" * 20, handle="h://q/1"))
    win.append(Item(ANSWER, "最匹配是城南那家"))
    win.append(Item(QUESTION, "帮我订会议室"))
    dropped = win.append(Item(OBSERVATION, "查询返回 0 条结果\nError: 权限不足", handle="h://q/2"))
    print("被驱逐的：", [d.payload[:20] for d in dropped])
    print("窗口内的：", [i.kind for i in win.items])
    print(json.dumps(win.render(), ensure_ascii=False, indent=2)[:400])


if __name__ == "__main__":
    demo()
