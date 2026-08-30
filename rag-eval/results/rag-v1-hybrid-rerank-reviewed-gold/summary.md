# RAG 离线评测结果（复核金标后重算）

- 原始检索明细：`rag-eval/results/rag-v1-hybrid-rerank-retrieval/hybrid-rerank-details.jsonl`
- 当前人工复核集：`rag-eval/datasets/rag-v1-manually-reviewed.jsonl`
- 说明：本报告只重算指标；不发起新的 HTTP 请求，不改变任何原始检索结果。

| 模式 | Recall@1 | Recall@3 | Recall@5 | MRR | 候选引用准确率 | 引用覆盖率 | 知识库路由准确率 |
|---|---:|---:|---:|---:|---:|---:|---:|
| HYBRID_RERANK | 0.7041 | 0.9082 | 0.9286 | 0.7920 | 0.1802 | 0.9286 | 0.9010 |
