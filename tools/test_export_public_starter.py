"""Reproducible portable starter exporter — source integrity, non-overwrite and clear evidence scope."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from export_public_starter import StarterError, STARTERS, export_public_starter

SOURCE = Path(__file__).resolve().parents[1]
# Unit tests establish local consistency; actual CLI use requires an EXTERNAL pin.
PIN = hashlib.sha256((SOURCE / 'SOURCE_MANIFEST.json').read_bytes()).hexdigest()


class PublicStarterTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.folder = Path(self.td.name)
        self.target = self.folder/'portable-kit'

    def build(self, profiles=None, **kwargs):
        return export_public_starter(SOURCE, PIN, profiles or ['agent'], self.target, **kwargs)

    def test_dry_run_stays_read_only(self):
        result = self.build(dry_run=True)
        self.assertEqual(result['status'], 'DRY_RUN')
        self.assertEqual(result['selected_files'], 3)
        self.assertEqual(result['tests_executed'], 0)
        self.assertFalse(self.target.exists())

    def test_exact_git_independent_source_bytes_are_copied(self):
        result = self.build()
        self.assertEqual(result['status'], 'EXPORTED')
        self.assertEqual(result['selected_files'], 3)
        for name in STARTERS['agent'].paths:
            self.assertEqual((self.target/name).read_bytes(), (SOURCE/name).read_bytes())
        self.assertFalse((self.target/'.git').exists())

    def test_output_manifest_binds_every_byte_and_disclaims_testing(self):
        report = self.build()
        raw = (self.target/'REUSE_MANIFEST.json').read_bytes()
        self.assertEqual(report['output_manifest_sha256'], hashlib.sha256(raw).hexdigest())
        manifest = json.loads(raw)
        self.assertEqual(manifest['externally_pinned_source_manifest_sha256'],PIN)
        self.assertEqual(manifest['tests_executed_by_generator'],0)
        for row in manifest['files']:
            data = (self.target/row['path']).read_bytes()
            self.assertEqual(row['bytes'],len(data))
            self.assertEqual(row['sha256'],hashlib.sha256(data).hexdigest())
        self.assertNotIn('private', [p['path'] for p in manifest['files']])

    def test_generated_readme_has_reproducible_command_and_boundary(self):
        self.build()
        doc = (self.target/'README.md').read_text('utf-8')
        self.assertIn('node --test --test-reporter=tap examples/mcp_agent/test_runtime.mjs',doc)
        self.assertIn('not a production-ready service', (self.target/'REUSE_MANIFEST.json').read_text('utf-8'))
        self.assertNotIn('deploy automatically',doc)

    def test_multiple_executed_profiles_copy_only_public_files(self):
        result = self.build(['agent','training','jobs','retrieval','evaluation'])
        self.assertEqual(result['profiles'], sorted(result['profiles']))
        allowed = set().union(*(set(STARTERS[n].paths) for n in result['profiles']))
        copied = {p.relative_to(self.target).as_posix() for p in self.target.rglob('*') if p.is_file()}
        self.assertEqual(copied, allowed | {'README.md','REUSE_MANIFEST.json'})
        self.assertTrue(all('private' not in name.lower() for name in copied))

    def test_new_policy_profile_exports_only_original_public_source(self):
        result = self.build(['policy'])
        self.assertEqual(result['profiles'], ['policy'])
        self.assertEqual(result['selected_files'], 4)
        paths = set(STARTERS['policy'].paths)
        files = {p.relative_to(self.target).as_posix()
                 for p in self.target.rglob('*') if p.is_file()}
        self.assertEqual(files, paths | {'README.md', 'REUSE_MANIFEST.json'})

    def test_ledger_starter_exports_only_allowlisted_public_source(self):
        report = self.build(['ledger'])
        self.assertEqual(report['selected_files'], 4)
        wanted = set(STARTERS['ledger'].paths)
        actual = {p.relative_to(self.target).as_posix() for p in self.target.rglob('*')
                  if p.is_file()}
        self.assertEqual(actual, wanted | {'README.md', 'REUSE_MANIFEST.json'})

    def test_hybrid_search_profile_exports_only_original_public_source(self):
        result = self.build(['hybrid-search'])
        self.assertEqual(result['selected_files'], 4)
        expected = set(STARTERS['hybrid-search'].paths)
        found = {p.relative_to(self.target).as_posix()
                 for p in self.target.rglob('*') if p.is_file()}
        self.assertEqual(found, expected | {'README.md','REUSE_MANIFEST.json'})

    def test_migration_starter_contains_only_four_original_public_files(self):
        report = self.build(['migration'])
        self.assertEqual(report['selected_files'], 4)
        expected=set(STARTERS['migration'].paths)
        found={p.relative_to(self.target).as_posix()
               for p in self.target.rglob('*') if p.is_file()}
        self.assertEqual(found, expected | {'README.md','REUSE_MANIFEST.json'})

    def test_graph_starter_contains_only_public_allowlisted_files(self):
        result = self.build(['build-graph'])
        self.assertEqual(result['selected_files'], 4)
        approved=set(STARTERS['build-graph'].paths)
        actual={p.relative_to(self.target).as_posix()
                for p in self.target.rglob('*') if p.is_file()}
        self.assertEqual(actual, approved | {'README.md','REUSE_MANIFEST.json'})

    def test_signed_api_bundle_exports_only_public_allowlisted_files(self):
        report = self.build(['signed-api'])
        self.assertEqual(report['selected_files'], 4)
        approved = set(STARTERS['signed-api'].paths)
        actual = {p.relative_to(self.target).as_posix()
                  for p in self.target.rglob('*') if p.is_file()}
        self.assertEqual(actual, approved | {'README.md','REUSE_MANIFEST.json'})

    def test_ui_starter_exports_only_six_original_public_files(self):
        result = self.build(['interface-lab'])
        self.assertEqual(result['selected_files'], 6)
        expected = set(STARTERS['interface-lab'].paths)
        found = {p.relative_to(self.target).as_posix()
                 for p in self.target.rglob('*') if p.is_file()}
        self.assertEqual(found, expected | {'README.md','REUSE_MANIFEST.json'})

    def test_ui_atlas_public_source_profile_contains_six_fixed_allowlisted_files(self):
        result = self.build(['ui-atlas'])
        self.assertEqual(result['selected_files'], 6)
        desired = set(STARTERS['ui-atlas'].paths)
        observed = {p.relative_to(self.target).as_posix()
                    for p in self.target.rglob('*') if p.is_file()}
        self.assertEqual(observed, desired | {'README.md','REUSE_MANIFEST.json'})

    def test_flow_lab_exports_exact_six_original_public_files(self):
        result = self.build(['flow-lab'])
        self.assertEqual(result['selected_files'], 6)
        expected = set(STARTERS['flow-lab'].paths)
        self.assertEqual(
            {p.relative_to(self.target).as_posix() for p in self.target.rglob('*') if p.is_file()},
            expected | {'README.md', 'REUSE_MANIFEST.json'},
        )
        self.assertEqual(result['tests_executed'], 0)

    def test_new_visual_analytics_profile_exports_six_public_files(self):
        result = self.build(['data-studio'])
        self.assertEqual(result['selected_files'], 6)
        expected=set(STARTERS['data-studio'].paths)
        actual={p.relative_to(self.target).as_posix() for p in self.target.rglob('*') if p.is_file()}
        self.assertEqual(actual, expected | {'README.md', 'REUSE_MANIFEST.json'})
        self.assertEqual(result['tests_executed'], 0)

    def test_cannot_duplicate_profile(self):
        with self.assertRaisesRegex(StarterError, 'duplicate_profile'):
            self.build(['agent','agent'])
        self.assertFalse(self.target.exists())

    def test_cannot_select_unknown_or_unverified_capability(self):
        for name in ['production-evm','../../secrets','root', 'private-profile', '']:
            with self.subTest(name=name):
                with self.assertRaisesRegex(StarterError, 'unknown_profile'):
                    self.build([name])
        self.assertFalse(self.target.exists())

    def test_historical_profile_requires_explicit_opt_in(self):
        with self.assertRaisesRegex(StarterError, 'explicit_historical_opt_in_required'):
            self.build(['rust-compiler'])
        self.assertFalse(self.target.exists())

    def test_opt_in_does_not_upgrade_historical_to_executed(self):
        self.build(['rust-compiler'],allow_historical=True)
        m=json.loads((self.target/'REUSE_MANIFEST.json').read_bytes())
        self.assertEqual(m['profile_qualification']['rust-compiler'],'historical')
        self.assertIn('historical evidence',(self.target/'README.md').read_text('utf-8'))

    def test_existing_directory_is_not_merged_or_overwritten(self):
        self.target.mkdir()
        (self.target/'keep.txt').write_text('unchanged')
        with self.assertRaisesRegex(StarterError,'destination_already_exists'):
            self.build()
        self.assertEqual((self.target/'keep.txt').read_text(),'unchanged')

    def test_existing_file_is_not_overwritten(self):
        self.target.write_text('client data')
        with self.assertRaisesRegex(StarterError,'destination_already_exists'):
            self.build()
        self.assertEqual(self.target.read_text(),'client data')

    def test_destination_symlink_is_rejected(self):
        try:
            self.target.symlink_to(self.folder, target_is_directory=True)
        except OSError as e:
            if os.name == 'nt' and getattr(e, 'winerror', None) == 1314:
                self.skipTest('Windows symlink creation privilege is unavailable')
            raise
        with self.assertRaisesRegex(StarterError,'destination_already_exists'):
            self.build()

    def test_cannot_generate_inside_source_checkout(self):
        dest = SOURCE/'untracked-deployment-folder'
        with self.assertRaisesRegex(StarterError,'destination_inside_source'):
            export_public_starter(SOURCE,PIN,['agent'],dest)
        self.assertFalse(dest.exists())

    def test_externally_pinned_manifest_is_mandatory(self):
        for pin in ['', '0'*64, '../manifest.json', 'xyz']:
            with self.subTest(pin=pin):
                with self.assertRaises(StarterError):
                    export_public_starter(SOURCE,pin,['agent'],self.target)
        self.assertFalse(self.target.exists())

    def test_rejects_tampered_source_byte_before_any_copy(self):
        clone = self.folder/'snapshot'
        shutil.copytree(SOURCE, clone)
        f=clone/'examples/mcp_agent/runtime.mjs'
        f.write_bytes(f.read_bytes()+b'\n// unauthorized source change\n')
        with self.assertRaisesRegex(StarterError,'unverified_public_source'):
            export_public_starter(clone,PIN,['agent'],self.target)
        self.assertFalse(self.target.exists())

    def test_rejects_symlink_source_without_following(self):
        clone=self.folder/'snapshot'
        shutil.copytree(SOURCE, clone)
        f=clone/'examples/mcp_agent/runtime.mjs'
        f.unlink()
        try:
            f.symlink_to(self.folder/'other-source')
        except OSError as e:
            if os.name == 'nt' and getattr(e, 'winerror', None) == 1314:
                self.skipTest('Windows symlink creation privilege is unavailable')
            raise
        with self.assertRaisesRegex(StarterError,'unverified_public_source'):
            export_public_starter(clone,PIN,['agent'],self.target)
        self.assertFalse(self.target.exists())

    def test_rejects_missing_pinned_manifest(self):
        clone=self.folder/'snapshot'
        shutil.copytree(SOURCE, clone)
        (clone/'SOURCE_MANIFEST.json').unlink()
        with self.assertRaisesRegex(StarterError,'unverified_public_source'):
            export_public_starter(clone,PIN,['agent'],self.target)
        self.assertFalse(self.target.exists())

    def test_readme_and_manifest_reproducible_for_same_inputs(self):
        self.build(['training','agent'])
        target2=self.folder/'second-kit'
        export_public_starter(SOURCE,PIN,['agent','training'],target2)
        self.assertEqual((self.target/'README.md').read_bytes(),(target2/'README.md').read_bytes())
        self.assertEqual((self.target/'REUSE_MANIFEST.json').read_bytes(),(target2/'REUSE_MANIFEST.json').read_bytes())

    def test_generated_agent_runtime_still_passes_actual_tests(self):
        self.build()
        result=subprocess.run(['node','--test','--test-reporter=tap','examples/mcp_agent/test_runtime.mjs'],
            cwd=self.target,capture_output=True,text=True,timeout=25)
        self.assertEqual(result.returncode,0,(result.stdout+result.stderr)[-1000:])
        self.assertIn('# tests 27', result.stdout.splitlines())
        self.assertIn('# pass 27', result.stdout.splitlines())
        self.assertIn('# fail 0', result.stdout.splitlines())

    def test_generated_training_code_still_trains_against_synthetic_data(self):
        self.build(['training'])
        result=subprocess.run([sys.executable,'-B','-m','unittest','discover',
             '-s','examples/synthetic_training','-v'], cwd=self.target,
             capture_output=True,text=True,timeout=25)
        self.assertEqual(result.returncode,0,(result.stdout+result.stderr)[-1500:])
        self.assertIn('OK',result.stdout+result.stderr)

    def test_cli_invalid_request_is_nonzero_and_does_not_create_target(self):
        # This test exercises the actual published-style CLI on a copy that has
        # the new file installed, while the root remains the immutable published checkout.
        q=subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('export_public_starter.py')),
                          '--root',str(SOURCE),'--expected-manifest-sha256',PIN,
                          '--profile','unverified','--destination',str(self.target)],
                          capture_output=True,text=True,timeout=25)
        self.assertNotEqual(q.returncode,0)
        self.assertEqual(json.loads(q.stdout)['status'],'FAIL')
        self.assertFalse(self.target.exists())


if __name__=='__main__':
    unittest.main()
