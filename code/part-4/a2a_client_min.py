# illustrative only
"""
最小 A2A 客户端：读自述页 → 派一个任务 → 顺着状态走到终态。
Python 3.9+ 标准库。先启动 a2a_server_min.py，再 python3 a2a_client_min.py
协议依据：A2A v1.0。教学示意，未做鉴权与证书校验。
"""

import json
import urllib.request

BASE, VERSION = "http://127.0.0.1:9000", "1.0"
MEDIA = "application/a2a+json"

# 本章的核心：任务要么停在"还要你补一句"，要么已经落地了。
INTERRUPTED = {"TASK_STATE_INPUT_REQUIRED", "TASK_STATE_AUTH_REQUIRED"}
TERMINAL = {"TASK_STATE_COMPLETED", "TASK_STATE_FAILED",
            "TASK_STATE_CANCELED", "TASK_STATE_REJECTED"}


def request(method, path, body=None):
    """一次协议请求。真实实现还要加超时、重试与鉴权头。"""
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", MEDIA)
    # A2A-Version 从 v1.0 起必填：对方升级之后，两端才知道在讲哪一版
    req.add_header("A2A-Version", VERSION)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def discover():
    """第 1 步：先读自述页，看它会什么，别急着派。"""
    card = request("GET", "/.well-known/agent-card.json")
    print("找到 Agent：{}（{}）".format(card["name"], card["version"]))
    for skill in card["skills"]:
        print("  技能：{} — {}".format(skill["name"], skill["description"]))


def send(text, task_id=None):
    """带 task_id 就是"接着那件事说"，不带就是"新开一件事"。"""
    msg = {"role": "ROLE_USER", "parts": [{"text": text}]}
    if task_id:
        msg["taskId"] = task_id
    return request("POST", "/message:send", {"message": msg})["task"]


def main():
    discover()
    print("\n派活：查一份 2023 年的项目验收档案")
    task = send("帮我查一份 2023 年的项目验收档案")
    task_id = task["id"]

    # 整个客户端的主循环就是这个 while：追着任务状态走，
    # 遇到"停下来问人"就补一句再送回去，遇到终态就收工。
    while True:
        state = task["status"]["state"]
        print("  状态：{}".format(state))
        if state in TERMINAL:
            break
        if state in INTERRUPTED:
            print("  它反问：{}".format(task["status"]["message"]["parts"][0]["text"]))
            task = send("限定 2023 年 1 月到 6 月", task_id)
            continue
        # 协议给了三种等结果的办法，这里用最简单的轮询。
        task = request("GET", "/tasks/{}".format(task_id))["task"]

    for art in task.get("artifacts", []):
        print("交付物[{}]：{}".format(art["name"], art["parts"][0]["text"]))


if __name__ == "__main__":
    main()
