# RAG 离线评测结果（复核金标后重算）

- 原始检索明细：`rag-eval/results/rag-v1-vector-hybrid-retrieval/vector-details.jsonl`
- 当前人工复核集：`rag-eval/datasets/rag-v1-manually-reviewed.jsonl`
- 说明：本报告只重算指标；不发起新的 HTTP 请求，不改变任何原始检索结果。

| 模式 | Recall@1 | Recall@3 | Recall@5 | MRR | 候选引用准确率 | 引用覆盖率 | 知识库路由准确率 |
|---|---:|---:|---:|---:|---:|---:|---:|
| VECTOR | 0.5000 | 0.6531 | 0.7245 | 0.5866 | 0.1816 | 0.7245 | 0.7030 |
