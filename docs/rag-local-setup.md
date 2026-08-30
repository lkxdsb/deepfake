# RAG 本地服务启动

本项目的低资源本地 RAG 默认只使用一个模型服务：Ollama。Chroma 是向量数据库，Reranker 为可选增强项，默认不启动。

## 1. Embedding

首次下载本地 Embedding 模型：

```bash
ollama pull embeddinggemma
curl http://127.0.0.1:11434/v1/embeddings \
  -H 'Content-Type: application/json' \
  -d '{"model":"embeddinggemma","input":["深度伪造检测"]}'
```

`embeddinggemma` 仅生成向量，不生成聊天回答。Java 后端使用 Ollama 的 OpenAI 兼容 `POST /v1/embeddings` 接口；`api-key: ollama` 是兼容占位值，本地 Ollama 不验证该值。

## 2. Chroma

```bash
docker run -d --name lingmou-chroma --restart unless-stopped \
  -p 8001:8000 -v "$(pwd)/.data/chroma:/chroma/chroma" chromadb/chroma:latest
curl http://127.0.0.1:8001/api/v2/heartbeat
```

## 3. 配置 NVIDIA 聊天模型

NVIDIA API Key 只保存在本机 `java-backend/.env`（已被 Git 忽略），不要写入 YAML 或提交到仓库。当前已选择并验证可调用的模型为 `nvidia/nemotron-3-nano-30b-a3b`，API 地址为 `https://integrate.api.nvidia.com/v1`。

## 4. 启动与构建索引

从仓库根目录启动，启用本地 RAG 配置：

```bash
cd java-backend
set -a; . .env; set +a
SPRING_PROFILES_ACTIVE=rag-local mvn spring-boot:run
```

另一个终端执行：

```bash
curl http://127.0.0.1:8080/api/rag/index/status
curl -X POST http://127.0.0.1:8080/api/rag/index/rebuild
```

知识来源由 `knowledge-base/sources.json` 明确列出。增量更新使用：

```bash
curl -X POST http://127.0.0.1:8080/api/rag/index/update
```

检索默认每篇文档最多保留 2 个 Chunk，避免一个长文档占满所有来源卡片。需要调整时设置
`RAG_MAX_CHUNKS_PER_DOCUMENT`；设为 `0` 则关闭这个多样性限制。

检索会保留 `RAG_TOP_K`（默认 5）个候选用于召回和离线评测，但问答模型与前端默认只接收
排名最高的 `RAG_ANSWER_SOURCE_K=2` 个证据 Chunk。这样不会降低检索评测的 Recall@K，同时能
减少弱候选被模型误引或被界面展示为“参考来源”。

## 5. 本地聊天模型（可选）

Embedding 不替代聊天大模型。若也希望聊天完全离线，可把已有 Ollama 文本模型提供给 Spring Boot：

```bash
export AI_CHAT_BASE_URL=http://127.0.0.1:11434/v1
export AI_CHAT_API_KEY=ollama
export AI_CHAT_MODEL=qwen3:4b
```

然后再启动后端。无聊天模型时，索引与检索可以工作，但无法生成自然语言答案。项目相关问题命中有效召回时会携带知识库来源；未命中或日常无关问题会走普通聊天回答，且不会伪造知识库引用。

## 6. 可选：本地 BGE Reranker（低资源机器默认不要启动）

在 Apple Silicon 上可用 Hugging Face Text Embeddings Inference（TEI）的 Metal 版本部署 BGE Reranker：

```bash
brew install text-embeddings-inference
text-embeddings-router --model-id BAAI/bge-reranker-v2-m3 --port 8002
```

模型下载约 2.3 GB。服务健康后启用精排：

```bash
export RERANKER_ENABLED=true
export RERANKER_URL=http://127.0.0.1:8002
```

默认每次精排请求只发送 4 个候选，避免低资源设备因一个大批次而拒绝请求；可通过
`RERANKER_MAX_BATCH_CANDIDATES` 调整。RAG 仍会按 `RAG_RERANK_CANDIDATE_K` 聚合全部候选的精排分数。

TEI 的 `/rerank` 协议使用 `query` 和 `texts` 字段；本项目的 Java Reranker 客户端已按此协议发送请求，并同时兼容返回数组及 `{ "results": [...] }` 形式。先确认服务可用：

```bash
curl http://127.0.0.1:8002/health
curl http://127.0.0.1:8002/rerank \
  -H 'Content-Type: application/json' \
  -d '{"query":"CASE 方法", "texts":["CASE 用于视频深度伪造检测。", "这是天气预报。"]}'
```
