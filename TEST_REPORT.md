# 测试报告

## 测试结论

已为 LLM 数据管道建立可离线运行的 pytest 回归测试。测试不调用外部大模型 API，重点验证 LLM 生成代码进入系统后的执行边界，以及样例数据生成器的稳定性。

## 真实模型质量指标

| 指标 | 结果 |
| --- | ---: |
| 首轮场景通过率 | 75.0%（3/4） |
| 代码可执行率 | 100.0%（4/4） |
| 数据值正确率 | 100.0%（4/4） |
| 自修复后通过率 | 100.0%（4/4） |

在线评测覆盖价格清洗、混合日期、嵌套 JSON 和用户编号四类任务。混合日期首轮失败，在收到实际值与期望值反馈后第二次生成通过，验证了项目的自修复闭环。

完整结果见 evaluation/LIVE_EVALUATION_REPORT.md，原始输出与生成代码见 evaluation/results.json。API 密钥不会写入评测结果或仓库。

## 覆盖范围

- 动态执行 clean_data 清洗函数，并验证返回值必须是 pandas DataFrame。
- 验证输入 DataFrame 使用副本，避免生成代码污染原始数据。
- 验证执行环境正确提供 pandas 和 json。
- 验证缺少函数、错误返回类型及业务异常均会转换为带异常类型、消息和堆栈的 RuntimeError。
- 验证销售数据的行数、字段、交易编号和 metadata JSON 结构。
- 验证服务器日志的行数、字段和两种日志格式。

## 成果价值

这组测试保护了项目风险最高的边界：未经人工确认的 LLM 代码执行。代码契约破坏、异常信息丢失、原始数据被修改或模拟数据格式漂移，都能在本地和 CI 中快速暴露。

## 验证方式

    python -m pytest -q

测试结果：7 passed

在线质量评测需要在进程环境中提供 OPENAI_API_KEY：

    python evaluation/evaluate_live_llm.py

## 测试文件

- tests/test_executor_and_generators.py
- evaluation/evaluate_live_llm.py
- evaluation/LIVE_EVALUATION_REPORT.md
