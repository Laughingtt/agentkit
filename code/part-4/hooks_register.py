# illustrative only
# depends: 无（纯骨架，所有标识符都是占位名）
# usage: 读文件即可，不需运行
#
# Ch21 21.5 的骨架：钩子 = 一张时刻表 + 挂在时刻上的确定性程序。
#
# 这份文件里故意没有一类回调：「判断这次动作危不危险」。
# 那是权限的活（21.5.3）。钩子只在事实层面工作——
# 唯一能变成"拦下"的，是"问了也没用"的那条底线（见下面那个回调）。

PASS = "pass"        # 放行：什么都不做，继续往下走
BLOCK = "block"      # 拦下：这次动作不执行 / 结果作废
PATCH = "patch"      # 改写：往事件里补一条信息，让后面的步骤和留痕都看得到

# 时刻表由外壳定死，不由模型定。名字可以增，语义不要改。
MOMENTS = ("会话开始前", "工具执行前", "工具执行后", "会话结束时")


class Hooks:
    """一张时刻表。每个时刻挂几个回调，到点按注册顺序跑。"""

    def __init__(self):
        self._table = {m: [] for m in MOMENTS}
        self.fired = []          # 留痕用：谁在什么时刻被叫过（职责六的黑匣子）

    def on(self, moment, fn):
        """挂一个回调。时刻名写错在这里就炸，不留到运行时才炸。"""
        if moment not in self._table:
            raise ValueError(f"没有这个时刻：{moment}；可用的是 {MOMENTS}")
        self._table[moment].append(fn)
        return fn                # 返回自己，可以直接当装饰器用

    def fire(self, moment, event):
        """到点就跑。返回值决定这一层能不能拦住这次动作。

        注意 fire 的调用点在外壳的流程里，不在模型够得着的地方——
        「触发权在流程手里，不在模型手里」就落在这一行。
        """
        if moment not in self._table:
            raise ValueError(f"没有这个时刻：{moment}")
        for fn in self._table[moment]:
            result = fn(event)
            if result is None:
                result = (PASS, None)      # 回调不返回东西就当放行
            verdict, patch = result if isinstance(result, tuple) else (result, None)
            self.fired.append((moment, getattr(fn, "__name__", "?"), verdict))
            if patch:
                event.update(patch)        # 补进去的信息，后面的回调也看得见
            if verdict == BLOCK:
                return BLOCK, fn           # 拦下之后，不再跑后面的回调
        return PASS, None


hooks = Hooks()


@hooks.on("工具执行后")
def 自动格式化(event):
    """纯机械的收尾：每次改完文件都跑，不需要理解模型想干什么。

    顺带演示 21.5.4 的「便宜钩子」——条件不满足就立刻返回，代价接近零。
    """
    if event["工具"] != "改文件":
        return None
    return PATCH, {"已格式化": True}


@hooks.on("工具执行前")
def 写进版本库就拦下(event):
    """拦的是一条"问了也没用"的底线：落点落进了版本库内部。

    路径里出现 .git 这一段就 BLOCK。它不需要配置——没有哪份权限规则
    会写"允许改 .git"，这不是授权问题。它判的不是"允不允许写"（21.5.3）。
    """
    分量 = event.get("展开后路径", "").split("/")
    if ".git" in 分量:
        return BLOCK
    return None


@hooks.on("工具执行后")
def 留一条痕(event):
    """职责六要的可回放（见 20.6；「流水账」这个说法见 17.4.6）：每步追加，不覆盖。"""
    return PATCH, {"留痕": f"{event['工具']} → {event['结果摘要']}"}
