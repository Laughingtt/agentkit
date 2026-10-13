# illustrative only
# depends: Python 3.10+ 标准库（json / subprocess / pathlib），不装任何第三方包
# usage: `python3 mcp_client_min.py`
#        它会按 stdio 传输拉起同目录的 mcp_server_min.py，
#        依次做：能力发现 → 列工具 → 调一次工具，并把三步打印出来。
#
# Ch18 18.8 的最小 MCP client。真实产品里这一层由 SDK 提供，
# 这里手写是为了让每一步都看得见。
#
# 最重要的一条：客户端的每个动作都只是「发一条请求、读一条响应」。
# 2026-07-28 版没有握手——不再有"先初始化再干活"这一步。

import json
import subprocess
import sys
from pathlib import Path

PROTOCOL_VERSION = "2026-07-28"
SERVER_SCRIPT = Path(__file__).with_name("mcp_server_min.py")


class StdioClient:
    """最小客户端：把请求写成一行 JSON 给子进程，再读回一行 JSON。"""

    def __init__(self, command):
        self.proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr,          # 服务端的日志走 stderr，不污染协议流
            text=True,
            encoding="utf-8",
        )
        self._next_id = 0

    def _new_id(self):
        """每个请求都要一个不重复的 id——响应靠它跟请求配对。"""
        self._next_id += 1
        return f"req-{self._next_id}"

    def request(self, method, params=None):
        # 每一行请求都自带这几样，这是 2026-07-28 版的核心变化：
        # 协议版本、客户端身份、客户端能力，都随请求走，而不是靠一次握手定下来。
        meta = {
            "io.modelcontextprotocol/protocolVersion": PROTOCOL_VERSION,
            "io.modelcontextprotocol/clientInfo": {"name": "demo-host", "version": "0.1.0"},
            "io.modelcontextprotocol/clientCapabilities": {},
        }
        payload = dict(params or {})
        payload["_meta"] = meta

        msg = {"jsonrpc": "2.0", "id": self._new_id(), "method": method, "params": payload}
        self.proc.stdin.write(json.dumps(msg, ensure_ascii=False) + "\n")
        self.proc.stdin.flush()

        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError("服务端没有回答就退出了")
        return json.loads(line)

    def close(self):
        self.proc.stdin.close()
        self.proc.wait(timeout=5)


def main():
    client = StdioClient([sys.executable, str(SERVER_SCRIPT)])

    # 第一步：能力发现（2026-07-28 版里服务端必须实现，客户端可选调用）
    info = client.request("server/discover")
    result = info["result"]
    print(f"[1] 服务端身份：{result['_meta']['io.modelcontextprotocol/serverInfo']}")
    print(f"    支持的协议版本：{result['supportedVersions']}")
    print(f"    声明的能力：{sorted(result['capabilities'].keys())}")

    # 第二步：列工具。宿主把这份清单转成模型能读的描述，塞进每一轮上下文。
    tools = client.request("tools/list")["result"]["tools"]
    print(f"[2] 这个 server 一共有 {len(tools)} 个工具：")
    for t in tools:
        required = t["inputSchema"].get("required", [])
        print(f"    - {t['name']}：{t['description']}（必填参数：{required}）")

    # 第三步：真调一次。模型给的是意图和参数，"要不要真执行"由宿主判定——
    # 这一步属于职责一，Ch18 不展开。
    call = client.request(
        "tools/call",
        {"name": "search_notes", "arguments": {"keyword": "协议"}},
    )
    if "error" in call:
        print(f"[3] 调用失败：{call['error']['message']}")
    else:
        print(f"[3] 调用结果（resultType={call['result']['resultType']}）：")
        for block in call["result"]["content"]:
            print("    " + block["text"])

    client.close()


if __name__ == "__main__":
    main()
