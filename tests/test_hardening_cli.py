import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from test_records import fixture, save, SCRIPTS
from qa_records import load_bundle, validate
import new_run

class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = fixture(self.root)
        save(self.bundle)
    def test_text_json_output_and_independent_file(self):
        cmd = [sys.executable, str(SCRIPTS/'summarize_results.py'), str(self.root)]
        plain = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', check=True)
        self.assertTrue(plain.stdout.startswith('VALID RECORDS'))
        out = self.root/'independent-summary.json'
        encoded = subprocess.run(cmd+['--json','--output',str(out)],capture_output=True,text=True,encoding='utf-8',check=True)
        self.assertEqual(json.loads(encoded.stdout), json.loads(out.read_text(encoding='utf-8')))
    def test_compact_matches_full(self):
        compact = {'run': self.bundle['run'], 'attempts':self.bundle['attempts']}
        for key in ('cases','defects','resources','evidence'):
            compact[key] = self.bundle[key][key]
        (self.root/'compact.json').write_text(json.dumps(compact),encoding='utf-8')
        for name in ('run.json','cases.json','defects.json','resources.json','evidence.json','results.jsonl'):
            (self.root/name).unlink()
        loaded, errors = load_bundle(self.root)
        self.assertEqual(validate(loaded,errors)[0], [])
    def test_initializer_rolls_back_only_new_directory(self):
        target=self.root/'initializing'
        sentinel=self.root/'sentinel'; sentinel.write_text('preserve')
        with patch.object(sys,'argv',['new_run.py',str(target)]), patch.object(Path,'read_text',side_effect=OSError('injected')), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(new_run.main(),1)
        self.assertFalse(target.exists())
        self.assertEqual(sentinel.read_text(),'preserve')
    def test_baseline_comparison(self):
        cmd=[sys.executable,str(SCRIPTS/'summarize_results.py'),str(self.root),'--json','--baseline',str(self.root)]
        result=json.loads(subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',check=True).stdout)
        self.assertEqual(result['comparison']['baseline_run_id'],'RUN-1')
        self.assertEqual(result['comparison']['changed'],[])
    @unittest.skipIf(os.name=='nt','colon is not a Windows filename')
    def test_posix_colon_filename(self):
        (self.root/'evidence/one.txt').rename(self.root/'evidence/one:sample.txt')
        self.bundle['evidence']['evidence'][0]['relative_path']='evidence/one:sample.txt'
        self.assertEqual(validate(self.bundle)[0],[])
