# illustrative only
# Ch14 示意代码：researcher + writer 两个 Agent 的最小消息传递
# 重点不是代码，是"交接"——上游的产出怎样成为下游的输入。


def researcher(task, search_fn):
    """研究 Agent：把任务拆成若干检索动作，把结果并成一份材料。"""
    findings = [search_fn(sub) for sub in task["拆解"]]
    return {"材料": findings, "交给": task["下游"]}


def writer(handoff, draft_fn):
    """写作 Agent：只做一件事——把上游材料变成一段成稿。"""
    return draft_fn(handoff["材料"])


def run(task, search_fn, draft_fn, send_fn):
    """主编排：上游产出交给下游，下游产出再回到调用方手里。"""
    handoff = researcher(task, search_fn)
    assert handoff["交给"] == "writer"     # 上游必须说清交给谁
    send_fn(handoff)                        # 这就是"发消息"这一步
    return writer(handoff, draft_fn)
