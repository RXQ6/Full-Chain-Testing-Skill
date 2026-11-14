"""Self-hosted case against this real repository; not independent Agent evaluation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
from test_records import fixture, save
from qa_records import validate

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output_dir')
    args=parser.parse_args()
    output=Path(args.output_dir).resolve()
    output.mkdir(parents=True,exist_ok=False)
    bundle=fixture(output)
    started=datetime.now(timezone.utc).isoformat()
    baseline=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-q'],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=180)
    # Copy only source directories into an exclusive isolated mutant workspace.
    with tempfile.TemporaryDirectory() as temporary:
        mutant=Path(temporary).resolve()/'mutant';mutant.mkdir()
        for name in ('scripts','tests','assets'):
            shutil.copytree(ROOT/name,mutant/name,ignore=shutil.ignore_patterns('__pycache__'))
        path=mutant/'scripts/qa_records.py'
        source=path.read_text(encoding='utf-8')
        assert 'root = Path(bundle["_root"]).resolve()' in source
        path.write_text(source.replace('root = Path(bundle["_root"]).resolve()','root = bundle["_root"]'),encoding='utf-8')
        env=dict(os.environ);env['PYTHONPATH']=str(mutant/'tests')
        control=subprocess.run([sys.executable,'-m','unittest','test_policy.PolicyTests.test_root_is_normalized_in_validator'],cwd=mutant,env=env,capture_output=True,text=True,encoding='utf-8',timeout=30)
        killed=control.returncode!=0 and 'FAIL: test_root_is_normalized_in_validator' in control.stderr
        control_text=(control.stdout+control.stderr).replace(str(mutant),'<isolated-mutant>')
    ended=datetime.now(timezone.utc).isoformat()
    log={'contract':'Repository test suite passes; reverting root canonicalization must break its targeted regression.',
         'baseline_exit':baseline.returncode,'baseline_output':(baseline.stdout+baseline.stderr).replace(str(ROOT),'<repository>'),
         'mutation':'remove root canonicalization','control_exit':control.returncode,'control_output':control_text,'killed':killed}
    payload=json.dumps(log,ensure_ascii=False,indent=2).encode()
    (output/'evidence/one.txt').write_bytes(payload)
    run=bundle['run'];run['id']='repository-self-hosted'
    run['scope']=['Validate the repository record tooling and root-path regression']
    run['authorized_actions']=['local test execution and mutation of an exclusively owned isolated source copy']
    run['requirements'][0].update(statement=log['contract'],source='evaluation/run_repository_case.py')
    run['scope_contract']['source']='evaluation/run_repository_case.py'
    run['acceptance']['source']='evaluation/run_repository_case.py'
    run['limits']={'duration_seconds':300,'max_calls':3,'max_concurrency':1}
    digest=hashlib.sha256(b''.join(p.read_bytes() for p in sorted((ROOT/'scripts').glob('*.py')))).hexdigest()
    test_digest=hashlib.sha256(b''.join(p.read_bytes() for p in sorted((ROOT/'tests').glob('*.py')))).hexdigest()
    run['revision']={'product':digest,'test':test_digest,'configuration':sys.version.split()[0]}
    run['environment_id']=sys.platform+'-self-hosted'
    run['negative_controls'][0].update(mutation=log['mutation'],outcome='killed' if killed else 'survived')
    ok=baseline.returncode==0 and killed
    run['quality_decision']='meets_agreed_criteria' if ok else 'does_not_meet_criteria'
    run['decision_basis']='Actual repository commands and isolated source mutation; not a third-party or independent model assessment.'
    case=bundle['cases']['cases'][0];case.update(title='Repository validation and root regression',status='passed' if ok else 'failed')
    case.update(timeout_seconds=240, preconditions=['repository source and Python standard library available'],
                steps=['execute repository tests', 'revert root normalization in an isolated copy', 'execute targeted regression and check expected failure'],
                cleanup_steps=['remove exclusively created mutant directory via TemporaryDirectory context'])
    case['oracle']={'source':run['requirements'][0]['source'],'assertions':[{'id':'A1','statement':log['contract']}]}
    attempt=bundle['attempts'][0];attempt.update(run_id=run['id'],revision=run['revision'],environment_id=run['environment_id'],started_at=started,ended_at=ended,status=case['status'],category='none' if ok else 'test',reason=None if ok else 'baseline or mutation check failed',invocation='python -m unittest discover; isolated root mutation regression')
    attempt['assertions'][0]['status']=case['status']
    evidence=bundle['evidence']['evidence'][0];evidence.update(run_id=run['id'],kind='actual-repository-process-output',description='Redacted actual baseline and negative control output',sha256=hashlib.sha256(payload).hexdigest(),captured_at=ended,redaction_status='redacted')
    save(bundle)
    errors,_=validate(bundle)
    print(json.dumps({'baseline_passed':baseline.returncode==0,'mutant_killed':killed,'record_errors':errors}))
    return 0 if ok and not errors else 1

if __name__=='__main__':
    sys.exit(main())
