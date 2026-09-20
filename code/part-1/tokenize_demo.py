# runnable: yes
# 依赖：transformers
# 用法：python tokenize_demo.py
# 说明：用 Qwen2.5 的 tokenizer 演示 BPE 编码与解码

from transformers import AutoTokenizer


def main() -> None:
    # 使用一个轻量级开源 tokenizer；若无网络，可替换为本地路径
    tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-0.5B")

    texts = [
        "Hello, world!",
        "Transformer 是 LLM 的核心架构。",
        "Tokenization 把文本切成子词单元。",
    ]

    for text in texts:
        ids = tokenizer.encode(text)
        tokens = tokenizer.convert_ids_to_tokens(ids)
        decoded = tokenizer.decode(ids)
        print(f"原文: {text}")
        print(f"  ids:   {ids}")
        print(f"  tokens:{tokens}")
        print(f"  解码:  {decoded}")
        assert decoded == text or decoded.strip() == text.strip(), \
            f"解码后与原文不一致：{decoded!r} vs {text!r}"

    print("OK：编码 / 解码可逆")


if __name__ == "__main__":
    main()
