# illustrative only
# depends: 无（纯骨架，所有标识符都是占位名）
# usage: 读文件即可，不需运行
#
# Ch17 17.2 的骨架。这是全 Part 4 的那圈循环——模型是零件，外壳是产品。
# 下面每行右边的〔职责几〕是路标，指向 Ch17 17.4 的七项职责编号。
# 正文里这一段代码与本文件逐字一致。

while not done:
    resp = call_model(memory.pack(budget), registry.list_tools())
    for call in parse(resp):                          # 把模型说的话翻译成一个动作
        if not policy.allow(call): ask_human(call)    # 这一步得先问人吗？      〔职责一〕
        result = sandbox.run(call)                    # 在受限环境里跑          〔职责二〕
        hooks.fire("post_tool", call)                 # 跑完做收尾              〔职责五〕
        memory.append(result)                         # 把结果记进上下文        〔职责三〕

# 另外三项没法单独占一行，它们藏在上面某一步里：
#   工具清单 registry.list_tools() 从协议登记而来            —— 职责四 协议接入
#   ask_human 之后，人怎么把"同意/拒绝"递回外壳              —— 职责七 投递接口
#   hooks.fire 顺手留下的那段执行记录，就是黑匣子              —— 职责六 会话与状态
#
# 注意循环里没有一行是"模型"。模型只在 call_model 里出现一次，
# 其余全是外壳在替它打杂——这正是 Ch17 要说的事。