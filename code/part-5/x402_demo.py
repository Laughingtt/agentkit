# runnable: no
# depends: 无（Python 3.10+ 标准库）
# usage: python x402_demo.py
"""
x402 微支付最小演示：把"HTTP 402 + 三个头"这条链路手写一遍。

⚠️ 关于本文件的诚实声明（重要）：
   1) 本文件由作者静态推演，**未在真实环境运行过**。
   2) **HTTP 状态码、三个请求/响应头名、facilitator 的 /verify 与 /settle
      两个端点、scheme 与 network 必须成对支持这些，是从 x402 仓库 README
      的流程描述逐条核对来的。**
   3) 两个 JSON 对象（PaymentRequirements / PaymentPayload）的**字段名**
      未能联网核对到规范原文，是按 v1 结构写的教学骨架。
      照抄前请对照 https://github.com/x402-foundation/x402/tree/main/specs
      逐字段核对一遍。
   4) 链上结算、签名、EIP-3009 转账授权，这里一律用假数据代替——
      本文件演示的是"钱怎么在协议层流动"，不是"钱怎么上链"。
"""

import base64
import json
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

BASE = "http://127.0.0.1:9200"
PRICE = "10000"  # 以资产最小单位计；真实系统里这是字符串，不是数字


def b64(obj: dict) -> str:
    return base64.b64encode(json.dumps(obj).encode("utf-8")).decode()


def unb64(blob: str) -> dict:
    return json.loads(base64.b64decode(blob))


# ---------------- 服务端：先报价，再验票，最后干活 ----------------

def payment_requirements() -> dict:
    """402 的响应体：告诉客户端"要多少钱、走哪条网、付给谁"。"""
    return {
        "x402Version": 1,
        "resource": f"{BASE}/search",
        "accepts": [
            {
                "scheme": "exact",           # 付固定额；协议预留了按用量付的 upto
                "network": "eip155:84532",  # 哪条链。scheme 与 network 必须成对支持
                "maxAmountRequired": PRICE,
                "description": "一次档案检索",
                "payTo": "0xSeller...",
                "maxTimeoutSeconds": 60,
                "asset": "0xUSDC...",
            }
        ],
    }


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: dict, extra: dict | None = None) -> None:
        raw = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        if self.path != "/search":
            self._send(404, {"error": "no such resource"})
            return

        ticket = self.headers.get("PAYMENT-SIGNATURE")
        if not ticket:
            # 没带票：回 402，把报价单塞进 PAYMENT-REQUIRED 头。
            # 客户端已经知道价格时可以跳过这一步，直接带票重来。
            self._send(402, {"error": "payment required"},
                       {"PAYMENT-REQUIRED": b64(payment_requirements())})
            return

        # 有票：先验后干。验不过不能干活——这是整个协议唯一的硬约束。
        payload = unb64(ticket)
        if payload.get("scheme") != "exact" or payload.get("network") != "eip155:84532":
            self._send(402, {"error": "unsupported scheme or network"},
                       {"PAYMENT-REQUIRED": b64(payment_requirements())})
            return

        settlement = self._settle(payload)
        if not settlement.get("success"):
            self._send(402, {"error": "verification failed"})
            return

        # 干活，并把结算结果回执塞回 PAYMENT-RESPONSE。
        self._send(200, {"result": "命中 3 条"},
                   {"PAYMENT-RESPONSE": b64(settlement)})

    def _settle(self, payload: dict) -> dict:
        """真实实现是 POST 到 facilitator 的 /verify 与 /settle 两个端点；
        这里用一次本地判定代替，把链上那部分折叠掉。"""
        auth = payload.get("payload", {}).get("authorization", {})
        if auth.get("value") != PRICE:
            return {"success": False, "error": "amount mismatch"}
        return {"success": True, "transaction": "0xDemoTx...", "network": payload["network"]}


# ---------------- 客户端：撞一次 402，付钱，重试 ----------------

def fetch(url: str, ticket: str | None = None) -> tuple[int, dict, dict]:
    headers = {"PAYMENT-SIGNATURE": ticket} if ticket else {}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, unb64_or_json(resp.read()), dict(resp.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"{}"), dict(exc.headers)


def unb64_or_json(raw: bytes) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw.decode("utf-8", "replace")}


def call_search() -> None:
    # 第 1 步：不带票去要。
    status, _, headers = fetch(f"{BASE}/search")
    print(f"第 1 次请求 → HTTP {status}")

    # 第 2 步：从 PAYMENT-REQUIRED 里读报价，选一个自己支持的 (scheme, network)。
    terms = unb64(headers["PAYMENT-REQUIRED"])
    chosen = next(t for t in terms["accepts"] if t["network"] == "eip155:84532")
    print(f"报价：{chosen['description']}，付 {chosen['maxAmountRequired']} 给 {chosen['payTo']}")

    # 第 3 步：按报价造一张支付凭据。真实系统在这里签名并把资产转账授权
    # 一起打包；本文件只造结构，不做密码学。
    ticket = b64({
        "x402Version": 1,
        "scheme": chosen["scheme"],
        "network": chosen["network"],
        "payload": {
            "signature": "0xDemoSig...",
            "authorization": {
                "from": "0xBuyer...",
                "to": chosen["payTo"],
                "value": chosen["maxAmountRequired"],
                "validAfter": str(int(time.time()) - 60),
                "validBefore": str(int(time.time()) + chosen["maxTimeoutSeconds"]),
                "nonce": "demo-nonce",
            },
        },
    })

    # 第 4 步：带上票重试同一个 URL。
    status, body, headers = fetch(f"{BASE}/search", ticket)
    print(f"第 2 次请求 → HTTP {status}，body={body}")
    print(f"回执 PAYMENT-RESPONSE：{unb64(headers['PAYMENT-RESPONSE'])}")


if __name__ == "__main__":
    import threading

    threading.Thread(
        target=HTTPServer(("127.0.0.1", 9200), Handler).serve_forever, daemon=True
    ).start()
    time.sleep(0.2)
    call_search()