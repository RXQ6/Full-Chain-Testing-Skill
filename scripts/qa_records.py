"""Shared, dependency-free record validation. Never executes recorded commands."""
from __future__ import annotations
import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path, PureWindowsPath

CASE_STATES = {"planned", "running", "passed", "failed", "blocked", "skipped", "not_applicable", "inconclusive"}
ATTEMPT_STATES = {"passed", "failed", "blocked", "inconclusive"}
RISKS = {"critical", "high", "medium", "low"}
CATEGORIES = {"none", "product", "test", "environment", "data", "requirements", "flaky", "unknown"}
REVISIONS = ("product", "test", "configuration")
FILES = {"run": "run.json", "cases": "cases.json", "evidence": "evidence.json",
         "defects": "defects.json", "resources": "resources.json"}

def _pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate JSON key")
        out[key] = value
    return out

def read_json(text):
    return json.loads(text, object_pairs_hook=_pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON number")))

def load_bundle(root):
    root = Path(root).resolve()
    bundle, errors = {}, []
    compact = root / "compact.json"
    if compact.exists():
        if any((root / name).exists() for name in (*FILES.values(), 'results.jsonl')):
            return {}, ['compact.json: mixed full and compact records are ambiguous']
        try:
            data = read_json(compact.read_text(encoding="utf-8-sig"))
            bundle = {"run": data["run"], "attempts": data["attempts"], "_root": root}
            for key in ("cases", "evidence", "defects", "resources"):
                bundle[key] = {key: data[key]}
            return bundle, []
        except (OSError, ValueError, KeyError, TypeError):
            return {}, ["compact.json: invalid compact record"]
    for key, name in FILES.items():
        try:
            value = read_json((root / name).read_text(encoding="utf-8-sig"))
            if not isinstance(value, dict):
                raise ValueError("object required")
            bundle[key] = value
        except (OSError, ValueError, RecursionError):
            errors.append(name + ": unreadable or invalid JSON object")
    attempts = []
    try:
        for number, line in enumerate((root / "results.jsonl").read_text(encoding="utf-8-sig").splitlines(), 1):
            if line.strip():
                try:
                    value = read_json(line)
                    if not isinstance(value, dict):
                        raise ValueError("object required")
                    attempts.append(value)
                except (ValueError, RecursionError):
                    errors.append("results.jsonl line " + str(number) + ": invalid JSON object")
    except OSError:
        errors.append("results.jsonl: unreadable")
    bundle["attempts"] = attempts
    bundle["_root"] = root
    return bundle, errors

def text(value):
    return isinstance(value, str) and bool(value.strip())

def string_list(value, nonempty=False):
    return isinstance(value, list) and (not nonempty or bool(value)) and all(text(x) for x in value)

def timestamp(value):
    if not text(value):
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return result if result.tzinfo is not None and result.utcoffset() is not None else None
    except ValueError:
        return None

def revision(value):
    return isinstance(value, dict) and all(text(value.get(k)) for k in REVISIONS)

def current(attempt, run):
    return (attempt.get("revision") == run.get("revision")
            and attempt.get("environment_id") == run.get("environment_id"))

def latest(attempts):
    return max(attempts, key=lambda a: a.get("sequence", 0)) if attempts else None

def rows(bundle, key, errors):
    value = bundle.get(key, {}).get(key)
    if not isinstance(value, list) or any(not isinstance(x, dict) for x in value):
        errors.append(key + ": list of objects required")
        return []
    return value

def index(items, location, errors):
    result = {}
    for n, row in enumerate(items):
        ident = row.get("id")
        if not text(ident):
            errors.append(location + "[" + str(n) + "]: nonempty id required")
        elif ident in result:
            errors.append(location + ": duplicate id")
        else:
            result[ident] = row
    return result

def refs(values, target, location, errors, nonempty=False):
    if not string_list(values, nonempty):
        errors.append(location + ": string list required")
        return
    if len(values) != len(set(values)):
        errors.append(location + ": duplicate reference")
    if any(value not in target for value in values):
        errors.append(location + ": unknown reference")

def requirement_gaps(bundle):
    run = bundle.get("run", {})
    requirements = run.get("requirements", [])
    cases = bundle.get("cases", {}).get("cases", [])
    exceptions = run.get("coverage_exceptions", [])
    gaps, coverage = [], []
    if not requirements:
        gaps.append("no requirements have been recorded")
    for req in requirements:
        ident = req["id"]
        mapped = [c for c in cases if ident in c.get("requirement_ids", [])]
        applicable = [c for c in mapped if c.get("status") != "not_applicable"]
        exception = [e for e in exceptions if e.get("requirement_id") == ident]
        required = [c for c in applicable if c.get("required")]
        verified_candidate = bool(required) and all(c["status"] == "passed" for c in required)
        if not mapped and not exception:
            gaps.append("requirement " + ident + ": no case or justified exception")
        if applicable and not required and not exception:
            gaps.append("requirement " + ident + ": no required verification or justified exception")
        coverage.append({"requirement_id": ident, "case_ids": [c["id"] for c in mapped],
                         "required_case_ids": [c["id"] for c in required],
                         "mapped": bool(mapped), "verified_candidate": verified_candidate,
                         "exceptions": exception})
    return gaps, coverage

def _validate(bundle, initial_errors=()):
    errors, warnings = list(initial_errors), []
    if errors:
        return errors, warnings
    run = bundle["run"]
    if type(run.get("schema_version")) is not int or run["schema_version"] != 1:
        errors.append("run.schema_version: expected 1")
    for field in ("id", "environment_id"):
        if not text(run.get(field)):
            errors.append("run." + field + ": nonempty string required")
    if run.get("mode") not in {"plan", "verify", "repair"}:
        errors.append("run.mode: invalid")
    if run.get("workflow_state") not in {"active", "completed", "partial", "blocked"}:
        errors.append("run.workflow_state: invalid")
    if run.get("quality_decision") not in {"pending", "meets_agreed_criteria", "does_not_meet_criteria", "insufficient_evidence"}:
        errors.append("run.quality_decision: invalid")
    if not revision(run.get("revision")):
        errors.append("run.revision: product/test/configuration required")
    for field in ("scope", "exclusions", "authorized_actions", "quality_criteria"):
        if not string_list(run.get(field), nonempty=(field == "scope")):
            errors.append("run." + field + ": string list required")
    if not isinstance(run.get("limits"), dict) or not isinstance(run.get("baseline"), dict):
        errors.append("run.limits/baseline: objects required")
    if run.get("quality_decision") != "pending" and not text(run.get("decision_basis")):
        errors.append("run.decision_basis: required for a final quality decision")
    reqs = run.get("requirements")
    if not isinstance(reqs, list) or any(not isinstance(x, dict) for x in reqs):
        errors.append("run.requirements: list of objects required")
        reqs = []
    req_index = index(reqs, "requirements", errors)
    for r in reqs:
        if any(not text(r.get(k)) for k in ("statement", "source")) or r.get("risk") not in RISKS:
            errors.append("requirement: statement/source/risk required")
    cs = rows(bundle, "cases", errors)
    es = rows(bundle, "evidence", errors)
    ds = rows(bundle, "defects", errors)
    resources = rows(bundle, "resources", errors)
    cases, evidence, defects = index(cs, "cases", errors), index(es, "evidence", errors), index(ds, "defects", errors)
    index(resources, "resources", errors)
    ats = bundle["attempts"]
    attempts = index(ats, "attempts", errors)
    assertions_by_case = {}
    for c in cs:
        if any(not text(c.get(k)) for k in ("title", "layer")) or c.get("risk") not in RISKS:
            errors.append("case: title/layer/risk required")
        if type(c.get("required")) is not bool or c.get("status") not in CASE_STATES:
            errors.append("case: required/status invalid")
        refs(c.get("requirement_ids"), req_index, "case.requirement_ids", errors, True)
        for field in ("preconditions", "steps", "cleanup_steps"):
            if not string_list(c.get(field), nonempty=(field == "steps")):
                errors.append("case." + field + ": string list required")
        timeout = c.get("timeout_seconds")
        if type(timeout) not in (int, float) or not 0 < timeout <= 604800:
            errors.append("case.timeout_seconds: positive finite bounded number required")
        oracle = c.get("oracle")
        if not isinstance(oracle, dict) or not text(oracle.get("source")):
            errors.append("case.oracle: source required")
            oracle = {}
        ax = oracle.get("assertions")
        if not isinstance(ax, list) or not ax or any(not isinstance(x, dict) for x in ax):
            errors.append("case.oracle.assertions: nonempty object list required")
            ax = []
        ai = index(ax, "oracle.assertions", errors)
        assertions_by_case[c.get("id", "")] = ai
        if any(not text(x.get("statement")) for x in ax):
            errors.append("oracle.assertion.statement: required")
        if c.get("status") in {"blocked", "skipped", "not_applicable", "inconclusive"} and not text(c.get("reason")):
            errors.append("case.reason: required for nonexecuted or uncertain status")
    seen_seq = {}
    for a in ats:
        cid = a.get("case_id")
        if a.get("run_id") != run.get("id") or cid not in cases:
            errors.append("attempt: unknown run/case")
        seq = a.get("sequence")
        if type(seq) is not int or seq < 1:
            errors.append("attempt.sequence: positive integer required")
        elif seq <= seen_seq.get(cid, 0):
            errors.append("attempt.sequence: must increase in append order per case")
        else:
            seen_seq[cid] = seq
        if a.get("status") not in ATTEMPT_STATES:
            errors.append("attempt.status: invalid")
        if not revision(a.get("revision")) or not text(a.get("environment_id")):
            errors.append("attempt: revision/environment required")
        start, end = timestamp(a.get("started_at")), timestamp(a.get("ended_at"))
        if start is None or end is None or end < start:
            errors.append("attempt: valid ordered timezone-aware timestamps required")
        if not text(a.get("invocation")):
            errors.append("attempt.invocation: execution description required")
        if a.get("category") not in CATEGORIES:
            errors.append("attempt.category: invalid")
        if a.get("status") == "passed" and a.get("category") != "none":
            errors.append("passed attempt: category must be none")
        if a.get("status") != "passed" and not text(a.get("reason")):
            errors.append("nonpassed attempt: reason required")
        refs(a.get("evidence_ids"), evidence, "attempt.evidence_ids", errors, True)
        refs(a.get("defect_ids"), defects, "attempt.defect_ids", errors)
        ax = a.get("assertions")
        if not isinstance(ax, list) or any(not isinstance(x, dict) for x in ax):
            errors.append("attempt.assertions: list of objects required")
            ax = []
        ai = index(ax, "attempt.assertions", errors)
        expected = assertions_by_case.get(cid, {})
        if set(ai) != set(expected):
            errors.append("attempt.assertions: must list every declared assertion exactly once")
        for assertion in ax:
            if assertion.get("status") not in {"passed", "failed", "not_evaluated"}:
                errors.append("attempt.assertion.status: invalid")
            refs(assertion.get("evidence_ids"), evidence, "assertion.evidence_ids", errors,
                 assertion.get("status") in {"passed", "failed"})
            if a.get("status") == "passed" and assertion.get("status") != "passed":
                errors.append("passed attempt: all assertions must pass")
        if a.get("status") == "failed" and not any(x.get("status") == "failed" for x in ax):
            warnings.append("failed attempt has no failed assertion; review execution failure evidence")
    root = Path(bundle["_root"]).resolve()
    for e in es:
        if e.get("run_id") != run.get("id"):
            errors.append("evidence: run mismatch")
        cid, aid = e.get("case_id"), e.get("attempt_id")
        if (cid is None) != (aid is None):
            errors.append("evidence: case/attempt must both be null or both present")
        elif cid is not None and (cid not in cases or aid not in attempts or attempts[aid].get("case_id") != cid):
            errors.append("evidence: unknown or mismatched case/attempt")
        if not text(e.get("kind")) or not text(e.get("description")) or timestamp(e.get("captured_at")) is None:
            errors.append("evidence: kind/description/time required")
        if e.get("redaction_status") not in {"redacted", "not_needed"}:
            errors.append("evidence: redaction review required")
        rel, digest = e.get("relative_path"), e.get("sha256")
        if not text(rel) or not isinstance(digest, str) or not re.fullmatch("[0-9a-f]{64}", digest):
            errors.append("evidence: relative_path and lowercase sha256 required")
            continue
        try:
            p = Path(rel.replace("\\", "/"))
            if p.is_absolute() or PureWindowsPath(rel).drive or ".." in p.parts or (__import__("os").name == "nt" and ":" in rel) or "\x00" in rel:
                errors.append("evidence: unsafe lexical path")
                continue
            target = (root / p).resolve()
            if not target.is_relative_to(root):
                errors.append("evidence: resolved path escapes run root")
                continue
            if not target.is_file():
                errors.append("evidence: file missing")
                continue
            h = hashlib.sha256()
            with target.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    h.update(chunk)
            if h.hexdigest() != digest:
                errors.append("evidence: content hash mismatch")
        except OSError:
            errors.append("evidence: file unreadable")
        except (ValueError, RuntimeError):
            errors.append("evidence: invalid or unresolvable path")
    for a in ats:
        aids = set(a.get("evidence_ids", [])) if string_list(a.get("evidence_ids")) else set()
        for x in a.get("assertions", []) if isinstance(a.get("assertions"), list) else []:
            if isinstance(x, dict) and string_list(x.get("evidence_ids")):
                aids.update(x["evidence_ids"])
        for eid in aids:
            if eid in evidence and (evidence[eid].get("case_id") != a.get("case_id") or evidence[eid].get("attempt_id") != a.get("id")):
                errors.append("attempt: evidence belongs to another case/attempt")
    for d in ds:
        if any(not text(d.get(k)) for k in ("title", "expected", "actual")) or d.get("severity") not in RISKS:
            errors.append("defect: title/expected/actual/severity required")
        if d.get("status") not in {"open", "fixed", "verified", "accepted_risk"}:
            errors.append("defect.status: invalid")
        refs(d.get("case_ids"), cases, "defect.case_ids", errors, True)
        refs(d.get("evidence_ids"), evidence, "defect.evidence_ids", errors, True)
        refs(d.get("verification_attempt_ids"), attempts, "defect.verification_attempt_ids", errors)
        if d.get("status") == "verified":
            vids = d.get("verification_attempt_ids", [])
            if not vids or any(attempts.get(x, {}).get("status") != "passed" or not current(attempts.get(x, {}), run) or attempts.get(x, {}).get("case_id") not in d.get("case_ids", []) for x in vids):
                errors.append("verified defect: current passed verification required")
        if d.get("status") == "accepted_risk":
            acceptance = d.get("acceptance")
            if not isinstance(acceptance, dict) or not text(acceptance.get("authority")) or not text(acceptance.get("reason")):
                errors.append("accepted risk: authority and reason required")
            else:
                refs(acceptance.get("evidence_ids"), evidence, "acceptance.evidence_ids", errors, True)
    for c in cs:
        relevant = [a for a in ats if a.get("case_id") == c.get("id") and current(a, run)
                    and type(a.get("sequence")) is int]
        recent = latest(relevant)
        if c.get("status") in {"passed", "failed", "inconclusive"}:
            if recent is None or recent.get("status") != c["status"]:
                errors.append("case terminal status: matching current attempt required")
        history = [a for a in ats if a.get("case_id") == c.get("id")]
        if c.get("status") == "passed" and any(a.get("status") == "failed" for a in history):
            resolution = c.get("failure_resolution")
            if not isinstance(resolution, dict) or resolution.get("kind") not in {"product_fixed", "test_corrected", "environment_resolved"} or not text(resolution.get("reason")):
                errors.append("passed-after-failure: explicit supported resolution required; otherwise inconclusive")
            else:
                refs(resolution.get("evidence_ids"), evidence, "failure_resolution.evidence_ids", errors, True)
                refs(resolution.get("defect_ids"), defects, "failure_resolution.defect_ids", errors)
            warnings.append("passed-after-failure: retain first failure and review stability")
    for r in resources:
        if r.get("owner_run_id") != run.get("id") or any(not text(r.get(k)) for k in ("kind", "locator")):
            errors.append("resource: owner/kind/locator required")
        if r.get("cleanup_status") not in {"pending", "cleaned", "retained", "failed"}:
            errors.append("resource.cleanup_status: invalid")
        refs(r.get("cleanup_evidence_ids"), evidence, "resource.cleanup_evidence_ids", errors,
             r.get("cleanup_status") == "cleaned")
        if r.get("cleanup_status") in {"retained", "failed"} and not text(r.get("reason")):
            errors.append("resource.reason: required")
    exceptions = run.get("coverage_exceptions")
    if not isinstance(exceptions, list) or any(not isinstance(x, dict) for x in exceptions):
        errors.append("run.coverage_exceptions: object list required")
    else:
        for ex in exceptions:
            if ex.get("requirement_id") not in req_index or ex.get("status") not in {"blocked", "skipped", "not_applicable"} or not text(ex.get("reason")):
                errors.append("coverage exception: requirement/status/reason invalid")
            refs(ex.get("evidence_ids"), evidence, "coverage_exception.evidence_ids", errors)
    if run.get("mode") == "plan" and (ats or run.get("quality_decision") in {"meets_agreed_criteria", "does_not_meet_criteria"}):
        errors.append("plan mode: cannot claim execution or product pass/fail")
    if run.get("mode") != "plan" and run.get("workflow_state") == "completed":
        if any(c.get("required") and c.get("status") in {"planned", "running", "blocked", "skipped", "inconclusive"} for c in cs):
            errors.append("completed verification: required work remains")
        if any(r.get("cleanup_status") in {"pending", "failed"} for r in resources):
            errors.append("completed verification: cleanup incomplete")
    if run.get("quality_decision") == "meets_agreed_criteria":
        if not run.get("quality_criteria"):
            errors.append("meets criteria: agreed criteria required")
        required = [c for c in cs if c.get("required") and c.get("status") != "not_applicable"]
        if not required or any(c.get("status") != "passed" for c in required):
            errors.append("meets criteria: all applicable required cases must pass")
        if any(d.get("severity") in {"critical", "high"} and d.get("status") in {"open", "fixed"} for d in ds):
            errors.append("meets criteria: unresolved high-impact defect")
        if not errors:
            gaps, coverage = requirement_gaps(bundle)
            if gaps or any(not x["verified_candidate"] and not any(e["status"] == "not_applicable" for e in x["exceptions"]) for x in coverage):
                errors.append("meets criteria: requirement verification incomplete")
        if any(r.get("cleanup_status") in {"pending", "failed"} for r in resources):
            errors.append("meets criteria: cleanup incomplete")
    return errors, warnings

def validate(bundle, initial_errors=()):
    try:
        errors, warnings = _validate(bundle, initial_errors)
        if not errors:
            from acceptance_policy import check_policy
            errors.extend(check_policy(bundle))
        return errors, warnings
    except (TypeError, KeyError, AttributeError, OverflowError, OSError, ValueError):
        return list(initial_errors) + ["invalid field type or record structure"], []

def summarize(bundle):
    run, cases, attempts = bundle["run"], bundle["cases"]["cases"], bundle["attempts"]
    counts = {s: sum(c["status"] == s for c in cases) for s in sorted(CASE_STATES)}
    denominator = counts["passed"] + counts["failed"]
    histories = []
    for c in cases:
        history = [a for a in attempts if a["case_id"] == c["id"]]
        ordered = sorted(history, key=lambda a: a["sequence"])
        cur = [a for a in ordered if current(a, run)]
        histories.append({"case_id": c["id"], "declared_status": c["status"],
                          "first_attempt_status": ordered[0]["status"] if ordered else None,
                          "latest_current_status": cur[-1]["status"] if cur else None,
                          "attempt_count": len(ordered),
                          "historical_attempt_count": len(ordered) - len(cur),
                          "ever_failed": any(a["status"] == "failed" for a in ordered),
                          "recovered_after_failure": bool(cur and cur[-1]["status"] == "passed" and any(a["status"] == "failed" for a in ordered)),
                          "failure_resolution": c.get("failure_resolution")})
    gaps, coverage = requirement_gaps(bundle)
    return {"run_id": run["id"], "workflow_state": run["workflow_state"],
            "quality_decision": run["quality_decision"], "case_counts": counts,
            "pass_rate_executed": counts["passed"] / denominator if denominator else None,
            "attempt_counts": dict(Counter(a["status"] for a in attempts)),
            "case_history": histories, "coverage": coverage, "traceability_gaps": gaps,
            "defects": dict(Counter(d["status"] for d in bundle["defects"]["defects"])),
            "cleanup": dict(Counter(r["cleanup_status"] for r in bundle["resources"]["resources"])),
            "notice": "Record consistency and candidate coverage only; not proof of correctness or release authorization."}
