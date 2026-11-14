"""Exercise a real LOOPBACK-ONLY synthetic API. Not a real product certification."""
import argparse
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import threading
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from qa_records import validate, summarize

def now():
    return datetime.now(timezone.utc).isoformat()

def make_server(variant):
    state = {"admin_writes": 0, "orders": [], "keys": {}}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def send(self, status, data):
            payload = json.dumps(data).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        def do_GET(self):
            if self.path == "/price":
                self.send(200, {"amount": 120 if variant == "defective" else 100})
            elif self.path == "/state":
                self.send(200, {"admin_writes": state["admin_writes"], "order_count": len(state["orders"])})
            else:
                self.send(404, {"error": "not_found"})
        def do_POST(self):
            if self.path == "/admin":
                if variant == "defective":
                    state["admin_writes"] += 1
                self.send(403, {"error": "forbidden"})
            elif self.path == "/orders":
                key = self.headers.get("Idempotency-Key")
                if variant == "fixed" and key in state["keys"]:
                    self.send(200, {"id": state["keys"][key]})
                    return
                order = len(state["orders"]) + 1
                state["orders"].append(order)
                state["keys"][key] = order
                self.send(200, {"id": order})
            else:
                self.send(404, {"error": "not_found"})
    return ThreadingHTTPServer(("127.0.0.1", 0), Handler)

