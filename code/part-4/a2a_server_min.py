# illustrative only
"""
最小 A2A 服务端：放自述页、接单、停下来反问、交付成果。
Python 3.9+ 标准库。运行：python3 a2a_server_min.py
协议依据：A2A v1.0。教学示意，未做鉴权与重试，不要搬去生产。
"""

import json
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

BASE, VERSION = "http://127.0.0.1:9000", "1.0"
MEDIA = "application/a2a+json"

# 任务表。真实系统该落库——进度要能被后来的人查回来，这正是第六项职责要的留痕。
# 它不是协议字段：协议只规定状态怎么变，不规定你怎么记。
TASKS = {}


def now():
    """协议要求 ISO 8601、UTC、毫秒精度。"""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def agent_card():
    """对外的自述页。发现地址被规范定死，拿到域名就能找到你。"""
    return {
        "name": "档案检索助手",
        "description": "只做一件事：把一份复杂档案查清楚并交回结论，不写报告。",
        "version": "1.0.0",
        "supportedInterfaces": [
            {"url": BASE, "protocolBinding": "HTTP+JSON", "protocolVersion": VERSION}],
        "capabilities": {"streaming": False, "pushNotifications": False},
        "skills": [{
            "id": "archive_lookup", "name": "复杂档案检索",
            "description": "给定档案主题与年份范围，检索并汇总成结构化结论。"}],
    }


def start_task():
    """接单：先返回"处理中"，干到一半才可能回头问人。"""
    task = {"id": str(uuid.uuid4()),
            "status": {"state": "TASK_STATE_WORKING", "timestamp": now()}}
    TASKS[task["id"]] = task
    return task


def ask_back(task, question):
    """停在"等你回话"上——这正是 A2A 与工具调用的分水岭。"""
    task["status"] = {"state": "TASK_STATE_INPUT_REQUIRED", "timestamp": now(),
                      "message": {"role": "ROLE_AGENT", "parts": [{"text": question}]}}


def deliver(task, answer):
    """交付。产出物用 artifact 装，和过程中的对话分开存放。"""
    task["status"] = {"state": "TASK_STATE_COMPLETED", "timestamp": now()}
    task["artifacts"] = [{"artifactId": str(uuid.uuid4()), "name": "检索结论",
                          "parts": [{"text": answer}]}]


class Handler(BaseHTTPRequestHandler):
    def reply(self, code, body):
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", MEDIA)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def not_found(self):
        # 协议规定错误响应用 problem+json
        self.reply(404, {"title": "Not Found", "status": 404})

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/.well-known/agent-card.json":
            self.reply(200, agent_card())
            return
        if path.startswith("/tasks/"):
            task = TASKS.get(path[len("/tasks/"):])
            self.reply(200, {"task": task}) if task else self.not_found()
            return
        self.not_found()

    def do_POST(self):
        if self.path.split("?")[0] != "/message:send":
            self.not_found()
            return
        # 真实实现还必须校验 A2A-Version 请求头
        n = int(self.headers.get("Content-Length", "0"))
        msg = json.loads(self.rfile.read(n) or b"{}").get("message", {})
        text = "".join(p.get("text", "") for p in msg.get("parts", []))
        task_id = msg.get("taskId")

        # 整个 A2A 的会话逻辑，就是下面这一个字段
        if task_id is None:
            task = start_task()
            ask_back(task, "这份档案要限定年份范围吗？给我一个起止年份。")
        else:
            task = TASKS.get(task_id)
            if task is None:
                self.not_found()
                return
            deliver(task, "已按「{}」检索完毕，命中 3 份相关文件。".format(text))
        self.reply(200, {"task": task})


if __name__ == "__main__":
    print("示例服务端：{}  自述页：{}/.well-known/agent-card.json".format(BASE, BASE))
    HTTPServer(("127.0.0.1", 9000), Handler).serve_forever()
