"""契约 §6 错误码（《行为与数据契约》03-行为与数据契约.md §6）。

错误码是跨组件的稳定契约：任何模块抛出/记录错误时使用统一字符串，
runner 与报告据此生成 reason_codes，便于审计与验收场景断言。
"""

# 安全隔离
SOURCE_ACCESS_VIOLATION = "SOURCE_ACCESS_VIOLATION"   # Coder 触达源码区
HOLDOUT_LEAK = "HOLDOUT_LEAK"                          # holdout 详情进入生成上下文
PROTECTION_MISMATCH = "PROTECTION_MISMATCH"            # 受保护文件哈希变化
EVALSET_LEAK = "EVALSET_LEAK"                          # 评测期望/golden 泄露给 Coder

# 模型与上下文
EMPTY_MODEL_OUTPUT = "EMPTY_MODEL_OUTPUT"              # 模型返回空内容（重试后仍空）
INCOMPLETE_CONTEXT = "INCOMPLETE_CONTEXT"              # 输入被截断或缺少必要知识
PROVIDER_ERROR = "PROVIDER_ERROR"                      # provider 调用失败

# 评测与门禁
COMPILE_FAILED = "COMPILE_FAILED"                      # 生成代码不可构建
ZERO_CASES = "ZERO_CASES"                              # 没有有效测试用例
INCONSISTENT_TOTAL = "INCONSISTENT_TOTAL"              # 重复评测 total 不一致
INVALID_EVALUATION = "INVALID_EVALUATION"              # 评测无效（零用例/统计缺失）
UNSTABLE_RESULT = "UNSTABLE_RESULT"                    # 重复结果方差超限
REGRESSION = "REGRESSION"                              # 主指标低于已接受基线
TRAIN_BELOW_THRESHOLD = "TRAIN_BELOW_THRESHOLD"        # train 未达阈值
HOLDOUT_REQUIRED = "HOLDOUT_REQUIRED"                  # 需要 holdout 但未执行
HOLDOUT_BELOW_THRESHOLD = "HOLDOUT_BELOW_THRESHOLD"    # holdout 未达标
MAX_BUDGET = "MAX_BUDGET"                              # 轮次/时间/成本耗尽
INCOMPLETE_FEEDBACK = "INCOMPLETE_FEEDBACK"            # 归因无修订指令，无法继续
NO_GENERATIONS = "NO_GENERATIONS"                      # 无有效生成候选
