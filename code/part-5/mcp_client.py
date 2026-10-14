# runnable: no
# depends: mcp>=2.0
# usage: python mcp_client.py
"""
最小 MCP 客户端：发现 → 调用 → 处理结果。

⚠️ 本文件由作者静态推演，未在真实环境运行过。
它假设 mcp_server.py 已经以 streamable-http 方式起了端口（3001）。
"""

import asyncio
import json

from mcp import Client

SERVER_URL = "http://127.0.0.1:3001/mcp"


def show_tool(tool) -> str:
    """把一份工具定义压成一行人能读的摘要——宿主登记工具时干的也是这件事。"""
    return f"{tool.name}：{tool.description or '(无说明)'} 入参={json.dumps(tool.input_schema, ensure_ascii=False)}"


async def main() -> None:
    # 传一个 URL 字符串，Client 就按 Streamable HTTP 连——这是你部署时用的那种。
    async with Client(SERVER_URL) as client:
        # 第一步：发现。这一步拿回来的每一项，就是宿主要塞进工具清单的东西。
        listed = await client.list_tools()
        for tool in listed.tools:
            print("·", show_tool(tool))

        # 第二步：调用。注意失败不是一个异常，而是一个结果对象——先看 is_error。
        created = await client.call_tool(
            "create_note", {"title": "读后感", "body": "这本书让我重看了三遍目录。"}
        )
        if created.is_error:
            # is_error 为真时 structured_content 可能是 None，务必先判它。
            print("工具内部报错：", created.content)
            return
        note_id = created.structured_content["result"]
        print("建好了：", note_id)

        # structured_content 是给代码读的：它已经是结构化对象，不用再解析字符串。
        # content 是给模型读的。两者都在时是有意重复一次，不是冗余。
        found = await client.call_tool("search_notes", {"keyword": "目录", "limit": 3})
        print("检索结果（给模型的那份）：", found.content)
        print("检索结果（给代码的那份）：", found.structured_content)

        # 调一个不存在的工具，同样不会抛异常，返回的是同形状的结果对象。
        missing = await client.call_tool("no_such_tool", {})
        print("不存在的工具，is_error =", missing.is_error)

        # 第三步：资源。应用主动读，不由模型点名——这是它和工具的真正差别。
        resources = await client.list_resources()
        print("登记的资源：", [str(r.uri) for r in resources.resources])
        body = await client.read_resource(f"notes://{note_id}/body")
        # contents 是一个列表，按类型收窄后再取 .text 或 .blob。
        print("正文第一行：", body.contents[0].text.splitlines()[0])

        # 带占位符的资源不在 list 里，而在模板列表里。
        templates = await client.list_resource_templates()
        print("资源模板：", [t.uri_template for t in templates.resource_templates])

        # 第四步：提示模板。人来挑，参数永远是字符串。
        prompt = await client.get_prompt("summarize", {"note_id": note_id})
        print("渲染出的第一句话：", prompt.messages[0].content.text[:20])


async def via_stdio() -> None:
    """本地 server 不必先起端口——直接让 SDK 把它当子进程拉起来，走 stdio。"""
    from mcp import StdioServerParameters

    params = StdioServerParameters(command="python", args=["mcp_server.py"])
    async with Client(params) as client:
        print("stdio 下的工具数：", len((await client.list_tools()).tools))


async def in_process() -> None:
    """测试专用：直接把 server 对象塞给 Client，不开进程、不占端口。"""
    from mcp_server import mcp

    async with Client(mcp) as client:
        print("进程内调用的结果：", (await client.call_tool("search_notes", {"keyword": "x"})).content)


if __name__ == "__main__":
    asyncio.run(main())