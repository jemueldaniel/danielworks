"""Real filesystem tests; never install dependencies or change a repository."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

MODULE_PATH = Path(__file__).with_name('verify_source.py')
V = None
if MODULE_PATH.is_file():
    spec = importlib.util.spec_from_file_location('verify_source', MODULE_PATH)
    V = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(V)

class SourceVerificationTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(V, 'Restored-source byte verification is not implemented')
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.payload = {'README.md': b'example\n', 'src/main.py': b'print(1)\n'}
        for name, data in self.payload.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.rows = [{'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
                     for name, data in self.payload.items()]
        self.write_manifest()

    def write_manifest(self, rows=None, **extra):
        data = {'schema': 1, 'files': self.rows if rows is None else rows, **extra}
        path = self.root / 'SOURCE_MANIFEST.json'
        path.write_text(json.dumps(data), encoding='utf-8')
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def rejected(self, code):
        with self.assertRaises(V.VerificationError) as caught:
            V.verify(self.root)
        self.assertEqual(caught.exception.code, code)

    def test_intact_inventory_is_verified_without_writing(self):
        before = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = V.verify(self.root)
        self.assertEqual(result['payload_files'], 2)
        self.assertEqual(result['total_files_including_manifest'], 3)
        self.assertEqual(result['manifest_authentication'], 'observed_only')
        self.assertEqual(before, {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_external_manifest_hash_is_checked(self):
        digest = self.write_manifest()
        self.assertEqual(V.verify(self.root, digest)['manifest_authentication'], 'external_hash_matched')
        with self.assertRaises(V.VerificationError) as caught:
            V.verify(self.root, '0' * 64)
        self.assertEqual(caught.exception.code, 'manifest_hash_mismatch')

    def test_tampered_equal_size_content_fails(self):
        (self.root / 'src/main.py').write_bytes(b'print(2)\n')
        self.rejected('file_hash_mismatch')

    def test_missing_source_fails(self):
        (self.root / 'src/main.py').unlink()
        self.rejected('inventory_mismatch')

    def test_unexpected_source_fails(self):
        (self.root / 'unreviewed.py').write_text('x=1')
        self.rejected('inventory_mismatch')

    def test_generated_files_are_not_silently_ignored(self):
        (self.root / 'node_modules').mkdir()
        (self.root / 'node_modules/cache').write_text('generated')
        self.rejected('inventory_mismatch')

    def test_top_level_regular_git_metadata_is_excluded(self):
        (self.root / '.git').mkdir()
        (self.root / '.git/config').write_text('private metadata not inspected')
        self.assertEqual(V.verify(self.root)['excluded_metadata'], ['.git'])

    def test_metadata_cannot_be_claimed_as_public_source(self):
        self.rows[0]['path'] = '.git/config'
        self.write_manifest()
        self.rejected('unsafe_path')

    def test_manifest_self_entry_is_rejected(self):
        self.rows[0]['path'] = 'SOURCE_MANIFEST.json'
        self.write_manifest()
        self.rejected('self_manifest_entry')

    def test_traversal_absolute_and_noncanonical_paths_are_rejected(self):
        for path in ['../leak', '/absolute', 'C:/leak', 'a\\b', 'a//b', 'a/./b', 'a/../b']:
            with self.subTest(path=path):
                self.rows[0]['path'] = path
                self.write_manifest()
                self.rejected('unsafe_path')

    def test_nonportable_names_are_rejected(self):
        for path in ['a.', 'a ', 'NUL.txt', 'x/COM1', 'a\x00b', 'folder/aux.py']:
            with self.subTest(path=path):
                self.rows[0]['path'] = path
                self.write_manifest()
                self.rejected('unsafe_path')

    def test_duplicate_paths_are_rejected(self):
        self.write_manifest(self.rows + [self.rows[0]])
        self.rejected('path_collision')

    def test_case_collisions_are_rejected(self):
        row = {**self.rows[0], 'path': 'readme.MD'}
        self.write_manifest(self.rows + [row])
        self.rejected('path_collision')

    def test_parent_file_conflicts_are_rejected(self):
        self.rows[1]['path'] = 'README.md/child'
        self.write_manifest()
        self.rejected('path_collision')

    def test_duplicate_json_keys_are_rejected(self):
        (self.root / 'SOURCE_MANIFEST.json').write_text('{"schema":1,"schema":1,"files":[]}')
        self.rejected('duplicate_json_key')

    def test_invalid_json_is_rejected(self):
        (self.root / 'SOURCE_MANIFEST.json').write_text('{broken')
        self.rejected('invalid_manifest')

    def test_invalid_sizes_and_hashes_are_rejected(self):
        for field, value in [('bytes', True), ('bytes', -1), ('bytes', 1.5), ('sha256', 'bad'), ('sha256', 'A'*64)]:
            with self.subTest(field=field, value=value):
                rows = [dict(row) for row in self.rows]
                rows[0][field] = value
                self.write_manifest(rows)
                self.rejected('invalid_manifest')

    def test_manifest_input_has_a_byte_limit(self):
        (self.root / 'SOURCE_MANIFEST.json').write_bytes(b' ' * (V.MAX_MANIFEST_BYTES + 1))
        self.rejected('resource_limit')

    def test_declared_source_file_has_a_byte_limit(self):
        self.rows[0]['bytes'] = V.MAX_FILE_BYTES + 1
        self.write_manifest()
        self.rejected('resource_limit')

    def test_manifest_count_and_payload_metadata_are_checked(self):
        for extra in [{'inventory_file_count': 7}, {'complete_checkpoint_file_count_including_this_manifest': 8},
                      {'payload_bytes_excluding_this_manifest': 0}, {'payload_path_sha256_binding': '0'*64}]:
            with self.subTest(extra=extra):
                self.write_manifest(**extra)
                self.rejected('manifest_metadata_mismatch')

    def test_file_size_mismatch_is_explicit(self):
        (self.root / 'README.md').write_bytes(b'new-size')
        self.rows[0]['bytes'] = 1
        self.write_manifest()
        self.rejected('file_size_mismatch')

    def test_symbolic_file_is_rejected(self):
        link = self.root / 'src/main.py'
        link.unlink()
        try:
            link.symlink_to(self.root / 'README.md')
        except OSError as error:
            self.skipTest('OS does not admit symbolic-link creation: ' + str(error.errno))
        self.rejected('nonregular_file')

    def test_symbolic_directory_is_rejected(self):
        (self.root / 'src/main.py').unlink()
        (self.root / 'src').rmdir()
        try:
            (self.root / 'src').symlink_to(self.root, target_is_directory=True)
        except OSError as error:
            self.skipTest('OS does not admit symbolic-link creation: ' + str(error.errno))
        self.rejected('nonregular_file')

    @unittest.skipUnless(os.name == 'nt', 'Windows NTFS junction case; Linux symlinks have separate tests')
    def test_windows_directory_junction_is_rejected(self):
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        target = Path(outside.name)
        (target / 'main.py').write_bytes(self.payload['src/main.py'])
        (self.root / 'src/main.py').unlink()
        (self.root / 'src').rmdir()
        result = subprocess.run(['cmd.exe', '/c', 'mklink', '/J', str(self.root / 'src'), str(target)],
                                capture_output=True, text=True, timeout=5)
        if result.returncode:
            self.skipTest('OS did not admit a disposable NTFS junction')
        self.addCleanup(lambda: (self.root / 'src').rmdir())
        self.rejected('nonregular_file')

    def test_declared_modes_are_not_claimed_verified_on_windows(self):
        for row in self.rows:
            row['mode'] = '100644'
        self.write_manifest()
        result = V.verify(self.root)
        self.assertEqual(result['mode_verification'], 'not_supported_on_windows' if os.name == 'nt' else 'verified')

    def test_partial_mode_coverage_is_reported_as_partial(self):
        self.rows[0]['mode'] = '100644'
        self.write_manifest()
        result = V.verify(self.root)
        self.assertEqual(result.get('mode_entries_declared'), 1)
        self.assertEqual(result.get('mode_entries_checked'), 0 if os.name == 'nt' else 1)
        self.assertEqual(result['mode_verification'], 'not_supported_on_windows' if os.name == 'nt' else 'partially_verified')

    @unittest.skipIf(os.name == 'nt', 'POSIX executable-bit test; not Windows qualification')
    def test_executable_mode_mismatch_is_rejected(self):
        self.rows[0]['mode'] = '100755'
        self.write_manifest()
        (self.root / 'README.md').chmod(0o644)
        self.rejected('file_mode_mismatch')

    def test_cli_reports_json_failure_without_traceback_or_writes(self):
        (self.root / 'README.md').write_text('changed')
        result = subprocess.run([sys.executable, '-B', str(MODULE_PATH), '--root', str(self.root)], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)['status'], 'FAIL')
        self.assertEqual(result.stderr, '')

if __name__ == '__main__':
    unittest.main()
