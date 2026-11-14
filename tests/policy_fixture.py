def add_contract(bundle):
    """Explicitly synthetic policy evidence for validator tests, not product evidence."""
    run = bundle['run']
    eid = bundle['evidence']['evidence'][0]['id']
    run['limits'] = {'duration_seconds': 30, 'max_calls': 20, 'max_concurrency': 1}
    ids = [r['id'] for r in run['requirements']]
    run['scope_contract'] = {'source': 'synthetic contract', 'evidence_ids': [eid],
        'items': [{'scope_index': i, 'requirement_ids': ids} for i in range(len(run['scope']))]}
    run['acceptance'] = {'source': 'synthetic contract', 'evidence_ids': [eid],
        'rules': [{'operator': 'all_required_pass', 'requirement_ids': ids}]}
    run['negative_controls'] = [{'case_id': c['id'], 'mutation': 'synthetic invalid-record control',
        'outcome': 'killed', 'evidence_ids': [eid]} for c in bundle['cases']['cases']]
