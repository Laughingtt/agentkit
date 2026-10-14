# Agent原理及实践

一本从原理到实践的中文技术书籍，面向有编程基础但无 AI/ML 背景的初学者。

## 阅读路线

| Part | 主题 | 状态 |
|---|---|---|
| 1 | 大模型基础 | ✅ 已完稿 |
| 2 | 大模型与 Agent 的演进 | ✅ 已完稿 |
| 3 | Agent 原理 | ✅ 已完稿 |
| 4 | Harness 工程 | ✅ 已完稿 |
| 5 | Agent 功能实现 | ✅ 已完稿 |
| 6 | 工业落地 | ✅ 已完稿 |

34 章全部写完，正文合计约 52.7 万字，配套示例代码在 `code/part-N/`。

## 仓库结构

- `CLAUDE.md`：写作规范与项目宪法
- `part-N-.../`：第 N 个 Part 的章节文件
- `code/part-N/`：第 N 个 Part 的示例代码
- `docs/superpowers/specs/`：设计 spec
- `docs/superpowers/plans/`：实现 plan

## 本地构建与预览

依赖 Node.js 24（`^22.13.0 || >=24.0.0`）。

```bash
npm ci          # 首次或依赖锁文件变更后安装依赖
npm run build   # 构建静态站点（含死链与 Mermaid 校验），输出到 .vitepress/dist
npm run preview # 本地预览构建产物，访问 http://localhost:4173/
```

写作时可改用 `npm run dev` 启动热更新开发服务器（http://localhost:5173/），改动 Markdown 即时生效。

## 当前进度

- ✅ Part 1–6 spec 与 plan
- ✅ Part 1–6 章节写作（Ch1–Ch34 全部完稿）
- ✅ 全书代码块与 `code/` 的逐行一致性核对
- ✅ 全书外链核查
- 🚧 出版排版与最终校样

## 各章速查

| 章 | 标题 | 读它回答什么问题 |
|---|---|---|
| Ch1-5 | 大模型基础 | 模型是怎么被造出来的？它到底在算什么？ |
| Ch6-10 | 大模型与 Agent 的演进 | Agent 这个想法从哪来？协议为什么长成今天这样？ |
| Ch11-16 | Agent 原理 | Agent 由哪些零件组成？它们怎么配合？ |
| Ch17-22 | Harness 工程 | 零件装到生产环境，外面为什么要包一层壳？ |
| Ch23-28 | Agent 功能实现 | 怎么亲手把工具、检索、记忆、协作、协议写出来？ |
| Ch29-34 | 工业落地 | 怎么在生产环境里把它管住、看清、算得过来账？ |