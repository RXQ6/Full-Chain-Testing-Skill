"""Summarize valid records, preserving failed/retried/historical attempts."""
import argparse
import json
import sys
from qa_records import load_bundle, validate, summarize

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    bundle, initial = load_bundle(args.run_dir)
    errors, warnings = validate(bundle, initial)
    result = {"valid": not errors, "errors": errors, "warnings": warnings}
    if not errors:
        result["summary"] = summarize(bundle)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if errors else 0

if __name__ == "__main__":
    sys.exit(main())
