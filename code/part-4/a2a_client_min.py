# illustrative only
"""
最小 A2A 客户端（只用标准库）

用途：演示委派一方的三步——读自述页 → 派一个任务 → 顺着任务状态走到终态。
依赖：Python 3.9+ 标准库，无第三方包。
运行：先启动 a2a_server_min.py，再 python3 a2a_client_min.py

协议依据：A2A v1.0（写在请求头里的协议版本号就是 "1.0"）。
本文件是教学示意：没做鉴权、超时重试与证书校验，不要直接搬去生产。
"""

import json
import uuid
import urllib.request

BASE = "http://127.0.0.1:9000"
A2A_VERSION = "1.0"
JSON_MEDIA = "application/a2a+json"

# 这两组是本章的核心：任务要么停在"还要你补一句"，要么已经落地了。
INTERRUPTED = {"TASK_STATE_INPUT_REQUIRED", "TASK_STATE_AUTH_REQUIRED"}
TERMINAL = {"TASK_STATE_COMPLETED", "TASK_STATE_FAILED", "TASK_STATE_CANCELED", "TASK_STATE_REJECTED"}


def request(method, path, body=None):
    """发一次协议请求。真实实现还要加超时、重试与鉴权头，这里只留主干。"""
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", JSON_MEDIA)
    # A2A-Version 从 v1.0 起是必填的：对方升级之后，两端才知道在讲哪一版
    req.add_header("A2A-Version", A2A_VERSION)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def discover():
    """第 1 步：先读自述页，看它会什么、从哪儿接活，别急着派。"""
    card = request("GET", "/.well-known/agent-card.json")
    print("找到 Agent：{}（{}）".format(card["name"], card["version"]))
    print("  简介：{}".format(card["description"]))
    for skill in card["skills"]:
        print("  技能：{} — {}".format(skill["name"], skill["description"]))
    for iface in card["supportedInterfaces"]:
        print(
            "  接口：{} {}（协议 {}）".format(
                iface["protocolBinding"], iface["url"], iface["protocolVersion"]
            )
        )
    return card


def send(text, task_id=None):
    """派一句话过去。带上 task_id 就是"接着那件事说"，不带就是"新开一件事"。"""
    message = {
        "role": "ROLE_USER",
        "parts": [{"text": text}],
        "messageId": str(uuid.uuid4()),
    }
    if task_id:
        message["taskId"] = task_id
    return request("POST", "/message:send", {"message": message})["task"]


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
            question = task["status"]["message"]["parts"][0]["text"]
            print("  它反问：{}".format(question))
            task = send("限定 2023 年 1 月到 6 月", task_id)
            continue

        # 还在干活：协议给了三种等结果的办法，这里用最简单的轮询。
        # 另外两种是流式订阅（边干边收）和回调（干完它来敲门）。
        task = request("GET", "/tasks/{}".format(task_id))["task"]

    for artifact in task.get("artifacts", []):
        print("交付物[{}]：{}".format(artifact["name"], artifact["parts"][0]["text"]))


if __name__ == "__main__":
    main()
