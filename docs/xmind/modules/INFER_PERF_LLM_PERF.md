# infer_perf/llm_perf 导图

- 模块目标
- 面向 LLM 的服务化推理测试
- 同时评估 accuracy 与 online performance

- 关键目录
- launch.py（总控）
- server/launch_server.py（服务启动）
- server/endpoint.py（请求处理）
- benchmark/bench.py（客户端压测）
- core/scheduler.py（调度抽象）
- backends/GPU/*（推理实现）
- utils/reporter.py（指标聚合）
- workloads/*.json
- model_zoo/*.json

- 输入
- task（如 chatglm2-torch-fp16-6b）
- hardware_type
- host/port

- 主流程
- launch 加载 workload
- prepare_model 下载模型
- 可选下载 accuracy baseline logits
- 启动 reporter
- Accuracy 阶段
- 启动 server
- 启动 1 个 benchmark client
- 读取数据集逐题推理
- 收集 perplexity/logits_dump
- 性能阶段
- 遍历 tp_size × batch_size × input_tokens
- 每组都启动 server + 多 client 并发压测
- reporter 实时汇总并最终落盘

- 服务端内部逻辑
- tokenizer 编码 prompt
- scheduler 接收任务
- context 阶段（prefill）
- decode 阶段（逐 token 迭代）
- sampler 选 token 并判断 finish
- streaming 返回 token 与时延拆分

- Accuracy 指标
- PPL
- Logits Diff
- Max Difference
- MSE
- MAE
- Cosine Similarity
- Token Diff

- Performance 指标
- First Token Latency（AVG/P90）
- Per Token Latency（AVG/P90）
- Context Wait/Model Time
- Decode Wait/Model Time
- Token Throughput
- QPS
- Request Number

- 关键风险点
- tokenizer/model 路径不一致
- baseline logits 缺失导致 accuracy diff 失败
- 并发下 server 未 ready 就发请求
- tp_size 与硬件资源不匹配

- 产物
- llm_perf/reports/<backend>/<task>/result.json
- logits/*.npy
- logits_diff.png
- token_diff.png
