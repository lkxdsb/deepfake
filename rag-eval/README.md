# RAG 离线评测

`datasets/` 中的 JSONL 是判定标准；每一条题目、关联来源和 Chunk ID 必须由维护者根据当前已索引资料人工复核。不要用大模型生成的问答直接作为金标，也不要把 mock 或失败降级输出写成真实结果。

## 当前准备状态

- `datasets/seed-manually-reviewed.jsonl`：26 条首批种子集，聚焦新补充的 4 份取证指南，用于先验证评测流程与指标实现。
- `datasets/rag-v1-manually-reviewed.jsonl`：101 条首版人工核对集，覆盖项目使用、图片/视频/音频流程、CASE/FCG/CCSA/Bi-ST、AASIST、指标解释、溯源与知识库外问题；它与当前 `rag-index/manifest.json` 的 Chunk ID 一起校验。
- `run_eval.py`：无第三方依赖的可复现 HTTP 执行器，针对同一个已启动的 Java 后端运行 `VECTOR`、`HYBRID`、`HYBRID_RERANK`；默认只调用检索端点，不消耗聊天模型配额。
- 结果写入独立的 `rag-eval/results/<UTC 时间>/`，不会覆盖旧结果。

## 数据集字段

```json
{"id":"eval-seed-001","question":"...","relevantChunkIds":["..."],"relevantSources":["..."],"answerPoints":["..."],"shouldRefuse":false}
```

`relevantChunkIds` 是严格的引用判定依据；`relevantSources` 便于人工审阅。索引重建后若源文本或 Chunk 参数变化，必须先重新核对 Chunk ID，再运行历史数据集。

当前产品允许“非知识库问题 → 普通模型回答且不附来源”。因此 `shouldRefuse: true` 在离线集中的含义是**不应展示知识库来源**，而不是必须让聊天模型沉默。报告把这项命名为“知识库路由准确率”，避免将普通聊天能力误判为失败。

## 指标

- Recall@K：可回答题中，前 K 个来源至少包含一个 `relevantChunkIds` 的比例。
- MRR：可回答题中第一个相关 Chunk 名次倒数的平均值；未命中记 0。
- 引用准确率：全部返回来源中，Chunk ID 位于该题 `relevantChunkIds` 的比例。
- 引用覆盖率：可回答题中，至少返回一个相关 Chunk 的比例。
- 知识库路由准确率：应使用知识库题命中相关来源，且 `shouldRefuse` 题不返回任何来源的比例。
- 延迟：默认调用 `/api/rag/retrieve`，真实测量模型无关的检索 P50/P95；加 `--include-answer` 时调用 `/api/chat/ask`，测量端到端 P50/P95。两种结果必须分开保存和解读。

## 运行

先确认 Java 后端、Chroma、Embedding 已经启动且索引是当前版本：

```bash
cd /Users/hjjtongxue/AI/GitHub项目/deepfake-java
curl http://127.0.0.1:8081/api/rag/index/status
python3 rag-eval/run_eval.py \
  --dataset rag-eval/datasets/seed-manually-reviewed.jsonl \
  --base-url http://127.0.0.1:8081 \
  --modes VECTOR HYBRID HYBRID_RERANK
```

精排模式只有在已启动 Reranker 且 `RERANKER_ENABLED=true` 的后端实例上才是实际精排；否则后端会降级，结果中的 `reportedRetrievalMode` 可以审计该事实。

若需要额外生成含模型回答的端到端报告，显式加 `--include-answer`；这会实际调用配置的大模型服务，耗时和费用均会增加。

当人工复核发现一题存在多个等价支持 Chunk 时，可在数据集补充这些 Chunk ID，然后用已保存的原始检索明细重算指标，不必重复调用模型：

```bash
python3 rag-eval/rescore_details.py \
  --dataset rag-eval/datasets/rag-v1-manually-reviewed.jsonl \
  --details rag-eval/results/rag-v1-hybrid-rerank-retrieval/hybrid-rerank-details.jsonl \
  --mode HYBRID_RERANK \
  --output-dir rag-eval/results/<new-reviewed-gold-run>
```

该操作只允许添加经过人工检查、确实能支持该题 `answerPoints` 的等价证据；脚本会保留原始明细，并在报告中明确标记为“复核金标后重算”。
