# infer_perf/general_perf 导图

- 模块目标
- 对 CV/NLP 等通用模型做端到端推理评测
- 统一编译、运行、精度、数值一致性、性能测试

- 关键目录
- launch.py（入口）
- core/perf_engine.py（执行引擎）
- workloads/*.json（任务配置）
- model_zoo/*.json（模型与数据集元信息）
- backends/<HW>/（编译后端与运行后端）
- datasets/<name>/（数据预处理与准确率逻辑）

- 输入
- task（如 resnet50-torch-fp32）
- hardware_type（如 CPU/GPU/自定义后端）
- compile_only
- skip_install

- 主流程
- 参数解析与环境准备
- workload 加载
- model_zoo 加载
- 模型/数据集按需下载与解压
- 可选 CPU numeric checker
- 进入 perf_engine
- 后端初始化（compile backend + runtime backend）
- 预优化与编译
- compile_only 分支判断
- accuracy 分支（可选）
- numeric 分支（可选）
- perf 分支（遍历 batch size）
- 汇总报告输出

- 核心测试开关
- test_perf
- test_accuracy
- test_numeric
- compile_only

- 指标输出
- Graph Compile
- Compile Duration
- Compile Precision
- Subgraph Coverage
- Optimizations
- Accuracy
- task-specific 指标（如 Top1/Top5、mAP）
- Numeric
- Mean Diff
- Std Diff
- Max Diff
- Mean Rel-Diff
- Max Rel-Diff
- Diff Dist
- Performance
- BS
- AVG Latency
- P99 Latency
- QPS

- 关键风险点
- task 名称不匹配导致 workload 为空
- 数据集 data_loader 缺失
- skip_install 后依赖缺失
- provider 未正确加载导致回退 CPU
- numeric 参考基线缺失

- 排障优先级
- 先看入口参数与 workload 命中
- 再看 model/dataset 文件是否齐全
- 再看后端 provider 是否生效
- 最后看单模型/单 batch 运行日志

- 产物
- reports/<backend>/<task>/result.json
- 可选 PDF/图片
