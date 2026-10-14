# illustrative only
# depends: 无（只用标准库 copy / re / fnmatch）
# usage: 读文件即可，不需运行
#
# Ch21 21.2 的骨架：一份权限规则怎么被读成一次判定。
# 这份代码刻意不是一张查表函数——它要回答两件事：
# 「一条规则要怎样才算对上」和「多条同时命中时听谁的」。

import copy
import re
import fnmatch

ALLOW, ASK, DENY = "allow", "ask", "deny"

# 第四种情况：规则没覆盖到怎么办。选 ask 而不是 allow（21.2.4）。
DEFAULT_VERDICT = ASK

# 三档的严格程度排序，用来比"哪一次更严"。allow 最松、deny 最严。
SEVERITY = {ALLOW: 0, ASK: 1, DENY: 2}

# 匹配写法从窄到宽的排名：越窄的写法越具体，优先级也越高。
# prefix / glob / regex 这三个标识符 = 21.2.2 讲的前缀 / 通配 / 正则。
KIND_RANK = {"prefix": 1, "glob": 2, "regex": 3}


class Action:
    """一次动作。判定只认 verb 和 target 两个字段，别的都不看。"""

    def __init__(self, verb, target):
        self.verb = verb                  # 动作类别：读 / 写 / 执行
        self.target = target              # 落点路径，或者整条命令

    def __repr__(self):
        return f"<{self.verb}:{self.target}>"


class Rule:
    """一条规则。target 用哪种写法匹配，由 kind 决定。"""

    def __init__(self, verb, target, verdict, kind="prefix"):
        self.verb = verb                  # 动作类别：读 / 写 / 执行
        self.target = target
        self.verdict = verdict
        self.kind = kind
        # 优先级由规则自己的性质决定，不由书写顺序决定（21.2.3）
        self.specificity = (KIND_RANK[kind], len(target))

    def __repr__(self):
        return f"<{self.verdict} {self.verb}:{self.target}>"


class Verdict:
    """一次判定的结果。why 必须带，因为它要能被人复述出来（见 20.6 的可回放）。"""

    def __init__(self, result, why):
        self.result = result
        self.why = why


def matches(rule, action):
    """这条规则算不算对上这个动作。对不上是最常见的情况，先判掉。"""
    if rule.verb != action.verb:
        return False
    if rule.kind == "prefix":
        return action.target.startswith(rule.target)
    if rule.kind == "glob":
        return fnmatch.fnmatch(action.target, rule.target)
    return re.search(rule.target, action.target) is not None


def _best(hits, verdict):
    """同一档里挑最具体的那条：先看写法宽窄，再看目标串长短。"""
    pool = [r for r in hits if r.verdict == verdict]
    return max(pool, key=lambda r: r.specificity) if pool else None


def decide(action, rules):
    """给一个动作定档。规则的书写顺序不影响结果（21.2.3）。"""
    hits = [r for r in rules if matches(r, action)]
    if not hits:
        return Verdict(DEFAULT_VERDICT, "没有规则命中，走默认档")

    denied = _best(hits, DENY)
    if denied:
        return Verdict(DENY, f"命中拒绝规则 {denied}")

    asked = _best(hits, ASK)
    allowed = _best(hits, ALLOW)
    if asked and (not allowed or asked.specificity >= allowed.specificity):
        return Verdict(ASK, f"命中询问规则 {asked}")
    if allowed:
        return Verdict(ALLOW, f"命中放行规则 {allowed}")
    return Verdict(DEFAULT_VERDICT, "没有可比的两条")


def decide_expanded(intent, expanded, rules, workdir):
    """21.3.4 的硬要求一：判定必须落在展开之后的那一行上。

    同一个意图展开成不同的命令，可能得到完全不同的判定——
    所以意图和展开后的命令各判一次，哪一次更严就听哪一次。
    展开后那一档一定会被采纳（那是真正跑出去的东西），
    展开前那一档若更严则压住它，免得"意图上就该拦、展开后看着却干净"这一路溜过去。

    硬要求二落在展开后这一侧：落点先过一遍 real_path 再进规则，
    比的是解析后的位置；workdir 是工作区根，意图那侧是对象名，不解析。
    比之前再还原成相对工作区的形状——规则写的就是这个形状（见 21.2.1）。
    """
    before = decide(intent, rules)
    after = decide(_归一落点(expanded, workdir), rules)
    if SEVERITY[before.result] > SEVERITY[after.result]:
        return Verdict(before.result, f"意图本身就该拦（{before.why}），展开后是 {after.result}")
    return after


def _归一落点(action, workdir):
    """落点归一：读 / 写 先过 real_path，再还原成相对工作区的形状去比规则。

    real_path 那一遍防的是模型给的 "src/../../.ssh/id_rsa"；
    还原成相对形状则是为了让配置能照 21.2.1 那份 yaml 写——绝对路径写死
    在配置里换台机器就废了，相对写法配绝对落点则会静悄悄地全落到兜底规则上。

    执行 的 target 是整条命令，不是落点，原样带走、一个字符都不改：
    塞进 real_path 会被拼成 <工作区>/rm -rf build/，`执行 "rm"` 这条前缀
    规则就再也对不上——硬拒绝悄悄退化成默认的 ask。判定对象错了就判错。
    """
    if action.verb != "读" and action.verb != "写":
        return action
    根 = "/" + "/".join(p for p in workdir.split("/") if p and p != ".")
    界 = 根 if 根.endswith("/") else 根 + "/"
    绝对 = real_path(action.target, workdir)
    换过 = copy.copy(action)
    # 工作区之外、相对形式不存在的，保持绝对原样交给兜底规则去判
    换过.target = 绝对[len(界):] if 绝对.startswith(界) else 绝对
    return 换过


def real_path(path, workdir):
    """21.3.4 的硬要求二：展开用的原料不可信，路径要解析成绝对路径再判。

    模型给出 "src/../../.ssh/id_rsa" 时，这串字看着在 src/ 下面，
    一路弹到底却能爬到工作区之外。所以 .. 只准弹工作区里的分量，
    弹到工作区根就停（21.3.4 说的"路径被夹在工作区里"就是这个选择）：
    它最后落在 <工作区>/.ssh/id_rsa，不在家目录里。代价是越界的 ..
    被"吃掉"而不是报错——../a.txt 与 a.txt 会落到同一处。
    绝对路径不和工作区混算，只把 . 与 .. 归一掉，原样交给调用方
    去比对规则——它可以落在工作区里面，也可以落在外面。
    """
    if path.startswith("/"):
        base, raw = [], path              # 绝对路径不和工作区混算
    else:
        base = [p for p in workdir.split("/") if p and p != "."]
        raw = path
    stack = list(base)
    floor = len(stack)                    # .. 弹到这一层就弹不动：工作区根
    for p in raw.split("/"):
        if not p or p == ".":
            continue
        if p == "..":
            if len(stack) > floor:
                stack.pop()
        else:
            stack.append(p)
    return "/" + "/".join(stack)
