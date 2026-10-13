# illustrative only
"""
最小 A2A 服务端（HTTP+JSON 绑定，只用标准库）

用途：演示一个"能被人委派的 Agent"最少的四件事——
      ① 在固定地址放一张自述页；② 接单并开工；③ 停下来反问；④ 交付成果。
依赖：Python 3.9+ 标准库，无第三方包。
运行：python3 a2a_server_min.py
      然后让 a2a_client_min.py 指向 http://127.0.0.1:9000

协议依据：A2A v1.0（写在请求头与卡片里的协议版本号就是 "1.0"）。
本文件是教学示意：没做鉴权、没做超时与重试、任务存在内存里进程一挂就没，
不要直接搬去生产。
"""

import json
import re
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

BASE = "http://127.0.0.1:9000"
A2A_VERSION = "1.0"
JSON_MEDIA = "application/a2a+json"

# 任务表：task_id -> task 对象。
# 真实系统里这份数据该落库，关键是"这件事的进度要能被后来的人查回来"，
# 而不是只活在一次函数调用里——这正是 harness 第六项职责要的留痕。
TASKS = {}

# 教学用的流水账，不是协议字段。协议只规定状态怎么变，不规定你怎么记。
LOG = []


def now():
    """协议要求时间戳是 ISO 8601、UTC、毫秒精度。"""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def build_agent_card():
    """对外的自述页。

    v1.0 规范把发现地址定死在 /.well-known/agent-card.json，
    调用方拿到域名就能找到你，一句配置都不用加。
    """
    return {
        "name": "档案检索助手",
        "description": "只做一件事：把一份复杂档案查清楚并交回结论，不写报告、不做决策。",
        "version": "1.0.0",
        "supportedInterfaces": [
            {
                "url": BASE,
                "protocolBinding": "HTTP+JSON",
                "protocolVersion": A2A_VERSION,
            }
        ],
        "capabilities": {"streaming": False, "pushNotifications": False},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "skills": [
            {
                "id": "archive_lookup",
                "name": "复杂档案检索",
                "description": "给定档案主题与年份范围，检索并汇总成结构化结论。",
                "tags": ["retrieval", "research"],
                "examples": ["查 2023 年 A 项目的三份验收报告"],
            }
        ],
    }


def start_task(request_text):
    """接单。返回一个新任务，此时它是"处理中"，还没问任何问题。"""
    task_id = str(uuid.uuid4())
    task = {
        "id": task_id,
        "contextId": str(uuid.uuid4()),
        "status": {"state": "TASK_STATE_WORKING", "timestamp": now()},
    }
    TASKS[task_id] = task
    LOG.append({"task": task_id, "event": "submitted", "text": request_text})
    return task


def ask_back(task, question):
    """把任务停在"等你回话"上。

    这是 A2A 和工具调用最本质的差别：对方不是一个函数，
    是一个会中途停下来、要人补一句才能继续的独立程序。
    """
    task["status"] = {
        "state": "TASK_STATE_INPUT_REQUIRED",
        "message": {"role": "ROLE_AGENT", "parts": [{"text": question}]},
        "timestamp": now(),
    }
    LOG.append({"task": task["id"], "event": "input-required", "text": question})


def deliver(task, answer):
    """交付成果。产出物用 artifact 装，和"对话过程中说的话"分开存放。"""
    task["status"] = {"state": "TASK_STATE_COMPLETED", "timestamp": now()}
    task["artifacts"] = [
        {
            "artifactId": str(uuid.uuid4()),
            "name": "检索结论",
            "parts": [{"text": answer}],
        }
    ]
    LOG.append({"task": task["id"], "event": "completed"})


class Handler(BaseHTTPRequestHandler):
    def _reply(self, code, body, media=JSON_MEDIA):
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", media)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _not_found(self):
        # 协议规定错误响应用 problem+json，不是随便一个 JSON
        self._reply(404, {"title": "Not Found", "status": 404}, "application/problem+json")

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/.well-known/agent-card.json":
            self._reply(200, build_agent_card())
            return
        matched = re.fullmatch(r"/tasks/([0-9a-fA-F-]+)", path)
        if matched:
            task = TASKS.get(matched.group(1))
            if task is None:
                self._not_found()
            else:
                self._reply(200, {"task": task})
            return
        self._not_found()

    def do_POST(self):
        if self.path.split("?")[0] != "/message:send":
            self._not_found()
            return

        # 真实实现必须在这里校验 A2A-Version 请求头，版本对不上要退回错误
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length) or b"{}")
        message = payload.get("message", {})
        text = "".join(part.get("text", "") for part in message.get("parts", []))
        task_id = message.get("taskId")

        if task_id is None:
            # 第一轮：接单开工。真实系统在这里会真的去翻档案，耗时若干秒。
            task = start_task(text)
            ask_back(task, "这份档案要限定年份范围吗？给我一个起止年份，我按范围查。")
        else:
            # 第二轮：带上 taskId 回话，等于在原来那件事上接着往下走
            task = TASKS.get(task_id)
            if task is None:
                self._not_found()
                return
            LOG.append({"task": task_id, "event": "resumed", "text": text})
            deliver(task, "已按「{}」检索完毕，命中 3 份相关文件，结论见正文。".format(text))

        self._reply(200, {"task": task})


if __name__ == "__main__":
    print("A2A 示例服务端已启动：{}".format(BASE))
    print("自述页：{}/.well-known/agent-card.json".format(BASE))
    HTTPServer(("127.0.0.1", 9000), Handler).serve_forever()
