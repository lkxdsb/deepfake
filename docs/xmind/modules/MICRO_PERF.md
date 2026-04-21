# micro_perf 导图

- 模块目标
- 面向单算子或算子组合的微基准测试
- 定位端到端性能瓶颈来源

- 典型内容
- GEMM/Attention/Dispatch 等核心算子
- prefill/decode 阶段关键算子
- MoE 路径关键算子

- 输入
- op 配置
- shape 配置
- dtype
- backend/hardware 配置
- 运行时参数（warmup/iters/并发）

- 主流程
- 加载算子 workload
- 初始化后端 runtime
- warmup
- 正式迭代
- 收集 latency/throughput
- 汇总 csv/json 报告

- 指标
- 平均延迟
- P50/P90/P99
- 吞吐（samples/s 或 tokens/s）
- 算子效率（可选）
- 内存占用（可选）

- 与其他模块关系
- 为 general_perf/llm_perf 的瓶颈提供归因
- 用于验证后端算子优化收益

- 风险点
- shape 不一致导致不可对比
- 计时窗口不统一导致抖动
- 后端 fallback 未显式暴露

- 建议输出
- 按 op 分类汇总表
- 同硬件跨版本对比图
- 同版本跨硬件对比图
