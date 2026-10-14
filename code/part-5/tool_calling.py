# runnable: no
# depends: anthropic
# usage: python tool_calling.py
#
# Ch23 23.4 的最小工具调用闭环。本书全程不执行代码，这份文件供逐行阅读。
# 真要跑起来需要两样东西：
#   1. 环境变量 ANTHROPIC_API_KEY
#   2. pip install anthropic
# 另外 23.5 讲并行调用时，要关掉并行得写
#   tool_choice={"type": "auto", "disable_parallel_tool_use": True}
# （它是 tool_choice 对象里的一个布尔字段，不在请求体顶层；
#   OpenAI 那一路是顶层一个 parallel_tool_calls=False。23.3.2 那张对照表的最后一行就是这件事。）

import json
import os

import anthropic

MODEL = "claude-sonnet-4-5"
MAX_ROUNDS = 8  # 循环的刹车：模型有可能一直调工具不收口

# ---- 第 1 段：工具说明书（这段是 23.2 的可视化，抄的就是"模型看到的那个数组"）----

TOOLS = [
    {
        "name": "get_weather",
        "description": "查询某个城市今天的天气。温度单位是摄氏度。",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "城市名，例如 北京"},
                "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
            },
            "required": ["city"],
        },
    },
    {
        "name": "search_docs",
        "description": "在公司内部文档里检索，返回最相关的若干段原文。",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "检索用的自然语言问题"},
                "top_k": {"type": "integer", "description": "要返回几段，默认 3"},
            },
            "required": ["query"],
        },
    },
]

# ---- 第 2 段：工具的实现（这段是外壳的活，模型看不见也管不着）----

def get_weather(city: str, unit: str = "celsius") -> dict:
    """这里本该去调气象 API。为了让文件能读懂，假装它返回了一个固定的字典。"""
    return {"city": city, "temp_c": 26, "condition": "晴"}


def search_docs(query: str, top_k: int = 3) -> list:
    """这里本该去查向量库。同样用假数据代替，形状要像真的。"""
    return [{"title": f"《{query}》相关片段", "snippet": "……正文……"}]


def dispatch(name: str, args: dict):
    """模型报上来的工具名和参数，在这里落地成一次真实的调用。"""
    if name == "get_weather":
        return get_weather(**args)
    if name == "search_docs":
        return search_docs(**args)
    raise ValueError(f"没有叫 {name} 的工具")


# ---- 第 3 段：那一圈循环（23.4 的主图就是这段代码画出来的）----

def run_loop(client, messages: list) -> list:
    for _ in range(MAX_ROUNDS):
        resp = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            tools=TOOLS,
            messages=messages,
        )
        # 模型这一轮可能说话，也可能点名要调工具。两样都要原样塞回对话里，
        # 因为下一轮它只能看见"已经发生过的事"。
        messages.append({"role": "assistant", "content": resp.content})

        calls = [b for b in resp.content if b.type == "tool_use"]
        if not calls:
            return messages  # 没有工具调用 = 模型收工了

        results = []
        for call in calls:
            try:
                out = dispatch(call.name, call.input)
                results.append(
                    {"type": "tool_result", "tool_use_id": call.id,
                     "content": json.dumps(out, ensure_ascii=False)}
                )
            except Exception as exc:  # 见 23.6：报错也要变成一段能喂回去的观察
                results.append(
                    {"type": "tool_result", "tool_use_id": call.id,
                     "content": f"调用失败：{exc}", "is_error": True}
                )
        messages.append({"role": "user", "content": results})
    return messages


# ---- 第 4 段：入口 ----

def main():
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    messages = [{"role": "user", "content": "北京今天多少度？顺便查一下报销标准。"}]
    run_loop(client, messages)
    print(messages[-1]["content"])


if __name__ == "__main__":
    main()