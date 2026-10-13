# illustrative only
# Ch15 示意代码：级联路由——便宜的判断先做，做不了才升级到中心大模型


def cheap_check(text):
    """小模型干粗活：判断这段话能不能用规则直接处理掉。
    返回 (handled, result)，handled 为 True 表示不用升级。"""
    if "?" in text or "？" in text:
        return False, None              # 问句要理解意图 → 升级
    if len(text) < 30:
        return True, f"已记录：{text}"    # 短指令照做，不用大模型
    return False, None


def central_llm(text):
    """中心大模型：兜底处理真正需要理解意图的活。"""
    return f"（大模型处理）{text}"


def route(text):
    """级联主函数：先便宜后昂贵，升级信号 = 小模型处理不了。"""
    handled, result = cheap_check(text)
    if handled:
        return "小模型", result
    return "中心LLM", central_llm(text)
