# runnable: no
# depends: chromadb openai
# usage: python naive_rag.py
#
# Ch23 23.9 的 Naive RAG 端到端。本书全程不执行代码，这份文件供逐行阅读。
# 真要跑起来需要：pip install chromadb openai，且设置 OPENAI_API_KEY。
# 下面三步（切块 → 建索引 → 检索）是这段代码的全部要点，
# 每一步都对应正文里的一张小图。

import os

import chromadb
import openai

COLLECTION = "handbook"
MODEL = "gpt-4o-mini"
EMBED_MODEL = "text-embedding-3-small"

# 一小段假装的手册原文。真实场景里这可以是几十份 PDF，
# 但流程一模一样：切块 → 向量化 → 检索。
DOCS = [
    "年假制度：入职满一年享有 5 天年假，满三年每年加 1 天，上限 15 天。",
    "报销制度：单笔超过 200 元的差旅需在出差结束后 30 天内提交发票。",
    "报销制度：餐费每人每天上限 100 元，需附带餐厅小票。",
    "加班制度：工作日加班按 1.5 倍计加班费，休息日按 2 倍计。",
]


# ---- 第 1 段：切块（chunker）------

def split_text(text: str, size: int = 60, overlap: int = 15) -> list:
    """按字符数切块，相邻两块故意重叠一部分。

    重叠是为了防"一句话被切断"：切点两侧的半句话，
    因为重叠而至少有一块里是完整的。
    """
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start:start + size])
        start += size - overlap
    return chunks


def build_index(chunks: list, embed_fn) -> chromadb.Collection:
    """把每一块向量化后存进向量库。向量库对外只暴露一个接口：按向量找最近的 k 块。"""
    client = chromadb.Client()
    col = client.get_or_create_collection(COLLECTION)
    vectors = embed_fn(chunks)
    col.add(ids=[str(i) for i in range(len(chunks))],
            documents=chunks, embeddings=vectors)
    return col


# ---- 第 2 段：检索（retriever）------

def retrieve(col, query: str, embed_fn, top_k: int = 2) -> list:
    """把问题也向量化一次，然后要回最相似的几块。"""
    qv = embed_fn([query])[0]
    return col.query(query_embeddings=[qv], n_results=top_k)["documents"][0]


# ---- 第 3 段：把检索结果塞进提示词，然后交给模型作答 ----

PROMPT = """你是公司的行政助手。只根据下面这几段原文回答，
原文里没有的信息一律回答"这个我不确定，去问 HR"。

原文：
{context}

问题：{question}
"""


def answer(context_chunks: list, question: str) -> str:
    context = "\n".join(f"- {c}" for c in context_chunks)
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user",
                   "content": PROMPT.format(context=context, question=question)}],
    )
    return resp.choices[0].message.content


# ---- 第 4 段：入口 ----

def main():
    embed_fn = lambda texts: openai.OpenAI(
        api_key=os.environ["OPENAI_API_KEY"]
    ).embeddings.create(model=EMBED_MODEL, input=texts).data  # 真机上换成能吐出向量的调用

    chunks = [c for d in DOCS for c in split_text(d)]
    col = build_index(chunks, embed_fn)
    hit = retrieve(col, "出差住宿费怎么报？", embed_fn)
    print(answer(hit, "出差住宿费怎么报？"))


if __name__ == "__main__":
    main()