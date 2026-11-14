# 本仓库真实代码的自托管案例
目标是校验器源码和命令行，而非合成订单API。执行run_repository_case.py运行实际测试套件，再在独立副本中撤回root归一化，要求针对性回归失败；失败原因需包含该测试名称，不能把环境故障当杀死变异。
~~~sh
python evaluation/run_repository_case.py .runs/repository-case
python scripts/summarize_results.py .runs/repository-case --json --output .runs/repository-case/independent-summary.json
~~~
产物目录：run.json、cases.json、results.jsonl、evidence.json、defects.json、resources.json、evidence/one.txt（实际进程输出，含基线/变异退出码、断言结果和脱敏后的失败输出）。最终摘要由独立汇总器生成。
这不是第三方系统、未知缺陷发现率或独立Agent前向评估；不可将自托管证据推广为全平台完成。实际执行摘要和短报告在验收后附入本页。

## 实际运行结果
本地Windows/Python3.12实际运行59项测试：58通过，1项POSIX冒号文件名测试按平台跳过。隔离撤回root规范化后，目标测试失败；负向对照检出，记录验证和独立汇总成功。
完整填好产物见 [run](examples/repository/run.json)、[用例](examples/repository/cases.json)、[尝试](examples/repository/results.jsonl)、[证据](examples/repository/evidence/one.txt)、[独立汇总](examples/repository/independent-summary.json)。等价的 [轻量产物](examples/compact/compact.json) 在独立目录，不能与多文件记录混放。
短报告：本次约定的校验器测试和路径回归满足条件；没有验证独立Agent行为或外部系统。测试证据中的机器路径已脱敏，源码版本以运行记录的内容摘要标识，不虚构为发布commit。
