"""Fail-closed public-capability evidence validation: metadata is not test execution."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import unittest

from verify_public_capabilities import ClaimError, validate_index
from verify_source import _pairs, VerificationError

ROOT = Path(__file__).resolve().parents[1]


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'docs/PUBLIC_CAPABILITIES.json').read_text('utf-8'))
        self.paths = {p.as_posix().removeprefix(ROOT.as_posix() + '/') for p in ROOT.rglob('*') if p.is_file()}

    def test_all_public_entries_structurally_bind_to_actual_paths(self):
        result = validate_index(self.data, self.paths)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['claims'], 28)
        self.assertIn('signed-event-delivery', {c['id'] for c in self.data['claims']})
        self.assertEqual(result['runtime_tests_executed_by_this_command'], 0)
        self.assertEqual(result['qualifications']['not_verified'], 3)

    def test_one_shot_claim_links_only_published_public_source_and_tests(self):
        claim = next(c for c in self.data['claims'] if c['id'] == 'one-shot-public-project')
        self.assertEqual(claim['qualification'], 'executed')
        self.assertIn('tools/one_shot_public_project.py', claim['implementation'])
        self.assertIn('tools/test_one_shot_public_project.py', claim['tests'])
        self.assertEqual(validate_index(self.data, self.paths)['status'], 'PASS')

    def test_duplicate_claim_id_rejected(self):
        self.data['claims'][1]['id'] = self.data['claims'][0]['id']
        with self.assertRaisesRegex(ClaimError, 'invalid_or_duplicate_id'):
            validate_index(self.data, self.paths)

    def test_missing_public_source_reference_rejected(self):
        self.data['claims'][0]['implementation'].append('examples/never_created/source.py')
        with self.assertRaisesRegex(ClaimError, 'unpublished_or_excluded_path'):
            validate_index(self.data, self.paths)

    def test_private_or_sensitive_paths_cannot_be_claimed(self):
        for bad in ['../secret.txt', 'D:/someone/private.py', '/absolute/private.py',
                    'node_modules/index.js', 'secrets/source.py', 'public/../../x.py']:
            with self.subTest(path=bad):
                data = copy.deepcopy(self.data)
                data['claims'][0]['implementation'].append(bad)
                with self.assertRaises(ClaimError):
                    validate_index(data, self.paths | {bad})

    def test_rejects_missing_test_entrypoints_for_executed_claim(self):
        self.data['claims'][0]['tests'] = []
        with self.assertRaisesRegex(ClaimError, 'missing_test_entrypoints'):
            validate_index(self.data, self.paths)

    def test_unverified_capability_cannot_claim_implementation(self):
        next(c for c in self.data['claims'] if c['qualification'] == 'not_verified')['implementation'] = ['examples/durable_jobs/jobs.py']
        with self.assertRaisesRegex(ClaimError, 'unverified_claim_has_public_proof'):
            validate_index(self.data, self.paths)

    def test_rejects_embedded_external_private_provenance(self):
        for private in ['contact: hidden.person' + '@' + 'example.com', 'private: https://example.net',
                        'machine: C:\\Users\\Person\\repo', 'key: ' + 'gh' + 'p_' + 'A' * 20]:
            with self.subTest(private=private):
                data = copy.deepcopy(self.data)
                data['claims'][0]['boundary'] = 'Information not suitable for publication: ' + private
                with self.assertRaisesRegex(ClaimError, 'external_or_sensitive_reference'):
                    validate_index(data, self.paths)

    def test_duplicate_path_within_one_claim_rejected(self):
        self.data['claims'][0]['tests'].append(self.data['claims'][0]['implementation'][0])
        with self.assertRaisesRegex(ClaimError, 'duplicate_claim_path'):
            validate_index(self.data, self.paths)

    def test_invalid_status_and_unknown_schema_are_rejected(self):
        self.data['claims'][0]['qualification'] = 'production-certified'
        with self.assertRaisesRegex(ClaimError, 'invalid_qualification'):
            validate_index(self.data, self.paths)
        self.data['claims'][0]['qualification'] = 'executed'
        self.data['hidden'] = 'undocumented extra field'
        with self.assertRaisesRegex(ClaimError, 'invalid_index_schema'):
            validate_index(self.data, self.paths)

    def test_malformed_nonstring_status_fails_closed(self):
        self.data['claims'][0]['qualification'] = ['executed']
        with self.assertRaisesRegex(ClaimError, 'invalid_qualification'):
            validate_index(self.data, self.paths)

    def test_purpose_cannot_embed_private_addresses(self):
        self.data['purpose'] = 'Private owner link: https://example.org/internal'
        with self.assertRaisesRegex(ClaimError, 'external_or_sensitive_reference'):
            validate_index(self.data, self.paths)

    def test_duplicate_json_keys_fail_closed(self):
        with self.assertRaises(VerificationError):
            json.loads('{"schema":1,"schema":2}', object_pairs_hook=_pairs)

    def test_file_reference_does_not_claim_tests_were_run(self):
        self.data['claims'][0]['qualification'] = 'source_only'
        res = validate_index(self.data, self.paths)
        self.assertEqual(res['runtime_tests_executed_by_this_command'], 0)
        self.assertEqual(res['qualifications']['source_only'], 1)


if __name__ == '__main__':
    unittest.main()
