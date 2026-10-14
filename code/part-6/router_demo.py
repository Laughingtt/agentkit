# runnable: no
# depends: 无（仅 Python 3.10+ 标准库）
# usage: python router_demo.py
"""最小规则路由器 + 四层缓存骨架。Part 6 Ch32 配套代码。

设计立场：**路由这件事读者自己就能写**。不接任何模型 API、不用任何外部路由
服务，只演示三件事：用「关键词 + 长度 + 多步迹象」分档；每次决策都带可解释的
理由（它要能被评测打分，见 Ch30）；同一会话把模型粘住，因为换模型等于让提示词
前缀缓存当场作废。四层缓存给骨架：exact / semantic 写成能跑的；prompt cache
写成「怎么摆前缀 + 怎么读回 usage」的接口；KV cache 只留注释。模型调用是确定性
假实现，只为看链路形状。纯标准库，拿到本地可直接跑。
"""

import hashlib

# ---------- 1. 三档模型的登记表 ----------
# 价格写成「相对最贵那档的倍数」，不写绝对报价：绝对价格每季度都在变，
# **档位之间的结构**才是不变的那一半。
TIERS = {
    "small": {"in": 0.1, "out": 0.1, "for": "检索摘要、分类、格式转换"},
    "mid": {"in": 0.3, "out": 0.3, "for": "常规问答、多轮工具调用"},
    "large": {"in": 1.0, "out": 1.0, "for": "多步推理、代码、长链条规划"},
}
ORDER = ["small", "mid", "large"]

# ---------- 2. 难度信号（三个都很便宜，规则路由的全部家当） ----------
HARD_WORDS = ("证明", "推导", "重构", "架构", "根因", "并发", "算法", "复杂度",
              "为什么", "哪一步错", "如何权衡", "设计")   # 要模型真想一想的词
EASY_WORDS = ("翻译", "改写", "润色", "总结", "摘要", "分类", "格式化", "提取")
MULTI_STEP = ("然后", "接着", "再把", "分别", "并且要", "之后")  # 一句塞了好几个动作


def classify(text: str) -> tuple[str, int, list[str]]:
    """给请求打难度分，返回 (档位, 分数, 理由)。

    三个信号各管一件事：词管**任务性质**，长度管**体量**，多步迹象管**链条长度**。"""
    reasons, score = [], 0
    for words, delta in ((HARD_WORDS, 2), (EASY_WORDS, -2)):
        hit = [w for w in words if w in text]
        if hit:
            score += delta * len(hit)
            reasons.append(f"{'高' if delta > 0 else '低'}难词 {hit}")
    if len(text) > 200:
        score += 1
        reasons.append(f"偏长（{len(text)} 字）")
    elif len(text) < 30:
        score -= 1
        reasons.append(f"很短（{len(text)} 字）")
    steps = [w for w in MULTI_STEP if w in text]
    if len(steps) >= 2:
        score += 2
        reasons.append(f"多步迹象 {steps}")
    tier = "large" if score >= 3 else ("mid" if score >= 0 else "small")
    return tier, score, reasons


class SessionPinner:
    """会话粘滞：一个会话里第一次定下档位，后面尽量不动。

    理由不是「一致性好」，而是**省钱**：换模型等于前缀缓存作废（32.4.3）。"""
    def __init__(self) -> None:
        self._pinned: dict[str, str] = {}

    def get(self, sid: str) -> str | None:
        return self._pinned.get(sid)

    def pin(self, sid: str, tier: str) -> None:
        self._pinned.setdefault(sid, tier)


def route(text: str, sid: str = "s", pinner: SessionPinner | None = None):
    """路由决策。返回的 reasons 是给人、给评测看的，不是给日志看的。"""
    pinner = pinner if pinner is not None else SessionPinner()
    tier, score, reasons = classify(text)
    pinned = pinner.get(sid)
    if pinned and pinned != tier:
        # 只许往上调、不许往下调：中途给任务换脑子，比多花点钱更容易出事。
        if ORDER.index(tier) > ORDER.index(pinned):
            pinner.pin(sid, tier)
            return tier, score, reasons + [f"会话从 {pinned} 上调到 {tier}"]
        return pinned, score, reasons + [f"会话粘在 {pinned}（不降档）"]
    pinner.pin(sid, tier)
    return tier, score, reasons


# ---------- 3. 缓存第 1 层：精确缓存 ----------
class ExactCache:
    """同一个问题问出同一个字面答案，直接返回，零 token。可跨会话共享。

    失效只有一种：提示词或模型变了——所以键里必须带档位名。"""
    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    @staticmethod
    def _key(text: str, tier: str) -> str:
        # 归一化：去空白转小写。否则用户多打一个空格就 miss。
        raw = f"{tier}|{''.join(text.lower().split())}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()

    def get(self, text: str, tier: str) -> str | None:
        return self._store.get(self._key(text, tier))

    def put(self, text: str, tier: str, answer: str) -> None:
        self._store[self._key(text, tier)] = answer


