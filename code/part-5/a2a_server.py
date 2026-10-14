# runnable: no
# depends: 无（Python 3.10+ 标准库）
# usage: python a2a_server.py
"""
最小 A2A 服务端：一份自述页 + 三个 JSON-RPC 方法。

协议依据：A2A v1.0。
自述页路径 /.well-known/agent-card.json、任务状态值取自 v1.0 规范。

⚠️ 与 Part 4 那个 a2a_server_min.py 的两处有意差别：
   1) 未命中时返回标准 JSON-RPC 2.0 error object（规范 §9.5 的要求），
      而不是 problem+json —— 后者不是 A2A 的规范性错误格式。
   2) 方法走 JSON-RPC 的 SendMessage / GetTask，路径仍是 POST /message:send
      与 GET /tasks/{id}。

⚠️ 本文件由作者静态推演，未在真实环境运行过。
"""

import json
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

BASE = "http://127.0.0.1:9100"
PROTOCOL_VERSION = "1.0"
RPC_PATH = "/message:send"
MEDIA = "application/a2a+json"

# 任务表。协议只规定状态怎么变，不规定你怎么记——真实系统该落库，
# 好让"后来的人"查得回来这条任务经历了什么。
TASKS: dict[str, dict] = {}


def now() -> str:
    """协议要求 ISO 8601、UTC、毫秒精度。"""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def agent_card() -> dict:
    """自述页。地址被规范定死，拿到域名就能找到你。"""
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "name": "行程整理助手",
        "description": "把一堆零散行程排成一份可执行的时间表，只排表不出门。",
        "version": "1.0.0",
        "url": BASE,
        "preferredTransport": "HTTP+JSON",
        "capabilities": {"streaming": False, "pushNotifications": False},
        "skills": [
            {
                "id": "itinerary",
                "name": "行程排程",
                "description": "输入若干条零散行程，输出一份带先后顺序与冲突提示的时间表。",
                "tags": ["travel", "planning"],
                "inputModes": ["text/plain"],
                "outputModes": ["text/markdown"],
            }
        ],
        # 鉴权方案在这里声明，客户端据此决定要不要先换票。演示用 Bearer 即可。
        "securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}},
    }


def _status(task: dict, state: str, message: str | None = None) -> dict:
    status = {"state": state, "timestamp": now()}
    if message:
        status["message"] = {"role": "ROLE_AGENT", "parts": [{"text": message}]}
    task["status"] = status
    return status


def send_message(params: dict) -> dict:
    """JSON-RPC 的 SendMessage：有 taskId 就是接话，没有就是开新单。"""
    message = params.get("message", {})
    text = "".join(p.get("text", "") for p in message.get("parts", []))
    task_id = message.get("taskId")

    if task_id is None:
        # 第一次派活：先承认收到，再把最该问的那一句问回去。
        task = {"id": str(uuid.uuid4()), "contextId": str(uuid.uuid4())}
        TASKS[task["id"]] = task
        _status(task, "TASK_STATE_SUBMITTED")
        _status(task, "TASK_STATE_INPUT_REQUIRED", "你打算哪天出发？我按这天重排一遍。")
        return task

    task = TASKS.get(task_id)
    if task is None:
        raise KeyError(task_id)

    _status(task, "TASK_STATE_COMPLETED")
    task["artifacts"] = [
        {
            "artifactId": str(uuid.uuid4()),
            "name": "行程表",
            "parts": [{"text": f"已按「{text}」排定：\n1. 09:00 出发\n2. 14:00 抵达"}],
        }
    ]
    return task


def get_task(params: dict) -> dict:
    """JSON-RPC 的 GetTask：客户端就是靠它轮询进度。"""
    task_id = params.get("id")
    task = TASKS.get(task_id)
    if task is None:
        raise KeyError(task_id)
    return task


class Handler(BaseHTTPRequestHandler):
    def _reply(self, code: int, body: dict) -> None:
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", MEDIA)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _rpc_error(self, rid, code: int, message: str) -> None:
        # 规范 §9.5：方法调用失败用标准 JSON-RPC 2.0 error object。
        self._reply(200, {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}})

    def do_GET(self) -> None:
        path = self.path.split("?")[0]
        if path == "/.well-known/agent-card.json":
            self._reply(200, agent_card())
        else:
            # REST 绑定下的资源式读取：GET /tasks/{id}
            if path.startswith("/tasks/"):
                task = TASKS.get(path[len("/tasks/"):])
                if task:
                    self._reply(200, {"task": task})
                    return
            self._rpc_error(None, -32601, f"未实现的路径：{path}")

    def do_POST(self) -> None:
        if self.path.split("?")[0] != RPC_PATH:
            self._rpc_error(None, -32601, f"未实现的路径：{self.path}")
            return

        length = int(self.headers.get("Content-Length", "0"))
        req = json.loads(self.rfile.read(length) or b"{}")
        rid, method, params = req.get("id"), req.get("method", ""), req.get("params", {})

        try:
            if method == "SendMessage":
                task = send_message(params)
            elif method == "GetTask":
                task = get_task(params)
            else:
                self._rpc_error(rid, -32601, f"未实现的方法：{method}")
                return
        except KeyError as exc:
            # 业务层找不到：-32001（server error），不占用标准码段。
            self._rpc_error(rid, -32001, f"没有这个任务：{exc}")
            return

        self._reply(200, {"jsonrpc": "2.0", "id": rid, "result": {"task": task}})


if __name__ == "__main__":
    print(f"自述页：{BASE}/.well-known/agent-card.json")
    HTTPServer(("127.0.0.1", 9100), Handler).serve_forever()