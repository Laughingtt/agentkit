# runnable: no
# depends: 无（仅 Python 3.10+ 标准库）
# usage: python eval_pipeline.py
"""最小评测流水线：数据集 → 候选答案 → 裁判打分 → 聚合 → 门禁。

正文见 Part 6 Ch30。本文件不调用任何模型 API——裁判是一个确定性的假实现，
用来把流水线跑通；换成真模型时只要替换 call_judge 这一个函数，其余不动。

头部标 runnable: no 是因为本书写作流程禁止执行代码。文件只依赖标准库，
拿到本地直接 `python eval_pipeline.py` 即可跑通。
"""

from statistics import mean

# ---------- 1. 评测数据集：每条样本自带「该被说到的要点」 ----------
# 要点用普通子串表示，够演示用；真实项目里这一列来自人工标注。
DATASET = [
    {
        "id": "s1",
        "question": "订单 A123 的退款什么时候到账？",
        "answer": "订单 A123 已于 3 月 2 日发起退款，原路退回，通常 3-5 个工作日到账。",
        "must_mention": ["3 月 2 日", "3-5 个工作日"],
    },
    {
        "id": "s2",
        "question": "订单 A456 能不能改成加急发货？",
        # 故意写一条啰嗦却漏了截止时间的答案：30.4.2 冗长偏置的靶子
        "answer": "您好，非常抱歉给您带来不便，我们非常理解您着急的心情。加急发货在系统里"
                  "是支持的，流程也一点都不复杂，您完全不用担心，只需要告诉我们一声就可以，"
                  "我们会竭尽全力为您处理，一定不会让您久等的，请放心。",
        "must_mention": ["截止今天 18:00"],
    },
    {
        "id": "s3",
        "question": "订单 A789 的物流单号是什么？",
        "answer": "物流单号 SF1234567890，由顺丰承运，预计明天送达。",
        "must_mention": ["SF1234567890"],
    },
    {
        "id": "s4",
        "question": "订单 A000 是不是已经签收？",
        "answer": "订单 A000 已于 5 月 6 日由本人签收。",
        "must_mention": ["5 月 6 日"],
    },
    {
        "id": "s5",
        "question": "发票抬头能改成「杭州云栖科技有限公司」吗？",
        # 故意写一条又长又堆砌、但恰好命中要点的答案：冗长偏置会把它抬上去
        "answer": "发票抬头当然是可以修改的，这一点请您完全放心，我们的后台系统支持自助修改，"
                  "流程非常简便，操作起来也一点都不麻烦，通常几分钟就可以完成，"
                  "您随时都可以在订单详情页自助处理，办理好了会重新寄送电子发票。"
                  "请把抬头改成「杭州云栖科技有限公司」并重新开具即可。",
        "must_mention": ["杭州云栖科技有限公司"],
    },
]

# ---------- 2. 评分细则：裁判手里的那张「评分卡」 ----------
RUBRIC = {
    "version": "2026-10-13.v1",
    "dimensions": {"faithfulness": 0.6, "conciseness": 0.4},
    "pass_line": 0.7,
}


def call_judge(sample: dict, rubric: dict) -> dict:
    """假裁判：确定性打分。换成真模型时，只替换这一个函数。"""
    answer = sample["answer"]
    hit = sum(1 for key in sample["must_mention"] if key in answer)
    # faithfulness 管「说到了没有」，conciseness 管「有没有为凑字数而啰嗦」
    faithfulness = hit / len(sample["must_mention"])
    conciseness = min(1.0, 0.4 + len(answer) / 400)   # 冗长偏置的最小复刻
    score = round(
        rubric["dimensions"]["faithfulness"] * faithfulness
        + rubric["dimensions"]["conciseness"] * conciseness, 3,
    )
    return {"score": score, "reasons": [
        f"命中要点 {hit}/{len(sample['must_mention'])}",
        f"答案 {len(answer)} 字",
    ]}


def pairwise_score(answer_a: str, answer_b: str) -> str:
    """成对比较：交换 A/B 各判一次，不一致就判平——位置偏置的最小对策。"""
    def one_winner(first: str, second: str) -> str:
        if len(first) == len(second):
            return "tie"          # 长度一样就没有胜者，别硬分
        return "A" if len(first) > len(second) else "B"

    forward = one_winner(answer_a, answer_b)
    backward = one_winner(answer_b, answer_a)
    return "tie" if forward != backward else forward


def run_eval(dataset: list[dict], rubric: dict) -> list[dict]:
    """逐条打分。一条样本一次裁判调用，返回值里带上分数和理由。"""
    rows = []
    for sample in dataset:
        judged = call_judge(sample, rubric)
        rows.append({**sample, **judged, "passed": judged["score"] >= rubric["pass_line"]})
    return rows


def aggregate(rows: list[dict]) -> dict:
    """把逐条分数压成两个数：平均分和通过率。门禁只看通过率。"""
    return {
        "n": len(rows),
        "mean_score": round(mean(row["score"] for row in rows), 3),
        "pass_rate": round(sum(row["passed"] for row in rows) / len(rows), 3),
    }


def main() -> None:
    rows = run_eval(DATASET, RUBRIC)
    summary = aggregate(rows)

    print(f"评分卡版本 {RUBRIC['version']}｜样本 {summary['n']} 条")
    print("-" * 58)
    for row in rows:
        flag = "PASS" if row["passed"] else "FAIL"
        detail = "｜".join(row["reasons"])
        print(f"[{flag}] {row['id']}  分数 {row['score']:.2f}  {detail}")

    print("-" * 58)
    print(f"平均分 {summary['mean_score']}｜通过率 {summary['pass_rate']:.0%}")

    # 成对比较演示：拿啰嗦的 s2 和简洁的 s3 比。只看长度的话 A 会赢，
    # 交换位置后结论翻转 → 判平，说明这一次比较本身不可信。
    noisy = next(row for row in rows if row["id"] == "s2")["answer"]
    crisp = next(row for row in rows if row["id"] == "s3")["answer"]
    print(f"\n成对比较 s2 vs s3：{pairwise_score(noisy, crisp)}（tie = 换顺序结论就翻转）")

    # 门禁：通过率低于 pass_line 就阻断这次发布，这一步不需要人参与
    if summary["pass_rate"] < RUBRIC["pass_line"]:
        print(f"门禁：未通过（{summary['pass_rate']:.0%} < {RUBRIC['pass_line']:.0%}），阻断发布")
    else:
        print("门禁：通过")


if __name__ == "__main__":
    main()
