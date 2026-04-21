# XMind 导图模板包

这个目录提供一套可直接导入 XMind 的 Markdown 导图源文件，包含：

- 总图：`PROJECT_OVERVIEW.md`
- 子图模板：`modules/*.md`

## 建议导入顺序

1. 导入 `PROJECT_OVERVIEW.md` 作为项目总览图。
2. 逐个导入 `modules/*.md` 作为模块逻辑子图。
3. 在总图里给每个模块节点添加「超链接」，指向对应子图文件或 XMind 主题。

## XMind 操作步骤

1. 打开 XMind。
2. 选择：`文件 -> 导入 -> Markdown`。
3. 选择本目录下的 `.md` 文件。
4. 导入后按需要调整布局（推荐「逻辑图」或「树形图」）。

## 命名建议

- 总图：`Project_Overview.xmind`
- 子图：
- `InferPerf_GeneralPerf.xmind`
- `InferPerf_LLMPerf.xmind`
- `MicroPerf.xmind`
- `TraceGen.xmind`

## 维护建议

- 结构变更时，先改对应模块 Markdown，再重新导入覆盖。
- 版本迭代时在各模块增加 `版本记录` 节点，保留关键变更历史。
