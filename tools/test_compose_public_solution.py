"""No private source and no manifest-provided arbitrary commands in public recipes."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from compose_public_solution import RECIPES, compose, select_recipe
from export_public_starter import STARTERS

ROOT = Path(__file__).resolve().parents[1]
PIN = hashlib.sha256((ROOT / "SOURCE_MANIFEST.json").read_bytes()).hexdigest()


class RecipeTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(prefix="public-recipe-")
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.dest = self.root / "starter"
        self.receipt = self.root / "receipt.json"

    def test_recipes_contain_only_prequalified_public_profiles(self):
        self.assertEqual(set(RECIPES), {"ai-search","service-foundation","event-platform","workflow-engine","full-reference"})
        for name in RECIPES:
            selected = select_recipe(name)
            self.assertEqual(len(selected), len(set(selected)))
            self.assertTrue(all(STARTERS[p].qualification == "executed" for p in selected))

    def test_unknown_recipe_rejected_without_side_effects(self):
        for bad in ("../private", "payments-prod", "", 17, "SERVICE-FOUNDATION"):
            with self.subTest(recipe=bad):
                result = compose(ROOT, PIN, bad, self.dest)
                self.assertEqual(result["status"], "FAIL")
                self.assertEqual(result["code"], "unknown_public_recipe")
                self.assertFalse(self.dest.exists())

    def test_dry_run_never_creates_output(self):
        result = compose(ROOT, PIN, "service-foundation", self.dest, dry_run=True)
        self.assertEqual(result["status"], "DRY_RUN")
        self.assertEqual(result["tested_groups"], 0)
        self.assertEqual(result["recipe"], "service-foundation")
        self.assertFalse(self.dest.exists())

    def test_bad_source_pin_prevents_any_file_copy(self):
        result = compose(ROOT, "0"*64, "service-foundation", self.dest)
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(self.dest.exists())

    def test_no_tests_does_not_claim_execution(self):
        result = compose(ROOT, PIN, "service-foundation", self.dest, run_tests=False)
        self.assertEqual(result["status"], "PASS_VERIFIED_ONLY", result)
        self.assertEqual(result["tested_groups"], 0)
        self.assertTrue(result["posttest_bytes_verified"])

    def test_ai_search_recipe_tests_actual_hybrid_fts5(self):
        result = compose(ROOT, PIN, "ai-search", self.dest, receipt=self.receipt)
        self.assertEqual(result['status'], 'PASS_TESTED', result)
        self.assertEqual(result['tested_groups'], 5)
        self.assertTrue((self.dest / 'examples/hybrid_search/hybrid.py').is_file())
        self.assertTrue(result['posttest_bytes_verified'])
        self.assertEqual(json.loads(self.receipt.read_text())['tested_groups'], 5)

    def test_workflow_engine_recipe_runs_four_original_components(self):
        result = compose(ROOT, PIN, "workflow-engine", self.dest, receipt=self.receipt)
        self.assertEqual(result['status'], 'PASS_TESTED', result)
        self.assertEqual(result['tested_groups'], 4)
        self.assertEqual(result['profiles'], ['build-graph', 'event-outbox', 'jobs', 'policy'])
        self.assertTrue(result['posttest_bytes_verified'])
        self.assertTrue((self.dest / 'examples/build_graph/graph.py').is_file())
        self.assertEqual(json.loads(self.receipt.read_text())['tested_groups'], 4)

    def test_real_service_recipe_exports_and_executes_all_four_groups(self):
        result = compose(ROOT, PIN, "service-foundation", self.dest, receipt=self.receipt)
        self.assertEqual(result["status"], "PASS_TESTED", result)
        self.assertEqual(result["tested_groups"], 4)
        self.assertEqual(result["profiles"], ["jobs", "ledger", "migration", "policy"])
        self.assertTrue(result["posttest_bytes_verified"])
        self.assertTrue((self.dest / "examples/atomic_ledger/ledger.py").exists())
        receipt = json.loads(self.receipt.read_text("utf-8"))
        self.assertEqual(receipt["status"], "PASS_TESTED")
        self.assertNotIn("recipe", receipt)
        self.assertEqual(receipt["output_manifest_sha256"], result["output_manifest_sha256"])

    def test_preexisting_output_never_overwritten(self):
        self.dest.mkdir()
        original = self.dest / "keep.txt"
        original.write_text("keep this content")
        result = compose(ROOT, PIN, "service-foundation", self.dest)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(original.read_text(), "keep this content")

    def test_preexisting_receipt_never_overwritten(self):
        self.receipt.write_text("original-receipt")
        result = compose(ROOT, PIN, "service-foundation", self.dest, receipt=self.receipt)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(self.receipt.read_text(), "original-receipt")
        self.assertFalse(self.dest.exists())

    def test_no_public_profile_can_be_replaced_by_private_source(self):
        modified=dict(RECIPES)
        try:
            with patch.dict(RECIPES, {"service-foundation":("jobs","some-private-module")}, clear=False):
                with self.assertRaisesRegex(ValueError, "unqualified_public_recipe"):
                    select_recipe("service-foundation")
        finally:
            self.assertEqual(RECIPES, modified)

    def test_cli_returns_receipt_and_acceptance(self):
        p = subprocess.run(
            [sys.executable, "-B", str(ROOT/"tools/compose_public_solution.py"),
             "--expected-source-sha256", PIN, "--root", str(ROOT),
             "--recipe", "service-foundation", "--destination", str(self.dest),
             "--receipt", str(self.receipt)],
            capture_output=True, text=True, timeout=120, check=False,
        )
        self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
        result=json.loads(p.stdout)
        self.assertEqual(result["tested_groups"], 4)
        self.assertTrue(result["posttest_bytes_verified"])


if __name__ == "__main__":
    unittest.main()
