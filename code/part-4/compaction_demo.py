# illustrative only
# depends: 无（纯骨架，所有标识符都是占位名）
# usage: 读文件即可，不需运行
#
# Ch20 20.4 的骨架。四种压缩策略的差别只在“被丢掉的那部分怎么办”这一步。

THRESHOLD = 0.8          # 用到窗口的这个比例就开始收拾，留出缓冲给模型自己的输出


def compact(ctx, budget):
    """装配已经完成了，模型还没被叫。超预算就在这里收拾。"""
    if ctx.total() <= budget * THRESHOLD:
        return ctx                      # 没到线，什么都不做——压缩只发生在“要用”的那一刻

    dropped = ctx.dropped()             # 超出预算的这部分，四种策略拿到的输入完全一样

    if STRATEGY == "滑窗":
        ctx.keep(last_n=ctx.tail(2))    # 丢掉的部分：不要了
        return ctx

    if STRATEGY == "摘要":
        ctx.keep(last_n=ctx.tail(2))
        ctx.insert(0, summarize(dropped,
                                must_keep=constraints_of(dropped)))
        return ctx                      # 丢掉的部分：换一段交接说明顶替

    if STRATEGY == "淘汰":
        ctx.keep_by(score=still_needed) # 不看新旧，只看还要不要用
        return ctx                      # 丢掉的部分：先挪个地方，有用再拿回来

    if STRATEGY == "外置":
        ctx.keep(last_n=ctx.tail(2))
        stash.put(dropped)              # 整段搬出窗口
        register_tool("取回第 k 轮", lambda k: stash.get(k))
        return ctx                      # 窗口里只多一个地址，正文一个字都没留