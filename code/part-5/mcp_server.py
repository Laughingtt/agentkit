# runnable: no
# depends: mcp>=2.0
# usage: python mcp_server.py
"""
最小 MCP 服务端：一次写齐三种活跃原语（tools / resources / prompts）。

协议依据：MCP 规范 2026-07-28 修订版（当前最新版）。
实现依据：官方 Python SDK 2.x。

⚠️ 一处最容易踩的版本坑（本书写作时 SDK 最新版为 2.3.0）：
   1.x 的 FastMCP 在 2.x 更名为 MCPServer，导入路径变成 mcp.server；
   mcp.server.fastmcp 这个模块在 2.x 已被删除，import 会直接抛
   ModuleNotFoundError 而不是 AttributeError。

⚠️ 本文件由作者静态推演，未在真实环境运行过；照抄前请先对着
   https://py.sdk.modelcontextprotocol.io/ 核对一遍 API。
"""

from mcp.server import MCPServer
from mcp.server.mcpserver import AssistantMessage, Message, UserMessage
from mcp.types import ToolAnnotations

# 构造函数只回答"我是什么"：名字、版本、给客户端看的一句话说明。
# 端口、路径这些"怎么被访问"的东西属于 run()，写在这里会直接 TypeError。
mcp = MCPServer(
    "读书笔记库",
    version="1.0.0",
    instructions="一个演示用的笔记库。改动写操作前请先问人。",
)

# ---- 记忆体。真实系统该落库，这里用模块级字典凑一个最小可读版本 ----
NOTES: dict[str, dict[str, str]] = {}


def _next_id() -> str:
    return f"n{len(NOTES) + 1:03d}"


# ============================================================
# 原语一：tools —— 模型决定要不要调
# 名字取自函数名，描述取自 docstring，入参 schema 由类型注解推出。
# annotations 是给客户端的"行为提示"，不是安全保证：
# 提示可以被无视，权限判定发生在宿主侧（见 Part 4 Ch21）。
# ============================================================


@mcp.tool(
    title="检索笔记",
    annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False),
)
def search_notes(keyword: str, limit: int = 5) -> str:
    """在笔记里按关键词检索，返回最多 limit 条的标题与 id。"""
    hits = [
        f"{nid}\t{note['title']}"
        for nid, note in NOTES.items()
        if keyword in note["title"] or keyword in note["body"]
    ]
    return "\n".join(hits[:limit]) or "没有命中"


@mcp.tool(
    title="新建笔记",
    annotations=ToolAnnotations(read_only_hint=False, idempotent_hint=False),
)
def create_note(title: str, body: str) -> str:
    """新建一条笔记，返回它的 id。"""
    note_id = _next_id()
    NOTES[note_id] = {"title": title, "body": body}
    return note_id


@mcp.tool()
def delete_note(note_id: str) -> str:
    """按 id 删除一条笔记，返回 deleted 或 not found。"""
    return "deleted" if NOTES.pop(note_id, None) else "not found"


# ============================================================
# 原语二：resources —— 应用决定端哪一份上来
# URI 是地址，返回值是内容，docstring 是简介。
# 关键一条：列表阶段不会执行你的函数，只有真的去读那个 URI 才执行。
# 所以你可以登记一千条资源，只有被人打开过的那几条会付出代价。
# ============================================================


@mcp.resource("notes://index")
def note_index() -> str:
    """当前所有笔记的清单，一行一条：id + 标题。"""
    return "\n".join(f"{nid}\t{note['title']}" for nid, note in NOTES.items()) or "（空）"


@mcp.resource("notes://{note_id}/body")
def note_body(note_id: str) -> str:
    """一条笔记的正文。URI 里的 {note_id} 必须和函数参数同名，否则导入即报错。"""
    note = NOTES.get(note_id)
    if note is None:
        raise ValueError(f"没有这条笔记：{note_id}")
    return note["body"]


@mcp.resource("notes://stats", mime_type="application/json")
def note_stats() -> dict[str, int]:
    """笔记条数。返回 dict 时 SDK 会序列化成 JSON 文本，mime_type 要自己声明。"""
    return {"count": len(NOTES)}


# ============================================================
# 原语三：prompts —— 人决定用不用
# 返回 str 就变成一条 user message；返回消息列表可以铺一段多轮对话的开头。
# get_prompt 的参数永远是 str -> str，所以这里的设计成"选哪个 id"。
# ============================================================


@mcp.prompt(title="两分钟读完一篇笔记")
def summarize(note_id: str) -> list[Message]:
    """生成一段"请把这篇笔记讲给我听"的多轮对话。"""
    note = NOTES.get(note_id, {"title": "（未命名）", "body": ""})
    return [
        UserMessage(f"先通读这篇《{note['title']}》，然后准备一段口头讲解。\n\n{note['body']}"),
        AssistantMessage("读完了，我准备好了。"),
        UserMessage("请讲一遍，控制在 120 字以内，不要罗列原文。"),
    ]


if __name__ == "__main__":
    # 不写参数就是 stdio：宿主把这个文件当子进程拉起，stdin/stdout 就是线路。
    # 想上端口就换成：
    #     mcp.run(transport="streamable-http", port=3001)
    # 客户端随后连 http://127.0.0.1:3001/mcp（默认路径就是 /mcp）。
    mcp.run()