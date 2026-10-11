"""Offline Git-object verification: real local commits, no network or push."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from verify_git_commit import verify, GitVerificationError


class GitCommitVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git('init', '-q', '-b', 'main')
        self._make_source(b'hello\n')

    def git(self, *args: str, input_data: bytes | None = None) -> str:
        result = subprocess.run(['git', '-C', str(self.root), *args], input=input_data,
                                capture_output=True, check=True, timeout=6)
        return result.stdout.decode().strip()

    def _commit(self):
        self.git('add', '-A')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture.invalid',
                 'commit', '--quiet', '-m', 'test fixture')
        return self.git('rev-parse', 'HEAD')

    def _make_source(self, readme: bytes):
        (self.root / 'README.md').write_bytes(readme)
        sha = hashlib.sha256(readme).hexdigest()
        manifest = {'schema': 1, 'files': [{'path': 'README.md', 'mode': '100644',
                                            'bytes': len(readme), 'sha256': sha}],
                    'inventory_file_count': 1, 'complete_checkpoint_file_count_including_this_manifest': 2,
                    'payload_bytes_excluding_this_manifest': len(readme),
                    'payload_path_sha256_binding': hashlib.sha256(
                        json.dumps({'README.md': sha}, separators=(',', ':'), sort_keys=True).encode()).hexdigest()}
        raw = (json.dumps(manifest, indent=2) + '\n').encode()
        (self.root / 'SOURCE_MANIFEST.json').write_bytes(raw)
        self.pin = hashlib.sha256(raw).hexdigest()
        self.sha = self._commit()

    def test_fresh_commit_has_exact_git_blob_inventory(self):
        report = verify(self.root, revision=self.sha, expected_manifest_sha256=self.pin)
        self.assertEqual(report['status'], 'PASS')
        self.assertEqual(report['tree_files'], 2)
        self.assertEqual(report['commit'], self.sha)
        self.assertTrue(report['working_tree_clean'])
        self.assertEqual(report['manifest_sha256'], self.pin)

    def test_git_blob_verification_is_distinct_from_changed_working_file(self):
        (self.root / 'README.md').write_bytes(b'changed on disk\n')
        report = verify(self.root, revision=self.sha, expected_manifest_sha256=self.pin)
        self.assertEqual(report['status'], 'PASS')
        self.assertFalse(report['working_tree_clean'])
        self.assertFalse(report['filesystem_bytes_verified'])

    def test_rejects_manifest_pin_mismatch(self):
        with self.assertRaises(GitVerificationError) as ctx:
            verify(self.root, revision=self.sha, expected_manifest_sha256='0' * 64)
        self.assertEqual(str(ctx.exception), 'manifest_hash_mismatch')

    def test_rejects_content_changed_without_updated_manifest(self):
        (self.root / 'README.md').write_bytes(b'tampered\n')
        new_commit = self._commit()
        with self.assertRaises(GitVerificationError) as ctx:
            verify(self.root, revision=new_commit, expected_manifest_sha256=self.pin)
        self.assertEqual(str(ctx.exception), 'file_size_mismatch')

    def test_rejects_unlisted_git_tree_entries(self):
        (self.root / 'EXTRA.txt').write_bytes(b'not in manifest\n')
        new_commit = self._commit()
        with self.assertRaises(GitVerificationError) as ctx:
            verify(self.root, revision=new_commit, expected_manifest_sha256=self.pin)
        self.assertEqual(str(ctx.exception), 'inventory_mismatch')

    def test_rejects_git_symlink_mode_without_materializing_it(self):
        oid = self.git('hash-object', '-w', '--stdin', input_data=b'README.md')
        self.git('update-index', '--add', '--cacheinfo', f'120000,{oid},BAD-LINK')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture.invalid',
                 'commit', '--quiet', '-m', 'link fixture')
        with self.assertRaises(GitVerificationError) as ctx:
            verify(self.root, revision=self.git('rev-parse', 'HEAD'), expected_manifest_sha256=self.pin)
        self.assertEqual(str(ctx.exception), 'nonregular_git_entry')

    def test_missing_committed_manifest_is_not_restored_from_worktree(self):
        (self.root / 'SOURCE_MANIFEST.json').unlink()
        new_commit = self._commit()
        with self.assertRaises(GitVerificationError) as ctx:
            verify(self.root, revision=new_commit, expected_manifest_sha256=self.pin)
        self.assertEqual(str(ctx.exception), 'missing_manifest')

    def test_rejects_case_collisions_in_git_tree(self):
        oid = self.git('hash-object', '-w', '--stdin', input_data=b'another readme')
        self.git('update-index', '--add', '--cacheinfo', f'100644,{oid},readme.md')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture.invalid',
                 'commit', '--quiet', '-m', 'case collision fixture')
        with self.assertRaises(GitVerificationError) as ctx:
            verify(self.root, revision=self.git('rev-parse', 'HEAD'), expected_manifest_sha256=self.pin)
        self.assertEqual(str(ctx.exception), 'invalid_git_tree')

    def test_disallows_ref_option_injection_and_unknown_revisions(self):
        with self.assertRaises(GitVerificationError) as ctx:
            verify(self.root, revision='--upload-pack=malicious', expected_manifest_sha256=self.pin)
        self.assertEqual(str(ctx.exception), 'invalid_revision')
        with self.assertRaises(GitVerificationError) as ctx:
            verify(self.root, revision='f' * 40, expected_manifest_sha256=self.pin)
        self.assertEqual(str(ctx.exception), 'git_unavailable')


if __name__ == '__main__':
    unittest.main()
