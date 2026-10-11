"""Independent deterministic negative/positive regression tests, no external service."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import diagnose_public_profiles as module
from diagnose_public_profiles import diagnose
from verify_exported_starter import ProofError

PIN = hashlib.sha256(b"synthetic-public-export-manifest").hexdigest()


class DiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.parent = Path(self.t.name)
        self.kit = self.parent / "kit"
        self.kit.mkdir()
        self.receipt = self.parent / "proof.json"
        self.document = {
            "status": "PASS", "manifest_sha256": PIN,
            "source_manifest_sha256": "a"*64,
            "files": 7, "profiles": ["agent", "event-outbox"],
            "qualifications": {"agent": "executed", "event-outbox": "historical"},
        }
        self.gate = patch.object(module, "validate", return_value=self.document)
        self.gate.start()
        self.addCleanup(self.gate.stop)

    def runner(self, root, verified, **kw):
        name = verified["profiles"][0]
        return {"status": "PASS", "tests_run": 1,
                "groups": [{"profile":name,"status":"PASS","qualification": verified["qualifications"][name]}]}

    def test_two_rounds_record_all_four_passes_and_retain_historical(self):
        result = diagnose(self.kit,PIN,rounds=2,runner=self.runner,receipt=self.receipt)
        self.assertEqual(result["status"],"PASS_REPEATED")
        self.assertEqual(result["tests_passed"],4)
        self.assertEqual(result["failures"],0)
        self.assertTrue(result["posttest_bytes_verified"])
        self.assertFalse(result["historical_evidence_promoted"])
        self.assertEqual(json.loads(self.receipt.read_text()),result)

    def test_failure_in_first_round_is_not_erased_by_pass_in_second(self):
        calls = []
        def flaky(root, verified, **kw):
            calls.append(verified["profiles"][0])
            if len(calls)==1:
                raise ProofError("test_failed")
            return self.runner(root,verified,**kw)
        result=diagnose(self.kit,PIN,runner=flaky)
        self.assertEqual(result["status"],"FAIL_RECORDED")
        self.assertEqual(result["failures"],1)
        self.assertEqual(result["tests_passed"],3)
        self.assertEqual(result["groups"][0]["code"],"test_failed")
        self.assertEqual(len(calls),4)

    def test_exception_details_never_contaminate_receipt(self):
        secret="private-client-token-must-not-leak"
        def f(*args,**kw):
            raise OSError(secret)
        result=diagnose(self.kit,PIN,runner=f,receipt=self.receipt)
        self.assertEqual(result["status"],"FAIL_RECORDED")
        self.assertNotIn(secret,self.receipt.read_text())
        self.assertTrue(all(g.get("code")=="runtime_unavailable" for g in result["groups"]))

    def test_bad_manifest_pin_refused_before_validation(self):
        with patch.object(module,"validate") as validate:
            result=diagnose(self.kit,"wrong",runner=self.runner)
        self.assertEqual(result["code"],"invalid_source_pin")
        validate.assert_not_called()

    def test_bool_and_excessive_rounds_rejected(self):
        for v in (True,False,-1,0,4,100,1.3):
            with self.subTest(rounds=v):
                self.assertEqual(diagnose(self.kit,PIN,rounds=v,runner=self.runner)["code"],"invalid_rounds")

    def test_out_of_range_timeouts_rejected(self):
        for v in (0,121,True,1.2):
            with self.subTest(timeout=v):
                self.assertEqual(diagnose(self.kit,PIN,timeout=v,runner=self.runner)["code"],"invalid_timeout")

    def test_wrong_selected_profile_cannot_run(self):
        for v in (["private-service"],["agent","agent"],[],[7]):
            with self.subTest(selection=v):
                result=diagnose(self.kit,PIN,selected_profiles=v,runner=self.runner)
                self.assertEqual(result["code"],"invalid_selected_profile")

    def test_one_selected_profile_works(self):
        result=diagnose(self.kit,PIN,selected_profiles=["event-outbox"],runner=self.runner)
        self.assertEqual(result["profiles_selected"],["event-outbox"])
        self.assertEqual(result["tests_passed"],2)

    def test_weak_success_without_actual_group_refused(self):
        def forged(*args,**kw):
            return {"status":"PASS","tests_run":0,"groups":[]}
        result=diagnose(self.kit,PIN,runner=forged,rounds=1)
        self.assertEqual(result["status"],"FAIL_RECORDED")
        self.assertEqual(result["failures"],2)
        self.assertTrue(all(g["code"]=="incomplete_test_execution" for g in result["groups"]))

    def test_manifest_mutation_aborts_before_next_profile(self):
        calls = 0
        def later_validate(*args,**kw):
            nonlocal calls
            calls += 1
            if calls >= 3:
                raise ProofError("content_hash_mismatch")
            return self.document
        with patch.object(module,"validate",side_effect=later_validate):
            result=diagnose(self.kit,PIN,runner=self.runner)
        self.assertEqual(result["status"],"FAIL_RECORDED")
        self.assertFalse(result["posttest_bytes_verified"])
        self.assertEqual(len(result["groups"]),2)
        self.assertEqual(result["groups"][1]["code"],"posttest_integrity_failure")

    def test_nonoverwriting_receipt_preserved(self):
        self.receipt.write_text("original-receipt")
        result=diagnose(self.kit,PIN,receipt=self.receipt,runner=self.runner)
        self.assertEqual(result["status"],"FAIL")
        self.assertEqual(self.receipt.read_text(),"original-receipt")

    def test_receipt_inside_kit_is_refused(self):
        result=diagnose(self.kit,PIN,receipt=self.kit/"result.json",runner=self.runner)
        self.assertEqual(result["status"],"FAIL")
        self.assertFalse((self.kit/"result.json").exists())

    def test_test_env_does_not_forward_private_values(self):
        seen=[]
        def record(*args,**kw):
            seen.append(kw["runtime_env"])
            return self.runner(*args,**kw)
        with patch.dict("os.environ",{"SECRET_FIXTURE":"never forward"}):
            r=diagnose(self.kit,PIN,runner=record,rounds=1)
        self.assertEqual(r["status"],"PASS_REPEATED")
        self.assertTrue(all("SECRET_FIXTURE" not in x for x in seen))

    def test_invalid_test_exception_code_redacted(self):
        def fatal(*args,**kw):
            raise ProofError("SECRET/client/path")
        r=diagnose(self.kit,PIN,runner=fatal,rounds=1)
        self.assertTrue(all(g["code"]=="test_failed" for g in r["groups"]))

    def test_report_contains_no_absolute_paths(self):
        result=diagnose(self.kit,PIN,runner=self.runner,receipt=self.receipt)
        self.assertNotIn(str(self.parent),json.dumps(result))


if __name__=="__main__":
    unittest.main()
