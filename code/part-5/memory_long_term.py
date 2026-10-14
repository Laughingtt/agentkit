# runnable: no
# depends: 无（纯标准库）
# usage: python memory_long_term.py
#
# Ch24 24.4 长时记忆：向量层 / 关系层 / 时序层的选型与读写。纯标准库，供逐行阅读。
#
# 这个文件刻意不 import 向量库或数据库驱动：真实系统里三层都是现成产品，
# 这里用内存里的假实现把「接口长什么样」和「三层的读法差在哪」写清楚。
# 你要做的是把这三个类换掉，接口不动，上层一行不改。

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from typing import Protocol

# 时序层的两列（正文 24.4 说的「轻的一条」）：事实不过期，只标失效时刻。
# 这两列就是本文件和真正的时序知识图谱之间的全部差别——成本是十分之一。
VALID_FOREVER = float("inf")


@dataclass
class MemoryRecord:
    """一条记忆。正文里说的「一句可以独立成立的陈述」就是这个 text。

    subject/object 拆开存是为了关系层：只有拆开了才能建唯一约束、
    才能问「和谁冲突」、才能做行级权限。一整段对话是拆不开的。
    """

    text: str
    subject: str
    predicate: str
    object: str
    owner: str = ""                 # 谁的记忆，行级权限按它判
    source_session: str = ""
    embedding: tuple[float, ...] = ()
    valid_from: float = field(default_factory=time.time)
    valid_to: float = VALID_FOREVER  # 到点失效，但行还在——不删是时序层的底线
    record_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def is_valid(self, now: float | None = None) -> bool:
        now = now if now is not None else time.time()
        return self.valid_from <= now < self.valid_to


class MemoryStore(Protocol):
    """长时记忆的公共接口。三层各自实现一份，上面只认这一个。

    抽出这层是因为：换掉向量库不该改调用方代码——这和 Ch23 讲
    JSON Schema 作为「契约」是同一个思路的另一处应用。
    """
    def upsert(self, record: MemoryRecord) -> str: ...                                             # 写入或更新
    def search(self, query: str, top_k: int) -> list[MemoryRecord]: ...                            # 语义
    def by_subject(self, subject: str, include_expired: bool = False) -> list[MemoryRecord]: ...   # 精确


