# 记录契约 v1
脚本使用Python 3.10+标准库，输入固定为UTF-8 JSON/JSONL；不依赖PyYAML。JSON可作为YAML子集，但脚本不接受一般YAML。不执行记录中的命令。原始证据可为任意文件，必须位于运行目录且哈希匹配。

## 创建与命令
用 scripts/new_run.py NEW_DIR --mode plan|verify|repair 创建全新目录，不覆盖已有目录。模板只有未执行状态，需填写实际范围、规则、版本和用例。复杂任务使用以下文件；简单任务可先内联记录，若要运行脚本再转换为相同契约。
- run.json：schema_version=1；id；mode；scope非空字符串列表；exclusions；authorized_actions；limits对象；baseline对象；environment_id；revision对象(product/test/configuration字符串)；requirements列表；coverage_exceptions列表；quality_criteria列表；workflow_state；quality_decision；decision_basis。
- cases.json：cases列表。每条id/title/risk/layer/required布尔/status/preconditions/steps/timeout_seconds/cleanup_steps/requirement_ids；oracle含source和assertions，每条断言id/statement。
- results.jsonl：每行一条完整尝试，空文件表示未执行。id/run_id/case_id/sequence；revision/environment_id；status；started_at/ended_at含时区；invocation为实际命令或人工/API/设备操作描述；category；reason；assertions(id/status/evidence_ids)；evidence_ids；defect_ids。sequence按用例递增，不能覆盖旧行。
- evidence.json：evidence列表。id/run_id/case_id/attempt_id/kind/relative_path/sha256/description/captured_at/redaction_status。全局证据case_id与attempt_id同时null；用例证据必须精确属于相应尝试。redaction_status为redacted或not_needed。
- defects.json：defects列表。id/title/severity/status/case_ids/evidence_ids/expected/actual/verification_attempt_ids；可附priority、root_cause与复现。accepted_risk需acceptance.authority/reason/evidence_ids；verified需当前版本通过的验证尝试。
- resources.json：resources列表。id/kind/locator/owner_run_id/cleanup_status/cleanup_evidence_ids/reason。locator只保留安全定位信息；cleaned需证据，retained/failed需原因。

## 枚举与约束
风险/严重程度：critical/high/medium/low。优先级另记，不混为严重程度。
用例状态：planned/running/passed/failed/blocked/skipped/not_applicable/inconclusive。
尝试状态：passed/failed/blocked/inconclusive。
断言状态：passed/failed/not_evaluated；每次尝试须列全声明断言，没执行的写not_evaluated。
分类：none/product/test/environment/data/requirements/flaky/unknown；passed分类为none。
清理：pending/cleaned/retained/failed。
工作流：active/completed/partial/blocked。
质量：pending/meets_agreed_criteria/does_not_meet_criteria/insufficient_evidence。
非pending结论需decision_basis；plan不得声称产品通过/失败或实际执行。
blocked/skipped/not_applicable/inconclusive用例有reason。非通过尝试有reason；失败可为执行器异常，断言全部未执行时附事实证据。
用例终态passed/failed/inconclusive必须有匹配当前产品/测试/配置及环境的最新尝试。
曾失败后声明passed必须有failure_resolution，含kind(product_fixed/test_corrected/environment_resolved)、reason、evidence_ids和defect_ids；确认flaky则保持inconclusive，不能只靠重跑升级为passed。
历史失败仍保留并进入汇总。

## 覆盖与结论
requirements每条id/statement/source/risk。每条需关联用例或coverage_exceptions（requirement_id/status/reason/evidence_ids）。例外状态为blocked/skipped/not_applicable。只有optional用例不能代替要求的验证。
completed的verify/repair不能仍有required的planned/running/blocked/skipped/inconclusive或未完成清理。已确认失败可以完成测试，但不满足质量条件。
meets_agreed_criteria需已约定标准、全部适用required用例通过、无未解决高影响缺陷、需求候选验证完整和清理完成。脚本只检查必要条件，无法验证标准是否真实、证据语义是否正确、风险接受是否获得真实授权，必须人工复核。

## 证据安全与复现
证据路径不能绝对路径、父目录跳转、Windows驱动器/ADS或解析后逃逸根目录；符号链接也不能逃逸。SHA-256只识别内容，不证明真实性。时间必须含时区，结束不早于开始。不得在记录中放密码、Token或真实客户资料。

可复制的单条结构示例：[用例](../assets/case-example.json)、[缺陷](../assets/defect-example.json)。这些是结构示例，不是执行证据。
