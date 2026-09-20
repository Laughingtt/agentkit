# runnable: yes
# 依赖：torch
# 用法：python attention.py
# 说明：手写 scaled dot-product attention，对一组随机 query/key/value 计算注意力输出与权重

import torch
import torch.nn.functional as F


def scaled_dot_product_attention(
    query: torch.Tensor,
    key: torch.Tensor,
    value: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Scaled dot-product attention.

    Args:
        query: shape (batch, seq_len, d_k)
        key: shape (batch, seq_len, d_k)
        value: shape (batch, seq_len, d_v)

    Returns:
        output: shape (batch, seq_len, d_v)
        attn: shape (batch, seq_len, seq_len)
    """
    d_k = query.size(-1)
    scores = torch.matmul(query, key.transpose(-2, -1)) / (d_k ** 0.5)
    attn = F.softmax(scores, dim=-1)
    output = torch.matmul(attn, value)
    return output, attn


def main() -> None:
    torch.manual_seed(0)
    batch, seq_len, d = 2, 4, 8
    q = torch.randn(batch, seq_len, d)
    k = torch.randn(batch, seq_len, d)
    v = torch.randn(batch, seq_len, d)

    output, attn = scaled_dot_product_attention(q, k, v)

    print(f"output shape: {tuple(output.shape)}")
    print(f"attn shape:   {tuple(attn.shape)}")

    # 验证：注意力权重每行和为 1
    row_sums = attn.sum(dim=-1)
    assert torch.allclose(row_sums, torch.ones_like(row_sums), atol=1e-5), \
        f"注意力权重行和应为 1，实际 = {row_sums}"
    # 验证：输出形状正确
    assert output.shape == (batch, seq_len, d), \
        f"输出形状错误：{output.shape}"

    print("OK：注意力权重行和为 1，输出形状正确")


if __name__ == "__main__":
    main()