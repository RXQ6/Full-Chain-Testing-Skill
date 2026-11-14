# 验证范围与复现

本项目的验证分为记录工具、合成 API 和独立模型行为三层。

## 自动验证

```sh
python -m unittest discover -s tests -v
python scripts/self_check.py .
```

覆盖记录状态、引用、证据路径与哈希、版本、断言、重跑历史、清理、新建目录与命令行退出行为。结构检查验证本包的简单元数据、本地引用、Python 语法及 JSON 模板，不是通用 YAML 解析器或行为认证。

结构检查允许仓库以不同目录名克隆，Skill 标识仍保持 `full-chain-testing`。

## 合成 API

```sh
python evaluation/run_fixture.py .runs/api-defective --variant defective
python evaluation/run_fixture.py .runs/api-fixed --variant fixed
```

实际向本地 loopback 服务发送请求，缺陷版包含错误金额、403 后写入、重复下单三个预设问题；修正版遵循相同契约。输出目录保存实际响应、逐项断言、缺陷、SHA-256、清理证据与质量结论。不得覆盖已有运行目录。

缺陷组记录有效且质量结论为 `does_not_meet_criteria`，两者并不矛盾。示例执行成功不表示未知缺陷发现率，也不证明并发和全平台能力。

## 独立行为及平台验收

[24项行为验收规约](../references/acceptance.md)是后续任务，不是全部已经通过的记录。没有以脚本测试代替独立模型前向评估，也没有声称真实浏览器、移动设备、桌面升级或硬件已经验收。

当前结构检查无需第三方依赖。开发阶段曾尝试外部 `skill-creator/quick_validate.py`，因该运行环境缺少 PyYAML 未执行成功；本项目不声称获得其认证。

GitHub Actions 的实际状态以对应提交的运行记录为准；本地结果不冒充远端结果。

## 2026-11-14 问题报告修复
- 路径根与目标统一resolve，区分逃逸、缺失和读取失败；POSIX文件名与Windows ADS分平台处理。
- 新增范围合同、结构化验收、豁免证据、缺陷发现时序、根因证据、执行预算、负向对照和flaky状态检查。
- CLI文本/JSON/显式文件输出、跨run对比；初始化失败清除独占新目录并提醒gitignore。
- 增加轻量契约、真实仓库自托管案例与填好记录；专项补充操作步骤和边界。
- 本地59项回归（1项平台跳过）及实际负向对照通过。双平台结果以此次提交的GitHub Actions为准，不能用本地代替Windows runner结果。
- 第三方真实项目与独立模型盲测仍未执行；本次案例明确是自托管真实代码，不宣称第三方评估。
