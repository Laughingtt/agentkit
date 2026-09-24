# Part 1 示例代码

依赖：

- Python ≥ 3.10
- PyTorch ≥ 2.0
- transformers ≥ 4.30
- numpy

安装：

```bash
pip install torch transformers numpy

# 若 huggingface.co 不可达，运行示例前设置镜像：
# export HF_ENDPOINT=https://hf-mirror.com
```

| 文件 | 对应章节 | 是否可运行 | 说明 |
|---|---|---|---|
| [`train_mlp.py`](train_mlp.py) | Ch2 | 是 | 一个最小 MLP 拟合正弦函数 |
| [`attention.py`](attention.py) | Ch3 | 是 | 手写 scaled dot-product attention |
| [`tokenize_demo.py`](tokenize_demo.py) | Ch4 | 是 | 用 transformers tokenizer 演示 BPE |