# ---------- 4. 缓存第 2 层：语义缓存（骨架） ----------
def _tokens(text: str) -> set[str]:
    """极简分词：按非字母数字切。真实系统这里该换成 embedding 模型。"""
    buf, out = "", set()
    for ch in text.lower() + " ":
        if ch.isalnum():
            buf += ch
        else:
            if buf:
                out.add(buf)
            buf = ""
    return out


class SemanticCache:
    """换个说法但意思一样，也直接返回。

    骨架用 Jaccard 相似度（交集 / 并集）当代理，够看清结构。生产里两个坑：
    一是**相似不等于同义**——「怎么退款」和「怎么不退款」相似度很高但答案
    相反，带否定语义的句子要么不进缓存要么提高阈值；二是**阈值不能拍脑袋**，
    唯一靠谱的办法是在自己的评测集上跑一遍（见 Ch30）。"""
    def __init__(self, threshold: float = 0.9) -> None:
        self.threshold = threshold
        self._entries: list[tuple[set[str], str]] = []

    def lookup(self, text: str) -> str | None:
        q = _tokens(text)
        if not q:
            return None
        for tokens, answer in self._entries:
            union = q | tokens
            if union and len(q & tokens) / len(union) >= self.threshold:
                return answer
        return None

    def put(self, text: str, answer: str) -> None:
        self._entries.append((_tokens(text), answer))


# ---------- 5. 缓存第 3 层：提示词（前缀）缓存 ----------
def split_prefix(user_text: str) -> tuple[str, str]:
    """把提示词切成「稳定段」与「变动段」，顺序不能反。

    规则一句话：**稳定的在前，会变的在后。** 系统提示、工具定义、长期记忆
    属于稳定段；用户这轮说的话、检索结果、时间戳属于变动段。稳定段只要有
    一个字节变了，它后面全部作废——前缀匹配是从头逐字节比的。"""
    return ("系统：你是客服助手。工具：订单查询 / 退款发起。知识库快照：2026-10-13。",
            user_text)


def fake_call(stable: str, volatile: str, tier: str) -> tuple[str, float]:
    """假模型调用。返回 (usage 说明, 折算单位成本)。

    usage 三档就是 Ch29 缓存成本归因的字段。真实服务里 cache_creation /
    cache_read 由厂商回传，自建推理则自己统计——**关键是分开记**，否则
    命中率掉了你从「总 token 没变」里根本看不出来。"""
    total_in = len(stable) + len(volatile)
    hit = total_in > 256          # 简化假设：前缀够长且逐字节相同就命中
    p, out_n = TIERS[tier], max(1, total_in // 8)
    cost = round((total_in * p["in"] * (0.1 if hit else 1.25) + out_n * p["out"])
                 / total_in, 4)
    return f"{'读' if hit else '写'}缓存 {total_in} / 输出 {out_n}", cost


# ---------- 6. 缓存第 4 层：KV cache（只留注释） ----------
# 模型内部的中间结果缓存：读过的 token 不重算。应用层碰不到它，只能靠
# 「别让模型重读同样的前缀」间接受益。原理见 Part 1 Ch3 3.8。


# ---------- 7. 串起来：一次完整请求 ----------
def serve(text: str, sid: str, exact: ExactCache, sem: SemanticCache,
          pinner: SessionPinner) -> tuple[str, str]:
    """返回 (答复, 这一步走的是哪条路)。真实系统在这里换成 API 调用。"""
    # 先定档再查缓存：缓存键里带着档位，改了路由策略旧答案自然不再命中。
    tier, _, _ = route(text, sid, pinner)
    hit = exact.get(text, tier)
    if hit is not None:
        return hit, f"exact-cache/{tier}"
    hit = sem.lookup(text)
    if hit is not None:
        return hit, "semantic-cache"
    stable, volatile = split_prefix(text)
    usage, cost = fake_call(stable, volatile, tier)
    answer = f"[{tier}] {usage}，折算单位成本 {cost}"
    exact.put(text, tier, answer)
    sem.put(text, answer)
    return answer, tier


if __name__ == "__main__":
    exact, sem, pinner = ExactCache(), SemanticCache(), SessionPinner()
    requests = [
        ("s1", "把下面这段英文翻译成中文，然后总结成一句话"),
        ("s1", "帮我设计一个订单服务的架构，说明为什么这样拆，然后给出复杂度分析"),
        ("s2", "把下面这段英文翻译成中文，然后总结成一句话"),   # 跨会话，exact 仍命中
        ("s2", "这个函数为什么会死锁？给出根因和修法，然后评估改动风险"),
        ("s3", "格式化这份 JSON，并提取其中的订单号"),
        ("s4", "把下面这段英文翻译成中文，然后把它压成一句话"),   # 语义近似，命中语义缓存
    ]
    for sid, text in requests:
        ans, path = serve(text, sid, exact, sem, pinner)
        print(f"{sid:<4}{path:<20}{ans}")
    print("\n会话粘滞表：", pinner._pinned)
