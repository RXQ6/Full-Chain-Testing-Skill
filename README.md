# 全链路测试工程师 · Full Chain Testing Skill

面向各类软件，完成测试规划、分层验证、缺陷定位与修复回归，交付可追溯证据和质量报告。

**Skill 标识：`full-chain-testing`**

它提供测试决策、执行 SOP、专项规则及记录工具。覆盖各类软件的测试设计，实际执行取决于当前环境、设备与工具；有限测试不能保证软件绝无缺陷。

## 能做什么

- 将需求、风险、用例、执行、证据、缺陷和回归连接起来。
- 组合处理 Web、移动端、桌面端、API、微服务、数据管道、CLI/SDK、AI/Agent 和硬件相关软件。
- 按需检查认证权限、并发幂等、一致性、性能、故障恢复、兼容和升级。
- 区分通过、失败、受阻、跳过、不适用和不确定，保留首次失败和重跑历史。
- 在明确的修复范围内验证修复，报告剩余风险与清理结果。

## 快速开始

```sh
git clone https://github.com/RXQ6/Full-Chain-Testing-Skill.git full-chain-testing
cd full-chain-testing
```

将目录放到所用 Agent 工具支持的技能位置，或在测试请求中明确提供本项目 `SKILL.md` 的实际路径。这里不自动修改宿主的全局设置。

示例请求：

```text
请读取 <本项目绝对路径>/SKILL.md，按该 Skill 测试我的项目。

项目：<被测项目路径>
模式：verify
范围：登录、个人信息和权限。

允许在本地隔离环境启动服务、创建测试数据及新增测试。
产品代码修改不在本次范围内。
请实际执行，交付缺陷、证据、覆盖缺口和剩余风险。
```

| 模式 | 行为 |
|---|---|
| `plan` | 设计方案，不声称已执行 |
| `verify` | 执行、取证、定位和报告；不擅自修改产品行为 |
| `repair` | 在用户明确授权范围内修复产品并回归 |

只测试一个函数时使用相称流程，不强制启动浏览器或微服务。已有授权沿用；测试授权不自动扩展为生产负载、真实支付、对外发送或发布。

## 运行记录工具

辅助脚本需要 **Python 3.10+**，只使用标准库，无需 `pip install`。

```sh
python scripts/new_run.py .runs/example --mode verify
```

新目录只包含未执行模板。填写实际需求、版本、环境和用例；实际执行后追加尝试、证据、缺陷和资源记录，再检查：

```sh
python scripts/validate_records.py .runs/example --json
python scripts/check_traceability.py .runs/example --json
python scripts/summarize_results.py .runs/example --json
```

**`valid: true` 仅表示记录通过相应检查，不表示被测产品通过验收。** 新建模板没有需求和执行结果，追溯检查应报告缺口。

## 测试这个 Skill

```sh
python -m unittest discover -s tests -v
python scripts/self_check.py .
```

本地合成 API 演示会真实启动 loopback 服务，不调用外部业务系统。使用尚不存在的输出目录：

```sh
python evaluation/run_fixture.py .runs/api-defective --variant defective
python evaluation/run_fixture.py .runs/api-fixed --variant fixed
python scripts/check_traceability.py .runs/api-defective --json
python scripts/summarize_results.py .runs/api-defective --json
```

缺陷版应检出三个契约问题：金额错误、403 后仍写入、相同幂等键重复订单；修正版相同三项通过。演示退出码为 0 表示执行和记录完整，不表示缺陷版没有问题。

GitHub Actions 在 Linux / Python 3.10 与 Windows / Python 3.12 上运行单元测试、结构检查和合成 API 验证。各平台远端执行结果以 Actions 页面为准。

脚本测试不代替 AI 行为验收、真实设备测试或未知缺陷发现能力评估。独立行为任务见 [验收清单](references/acceptance.md)，实际本地验证范围见 [验证说明](evaluation/validation-report.md)。

## 文档导航

| 文档 | 内容 |
|---|---|
| [SKILL.md](SKILL.md) | 入口、模式、核心规则和专项路由 |
| [架构蓝图](references/blueprint.md) | 分层与能力边界 |
| [完整 SOP](references/workflow.md) | S0—S12 执行流程 |
| [用例设计](references/case-design.md) | 判断依据与覆盖方法 |
| [记录契约](references/records-and-status.md) | JSON/JSONL、状态和证据格式 |
| [证据与报告](references/evidence-and-reporting.md) | 指标、版本与结论 |
| [工具适配](references/tool-adapters.md) | 工具发现、执行和 CI 规则 |
| [正反样例](references/examples.md) | 正确行为与常见误用 |
| [开发手则](references/development.md) | 开发流程与维护标准 |
| [行为验收](references/acceptance.md) | 24 项独立行为场景 |

对象专项位于 `references/objects/`，跨对象质量专项位于 `references/quality/`；按需读取，不必每次加载全部文件。

## 贡献

围绕可复现的漏测、误报、越界或证据问题提交改进，并补充有区分力的测试。保留需求依据和首次失败，不通过削弱断言制造成功；提交前运行上述校验。请勿提交真实凭证、客户数据或本机临时记录。
