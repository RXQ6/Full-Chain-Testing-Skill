"""Create an unexecuted run in a NEW directory, never overwrite existing work."""
import argparse
import json
from pathlib import Path
import sys
import uuid
import shutil

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir")
    parser.add_argument("--mode", choices=["plan", "verify", "repair"], default="plan")
    args = parser.parse_args()
    target = Path(args.output_dir).resolve()
    try:
        target.mkdir(parents=True, exist_ok=False)
    except OSError:
        print("Cannot create new run directory; existing paths are never overwritten.", file=sys.stderr)
        return 1
    assets = Path(__file__).resolve().parent.parent / "assets"
    try:
        for name in ("run", "cases", "evidence", "defects", "resources"):
            data = json.loads((assets / (name + "-template.json")).read_text(encoding="utf-8"))
            if name == "run":
                data["id"] = "run-" + uuid.uuid4().hex[:12]
                data["mode"] = args.mode
            (target / (name + ".json")).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (target / "results.jsonl").write_text("", encoding="utf-8")
        (target / "report.md").write_text((assets / "report-template.md").read_text(encoding="utf-8"), encoding="utf-8")
    except (OSError, ValueError):
        shutil.rmtree(target)
        print("Initialization failed; exclusively created directory removed.", file=sys.stderr)
        return 1
    print("Add the run directory to .gitignore; review and redact evidence before sharing.")
    print("Created an UNEXECUTED run. Fill scope, rules, versions and cases before testing.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
