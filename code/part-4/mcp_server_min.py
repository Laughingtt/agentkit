# illustrative only
# depends: Python 3.10+ 标准库（json / sys），不装任何第三方包
# usage: 通常由 mcp_client_min.py 以子进程方式拉起（走 stdio 传输）；
#        想手工看一眼：把一段 JSON-RPC 请求写进文件，
#        然后 `python3 mcp_server_min.py < in.jsonl`，逐行读它的回答。
#
# Ch18 18.8 的最小 MCP server。它只干三件事，其余一律不实现：
#   1. server/discover —— 把自己支持哪个协议版本、有哪些能力报出去
#   2. tools/list      —— 把工具清单列出来（模型据此决定能调什么）
#   3. tools/call      —— 把一次调用真正跑完，返回结果
#
# 消息格式严格照 2026-07-28 版规范，有两处最容易写错，先记住：
#   · 每条请求都自带 _meta（协议版本 + 客户端能力）——协议不再靠握手协商
#   · 每条成功返回都自带 resultType（"complete" 或 "input_required"）

import json
import sys

PROTOCOL_VERSION = "2026-07-28"
SERVER_INFO = {"name": "notes-demo", "version": "0.1.0"}

# ---- 工具清单 -----------------------------------------------------------
# 一个工具 = 名字 + 一句用途 + 一份参数说明 + 一个普通 Python 函数。
# 模型能看见的只有前三样；第四样是它被叫到时真正跑的东西。
# 参数说明用的是 JSON Schema——所以宿主不必写代码去解析说明，交给模型读。

TOOLS = [
    {
        "name": "search_notes",
        "title": "搜索笔记",
        "description": "在笔记库里按关键词查找，返回命中的标题和摘要。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "要搜的关键词"},
                "limit": {"type": "integer", "description": "最多返回几条", "default": 5},
            },
            "required": ["keyword"],
        },
    },
    {
        "name": "read_note",
        "title": "读一篇笔记",
        "description": "按标题取回一篇笔记的全文。",
        "inputSchema": {
            "type": "object",
            "properties": {"title": {"type": "string", "description": "笔记标题"}},
            "required": ["title"],
        },
    },
    {
        "name": "create_note",
        "title": "新建笔记",
        "description": "新建一篇笔记。会改动外部世界，所以宿主通常会先问人。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["title", "body"],
        },
    },
]

# ---- 数据：拿一个内存字典当数据库，省得引依赖 ---------------------------

NOTES = {
    "周会纪要": "周三例会。结论：MCP 的传输层先定 stdio 与 HTTP 两条线。",
    "读书笔记": "《协议设计》第 3 章：弃用要给迁移时钟，不要给静默删除。",
}


def _text_result(text):
    """所有成功返回都长这样：resultType 标结果类型，content 里装内容块。"""
    return {"resultType": "complete", "content": [{"type": "text", "text": text}]}


def call_search_notes(params):
    args = params.get("arguments", {})
    keyword = args.get("keyword", "")
    limit = args.get("limit", 5)
    hits = [t for t in NOTES if keyword in t]
    if not hits:
        return _text_result("没有命中任何笔记。")
    body = "\n".join(f"- {t}：{NOTES[t][:20]}…" for t in hits[:limit])
    return _text_result(f"命中 {len(hits)} 篇：\n{body}")


def call_read_note(params):
    title = params.get("arguments", {}).get("title", "")
    if title not in NOTES:
        return _text_result(f"没有名为「{title}」的笔记。")
    return _text_result(NOTES[title])


def call_create_note(params):
    args = params.get("arguments", {})
    title, body = args.get("title", ""), args.get("body", "")
    NOTES[title] = body
    return _text_result(f"已创建「{title}」。")


HANDLERS = {
    "search_notes": call_search_notes,
    "read_note": call_read_note,
    "create_note": call_create_note,
}

# ---- 能力发现：这一条在 2026-07-28 版里是强制的 --------------------------


def handle(req):
    """把一条请求变成一条响应。返回值永远是 dict，直接序列化即可。"""
    method = req.get("method", "")
    params = req.get("params", {})
    rid = req.get("id")

    if method == "server/discover":
        return {
            "jsonrpc": "2.0",
            "id": rid,
            "result": {
                "resultType": "complete",
                "supportedVersions": [PROTOCOL_VERSION],
                "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
                "_meta": {"io.modelcontextprotocol/serverInfo": SERVER_INFO},
                "instructions": "一个演示用的笔记库。改动写操作前请先问人。",
            },
        }

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": rid,
            "result": {"resultType": "complete", "tools": TOOLS},
        }

    if method == "tools/call":
        name = params.get("name", "")
        handler = HANDLERS.get(name)
        if handler is None:
            # 工具不存在：用 JSON-RPC 的标准错误码，别自己编一个
            return {
                "jsonrpc": "2.0",
                "id": rid,
                "error": {"code": -32601, "message": f"没有这个工具：{name}"},
            }
        return {"jsonrpc": "2.0", "id": rid, "result": handler(params)}

    return {
        "jsonrpc": "2.0",
        "id": rid,
        "error": {"code": -32601, "message": f"未实现的方法：{method}"},
    }


# ---- stdio 传输：一行一条 JSON，stdin 进、stdout 出 -----------------------


def main():
    # 请求里的 _meta 带协议版本；服务端据此判断来者是不是 2026 版。
    # 这里只做最基本的核对：版本不认识就报 -32022。
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            sys.stdout.write(
                json.dumps({"jsonrpc": "2.0", "id": None,
                            "error": {"code": -32700, "message": "不是合法的 JSON"}}) + "\n"
            )
            sys.stdout.flush()
            continue

        meta = req.get("params", {}).get("_meta", {})
        version = meta.get("io.modelcontextprotocol/protocolVersion")
        if version and version != PROTOCOL_VERSION:
            sys.stdout.write(
                json.dumps({"jsonrpc": "2.0", "id": req.get("id"),
                            "error": {"code": -32022,
                                      "message": f"不支持的协议版本：{version}"}}) + "\n"
            )
            sys.stdout.flush()
            continue

        sys.stdout.write(json.dumps(handle(req), ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
