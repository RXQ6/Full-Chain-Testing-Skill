"""Summarize valid records, preserving failed/retried/historical attempts."""
import argparse
import json
import sys
from pathlib import Path
from qa_records import load_bundle, validate, summarize

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output", type=Path, help="write the generated result (including invalid status) to this JSON file")
    parser.add_argument("--baseline", help="compare with a separately validated prior run")
    args = parser.parse_args()
    bundle, initial = load_bundle(args.run_dir)
    errors, warnings = validate(bundle, initial)
    result = {"valid": not errors, "errors": errors, "warnings": warnings}
    if not errors:
        result["summary"] = summarize(bundle)
    if not errors and args.baseline:
        old, initial = load_bundle(args.baseline)
        prior_errors, _ = validate(old, initial)
        if prior_errors:
            errors.extend(['baseline: ' + e for e in prior_errors])
            result['valid'] = False
        else:
            before = {c['id']: c for c in old['cases']['cases']}
            after = {c['id']: c for c in bundle['cases']['cases']}
            result['comparison'] = {'baseline_run_id': old['run']['id'],
                'added': sorted(after.keys() - before.keys()), 'removed': sorted(before.keys() - after.keys()),
                'changed': [{'case_id': k, 'before': before[k]['status'], 'after': after[k]['status'],
                             'definition_changed': before[k]['oracle'] != after[k]['oracle']}
                            for k in sorted(before.keys() & after.keys()) if before[k] != after[k]],
                'comparable_environment': old['run']['environment_id'] == bundle['run']['environment_id']}
    encoded = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        try:
            args.output.write_text(encoded + '\n', encoding='utf-8')
        except OSError:
            parser.error('cannot write output file; create its parent directory and check permissions')
    if args.json:
        print(encoded)
    else:
        print('VALID RECORDS' if not errors else 'INVALID RECORDS')
        if 'summary' in result:
            print('Cases: ' + json.dumps(result['summary']['case_counts']))
        for error in errors:
            print(error)
    return 1 if errors else 0

if __name__ == "__main__":
    sys.exit(main())
