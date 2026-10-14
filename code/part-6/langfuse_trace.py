# runnable: no
# depends: langfuse>=4.17.0
# usage: python langfuse_trace.py

"""把一次 Agent 请求的嵌套结构记录成一条可查询的 trace。

本文件不调用真实模型：`fake_llm` 是一个桩，代替各家模型 SDK 的调用。
这样读者可以把注意力放在"在哪一层开 observation、记哪些字段"这件事上，
而不被 API 的样板代码淹没。

跑起来需要三样东西，缺一样就会失败而不是静默跑过：

1. 一个可用的 trace 接收端。自托管用仓库自带的 docker compose 起一个，
   云端版则去控制台建项目；两者都要给你一对密钥。
2. 环境变量 LANGFUSE_PUBLIC_KEY 与 LANGFUSE_SECRET_KEY。
3. 自托管时再加一个 LANGFUSE_BASE_URL 指向本地地址，例如 http://localhost:3000；
   用云端版则留空，SDK 会走默认地址。

为什么标成 `# runnable: no`：它需要一个真实部署好的接收端才能看到数据，
光在本机跑一遍是看不到 trace 的，而 trace 正是这个文件要演示的东西。
"""

import time

from langfuse import get_client


# --- 桩：假装调了一次模型 -----------------------------------------------------
def fake_llm(prompt: str) -> tuple[str, dict]:
    """返回 (模型回答, usage_details)。

    三个键对应三类用量：input、output 是基础量，cache_read_input_tokens 是命中
    缓存的那部分（通常按更低的价计费）。漏记这一档，成本就算不准——见 29.8。
    """
    return "已收到：" + prompt, {
        "input": 1200,
        "output": 180,
        "cache_read_input_tokens": 640,
    }


def search_docs(query: str) -> list[str]:
    """假检索。特定查询下故意超时，好演示一层失败时 trace 长什么样。"""
    if "收费" in query:
        # 真实项目里这里是 HTTP 调用、超时、重试、退避；这里只保留结构
        raise TimeoutError("检索服务 3 秒内没返回")
    return ["doc-pricing-01", "doc-billing-02"]


# --- 主链路：with 块嵌套几层，trace 树就长几层 -------------------------------
def handle_user_request(client, question: str) -> str:
    """一次用户请求 = 一条 trace。层级关系由代码的嵌套关系自然形成。"""
    # 最外层：一层 span 覆盖用户的一次完整请求，是整条 trace 的根
    with client.start_as_current_observation(
        as_type="span",
        name="handle_user_request",
        input={"question": question},
        metadata={"release": "2026-10-13", "channel": "cli"},
    ) as root:
        # 第 1 段：规划。让模型决定这活儿要怎么干
        with client.start_as_current_observation(
            as_type="generation",
            name="plan",
            model="demo-model-small",
            input={"messages": [{"role": "user", "content": question}]},
            model_parameters={"temperature": 0.0, "max_tokens": 512},
        ) as plan:
            plan_text, plan_usage = fake_llm(question)
            # 用 update 而不是等退出代码块：出问题时这段也留在 trace 里
            plan.update(output=plan_text, usage_details=plan_usage)

        # 第 2 段：工具。工具失败不往上抛到根，只记在自己这一层
        with client.start_as_current_observation(
            as_type="tool",
            name="search_docs",
            input={"query": question},
        ) as tool:
            try:
                docs = search_docs(question)
                tool.update(output={"docs": docs})
            except TimeoutError as exc:
                # level 决定它算不算进错误率；status_message 保留原始原因
                tool.update(output={"error": str(exc)}, level="ERROR",
                            status_message=str(exc))
                raise

        # 第 3 段：拿检索结果去写最终答案
        with client.start_as_current_observation(
            as_type="generation",
            name="compose_answer",
            model="demo-model-large",
            input={"question": question, "retrieved": docs},
            model_parameters={"temperature": 0.2, "max_tokens": 800},
        ) as compose:
            answer, compose_usage = fake_llm(question)
            compose.update(output=answer, usage_details=compose_usage)

        root.update(output={"answer": answer})
        return answer


def main() -> int:
    client = get_client()

    # 问题里带"收费"两个字，会让下面的检索超时，用来演示失败路径
    for question in ("介绍 Agent 的计费方式", "帮我查一下 Agent 怎么收费"):
        started = time.perf_counter()
        try:
            answer = handle_user_request(client, question)
        except TimeoutError as exc:
            print(f"[失败] {exc}")
            print("       去 trace 界面上看 search_docs 这一层，它被标成了 ERROR")
        else:
            elapsed = (time.perf_counter() - started) * 1000
            print(f"[成功] {answer}（本地耗时 {elapsed:.0f} ms）")
        finally:
            # 短命进程必须在退出前把缓冲区倒空，否则这段 trace 会丢
            client.flush()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())