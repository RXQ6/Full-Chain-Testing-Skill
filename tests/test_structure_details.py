from pathlib import Path
import shutil
import tempfile
import unittest
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from self_check import check

class StructureDetails(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'skill'
        shutil.copytree(ROOT,self.root,ignore=shutil.ignore_patterns('.git','__pycache__','.runs'))
    def test_missing_frontmatter(self):
        (self.root/'SKILL.md').write_text('body',encoding='utf-8')
        self.assertTrue(check(self.root))
    def test_broken_link(self):
        (self.root/'new.md').write_text('[bad](missing.md)',encoding='utf-8')
        self.assertTrue(check(self.root))
    def test_title_and_anchor_link(self):
        (self.root/'new.md').write_text('[entry](SKILL.md#开始与模式 "title")',encoding='utf-8')
        self.assertEqual(check(self.root),[])
    def test_short_host_label_advisory(self):
        p=self.root/'agents/openai.yaml'
        s=p.read_text(encoding='utf-8')
        import re
        p.write_text(re.sub(r'short_description:.*','short_description: "QA"',s),encoding='utf-8')
        self.assertEqual(check(self.root),[])
    def test_prompt_name_is_derived(self):
        p=self.root/'SKILL.md';p.write_text(p.read_text(encoding='utf-8').replace('name: full-chain-testing','name: renamed-skill'),encoding='utf-8')
        p=self.root/'agents/openai.yaml';p.write_text(p.read_text(encoding='utf-8').replace('$full-chain-testing','$renamed-skill'),encoding='utf-8')
        self.assertEqual(check(self.root),[])
    def test_invalid_python(self):
        (self.root/'scripts/bad.py').write_text('def broken(',encoding='utf-8')
        self.assertTrue(check(self.root))
