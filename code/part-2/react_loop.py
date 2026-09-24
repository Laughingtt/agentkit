# runnable: yes
# 最小 ReAct 循环（Ch10 配套示例）
# 依赖：Python >= 3.10，仅标准库；用规则模拟 LLM 的 Thought/Action 决策，不依赖外部 API
# 目的：让读者看见 Thought -> Action -> Observation 三步循环的真实数据流

# ---------- 两个模拟工具 ----------
def search(query: str) -> str:
    """检索工具：从内置小知识库里找事实"""
    kb = {"法国首都": "法国的首都是巴黎，人口约 210 万"}
    for key, fact in kb.items():
        if key in query:
            return fact
    return "没查到。"


def calc(expr: str) -> str:
    """计算工具：支持 a + b / a * b（仅演示，生产环境勿用 eval）"""
    try:
        return str(eval(expr, {"__builtins__": {}}, {}))
    except Exception:
        return "算式无法解析。"


TOOLS = {"search": search, "calc": calc}


# ---------- 用规则模拟 LLM 的"思考" ----------
def llm_decide(observations: list) -> str:
    """根据已有观察决定下一步。真实系统里这里是 LLM 补全。"""
    if not observations:
        return "Thought: 需要先知道巴黎人口\nAction: search: 法国首都人口"
    if len(observations) == 1:
        return "Thought: 拿到人口 210 万，接下来算两倍\nAction: calc: 210 * 2"
    return "Thought: 已经算出结果\nFinal Answer: " + observations[-1] + " 万"


# ---------- ReAct 主循环 ----------
def react(question: str, max_steps: int = 5) -> str:
    observations = []
    for _ in range(max_steps):
        decision = llm_decide(observations)
        print(decision)
        # 判断最后一行是否已是最终答案
        last_line = decision.splitlines()[-1]
        if last_line.startswith("Final Answer"):
            return last_line.replace("Final Answer: ", "")
        # 解析最后一行 "Action: tool_name: argument"
        tool_name, _, argument = last_line.replace("Action: ", "").partition(": ")
        observation = TOOLS[tool_name](argument.strip())
        observations.append(observation)
        print("Observation: " + observation)
    return "达到最大步数，未得到答案。"


if __name__ == "__main__":
    answer = react("法国首都人口的两倍是多少？")
    print("\n>>> " + answer)
