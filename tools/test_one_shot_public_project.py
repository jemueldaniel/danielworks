"""End-to-end public-only one-command assembly tests with negative security cases."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from one_shot_public_project import assemble
from verify_exported_starter import ProofError, validate
from export_public_starter import STARTERS

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PIN = hashlib.sha256((ROOT / 'SOURCE_MANIFEST.json').read_bytes()).hexdigest()
CLI = ROOT / 'tools' / 'one_shot_public_project.py'


class OneShotPublicProjectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='public-project-test-')
        self.addCleanup(self.tmp.cleanup)
        self.parent = Path(self.tmp.name)
        self.output = self.parent / 'out'
        self.receipt = self.parent / 'acceptance.json'

    def create(self, profiles=None, **kwargs):
        return assemble(ROOT, SOURCE_PIN, self.output, profiles or ['training'], **kwargs)

    def test_plan_does_not_write_or_claim_test_execution(self):
        result = self.create(dry_run=True)
        self.assertEqual(result['status'], 'DRY_RUN')
        self.assertFalse(self.output.exists())
        self.assertEqual(result['tested_groups'], 0)
        self.assertEqual(result['qualification'], 'not_tested')

    def test_missing_profiles_is_not_success(self):
        result = assemble(ROOT, SOURCE_PIN, self.output, [])
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['code'], 'no_profile_selected')
        self.assertFalse(self.output.exists())

    def test_unknown_profile_has_no_side_effect(self):
        result = self.create(['private-billing-code'])
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['code'], 'unknown_profile')
        self.assertFalse(self.output.exists())

    def test_duplicate_selection_is_refused(self):
        result = self.create(['jobs', 'jobs'])
        self.assertEqual(result['code'], 'duplicate_profile')
        self.assertFalse(self.output.exists())

    def test_duplicate_between_explicit_and_all_executed_is_refused(self):
        result = self.create(['agent'], all_executed=True)
        self.assertEqual(result['code'], 'duplicate_profile')
        self.assertFalse(self.output.exists())

    def test_source_pin_mismatch_blocks_export(self):
        result = assemble(ROOT, '0'*64, self.output, ['training'])
        self.assertEqual(result['status'], 'FAIL')
        self.assertFalse(self.output.exists())

    def test_no_tests_remains_verified_only_not_executed(self):
        result = self.create(run_tests=False)
        self.assertEqual(result['status'], 'PASS_VERIFIED_ONLY')
        self.assertEqual(result['tested_groups'], 0)
        self.assertEqual(result['groups'], [])
        self.assertTrue(result['posttest_bytes_verified'])
        self.assertEqual(validate(self.output,result['output_manifest_sha256'])['status'], 'PASS')

    def test_training_real_cpu_test_is_run(self):
        result = self.create()
        self.assertEqual(result['status'], 'PASS_TESTED')
        self.assertEqual(result['tested_groups'], 1)
        self.assertEqual(result['groups'][0]['profile'], 'training')
        self.assertTrue(result['posttest_bytes_verified'])

    def test_all_seven_executed_profiles_run_and_retained(self):
        result = assemble(ROOT, SOURCE_PIN, self.output, [], all_executed=True, timeout=60)
        self.assertEqual(result['status'], 'PASS_TESTED',result)
        self.assertEqual(set(result['profiles']), {p for p,x in STARTERS.items() if x.qualification == 'executed'})
        self.assertEqual(result['tested_groups'], 7)
        self.assertEqual({g['status'] for g in result['groups']},{'PASS'})
        self.assertTrue(result['posttest_bytes_verified'])

    def test_signed_event_outbox_runs_from_exported_bytes(self):
        result = self.create(['event-outbox'], receipt=self.receipt)
        self.assertEqual(result['status'], 'PASS_TESTED', result)
        self.assertEqual(result['tested_groups'], 1)
        self.assertEqual(result['profiles'], ['event-outbox'])
        self.assertEqual(result['groups'][0]['status'], 'PASS')
        self.assertTrue((self.output/'examples/event_outbox/test_event_outbox.py').is_file())
        self.assertTrue(result['posttest_bytes_verified'])
        self.assertEqual(json.loads(self.receipt.read_text()), result)

    def test_new_portable_proof_platform_exports_and_tests_real_http_sqlite(self):
        result = self.create(['proof-platform'], receipt=self.receipt)
        self.assertEqual(result['status'], 'PASS_TESTED', result)
        self.assertEqual(result['tested_groups'], 1)
        self.assertEqual(result['profiles'], ['proof-platform'])
        self.assertEqual(result['groups'][0]['status'], 'PASS')
        self.assertTrue((self.output / 'projects/portable-proof-studio/server.py').is_file())
        self.assertTrue(result['posttest_bytes_verified'])
        self.assertEqual(json.loads(self.receipt.read_text()), result)

    def test_historical_profile_requires_explicit_optin(self):
        result = self.create(['typed-api'])
        self.assertEqual(result['code'], 'explicit_historical_opt_in_required')
        self.assertFalse(self.output.exists())

    def test_historical_profile_remains_historical_even_after_real_tests(self):
        result = self.create(['typed-api'], allow_historical=True)
        self.assertEqual(result['status'], 'PASS_TESTED')
        self.assertEqual(result['profile_qualifications'], {'typed-api':'historical'})
        self.assertFalse(result['historical_evidence_promoted'])

    def test_existing_output_directory_is_never_overwritten(self):
        self.output.mkdir()
        prior = self.output / 'original.txt'
        prior.write_text('do not erase')
        result = self.create()
        self.assertEqual(result['code'], 'destination_already_exists')
        self.assertEqual(prior.read_text(), 'do not erase')

    def test_export_cannot_write_inside_source(self):
        result = assemble(ROOT,SOURCE_PIN,ROOT/'temporary-public-kit', ['training'])
        self.assertEqual(result['status'], 'FAIL')
        self.assertFalse((ROOT/'temporary-public-kit').exists())

    def test_out_of_band_receipt_matches_run_and_is_exclusive(self):
        result = self.create(receipt=self.receipt)
        self.assertEqual(result['status'],'PASS_TESTED')
        self.assertEqual(json.loads(self.receipt.read_text()), result)
        self.assertNotIn(str(self.parent), self.receipt.read_text())
        repeat = self.create(receipt=self.receipt)
        self.assertEqual(repeat['code'], 'receipt_already_exists')
        self.assertEqual(json.loads(self.receipt.read_text()), result)

    def test_preexisting_receipt_never_overwritten_or_runs(self):
        self.receipt.write_text('original')
        result = self.create(receipt=self.receipt)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['code'], 'receipt_already_exists')
        self.assertEqual(self.receipt.read_text(), 'original')
        self.assertFalse(self.output.exists())

    def test_receipt_inside_destination_is_blocked_before_export(self):
        result = self.create(receipt=self.output/'proof.json')
        self.assertEqual(result['code'], 'unsafe_receipt_parent')
        self.assertFalse(self.output.exists())

    def test_receipt_inside_source_is_blocked(self):
        result = self.create(receipt=ROOT/'proof.json')
        self.assertEqual(result['code'],'receipt_inside_protected_tree')
        self.assertFalse(self.output.exists())

    def test_invalid_timeout_fails_before_creating_kit(self):
        for timeout in [0,121,True,1.4]:
            with self.subTest(timeout=timeout):
                result = self.create(timeout=timeout)
                self.assertEqual(result['code'],'invalid_timeout')
                self.assertFalse(self.output.exists())

    def test_raises_from_runtime_never_claims_pass_or_deletes_kit(self):
        with patch('one_shot_public_project.run_profiles',side_effect=ProofError('test_failed')):
            result = self.create()
        self.assertEqual(result['status'],'FAIL')
        self.assertEqual(result['stage'],'runtime_tests')
        self.assertTrue(self.output.exists())
        self.assertFalse(self.receipt.exists())

    def test_child_process_environment_excludes_ambient_private_values(self):
        import one_shot_public_project as module
        with patch.dict('os.environ', {'PRIVATE_SAMPLE_CREDENTIAL':'do-not-forward',
                                     'NODE_OPTIONS':'--require untrusted-module',
                                     'PYTHONPATH':'/not/an/allowlisted/import/path'}), \
             patch.object(module, 'run_profiles', return_value={
                 'tests_run':1,'groups':[{'profile':'training','status':'PASS','qualification':'executed'}]
             }) as runner:
            result = self.create()
        self.assertEqual(result['status'],'PASS_TESTED')
        env = runner.call_args.kwargs['runtime_env']
        self.assertNotIn('PRIVATE_SAMPLE_CREDENTIAL',env)
        self.assertNotIn('NODE_OPTIONS',env)
        self.assertNotIn('PYTHONPATH',env)
        self.assertIn('PYTHONDONTWRITEBYTECODE',env)
        self.assertEqual(env['PYTHONNOUSERSITE'],'1')

    def test_tampered_exported_readme_fails_before_starting_tests(self):
        import one_shot_public_project as module
        original_export=module.export_public_starter
        def tampered_export(*args,**kwargs):
            result=original_export(*args,**kwargs)
            (self.output/'README.md').write_text('tampered public README')
            return result
        with patch.object(module,'export_public_starter',side_effect=tampered_export),patch.object(module,'run_profiles') as runtime:
            result=self.create()
        self.assertEqual(result['status'],'FAIL')
        self.assertEqual(result['stage'],'pretest_integrity')
        runtime.assert_not_called()

    def test_modified_worktree_after_tests_fails_posttest_integrity(self):
        import one_shot_public_project as module
        def mutate_posttest(*args,**kwargs):
            (self.output/'README.md').write_text('post-test file mutation')
            return {'tests_run':1,'groups':[{'profile':'training','status':'PASS','qualification':'executed'}]}
        with patch.object(module,'run_profiles',side_effect=mutate_posttest):
            result=self.create()
        self.assertEqual(result['status'],'FAIL')
        self.assertEqual(result['stage'],'posttest_integrity')
        self.assertTrue(self.output.exists())

    def test_test_count_mismatch_is_not_complete(self):
        import one_shot_public_project as module
        with patch.object(module,'run_profiles',return_value={'tests_run':0,'groups':[]}):
            result=self.create()
        self.assertEqual(result['status'],'FAIL')
        self.assertEqual(result['code'],'incomplete_test_execution')

    def test_cli_exposes_external_pin_and_no_absolute_path_or_secret(self):
        command=[sys.executable,'-B',str(CLI),'--root',str(ROOT),
                 '--expected-source-sha256',SOURCE_PIN,'--destination',str(self.output),
                 '--profile','training','--receipt',str(self.receipt)]
        completed=subprocess.run(command,capture_output=True,text=True,timeout=60,check=False)
        self.assertEqual(completed.returncode,0,completed.stderr+completed.stdout)
        obj=json.loads(completed.stdout)
        self.assertEqual(obj['status'],'PASS_TESTED')
        self.assertNotIn(str(self.parent),completed.stdout)
        self.assertEqual(obj['output_manifest_sha256'],hashlib.sha256((self.output/'REUSE_MANIFEST.json').read_bytes()).hexdigest())

    def test_symlink_receipt_is_refused(self):
        target=self.parent/'protected.json'
        target.write_text('protected')
        try:
            self.receipt.symlink_to(target)
        except OSError:
            self.skipTest('symlink creation is unavailable on this OS')
        result=self.create(receipt=self.receipt)
        self.assertEqual(result['code'], 'receipt_already_exists')
        self.assertEqual(target.read_text(), 'protected')

    def test_no_dynamic_command_execution_from_generated_manifest(self):
        result=self.create(run_tests=False)
        self.assertEqual(result['status'], 'PASS_VERIFIED_ONLY')
        item=self.output/'REUSE_MANIFEST.json'
        doc=json.loads(item.read_text())
        marker=self.parent/'command-would-execute-marker'
        doc['tests_to_run_manually']=[f'python -c "open({str(marker)!r},\'w\').write(1)"']
        item.write_text(json.dumps(doc))
        # Even a freshly pinned malicious manifest cannot cause the high-level
        # pipeline to dynamically run it; accepted commands remain hardcoded.
        from verify_exported_starter import run_profiles
        rebound=hashlib.sha256(item.read_bytes()).hexdigest()
        verified=validate(self.output,rebound)
        run_profiles(self.output,verified)
        self.assertFalse(marker.exists())


if __name__=='__main__':
    unittest.main()
