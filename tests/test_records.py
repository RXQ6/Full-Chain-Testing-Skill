"""Behavioral invariants of record tools using isolated synthetic data."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from policy_fixture import add_contract
from qa_records import load_bundle, validate, summarize, requirement_gaps

def fixture(root):
    evidence_dir = root / "evidence"
    evidence_dir.mkdir()
    payload = b"synthetic assertion evidence, not a real product run\n"
    (evidence_dir / "one.txt").write_bytes(payload)
    run = {"schema_version": 1, "id": "RUN-1", "mode": "verify",
           "scope": ["synthetic order contract"], "exclusions": [],
           "environment_id": "isolated-fixture", "revision": {"product": "p1", "test": "t1", "configuration": "c1"},
           "authorized_actions": ["local synthetic records"], "limits": {}, "baseline": {},
           "requirements": [{"id": "R1", "statement": "one valid order", "source": "synthetic contract", "risk": "high"}],
           "coverage_exceptions": [], "quality_criteria": ["R1 verified"], "workflow_state": "completed",
           "quality_decision": "meets_agreed_criteria", "decision_basis": "synthetic fixture only"}
    case = {"id": "C1", "title": "one order", "requirement_ids": ["R1"], "risk": "high",
            "layer": "synthetic", "required": True, "status": "passed", "reason": None,
            "preconditions": [], "steps": ["read fixture"], "timeout_seconds": 3, "cleanup_steps": [],
            "oracle": {"source": "synthetic contract", "assertions": [{"id": "A1", "statement": "one record"}]},
            "failure_resolution": None}
    attempt = {"id": "T1", "run_id": "RUN-1", "case_id": "C1", "sequence": 1,
               "revision": copy.deepcopy(run["revision"]), "environment_id": run["environment_id"],
               "status": "passed", "started_at": "2026-01-01T00:00:00Z", "ended_at": "2026-01-01T00:00:01Z",
               "invocation": "synthetic fixture inspection", "category": "none", "reason": None,
               "assertions": [{"id": "A1", "status": "passed", "evidence_ids": ["E1"]}],
               "evidence_ids": ["E1"], "defect_ids": []}
    ev = {"id": "E1", "run_id": "RUN-1", "case_id": "C1", "attempt_id": "T1",
          "kind": "synthetic", "relative_path": "evidence/one.txt", "sha256": hashlib.sha256(payload).hexdigest(),
          "description": "synthetic only", "captured_at": "2026-01-01T00:00:01Z", "redaction_status": "not_needed"}
    bundle = {"run": run, "cases": {"cases": [case]}, "attempts": [attempt],
            "evidence": {"evidence": [ev]}, "defects": {"defects": []}, "resources": {"resources": []}, "_root": root}
    add_contract(bundle)
    return bundle

def save(bundle):
    root = bundle["_root"]
    for key in ("run", "cases", "evidence", "defects", "resources"):
        (root / (key + ".json")).write_text(json.dumps(bundle[key], ensure_ascii=False), encoding="utf-8")
    (root / "results.jsonl").write_text("".join(json.dumps(a) + "\n" for a in bundle["attempts"]), encoding="utf-8")

class RecordTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.bundle = fixture(Path(self.temp.name))

    def assertInvalid(self):
        errors, _ = validate(self.bundle)
        self.assertTrue(errors)

    def test_valid_current_pass(self):
        self.assertEqual(validate(self.bundle)[0], [])

    def test_missing_evidence_file(self):
        (self.bundle["_root"] / "evidence/one.txt").unlink()
        self.assertInvalid()

    def test_content_hash_mismatch(self):
        (self.bundle["_root"] / "evidence/one.txt").write_text("changed", encoding="utf-8")
        self.assertInvalid()

    def test_parent_path_escape(self):
        self.bundle["evidence"]["evidence"][0]["relative_path"] = "../outside.txt"
        self.assertInvalid()

    def test_absolute_windows_path(self):
        self.bundle["evidence"]["evidence"][0]["relative_path"] = "C:\\outside.txt"
        self.assertInvalid()

    def test_windows_ads_path(self):
        self.bundle["evidence"]["evidence"][0]["relative_path"] = "evidence/one.txt:stream"
        self.assertInvalid()

    def test_stale_product_revision(self):
        self.bundle["run"]["revision"]["product"] = "p2"
        self.assertInvalid()

    def test_stale_environment(self):
        self.bundle["run"]["environment_id"] = "other-env"
        self.assertInvalid()

    def test_pass_without_execution(self):
        self.bundle["attempts"] = []
        self.assertInvalid()

    def test_missing_assertion(self):
        self.bundle["attempts"][0]["assertions"] = []
        self.assertInvalid()

    def test_failed_assertion_cannot_pass(self):
        self.bundle["attempts"][0]["assertions"][0]["status"] = "failed"
        self.assertInvalid()

    def test_unknown_requirement(self):
        self.bundle["cases"]["cases"][0]["requirement_ids"] = ["missing"]
        self.assertInvalid()

    def test_optional_only_not_acceptance(self):
        self.bundle["cases"]["cases"][0]["required"] = False
        self.assertInvalid()

    def test_orphan_requirement_detected(self):
        self.bundle["run"]["requirements"].append({"id": "R2", "statement": "other", "source": "contract", "risk": "low"})
        self.bundle["run"]["quality_decision"] = "pending"
        self.assertEqual(validate(self.bundle)[0], [])
        self.assertTrue(requirement_gaps(self.bundle)[0])

    def test_zero_denominator_is_null(self):
        self.bundle["run"].update(mode="plan", workflow_state="active", quality_decision="pending")
        self.bundle["cases"]["cases"][0]["status"] = "planned"
        self.bundle["attempts"] = []
        self.bundle["evidence"]["evidence"] = []
        self.assertEqual(validate(self.bundle)[0], [])
        self.assertIsNone(summarize(self.bundle)["pass_rate_executed"])

    def test_blocked_not_completed(self):
        self.bundle["cases"]["cases"][0].update(status="blocked", reason="no device")
        self.bundle["run"]["quality_decision"] = "insufficient_evidence"
        self.bundle["attempts"] = []
        self.bundle["evidence"]["evidence"] = []
        self.assertInvalid()

    def test_blocked_partial_is_valid(self):
        self.bundle["cases"]["cases"][0].update(status="blocked", reason="no device")
        self.bundle["run"].update(workflow_state="partial", quality_decision="insufficient_evidence")
        self.bundle["attempts"] = []
        self.bundle["evidence"]["evidence"] = []
        self.assertEqual(validate(self.bundle)[0], [])

    def add_failed_then_pass(self):
        old = self.bundle["attempts"][0]
        old.update(status="failed", category="product", reason="duplicate")
        old["assertions"][0]["status"] = "failed"
        new = copy.deepcopy(old)
        new.update(id="T2", sequence=2, status="passed", category="none", reason=None)
        new["assertions"] = [{"id": "A1", "status": "passed", "evidence_ids": ["E2"]}]
        new["evidence_ids"] = ["E2"]
        ev = copy.deepcopy(self.bundle["evidence"]["evidence"][0])
        ev.update(id="E2", attempt_id="T2")
        self.bundle["evidence"]["evidence"].append(ev)
        self.bundle["attempts"].append(new)

    def test_retry_cannot_hide_first_failure(self):
        self.add_failed_then_pass()
        self.assertInvalid()

    def test_supported_resolution_retains_failure(self):
        self.add_failed_then_pass()
        self.bundle["cases"]["cases"][0]["failure_resolution"] = {
            "kind": "environment_resolved", "reason": "fixture environment reset with evidence", "evidence_ids": ["E2"], "defect_ids": []}
        self.assertEqual(validate(self.bundle)[0], [])
        summary = summarize(self.bundle)
        history = summary["case_history"][0]
        self.assertEqual(history["first_attempt_status"], "failed")
        self.assertTrue(history["recovered_after_failure"])
        self.assertEqual(summary["attempt_counts"]["failed"], 1)

    def test_wrong_attempt_evidence(self):
        self.bundle["evidence"]["evidence"][0]["attempt_id"] = "other"
        self.assertInvalid()

    def test_no_agreed_criteria(self):
        self.bundle["run"]["quality_criteria"] = []
        self.assertInvalid()

    def test_plan_cannot_claim_executed(self):
        self.bundle["run"]["mode"] = "plan"
        self.assertInvalid()

    def test_duplicate_attempt_sequence(self):
        self.bundle["attempts"].append(copy.deepcopy(self.bundle["attempts"][0]))
        self.assertInvalid()

    def test_timezone_required(self):
        self.bundle["attempts"][0]["started_at"] = "2026-01-01T00:00:00"
        self.assertInvalid()

    def test_end_before_start(self):
        self.bundle["attempts"][0]["ended_at"] = "2025-01-01T00:00:00Z"
        self.assertInvalid()

    def test_cleanup_failure_not_completed(self):
        self.bundle["resources"]["resources"] = [{"id":"X1","owner_run_id":"RUN-1","kind":"test-data",
            "locator":"synthetic-id","cleanup_status":"failed","cleanup_evidence_ids":[],"reason":"locked"}]
        self.assertInvalid()

    def test_open_high_defect_blocks_quality_pass(self):
        self.bundle["defects"]["defects"] = [{"id":"D1","title":"duplicate order","severity":"high","status":"open",
            "case_ids":["C1"],"evidence_ids":["E1"],"expected":"one","actual":"two","verification_attempt_ids":[]}]
        self.assertInvalid()

    def test_malformed_json_line_not_ignored(self):
        save(self.bundle)
        with (self.bundle["_root"] / "results.jsonl").open("a", encoding="utf-8") as stream:
            stream.write("{bad json}\n")
        _, errors = load_bundle(self.bundle["_root"])
        self.assertTrue(errors)

    def test_duplicate_json_key_rejected(self):
        save(self.bundle)
        (self.bundle["_root"] / "run.json").write_text('{"id":"a","id":"b"}', encoding="utf-8")
        _, errors = load_bundle(self.bundle["_root"])
        self.assertTrue(errors)

    def test_nonfinite_json_rejected(self):
        save(self.bundle)
        (self.bundle["_root"] / "run.json").write_text('{"x":NaN}', encoding="utf-8")
        _, errors = load_bundle(self.bundle["_root"])
        self.assertTrue(errors)

    def test_cli_roundtrip(self):
        save(self.bundle)
        for name in ("validate_records.py", "check_traceability.py", "summarize_results.py"):
            result = subprocess.run([sys.executable, str(SCRIPTS/name), str(self.bundle["_root"]), "--json"],
                                    capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertTrue(json.loads(result.stdout)["valid"])

    def test_cli_invalid_returns_nonzero(self):
        save(self.bundle)
        (self.bundle["_root"] / "evidence/one.txt").unlink()
        result = subprocess.run([sys.executable,str(SCRIPTS/"summarize_results.py"),str(self.bundle["_root"]),"--json"],
                                capture_output=True,text=True,encoding="utf-8")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("summary", json.loads(result.stdout))

    def test_initializer_never_overwrites(self):
        target = self.bundle["_root"] / "new-run"
        command = [sys.executable, str(SCRIPTS/"new_run.py"), str(target)]
        first = subprocess.run(command, capture_output=True)
        self.assertEqual(first.returncode, 0)
        original = (target/"run.json").read_bytes()
        second = subprocess.run(command, capture_output=True)
        self.assertNotEqual(second.returncode, 0)
        self.assertEqual((target/"run.json").read_bytes(), original)

    def test_initializer_is_not_a_pass(self):
        target = self.bundle["_root"]/"new-run"
        subprocess.run([sys.executable,str(SCRIPTS/"new_run.py"),str(target)],check=True,capture_output=True)
        bundle, errors = load_bundle(target)
        self.assertEqual(validate(bundle, errors)[0], [])
        self.assertTrue(requirement_gaps(bundle)[0])
        self.assertIsNone(summarize(bundle)["pass_rate_executed"])

    def test_wrong_scalar_types_fail_without_traceback(self):
        for location, key in (("run","mode"),("run","quality_decision"),("attempt","case_id"),("evidence","case_id")):
            for value in ([], {}, 42, None):
                with self.subTest(location=location, key=key, value=value):
                    bundle = copy.deepcopy(self.bundle)
                    target = bundle["run"] if location=="run" else bundle["attempts"][0] if location=="attempt" else bundle["evidence"]["evidence"][0]
                    target[key] = value
                    self.assertTrue(validate(bundle)[0])

if __name__ == "__main__":
    unittest.main()
