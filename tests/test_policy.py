import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_records import fixture
from qa_records import validate

class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.b = fixture(Path(self.temp.name))
    def test_root_is_normalized_in_validator(self):
        self.b['_root'] = self.b['_root'] / '..' / self.b['_root'].name
        self.assertEqual(validate(self.b)[0], [])
    def test_scope_omission(self):
        self.b['run']['scope'].append('permissions and payment')
        self.assertTrue(validate(self.b)[0])
    def test_one_rule_cannot_stand_in_for_multiple_scope_items(self):
        self.b['run']['scope'].append('another feature')
        self.b['run']['scope_contract']['items'].append({'scope_index':1,'requirement_ids':['R1']})
        self.assertTrue(validate(self.b)[0])
    def test_unsupported_na(self):
        self.b['run']['coverage_exceptions'] = [{'requirement_id':'R1','status':'not_applicable','reason':'skip','evidence_ids':[]}]
        self.assertTrue(validate(self.b)[0])
    def test_unknown_version(self):
        self.b['attempts'][0]['revision']['product'] = 'unrecorded'
        self.assertTrue(validate(self.b)[0])
    def test_missing_limits(self):
        self.b['run']['limits'] = {}
        self.assertTrue(validate(self.b)[0])
    def test_free_text_criteria_not_enough(self):
        del self.b['run']['acceptance']
        self.assertTrue(validate(self.b)[0])
    def test_negative_control_missing(self):
        self.b['run']['negative_controls'] = []
        self.assertTrue(validate(self.b)[0])
    def test_negative_control_survives(self):
        self.b['run']['negative_controls'][0]['outcome'] = 'survived'
        self.assertTrue(validate(self.b)[0])
    def test_medium_defect_blocks(self):
        self.b['defects']['defects'] = [{'id':'D','title':'bug','expected':'one','actual':'two','severity':'medium','status':'open','case_ids':['C1'],'evidence_ids':['E1'],'verification_attempt_ids':[], 'opened_at':'2026-01-01T00:00:02Z'}]
        self.assertTrue(validate(self.b)[0])
    def test_old_attempt_cannot_close_defect(self):
        self.b['defects']['defects'] = [{'id':'D','title':'bug','expected':'one','actual':'two','severity':'low','status':'verified','case_ids':['C1'],'evidence_ids':['E1'],'verification_attempt_ids':['T1'], 'opened_at':'2026-01-01T00:00:02Z'}]
        self.assertTrue(validate(self.b)[0])
    def test_confirmed_cause_requires_evidence(self):
        self.b['run']['quality_decision'] = 'pending'
        self.b['defects']['defects'] = [{'id':'D','title':'bug','expected':'one','actual':'two','severity':'low','status':'open','case_ids':['C1'],'evidence_ids':['E1'],'verification_attempt_ids':[], 'opened_at':'2026-01-01T00:00:02Z','root_cause':{'state':'confirmed'}}]
        self.assertTrue(validate(self.b)[0])
