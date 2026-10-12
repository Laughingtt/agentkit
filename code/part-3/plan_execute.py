# illustrative only
# Ch12 示意代码：Plan-and-Execute 三段式状态机
# 纯标准库；三个角色都用假实现，目的是让"先规划、再执行、边执行边重规划"
# 这条骨架一眼看得见——真实系统里，planner / executor 里跑的是大模型。

PLAN = {
    "目标": "比较两家云厂商的按月价格，选出更便宜的一家",
    "步骤": ["fetch_price(A)", "fetch_price(B)", "compare(A, B)"],
    "已完成": [],
    "结果": {},
}


def planner(state, observation):
    """重规划器：拿到上一步的观察后决定下一步；没有待办步骤就返回 None。"""
    pending = [s for s in state["步骤"] if s not in state["已完成"]]
    if not pending:
        return None                      # 没有待办 → 规划结束
    if observation:
        state["结果"][pending[0]] = observation
    return pending[0]


def executor(step):
    """执行器：真实系统里这里调工具；示意版直接回一个假结果。"""
    fake = {
        "fetch_price(A)": "A: ￥120/月",
        "fetch_price(B)": "B: ￥98/月",
        "compare(A, B)": "结论：选 B",
    }
    if step not in fake:
        raise ValueError(f"未知步骤：{step}")
    return fake[step]


def run(initial_state, max_steps=10):
    """主循环：规划 → 执行 → 把结果喂回规划器，最多 max_steps 步。"""
    state = initial_state
    step = planner(state, None)
    while step is not None and max_steps > 0:
        observation = executor(step)
        state["已完成"].append(step)
        step = planner(state, observation)
        max_steps -= 1
    return state
