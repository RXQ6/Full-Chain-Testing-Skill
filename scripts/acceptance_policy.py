"""Necessary acceptance gates; cannot authenticate user intent or evidence semantics."""
from datetime import datetime

UNKNOWN = {'unrecorded', 'unknown', 'n/a', 'none', 'todo', ''}

def known(value):
    return isinstance(value, str) and value.strip().lower() not in UNKNOWN

def check_policy(bundle):
    run = bundle['run']
    errors = []
    passed = run.get('quality_decision') == 'meets_agreed_criteria'
    evidence = {e['id'] for e in bundle['evidence']['evidence']}
    cases = bundle['cases']['cases']
    requirements = {r['id']: r for r in run['requirements']}
    def supported(record):
        ids = record.get('evidence_ids', [])
        return (isinstance(ids, list) and bool(ids)
                and all(isinstance(i, str) and i in evidence for i in ids))
    if bundle['attempts']:
        limits = run.get('limits', {})
        if not all(type(limits.get(k)) in (int, float) and 0 < limits[k] < float('inf')
                   for k in ('duration_seconds', 'max_calls', 'max_concurrency')):
            errors.append('limits: positive duration_seconds/max_calls/max_concurrency required for execution')
        for a in bundle['attempts']:
            if not known(a.get('environment_id')) or not all(known(a['revision'].get(k)) for k in ('product', 'test', 'configuration')):
                errors.append('attempt: unidentified environment/revision cannot be execution evidence')
    for d in bundle['defects']['defects']:
        opened = d.get('opened_at')
        try:
            opened = datetime.fromisoformat(opened.replace('Z', '+00:00'))
            if opened.tzinfo is None:
                raise ValueError()
        except (AttributeError, ValueError, TypeError):
            errors.append('defect.opened_at: timezone-aware timestamp required')
            opened = None
        cause = d.get('root_cause', {'state': 'unknown'})
        if cause.get('state') not in {'unknown', 'hypothesis', 'confirmed'}:
            errors.append('root_cause.state: invalid')
        if cause.get('state') == 'confirmed' and not supported(cause):
            errors.append('confirmed root cause: evidence required')
        if d.get('status') == 'verified' and opened is not None:
            attempts = {a['id']: a for a in bundle['attempts']}
            for aid in d.get('verification_attempt_ids', []):
                a = attempts.get(aid, {})
                start = datetime.fromisoformat(a.get('started_at', '').replace('Z', '+00:00'))
                if start <= opened:
                    errors.append('verified defect: verification must start after discovery')
    for ex in run.get('coverage_exceptions', []):
        if ex.get('status') == 'not_applicable':
            if not supported(ex):
                errors.append('not_applicable: supporting evidence required')
            if requirements.get(ex['requirement_id'], {}).get('risk') in {'critical', 'high'}:
                errors.append('high-risk requirement cannot be waived as not_applicable; revise agreed scope explicitly')
    for c in cases:
        if c.get('status') == 'not_applicable' and any(requirements[r]['risk'] in {'critical', 'high'} for r in c['requirement_ids']):
            errors.append('high-risk case cannot bypass verification as not_applicable')
        stability = c.get('stability', {})
        if stability:
            if stability.get('state') not in {'stable', 'flaky', 'quarantined'}:
                errors.append('stability.state: invalid')
            if stability.get('state') in {'flaky', 'quarantined'}:
                if c.get('status') == 'passed' or (passed and c.get('required')):
                    errors.append('flaky/quarantined required case cannot satisfy acceptance')
                if not all(known(stability.get(k)) for k in ('owner', 'reason', 'recheck_at')):
                    errors.append('quarantine requires owner/reason/recheck_at')
        budget = stability.get('max_attempts', 3)
        history = [a for a in bundle['attempts'] if a['case_id'] == c['id']]
        if type(budget) is not int or budget < 1 or len(history) > budget:
            errors.append('case diagnostic retry budget exceeded or invalid')
    if not passed:
        return errors
    contract = run.get('scope_contract', {})
    items = contract.get('items', [])
    if (not known(contract.get('source')) or not supported(contract)
            or not isinstance(items, list) or len(items) != len(run['scope'])):
        errors.append('scope_contract: sourced evidence and one item per scope entry required')
    indexes = []
    for item in items:
        indexes.append(item.get('scope_index'))
        ids = item.get('requirement_ids', [])
        if not ids or any(r not in requirements for r in ids):
            errors.append('scope_contract: every scope item needs known requirements')
    if indexes != list(range(len(run['scope']))):
        errors.append('scope_contract: scope indexes must cover the exact agreed scope')
    mapped = {r for i in items for r in i.get('requirement_ids', [])}
    assigned = [r for i in items for r in i.get('requirement_ids', [])]
    if len(assigned) != len(set(assigned)):
        errors.append('scope_contract: split shared requirements into scope-specific verifiable rules')
    if mapped != set(requirements):
        errors.append('scope_contract: unmapped requirement or omitted scope')
    criteria = run.get('acceptance', {})
    rules = criteria.get('rules', [])
    if not known(criteria.get('source')) or not supported(criteria) or not rules:
        errors.append('acceptance: sourced structured rules and evidence required')
    covered = set()
    for rule in rules:
        ids = rule.get('requirement_ids', [])
        if (rule.get('operator') != 'all_required_pass' or not ids
                or any(r not in requirements for r in ids)):
            errors.append('acceptance rule: known requirements and all_required_pass operator required')
        covered.update(ids)
    if covered != set(requirements):
        errors.append('acceptance rules must cover every requirement')
    for d in bundle['defects']['defects']:
        if d['status'] not in {'verified', 'accepted_risk'}:
            errors.append('acceptance: unresolved defect at any severity')
    controls = run.get('negative_controls', [])
    for c in cases:
        if not c['required'] or c['status'] == 'not_applicable':
            continue
        matches = [x for x in controls if x.get('case_id') == c['id']]
        if not any(x.get('outcome') == 'killed' and known(x.get('mutation')) and supported(x) for x in matches):
            errors.append('negative control: required case needs killed isolated mutant evidence')
    return errors
