# 项目总览导图

- 项目目标
- 统一性能基准能力
- 覆盖通用模型、LLM、微算子、Trace 回放
- 输出可复现的性能与精度报告

- 顶层模块
- infer_perf
- general_perf（通用模型端到端）
- llm_perf（大模型在线推理链路）
- micro_perf（算子级性能）
- trace_gen（业务负载/请求轨迹构造）
- datasets 与 model_zoo
- scripts 与 tools
- reports 与可视化

- 模块关系
- trace_gen 产出负载模式与输入分布
- micro_perf 评估单算子上限与瓶颈
- infer_perf/general_perf 评估模型端到端性能与精度
- infer_perf/llm_perf 评估服务化 LLM 推理指标
- reports 汇总所有评估结果形成横向对比

- 统一输入
- workload 配置
- model_zoo 配置
- backend 配置
- dataset 配置

- 统一输出
- 编译信息
- 精度指标
- 数值一致性指标
- 性能指标（吞吐/延迟）
- 报告文件（json/pdf/png）

- 横切能力
- 环境管理（依赖、虚拟环境、跳过安装）
- 日志与可观测性
- 错误处理与降级路径
- 自动化脚本

- 子图索引
- infer_perf/general_perf -> modules/INFER_PERF_GENERAL_PERF.md
- infer_perf/llm_perf -> modules/INFER_PERF_LLM_PERF.md
- micro_perf -> modules/MICRO_PERF.md
- trace_gen -> modules/TRACE_GEN.md
