"""Check requirement-to-case coverage; not business acceptance."""
import argparse
import json
import sys
from qa_records import load_bundle, validate, requirement_gaps

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    bundle, initial = load_bundle(args.run_dir)
    errors, warnings = validate(bundle, initial)
    coverage = []
    if not errors:
        gaps, coverage = requirement_gaps(bundle)
        errors.extend(gaps)
    result = {"valid": not errors, "errors": errors, "warnings": warnings, "coverage": coverage}
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else
          "\n".join(["TRACEABLE" if not errors else "GAPS"] + errors + warnings))
    return 1 if errors else 0

if __name__ == "__main__":
    sys.exit(main())
