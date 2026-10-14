# runnable: no
# depends: 无（Python 3.10+ 标准库；本文件用 urllib，换 httpx 也一样）
# usage: python a2a_client.py
"""
最小 A2A 客户端：发现 → 派活 → 轮询 → 取成果。

⚠️ 本文件由作者静态推演，未在真实环境运行过。
它假设 a2a_server.py 已经在 127.0.0.1:9100 上跑着。
"""

import json
import time
import urllib.request

BASE = "http://127.0.0.1:9100"
CARD_URL = f"{BASE}/.well-known/agent-card.json"
RPC_URL = f"{BASE}/message:send"


def _post(payload: dict) -> dict:
    """发一条 JSON-RPC 请求。id 是配对用的，没有它就分不清哪条回复是谁的。"""
    req = urllib.request.Request(
        RPC_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "A2A-Version": "1.0"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def discover() -> dict:
    """第一步：拿域名换一份自述页。地址是规范定死的，所以这一步零配置。"""
    with urllib.request.urlopen(CARD_URL) as resp:
        return json.loads(resp.read())


def pick_skill(card: dict, wanted: str) -> dict:
    """第二步：从自述页里挑一项技能。挑错了对方会当场拒绝，这比调错了再报错省事。"""
    for skill in card.get("skills", []):
        if skill["id"] == wanted:
            return skill
    raise SystemExit(f"对方没有这项技能：{wanted}")


def text_message(text: str, task_id: str | None = None) -> dict:
    """把一句话装成 A2A 的 message。taskId 有没有，决定这是开新单还是接上一单。"""
    msg = {"role": "ROLE_USER", "parts": [{"text": text}], "messageId": str(time.time_ns())}
    if task_id:
        msg["taskId"] = task_id
    return msg


def main() -> None:
    card = discover()
    print(f"找到 {card['name']}（{card['version']}）：{card['description']}")
    skill = pick_skill(card, "itinerary")
    print(f"选中技能：{skill['name']} —— {skill['description']}")

    # 第三步：派活。不带 taskId = 开新单。
    reply = _post(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "SendMessage",
            "params": {"message": text_message("帮我把下周的行程排一下")},
        }
    )
    task = reply["result"]["task"]
    task_id = task["id"]
    print(f"任务 {task_id} 当前状态：{task['status']['state']}")

    # 第四步：轮询。A2A 允许任务停在 input-required 上等任意久，
    # 所以客户端的循环体必须能同时处理"还在做"和"要你回话"两种情况。
    for _ in range(3):
        if task["status"]["state"] == "TASK_STATE_INPUT_REQUIRED":
            question = task["status"]["message"]["parts"][0]["text"]
            reply = _post(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "SendMessage",
                    "params": {"message": text_message("下周三", task_id)},
                }
            )
            task = reply["result"]["task"]
            continue

        # 没停在等你回话上，就真的去问一次进度。这才是"轮询"。
        reply = _post(
            {"jsonrpc": "2.0", "id": 3, "method": "GetTask", "params": {"id": task_id}}
        )
        task = reply["result"]["task"]
        if task["status"]["state"] == "TASK_STATE_COMPLETED":
            break
        time.sleep(1)

    print("最终状态：", task["status"]["state"])
    for artifact in task.get("artifacts", []):
        print(f"成果《{artifact['name']}》：")
        print(artifact["parts"][0]["text"])


if __name__ == "__main__":
    main()