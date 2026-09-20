# runnable: yes
# 依赖：torch
# 用法：python train_mlp.py
# 说明：用一个最小 MLP（2 层隐藏层）拟合 y = sin(x)，演示 PyTorch 训练基本流程

import torch
import torch.nn as nn
import torch.optim as optim


class MLP(nn.Module):
    """最小 MLP：输入 1 → 隐藏 32 → 隐藏 32 → 输出 1"""

    def __init__(self) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(1, 32),
            nn.ReLU(),
            nn.Linear(32, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def main() -> None:
    torch.manual_seed(0)
    x = torch.linspace(-2 * torch.pi, 2 * torch.pi, 200).reshape(-1, 1)
    y = torch.sin(x)

    model = MLP()
    optimizer = optim.Adam(model.parameters(), lr=1e-2)
    loss_fn = nn.MSELoss()

    for step in range(1000):
        pred = model(x)
        loss = loss_fn(pred, y)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        if step % 200 == 0:
            print(f"step {step:4d}  loss={loss.item():.4f}")

    final_loss = loss_fn(model(x), y).item()
    print(f"final loss = {final_loss:.4f}")
    assert final_loss < 0.01, f"训练未收敛：final loss = {final_loss}"


if __name__ == "__main__":
    main()