def _cosine(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    """余弦相似度。真机上这一步发生在索引里，不在应用进程里。"""
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


class VectorLayer:
    """向量层：管「找得到」。

    弱点写在这里免得忘了：捞得出错的，也捞得出过期的。它不知道一条
    记忆属于谁、什么时候失效，所以它只能当召回器，不能当事实来源。
    """

    def __init__(self) -> None:
        self._rows: dict[str, MemoryRecord] = {}

    def upsert(self, record: MemoryRecord) -> str:
        self._rows[record.record_id] = record
        return record.record_id

    def search(self, query: str, top_k: int = 5,
               embedding: tuple[float, ...] = ()) -> list[MemoryRecord]:
        """按向量近邻排。

        注意这里没有过期过滤——这正是正文说的那个洞。过滤是关系层的活，
        留给 RetrievalPipeline 去做，不是向量层自己该管的。
        """
        rows = list(self._rows.values())
        if not embedding:
            return rows[:top_k]
        scored = [(_cosine(embedding, r.embedding), r) for r in rows]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [r for _, r in scored[:top_k]]

    def find_existing(self, embedding: tuple[float, ...],
                      threshold: float = 0.92) -> MemoryRecord | None:
        """写入前查一次：同一条事实第二次出现时不要新建，要更新。

        判据用向量检索自己判，不用文本相等——用户换个说法说同一件事
        太常见了，文本相等永远命中不了。
        """
        hit = self.search("", top_k=1, embedding=embedding)
        if hit and _cosine(embedding, hit[0].embedding) >= threshold:
            return hit[0]
        return None


class RelationalLayer:
    """关系层：管「信得过、管得住」。

    三件东西在这里落地：唯一约束、失效时间列、行级权限。
    正文说这是最容易被省掉的一层——半年后线上问题全是
    「Agent 引用了三个月前作废的规定」，根因就是省了这一层。
    """

    def __init__(self) -> None:
        self._rows: dict[tuple[str, str, str], MemoryRecord] = {}

    @staticmethod
    def key(r: MemoryRecord) -> tuple[str, str, str]:
        """唯一约束：定出「这是哪个槽位的那一行」。

        带谓词时，key 不含 object——槽位由 (owner, subject, predicate)
        认，object 变一次就是同一槽位的新值，于是 upsert 会给旧行关上
        valid_from，这是「同一条事实改了说法」的更新。

        不带谓词时（三元组），反过来把 object 放进 key：这样
        「上限 5000」和「上限 3000」落在两个不同的行上，并存而不互相覆盖。
        这不是 bug——正文说得很清楚，矛盾不等于更新：它们是同一个槽位在
        不同时间的两个值，要靠时序层一起留着。**别为了「省一行」把 object
        从三元组的 key 里拿掉**，那会让新值默默盖掉旧值，正是这一层要防的
        「Agent 引用了三个月前作废的规定」。

        代价要说清楚：三元组是「主体只有这一个属性」的假设。
        同一个 subject 若要挂多个不带谓词的三元组（张三 会跑步 / 张三 会游泳），
        它们会互相覆盖——这种场景请补上 predicate。
        """
        return (r.owner, r.subject, r.object) if r.predicate == "" \
            else (r.owner, r.subject, r.predicate)

    def upsert(self, record: MemoryRecord) -> str:
        k = self.key(record)
        old = self._rows.get(k)
        if old is not None:
            # 覆盖时先给旧行关上有效期，而不是删掉它。
            old.valid_to = record.valid_from
        self._rows[k] = record
        return record.record_id

    def by_subject(self, subject: str,
                    include_expired: bool = False,
                    owner: str | None = None) -> list[MemoryRecord]:
        """精确查：这条属于谁、和谁冲突、现在还有效吗。

        owner 参数就是行级权限：能不能看到哪一行由角色决定，
        不由检索分数决定。这一步在流水线上必须排在拼装之前。
        """
        now = time.time()
        out = []
        for r in self._rows.values():
            if r.subject != subject:
                continue
            if owner is not None and r.owner != owner:
                continue
            if not include_expired and not r.is_valid(now):
                continue
            out.append(r)
        return out

    def history(self, subject: str) -> list[MemoryRecord]:
        """时序层的轻量版读法：返回这一主体的全部版本，含已失效的。

        「一月上限 5000，三月起 3000」这类问题只能靠它回答，
        向量检索答不了，关系层不带 include_expired 也答不了。
        """
        return sorted(
            (r for r in self._rows.values() if r.subject == subject),
            key=lambda r: r.valid_from,
        )


class TemporalLayer(RelationalLayer):
    """时序层：管「说得清它什么时候变的」。

    它没有新数据结构，只是把 RelationalLayer 的写入语义讲清楚了：
    新事实不覆盖旧的，而是把旧事实的有效期关上。什么时候该上这一层，
    判据只有一条——业务里有没有「同一个人在不同时刻需要拿到不同答案」
    的场景。没有的话，向量 + 关系两层就是终点。
    """

    def timeline(self, subject: str) -> list[tuple[str, str, str]]:
        """返回 [(起点, 该时段的取值, 终点)]，人可直接读。"""
        return [
            (time.strftime("%Y-%m", time.localtime(r.valid_from)),
             r.object,
             "至今" if r.valid_to == VALID_FOREVER
             else time.strftime("%Y-%m", time.localtime(r.valid_to)))
            for r in self.history(subject)
        ]


class RetrievalPipeline:
    """24.6 的六道闸里属于记忆侧的那部分。

    顺序不是风格问题：画像在前、中时在语义检索前、权限在拼装前，
    每一条换序都有具体代价，代价最大的一条是安全问题。
    """

    def __init__(self, profile: dict[str, str], vector: VectorLayer,
                 relational: RelationalLayer) -> None:
        self.profile = profile          # ① 画像：常驻，不检索
        self.vector = vector            # ④ 语义
        self.relational = relational    # ⑤ 权限与主体
        self.hot: dict[str, str] = {}   # ③ 中时：按键取，几毫秒

    def recall(self, query: str, embedding: tuple[float, ...] = (),
               owner: str | None = None, top_k: int = 5) -> list[MemoryRecord]:
        """③④⑤ 三道闸。①②⑥ 在上层装配器里，这里不碰。"""
        candidates: list[MemoryRecord] = []
        for text in self.hot.values():                       # ③ 中时
            candidates.append(MemoryRecord(text=text, subject="", predicate="hot",
                                           object="", owner=owner or ""))
        candidates.extend(self.vector.search(query, top_k, embedding))  # ④ 语义
        # ⑤ 权限：越权内容一旦混进上下文，后面的裁剪和排序都救不回来。
        visible = [c for c in candidates
                   if owner is None or c.owner in ("", owner)]
        valid = [c for c in visible if c.is_valid()]
        return valid[:top_k]


def demo() -> None:
    """把「一月 5000、三月起 3000」这条事实走一遍全链路。"""
    v, tmp = VectorLayer(), TemporalLayer()
    tmp.upsert(MemoryRecord(text="报销上限 5000", subject="财务制度", predicate="上限",
                            object="5000", owner="u42", embedding=(0.9, 0.1)))
    tmp.upsert(MemoryRecord(text="报销上限 3000", subject="财务制度", predicate="上限",
                            object="3000", owner="u42", embedding=(0.91, 0.09)))
    print("现在生效的：", [r.text for r in tmp.by_subject("财务制度")])
    print("u99 读到的：", tmp.by_subject("财务制度", owner="u99"))
    print("时间线：", tmp.timeline("财务制度"))
    pipe = RetrievalPipeline(profile={"语言": "中文"}, vector=v, relational=tmp)
    print("流水线召回：", [r.text for r in pipe.recall("报销多少", owner="u42")])


if __name__ == "__main__":
    demo()
