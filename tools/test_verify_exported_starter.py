"""A completed export must be a verifiable, actually testable public bundle."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from export_public_starter import export_public_starter
from verify_exported_starter import ProofError, run_profiles, validate

SOURCE = Path(__file__).resolve().parents[1]
PIN = hashlib.sha256((SOURCE / 'SOURCE_MANIFEST.json').read_bytes()).hexdigest()


class ExportVerificationTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory(prefix='public-export-')
        self.addCleanup(td.cleanup)
        self.parent = Path(td.name)
        self.project = self.parent / 'starter'

    def build(self, profiles=None, **kw):
        report = export_public_starter(SOURCE, PIN, profiles or ['agent'], self.project, **kw)
        return report['output_manifest_sha256']

    def test_verified_export_does_not_falsely_claim_executed_tests(self):
        pin = self.build(['agent', 'training'])
        report = validate(self.project, pin)
        self.assertEqual(report['tests_run'], 0)
        self.assertEqual(report['profiles'], ['agent','training'])
        self.assertEqual(report['files'], 9)
        self.assertEqual(report['qualifications'], {'agent':'executed','training':'executed'})

    def test_real_exported_agent_and_training_tests_are_executed(self):
        pin = self.build(['agent','training'])
        report = run_profiles(self.project, validate(self.project, pin))
        self.assertEqual(report['status'], 'PASS')
        self.assertEqual(report['tests_run'], 2)
        self.assertEqual([r['profile'] for r in report['groups']], ['agent','training'])

    def test_policy_profile_uses_fixed_runtime_tests(self):
        pin = self.build(['policy'])
        before = validate(self.project, pin)
        self.assertEqual(before['qualifications']['policy'], 'executed')
        result = run_profiles(self.project, before)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['tests_run'], 1)
        self.assertEqual(result['groups'][0]['profile'], 'policy')

    def test_ledger_profile_runs_real_reconciliation_checks(self):
        pin = self.build(['ledger'])
        verified = validate(self.project, pin)
        result = run_profiles(self.project, verified)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['tests_run'], 1)
        self.assertEqual(result['groups'][0]['profile'], 'ledger')

    def test_hybrid_search_bundle_runs_real_fts_tests(self):
        pin = self.build(['hybrid-search'])
        verified = validate(self.project, pin)
        report = run_profiles(self.project, verified)
        self.assertEqual(report['status'], 'PASS')
        self.assertEqual(report['tests_run'], 1)
        self.assertEqual(report['groups'][0]['profile'], 'hybrid-search')

    def test_migration_profile_runs_real_sqlite_checks(self):
        pin=self.build(['migration'])
        verified=validate(self.project,pin)
        outcome=run_profiles(self.project,verified)
        self.assertEqual(outcome['status'],'PASS')
        self.assertEqual(outcome['tests_run'],1)
        self.assertEqual(outcome['groups'][0]['profile'],'migration')

    def test_graph_bundle_executes_real_local_claim_regressions(self):
        pin = self.build(['build-graph'])
        verified = validate(self.project, pin)
        result = run_profiles(self.project, verified)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['tests_run'], 1)
        self.assertEqual(result['groups'][0]['profile'], 'build-graph')

    def test_file_bytes_mutation_fails(self):
        pin = self.build()
        path = self.project / 'examples/mcp_agent/runtime.mjs'
        path.write_bytes(path.read_bytes()+b'\n// mutated\n')
        with self.assertRaises(ProofError):
            validate(self.project, pin)

    def test_missing_or_unlisted_files_are_rejected(self):
        pin = self.build()
        p = self.project / 'examples/mcp_agent/test_runtime.mjs'
        p.unlink()
        with self.assertRaisesRegex(ProofError,'missing_file'):
            validate(self.project, pin)
        self.project.joinpath('extra.txt').write_text('new untracked data')
        with self.assertRaises(ProofError):
            validate(self.project, pin)

    def test_unexpected_file_rejected_even_when_all_expected_files_exist(self):
        pin = self.build()
        (self.project/'unexpected.py').write_text('no')
        with self.assertRaisesRegex(ProofError,'extra_or_changed_file'):
            validate(self.project, pin)

    def test_generated_readme_is_covered_by_manifest(self):
        pin = self.build()
        (self.project/'README.md').write_text('edited caveats')
        with self.assertRaisesRegex(ProofError,'content_hash_mismatch'):
            validate(self.project, pin)

    def test_external_manifest_pin_is_mandatory(self):
        pin = self.build()
        for bad in ['', '0'*64, '../README.md', 'xyz']:
            with self.subTest(bad=bad), self.assertRaises(ProofError):
                validate(self.project,bad)
        self.assertEqual(validate(self.project,pin)['status'],'PASS')

    def test_duplicate_json_keys_and_path_traversal_fail(self):
        self.build()
        path = self.project/'REUSE_MANIFEST.json'
        path.write_text('{"schema":1,"schema":1}')
        with self.assertRaisesRegex(ProofError,'duplicate_json_key'):
            validate(self.project, hashlib.sha256(path.read_bytes()).hexdigest())
        obj={'schema':1,'profiles':['agent'],'files':[{'path':'../private.py','bytes':1,'sha256':'0'*64,'mode':'100644'}],
             'profile_qualification':{'agent':'executed'},'generated_readme_sha256':'0'*64,
             'externally_pinned_source_manifest_sha256':'0'*64,'tests_executed_by_generator':0}
        path.write_text(json.dumps(obj))
        with self.assertRaisesRegex(ProofError,'unsafe_path'):
            validate(self.project,hashlib.sha256(path.read_bytes()).hexdigest())

    def test_generated_bundle_refuses_link_or_case_collisions(self):
        pin = self.build()
        collision = self.project/'examples/mcp_agent/RUNTIME.mjs'
        collision.write_text('duplicate casing')
        with self.assertRaises(ProofError):
            validate(self.project,pin)
        collision.unlink()
        link = self.project/'shortcut.mjs'
        try:
            link.symlink_to('examples/mcp_agent/runtime.mjs')
        except OSError:
            self.skipTest('symlink creation requires privileges')
        with self.assertRaisesRegex(ProofError, 'unsafe_link'):
            validate(self.project,pin)

    def test_cannot_promote_historical_evidence_by_running_tests(self):
        pin = self.build(['typed-api'], allow_historical=True)
        before = validate(self.project,pin)
        self.assertEqual(before['qualifications']['typed-api'],'historical')
        r = run_profiles(self.project,before)
        self.assertEqual(r['groups'][0]['qualification'],'historical')
        self.assertEqual(r['groups'][0]['status'],'PASS')

    def test_does_not_execute_manifest_supplied_commands(self):
        pin = self.build(['agent'])
        path=self.project/'REUSE_MANIFEST.json'
        item=json.loads(path.read_text())
        marker=self.parent/'must-never-be-written'
        item['tests_to_run_manually']=[f'python -c "open({str(marker)!r},\'w\').write(1)"']
        path.write_text(json.dumps(item))
        new_pin=hashlib.sha256(path.read_bytes()).hexdigest()
        verified=validate(self.project,new_pin)
        result=run_profiles(self.project,verified)
        self.assertEqual(result['tests_run'],1)
        self.assertFalse(marker.exists())
        self.assertNotEqual(pin,new_pin)

    def test_cli_validates_and_runs_selected_tests(self):
        pin = self.build(['agent'])
        runner = SOURCE/'tools/verify_exported_starter.py'
        result=subprocess.run([sys.executable,'-B',str(runner),'--destination',str(self.project),
                               '--expected-manifest-sha256',pin,'--run-tests'],capture_output=True,text=True,timeout=40)
        self.assertEqual(result.returncode,0,result.stderr+result.stdout)
        self.assertEqual(json.loads(result.stdout)['tests_run'],1)

    def test_missing_runtime_is_not_a_success(self):
        pin=self.build()
        with self.assertRaisesRegex(ProofError,'invalid_timeout'):
            run_profiles(self.project,validate(self.project,pin),timeout=0)

    def test_false_test_execution_in_manifest_fails(self):
        self.build()
        path=self.project/'REUSE_MANIFEST.json'
        obj=json.loads(path.read_text())
        obj['tests_executed_by_generator']=99
        path.write_text(json.dumps(obj))
        with self.assertRaisesRegex(ProofError,'false_test_claim'):
            validate(self.project,hashlib.sha256(path.read_bytes()).hexdigest())

    def test_missing_bundle_readme_rejected(self):
        pin=self.build()
        (self.project/'README.md').unlink()
        with self.assertRaisesRegex(ProofError,'missing_file'):
            validate(self.project,pin)


if __name__=='__main__':
    unittest.main()
