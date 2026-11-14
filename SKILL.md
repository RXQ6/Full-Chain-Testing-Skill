---
name: full-chain-testing
description: 对软件、功能、接口和跨组件业务链路开展风险驱动的测试规划、实际验证、缺陷定位与修复回归，交付可追溯证据、覆盖状态和质量结论。适用于各类软件及组合链路的测试请求；根据对象、环境和工具能力加载专项，不用于一般概念讲解或无关开发。
---

# 全链路软件测试与质量验证

使需求、风险、用例、执行、证据、缺陷、回归和结论连成闭环。覆盖各类软件对象；实际执行能力由环境、设备和工具决定。有限测试不保证绝无缺陷，必须报告未覆盖部分与剩余风险。

## 开始与模式

先读取用户上下文、项目指令、需求、源码、现有测试和 CI，再补问影响正确性或操作边界的必要信息。已有授权持续有效；继续不依赖缺失信息的工作。

- `plan`：设计方案，不声称执行。适用“设计测试方案”。
- `verify`：执行测试、添加测试与必要测试辅助代码、定位并报告。适用“测试这个项目”。不擅自改变产品行为。
- `repair`：在用户明确要求修复时，实施有针对性的产品修复并回归。
- 全面测试先建立对象和风险地图；单点任务使用相称流程，不强制启动无关服务。
- 不将测试授权扩展为生产负载、真实支付、对外发送、部署发布或破坏性操作授权。沿用明确已有授权；需要时只阻塞相应动作。

## 必须守住三条
1. 预期来自约定规则，实际执行绑定版本与证据；静态、模拟、真实集成和未测分别报告。
2. 保留失败与全部尝试，不削弱断言、不缩范围、不将受阻/不确定伪装通过。
3. 沿用授权并隔离数据，保护秘密与不可信输入边界，只清理本次拥有的资源。

应当：风险优先；独立断言；有界异步与重试；追踪业务副作用；复核清理与剩余风险。
机器契约及全部细则见 [记录规范](references/records-and-status.md)。

## 按任务成本选路径
- 单函数/单接口、至多3个用例、无共享状态/外部写入/并发/权限/性能风险：使用 [compact.json](assets/compact-template.json)，内联run、cases、attempts、evidence、defects、resources；证据文件仍需实际落盘和哈希。
- 超过阈值或涉及上述高风险：完整多文件路径。轻量与完整模式使用同一个校验器，不能因轻量而弱化断言。
- verify新增测试优先放被测项目既有测试目录并说明差异；无写入授权或只是探索时放run目录，由可信命令显式运行。不改产品行为。
- 对可安全隔离的关键规则执行负向对照：原实现通过、注入已知违例后失败；未检出则用例不能支撑验收。不可安全注入时记录inconclusive，提出替代验证，不在生产/设备上强行注入。
- 每例默认最多3次诊断尝试，失败不被多数通过抵消；flaky/quarantined保留不确定，注明owner、reason、recheck_at，不能满足必测验收。

完整设计见 [架构蓝图](references/blueprint.md)，执行工具接口见 [工具适配契约](references/tool-adapters.md)。

## 执行路径

执行时阅读 [完整 SOP](references/workflow.md)。复杂任务先读 [记录与状态](references/records-and-status.md)，按需读取 [用例设计](references/case-design.md) 和 [证据与报告](references/evidence-and-reporting.md)。

1. 确定目标、模式、环境、范围、排除项和已有授权。
2. 识别组合对象，检查工具和设备，记录版本及相关已有测试基线。
3. 建立业务链路、状态机、信任边界、同步/异步步骤与副作用清单。
4. 将需求映射到风险和用例；不适用、跳过或受阻必须有理由。
5. 准备隔离数据、可观测性和清理清单；先预检与冒烟，再执行分层及专项测试。
6. 保存所有尝试，分类失败，建立最小复现；修复模式下保留原失败并验证修复及影响范围。
7. 复核覆盖、证据、版本、遗留问题与清理，交付范围受限的质量结论。

## 对象路由：只读适用项，可组合

| 对象 | 参考 |
|---|---|
| Web、浏览器、可访问性 | [web](references/objects/web.md) |
| Android、iOS | [mobile](references/objects/mobile.md) |
| 桌面、安装更新、IPC | [desktop](references/objects/desktop.md) |
| HTTP、RPC、GraphQL、WebSocket、微服务 | [API与服务](references/objects/api-and-services.md) |
| 数据库、缓存、消息、ETL、定时任务 | [数据与管道](references/objects/data-and-pipelines.md) |
| CLI、脚本、SDK、文件和媒体 | [CLI/SDK/文件](references/objects/cli-sdk-files.md) |
| LLM、RAG、Agent | [AI与Agent](references/objects/ai-agent.md) |
| IoT、嵌入式和硬件 | [设备](references/objects/device-and-embedded.md) |

按风险叠加 [认证与安全](references/quality/auth-and-security.md)、[并发与一致性](references/quality/concurrency-and-consistency.md)、[性能与恢复](references/quality/performance-and-recovery.md)、[兼容与升级](references/quality/compatibility-and-upgrades.md)。专项并非每项任务都必须执行。

## 工具与产物

优先复用项目已有且适用的框架、测试入口和 CI，不强制语言或框架。API、设备、浏览器、数据库工具缺失时明确记录能力差距；模拟验证不能冒充真实验证。工具版本/API以本地依赖和相应官方资料为准。

复杂任务复制 [运行模板](assets/run-template.json) 与 [用例模板](assets/cases-template.json)，结合 [缺陷模板](assets/defects-template.json)、[证据模板](assets/evidence-template.json)、[资源模板](assets/resources-template.json) 和 [报告模板](assets/report-template.md) 生成用户产物。模板是未执行记录，不是通过证据。小任务可以精简文件，但保留相同语义。

三个辅助命令使用 Python 3.10+ 标准库，无第三方依赖。`RUN_DIR` 是用户的运行产物目录；脚本不调用被测服务，不执行记录中的命令，不自动判业务或发布。

```text
python scripts/validate_records.py RUN_DIR --json
python scripts/check_traceability.py RUN_DIR --json
python scripts/summarize_results.py RUN_DIR --json
```

读取失败、非法状态、缺失证据或追溯缺口返回非零。汇总保留首次失败、当前版本及历史尝试；不能用汇总代替人工业务判断。详细格式见记录文档。

## 停止、恢复与交付

设定负载、时长、调用量和成本边界。出现未预期外部动作、数据污染或明显环境异常时停止相关执行，继续独立工作。中断时保存运行记录、资源、已完成项及下一步；恢复前检查版本和环境。

报告先给结论及范围，再给版本、关键发现、执行与覆盖、修复回归、未测和受阻、剩余风险、复现与清理。没有质量标准时报告观察和建议，不自行宣称验收通过。

行为边界见 [正反样例](references/examples.md)。维护或验收 Skill 本身时阅读 [开发手则与流程](references/development.md) 和 [行为验收集](references/acceptance.md)，不要每次测试用户软件都执行 Skill 的自检。
