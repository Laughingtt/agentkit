# illustrative only
# Ch12 示意代码：Plan-and-Execute 三段式状态机
# 纯标准库；三个角色都用假实现，目的是让"先规划、再执行、边执行边重规划"
# 这条骨架一眼看得见——真实系统里，planner / executor 里跑的是大模型。
# 跑一遍你会看到：B 家第一次取价返回空值 → 升级信号触发 → planner 改写了清单。

PLAN = {
    "目标": "比较两家云厂商的按月价格，选出更便宜的一家",
    "步骤": ["fetch_price(A)", "fetch_price(B)", "compare(A, B)"],
    "已完成": [],
    "结果": {},
    "重规划次数": 0,
}


def planner(state, observation):
    """重规划器：拿到上一步的观察后决定下一步；没有待办步骤就返回 None。

    三份工按顺序：① 归档观察 → ② 判升级信号、必要时改写清单 → ③ 挑下一个待办。
    第 ② 步就是"重规划"的全部——它只改 state["步骤"] 这一个字段。
    """
    # ① 归档：观察挂在"刚做完的那一步"上，所以最后一步的结果也查得到
    if observation is not None and state["已完成"]:
        state["结果"][state["已完成"][-1]] = observation

    # ② 重规划：升级信号触发时，把清单里那一条换掉（换数据源再取）
    if observation == "取价失败" and "fetch_price(B)" in state["步骤"]:
        i = state["步骤"].index("fetch_price(B)")
        state["步骤"][i] = "fetch_price(B, 备用源)"
        state["重规划次数"] += 1

    # ③ 挑下一个待办；没有待办 → 规划结束
    pending = [s for s in state["步骤"] if s not in state["已完成"]]
    return pending[0] if pending else None


def executor(step):
    """执行器：真实系统里这里调工具；示意版直接回一个假结果。

    B 家第一次取价返回空值，模拟数据源故障——这正是重规划器的触发场景。
    """
    fake = {
        "fetch_price(A)": "A: ￥120/月",
        "fetch_price(B)": None,                      # 第一次取 B 家：数据源故障
        "fetch_price(B, 备用源)": "B: ￥98/月",        # 换源再取：成功
        "compare(A, B)": "结论：选 B",
    }
    if step not in fake:
        raise ValueError(f"未知步骤：{step}")
    if fake[step] is None:
        return "取价失败"                            # 归一层把空值归一成一条信号
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
