# illustrative only
# Ch13 示意代码：记忆的"写 / 读 / 忘"三段
# 每条记忆带三样东西：内容、重要度、写入时刻。
# 重要度随时间衰减；读的时候按"重要度 ÷ 距今时间"排序取前几条。
#
# 说明：这是为"读完即懂"准备的最小实现，不追求工程完整，因此刻意省略了
# 来源字段、命中计数、容量上限与定期合并。生产环境里请见 Part 4 Ch20。

import time


def write(store, content, importance=1.0, now=None):
    """写入一条记忆。importance 表示这件事有多值得记。"""
    store.append({
        "内容": content,
        "重要度": importance,
        "写入时刻": now if now is not None else time.time(),
    })
    return store


def score(item, now):
    """打分 = 重要度 ÷ 距今时间。分越高越优先被读出来。"""
    age = max(now - item["写入时刻"], 1.0)   # 防止刚写入就除以 0
    return item["重要度"] / age


def read(store, query, now=None, top_k=3):
    """检索：示意版用最简单的子串命中，真实系统用向量检索或知识图谱。"""
    now = now if now is not None else time.time()
    hits = [it for it in store if query in it["内容"]]
    hits.sort(key=lambda it: score(it, now), reverse=True)
    return hits[:top_k]


def forget(store, now, threshold=1e-4):
    """遗忘：清掉打分低于阈值的老记忆，返回清理条数。"""
    before = len(store)
    store[:] = [it for it in store if score(it, now) >= threshold]
    return before - len(store)