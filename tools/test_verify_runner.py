"""Verifier CLI summary compatibility with tested Node versions."""
from __future__ import annotations
import subprocess
import sys
import unittest
from unittest.mock import patch
import verify


class SummaryTests(unittest.TestCase):
    def check(self, text: str, exit_code: int = 0):
        fake = subprocess.CompletedProcess(args=['node', '--test'], returncode=exit_code,
                                           stdout=text, stderr='')
        with patch.object(verify, 'execute', return_value=fake):
            return verify.test_result('sdk', ['node', '--test'], r'# tests (\d+)')

    def test_sdk_cli_forces_stable_tap_reporter_across_node_versions(self):
        """The actual CLI must not depend on locale/ANSI spec output."""
        compiled = subprocess.CompletedProcess(args=['tsc'], returncode=0, stdout='', stderr='')
        with (patch.object(sys, 'argv', ['verify.py', '--component', 'sdk']),
              patch.object(verify, 'version', side_effect=['v24.15.0', 'Version 5.9.3']),
              patch.object(verify.shutil, 'which', side_effect=lambda name: name),
              patch.object(verify, 'execute', return_value=compiled),
              patch.object(verify, 'test_result', return_value={'component': 'sdk', 'status': 'PASS', 'tests': 28}) as run):
            self.assertEqual(verify.main(), 0)
            argv = run.call_args.args[1]
            self.assertIn('--test-reporter=tap', argv)

    def test_node22_tap_summary_counts_only_successful_tests(self):
        result = self.check('# tests 28\n# pass 28\n# fail 0\n')
        self.assertEqual(result, {'component': 'sdk', 'status': 'PASS', 'tests': 28})

    def test_node24_spec_summary_counts_only_successful_tests(self):
        result = self.check('ℹ tests 28\nℹ pass 28\nℹ fail 0\n')
        self.assertEqual(result, {'component': 'sdk', 'status': 'PASS', 'tests': 28})

    def test_node24_reported_failure_is_not_silently_accepted(self):
        result = self.check('ℹ tests 28\nℹ pass 27\nℹ fail 1\n')
        self.assertEqual(result['status'], 'FAIL')

    def test_nonzero_exit_is_failure_even_when_summary_says_pass(self):
        result = self.check('ℹ tests 28\nℹ pass 28\nℹ fail 0\n', 1)
        self.assertEqual(result['status'], 'FAIL')

    def test_missing_or_zero_test_count_is_failure(self):
        self.assertEqual(self.check('ℹ tests 0\nℹ pass 0\nℹ fail 0\n')['status'], 'FAIL')
        self.assertEqual(self.check('just an arbitrary success message')['status'], 'FAIL')


if __name__ == '__main__':
    unittest.main()
