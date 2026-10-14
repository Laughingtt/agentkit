# runnable: no
# depends: chromadb openai
# usage: python agentic_rag.py
#
# Ch23 23.11 的 Agentic RAG。核心只有一句话：
# 把"检索"从一条固定的流水线，降级成一个普通工具，交给模型自己决定调几次。
# 对照 naive_rag.py 看差异：那边是 retrieve() 被写死在 main 里；
# 这边 retrieve 变成了 TOOLS 里的一项，模型不点头就根本不发生。

import json
import os

import chromadb
import openai

MODEL = "gpt-4o-mini"
EMBED_MODEL = "text-embedding-3-small"
MAX_ROUNDS = 6

DOCS = [
    "年假制度：入职满一年享有 5 天年假，满三年每年加 1 天，上限 15 天。",
    "报销制度：单笔超过 200 元的差旅需在出差结束后 30 天内提交发票。",
    "报销制度：住宿费一线城市每晚上限 500 元，二线 400 元。",
    "加班制度：工作日加班按 1.5 倍计加班费，休息日按 2 倍计。",
    "试用期制度：试用期 3 个月，期间不享受年假，考核通过转正后按入职日折算年假。",
]


def embed(texts: list) -> list:
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [d.embedding for d in resp.data]


# ---- 第 1 段：索引（这一步和 Naive RAG 完全一样，是"基建"）------

def build_index() -> chromadb.Collection:
    col = chromadb.Client().get_or_create_collection("handbook")
    chunks = [c for d in DOCS for c in
              [d[i:i + 60] for i in range(0, len(d), 45)]]
    col.add(ids=[str(i) for i in range(len(chunks))],
            documents=chunks, embeddings=embed(chunks))
    return col


# ---- 第 2 段：检索工具的说明书（关键在 description，它就是给模型的"使用说明"）----

RETRIEVE_TOOL = {
    "type": "function",
    "function": {
        "name": "search_handbook",
        "description": (
            "检索公司员工手册。只有当问题涉及具体制度、金额、天数时才调用它。"
            "一次只问一个子问题；查完一轮如果信息还不够，换个说法再调一次。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "一个具体、制度导向的问题"},
                "top_k": {"type": "integer", "description": "返回几段，默认 3"},
            },
            "required": ["query"],
        },
    },
}


# ---- 第 3 段：工具实现 —— 注意它就是 naive_rag 里的 retrieve，掉了个马甲 ----

def search_handbook(col, query: str, top_k: int = 3) -> str:
    qv = embed([query])[0]
    hits = col.query(query_embeddings=[qv], n_results=top_k)["documents"][0]
    return json.dumps(hits, ensure_ascii=False)


# ---- 第 4 段：循环。和 tool_calling.py 是同一圈循环，区别只在工具是什么 ----

def run(col, question: str) -> str:
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    messages = [{"role": "user", "content": question}]
    for _ in range(MAX_ROUNDS):
        resp = client.chat.completions.create(
            model=MODEL, messages=messages, tools=[RETRIEVE_TOOL]
        )
        msg = resp.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))

        if not msg.tool_calls:
            return msg.content  # 收工

        results = []
        for call in msg.tool_calls:
            args = json.loads(call.function.arguments)
            results.append({
                "role": "tool", "tool_call_id": call.id,
                "content": search_handbook(col, **args),
            })
        messages.append({"role": "user", "content": results})
    return messages[-1]["content"]


def main():
    col = build_index()
    print(run(col, "我下个月出差，住宿和报销分别怎么规定？"))


if __name__ == "__main__":
    main()