def request(base, path, method="GET", headers=None):
    req = urllib.request.Request(base + path, data=b"" if method == "POST" else None,
                                 headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=3) as response:
            return {"status": response.status, "body": json.load(response)}
    except urllib.error.HTTPError as error:
        return {"status": error.code, "body": json.load(error)}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir")
    parser.add_argument("--variant", choices=["defective", "fixed"], required=True)
    args = parser.parse_args()
    out = Path(args.output_dir).resolve()
    try:
        out.mkdir(parents=True, exist_ok=False)
    except OSError:
        parser.error("output must be a new writable directory")
    (out / "evidence").mkdir()
    variant = args.variant
    revision = {"product": "synthetic-api-" + variant, "test": "fixture-client-v1", "configuration": "loopback-only-v1"}
    run = {"schema_version": 1, "id": "fixture-" + variant, "mode": "verify",
           "scope": ["synthetic loopback API: amount, forbidden side effect, sequential idempotency"],
           "exclusions": ["No real software/platform acceptance", "No concurrency, mobile, desktop or model evaluation"],
           "environment_id": "isolated-loopback-" + variant, "revision": revision,
           "authorized_actions": ["local synthetic server and new output directory"],
           "limits": {"request_timeout_seconds": 3, "external_calls": 0, "duration_seconds": 60, "max_calls": 40, "max_concurrency": 1}, "baseline": {},
           "requirements": [
               {"id": "R-AMOUNT", "statement": "120 minus 20 equals 100", "source": "fixture contract", "risk": "high"},
               {"id": "R-AUTH", "statement": "forbidden operation does not write", "source": "fixture contract", "risk": "high"},
               {"id": "R-IDEMP", "statement": "same key creates one order", "source": "fixture contract", "risk": "high"}],
           "coverage_exceptions": [], "quality_criteria": ["all three fixture contract checks pass"],
           "workflow_state": "completed", "quality_decision": "pending", "decision_basis": ""}
    cases, attempts, evidence, defects = [], [], [], []
    server = make_server(variant)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = "http://127.0.0.1:" + str(server.server_port)
    run["baseline"] = {"endpoint": base, "notice": "Deliberately seeded synthetic fixture, not independent model evaluation."}
    def record(cid, rid, title, assertion_specs, observations, started, invocation):
        failed = any(not ok for _, _, ok in assertion_specs)
        aid, eid, did = "T-" + cid, "E-" + cid, "D-" + cid
        payload = json.dumps({"synthetic": True, "variant": variant, "observations": observations},
                             ensure_ascii=False, indent=2).encode("utf-8")
        relative = "evidence/" + cid + ".json"
        (out / relative).write_bytes(payload)
        ended = now()
        evidence.append({"id": eid, "run_id": run["id"], "case_id": cid, "attempt_id": aid,
                         "kind": "actual-loopback-response", "relative_path": relative,
                         "sha256": hashlib.sha256(payload).hexdigest(),
                         "description": "Actual response from seeded synthetic API",
                         "captured_at": ended, "redaction_status": "not_needed"})
        cases.append({"id": cid, "title": title, "requirement_ids": [rid], "risk": "high",
                      "layer": "loopback-api-integration", "required": True,
                      "status": "failed" if failed else "passed", "reason": None,
                      "preconditions": ["fresh isolated synthetic server"], "steps": [invocation],
                      "timeout_seconds": 10, "cleanup_steps": ["stop fixture server"],
                      "oracle": {"source": "fixture contract", "assertions": [{"id": x, "statement": statement} for x, statement, _ in assertion_specs]},
                      "failure_resolution": None})
        attempts.append({"id": aid, "run_id": run["id"], "case_id": cid, "sequence": 1,
                         "revision": dict(revision), "environment_id": run["environment_id"],
                         "status": "failed" if failed else "passed", "started_at": started, "ended_at": ended,
                         "invocation": invocation, "category": "product" if failed else "none",
                         "reason": "Seeded fixture violates its explicit contract" if failed else None,
                         "assertions": [{"id": x, "status": "passed" if ok else "failed", "evidence_ids": [eid]} for x, _, ok in assertion_specs],
                         "evidence_ids": [eid], "defect_ids": [did] if failed else []})
        if failed:
            defects.append({"id": did, "title": title, "severity": "high", "status": "open", "case_ids": [cid],
                            "evidence_ids": [eid], "expected": "; ".join(s for _, s, _ in assertion_specs),
                            "actual": "See actual-loopback-response evidence", "verification_attempt_ids": [],
                            "opened_at": ended, "root_cause": {"state": "confirmed", "evidence_ids": [eid], "description": "Explicitly seeded fixture behavior"}})
    try:
        started = now()
        response = request(base, "/price")
        record("C-AMOUNT", "R-AMOUNT", "discounted amount",
               [("A-STATUS", "HTTP status is 200", response["status"] == 200),
                ("A-AMOUNT", "amount is 100", response["body"].get("amount") == 100)],
               response, started, "GET /price; independently compare 120-20")
        started = now()
        before = request(base, "/state")
        response = request(base, "/admin", "POST")
        after = request(base, "/state")
        record("C-AUTH", "R-AUTH", "forbidden operation has no write",
               [("A-FORBIDDEN", "HTTP status is 403", response["status"] == 403),
                ("A-NO-WRITE", "admin write count unchanged", before["body"]["admin_writes"] == after["body"]["admin_writes"])],
               {"before": before, "response": response, "after": after}, started,
               "GET /state; POST /admin as unauthorized fixture caller; GET /state")
        started = now()
        before = request(base, "/state")
        first = request(base, "/orders", "POST", {"Idempotency-Key": "fixture-key"})
        second = request(base, "/orders", "POST", {"Idempotency-Key": "fixture-key"})
        after = request(base, "/state")
        record("C-IDEMP", "R-IDEMP", "sequential duplicate request is idempotent",
               [("A-SAME-ID", "same order ID returned", first["body"]["id"] == second["body"]["id"]),
                ("A-ONE-ORDER", "one order created", after["body"]["order_count"] - before["body"]["order_count"] == 1)],
               {"before": before, "first": first, "second": second, "after": after}, started,
               "POST /orders twice with same key; compare order IDs and state")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
    cleanup_path = "evidence/server-cleanup.txt"
    cleanup_payload = ("server thread alive: " + str(thread.is_alive()) + "\n").encode()
    (out / cleanup_path).write_bytes(cleanup_payload)
    evidence.append({"id": "E-CLEANUP", "run_id": run["id"], "case_id": None, "attempt_id": None,
                     "kind": "cleanup", "relative_path": cleanup_path, "sha256": hashlib.sha256(cleanup_payload).hexdigest(),
                     "description": "Fixture server shutdown and closed", "captured_at": now(), "redaction_status": "not_needed"})
    resources = [{"id": "X-SERVER", "kind": "loopback-server", "locator": base, "owner_run_id": run["id"],
                  "cleanup_status": "failed" if thread.is_alive() else "cleaned", "cleanup_evidence_ids": ["E-CLEANUP"],
                  "reason": "server thread did not exit" if thread.is_alive() else None}]
    run["quality_decision"] = "does_not_meet_criteria" if defects else "meets_agreed_criteria"
    run["decision_basis"] = "Actual synthetic loopback requests and explicit independent assertions; no claim about real products."
    if thread.is_alive():
        run.update(workflow_state="partial", quality_decision="insufficient_evidence")
    bundle = {"run": run, "cases": {"cases": cases}, "attempts": attempts,
              "evidence": {"evidence": evidence}, "defects": {"defects": defects},
              "resources": {"resources": resources}, "_root": out}
    for name in ("run", "cases", "evidence", "defects", "resources"):
        (out / (name + ".json")).write_text(json.dumps(bundle[name], ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "results.jsonl").write_text("".join(json.dumps(a, ensure_ascii=False) + "\n" for a in attempts), encoding="utf-8")
    # Execute an isolated known-bad control, independent of the fixed responses.
    mutant = make_server("defective")
    mt = threading.Thread(target=mutant.serve_forever, daemon=True)
    mt.start()
    mb = "http://127.0.0.1:" + str(mutant.server_port)
    try:
        bad_price = request(mb, "/price")
        before = request(mb, "/state")
        request(mb, "/admin", "POST")
        after = request(mb, "/state")
        first = request(mb, "/orders", "POST", {"Idempotency-Key":"control"})
        second = request(mb, "/orders", "POST", {"Idempotency-Key":"control"})
        killed = {"C-AMOUNT": bad_price["body"]["amount"] != 100,
                  "C-AUTH": before["body"]["admin_writes"] != after["body"]["admin_writes"],
                  "C-IDEMP": first["body"]["id"] != second["body"]["id"]}
    finally:
        mutant.shutdown(); mutant.server_close(); mt.join(timeout=3)
    contract = {"scope":run["scope"], "requirements":run["requirements"], "negative_control_results":killed}
    data = json.dumps(contract, indent=2).encode()
    (out / "evidence/contract-control.json").write_bytes(data)
    evidence.append({"id":"E-CONTRACT", "run_id":run["id"], "case_id":None, "attempt_id":None,
        "kind":"contract-and-negative-control", "relative_path":"evidence/contract-control.json",
        "sha256":hashlib.sha256(data).hexdigest(), "description":"Fixture contract and actual isolated mutant checks",
        "captured_at":now(), "redaction_status":"not_needed"})
    ids = [r["id"] for r in run["requirements"]]
    run["scope_contract"] = {"source":"fixture contract", "evidence_ids":["E-CONTRACT"],
        "items":[{"scope_index":0,"requirement_ids":ids}]}
    run["acceptance"] = {"source":"fixture contract", "evidence_ids":["E-CONTRACT"],
        "rules":[{"operator":"all_required_pass","requirement_ids":ids}]}
    run["negative_controls"] = [{"case_id":c, "mutation":"isolated seeded contract violation", "outcome":"killed" if ok else "survived", "evidence_ids":["E-CONTRACT"]} for c,ok in killed.items()]
    for name in ("run", "evidence"):
        (out / (name + ".json")).write_text(json.dumps(bundle[name], indent=2), encoding="utf-8")
    errors, warnings = validate(bundle)
    result = {"valid": not errors, "errors": errors, "warnings": warnings}
    if not errors:
        result["summary"] = summarize(bundle)
    (out / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "report.md").write_text(
        "# 本地合成API验证\n\n"
        "这是预设缺陷的本地示例，不是真实产品验收或独立模型前向评估。\n\n"
        + "版本：" + variant + "\n\n"
        + "实际执行：" + str(len(attempts)) + "项；失败：" + str(len(defects)) + "项。\n\n"
        + "分别检查金额、403后的副作用、顺序重复请求。并发、设备、浏览器和模型表现未执行。\n\n"
        + "证据见evidence目录，服务已执行shutdown/server_close并核对线程状态。\n", encoding="utf-8")
    print(json.dumps({"variant": variant, "valid_records": not errors,
                      "actual_cases": len(cases), "detected_contract_failures": len(defects),
                      "server_stopped": not thread.is_alive(), "errors": errors}, indent=2))
    return 1 if errors else 0

if __name__ == "__main__":
    sys.exit(main())
