"""Deterministic transaction, isolation, concurrency and integrity checks."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from ledger import Ledger, LedgerError


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "journal.sqlite"
        self.ledger = Ledger(self.db)
        self.ledger.create_account("tenant-a", "clearing", "UNIT", kind="clearing")
        self.ledger.create_account("tenant-a", "alice", "UNIT")
        self.ledger.create_account("tenant-a", "bob", "UNIT")

    def fund(self, amount=1000):
        return self.ledger.transfer("tenant-a", "funding-one", "clearing",
                                    "alice", "UNIT", amount)

    def test_initial_balances_are_zero(self):
        self.assertEqual(self.ledger.balances("tenant-a"),
                         {"alice": 0, "bob": 0, "clearing": 0})

    def test_posted_transfer_is_balanced(self):
        self.fund()
        self.assertEqual(self.ledger.balances("tenant-a"),
                         {"alice": 1000, "bob": 0, "clearing": -1000})

    def test_two_hops_sum_to_zero(self):
        self.fund()
        self.ledger.transfer("tenant-a", "payout-one", "alice", "bob", "UNIT", 400)
        self.assertEqual(self.ledger.balances("tenant-a"),
                         {"alice": 600, "bob": 400, "clearing": -1000})
        self.assertTrue(self.ledger.audit("tenant-a")["all_assets_zero_sum"])

    def test_exact_replay_has_no_side_effect(self):
        self.fund()
        before = self.ledger.balances("tenant-a")
        r = self.fund()
        self.assertEqual(r["status"], "replayed")
        self.assertEqual(before, self.ledger.balances("tenant-a"))
        self.assertEqual(self.ledger.audit("tenant-a")["transfers"], 1)

    def test_replay_rejects_conflicting_amount(self):
        self.fund()
        with self.assertRaisesRegex(LedgerError, "idempotency_conflict"):
            self.ledger.transfer("tenant-a", "funding-one", "clearing", "alice", "UNIT", 999)
        self.assertEqual(self.ledger.audit("tenant-a")["transfers"], 1)

    def test_replay_rejects_conflicting_accounts(self):
        self.fund()
        with self.assertRaisesRegex(LedgerError, "idempotency_conflict"):
            self.ledger.transfer("tenant-a", "funding-one", "clearing", "bob", "UNIT", 1000)

    def test_replayed_post_after_spending_remains_replay(self):
        self.fund()
        self.ledger.transfer("tenant-a", "payout-one", "alice", "bob", "UNIT", 999)
        self.assertEqual(self.fund()["status"], "replayed")

    def test_same_account_fails_closed(self):
        with self.assertRaisesRegex(LedgerError, "same_account"):
            self.ledger.transfer("tenant-a", "selftx", "alice", "alice", "UNIT", 1)

    def test_insufficient_funds_is_rolled_back(self):
        with self.assertRaisesRegex(LedgerError, "insufficient_funds"):
            self.ledger.transfer("tenant-a", "unfunded", "alice", "bob", "UNIT", 1)
        self.assertEqual(self.ledger.audit("tenant-a")["transfers"], 0)

    def test_spend_exact_remaining_amount(self):
        self.fund(1000)
        self.ledger.transfer("tenant-a", "exact", "alice", "bob", "UNIT", 1000)
        self.assertEqual(self.ledger.balances("tenant-a")["alice"], 0)

    def test_duplicate_account_definition_is_idempotent(self):
        self.assertEqual(self.ledger.create_account("tenant-a", "alice", "UNIT"), "existing")

    def test_account_definition_conflict_rejected(self):
        with self.assertRaisesRegex(LedgerError, "account_definition_conflict"):
            self.ledger.create_account("tenant-a", "alice", "OTHER")

    def test_unknown_account_rejected(self):
        self.fund()
        with self.assertRaisesRegex(LedgerError, "account_not_found"):
            self.ledger.transfer("tenant-a", "to-unknown", "alice", "unknown", "UNIT", 50)

    def test_cross_tenant_account_reference_is_rejected(self):
        self.fund()
        self.ledger.create_account("tenant-b", "outsider", "UNIT")
        with self.assertRaisesRegex(LedgerError, "account_not_found"):
            self.ledger.transfer("tenant-a", "cross", "alice", "outsider", "UNIT", 50)

    def test_identical_account_ids_across_tenants_do_not_collide(self):
        self.ledger.create_account("tenant-b", "clearing", "UNIT", kind="clearing")
        self.ledger.create_account("tenant-b", "alice", "UNIT")
        self.fund()
        self.ledger.transfer("tenant-b", "funding-one", "clearing", "alice", "UNIT", 70)
        self.assertEqual(self.ledger.balances("tenant-a")["alice"], 1000)
        self.assertEqual(self.ledger.balances("tenant-b")["alice"], 70)
        self.assertEqual(self.ledger.audit("tenant-b")["transfers"], 1)

    def test_asset_mismatch_rejected(self):
        self.fund()
        self.ledger.create_account("tenant-a", "other", "OTHER")
        with self.assertRaisesRegex(LedgerError, "asset_mismatch"):
            self.ledger.transfer("tenant-a", "cross-asset", "alice", "other", "UNIT", 1)

    def test_separate_assets_have_independent_zero_sum(self):
        self.ledger.create_account("tenant-a", "other-clearing", "OTHER", kind="clearing")
        self.ledger.create_account("tenant-a", "other-owner", "OTHER")
        self.fund()
        self.ledger.transfer("tenant-a", "asset-other", "other-clearing", "other-owner", "OTHER", 50)
        self.assertEqual(self.ledger.audit("tenant-a")["asset_count"], 2)

    def test_floats_bools_zero_negative_and_huge_amounts_rejected(self):
        for value in (1.0, True, None, 0, -1, 1_000_000_000_001):
            with self.subTest(value=value), self.assertRaisesRegex(LedgerError, "invalid_amount"):
                self.ledger.transfer("tenant-a", "bad-amount", "clearing", "alice", "UNIT", value)

    def test_invalid_tenant_and_request_ids_rejected(self):
        for value in ("", "../tenant", "a\n", "a b", "a"*49, 42):
            with self.subTest(value=value), self.assertRaises(LedgerError):
                self.ledger.transfer(value, "request", "clearing", "alice", "UNIT", 1)
        with self.assertRaisesRegex(LedgerError, "invalid_request"):
            self.ledger.transfer("tenant-a", "a/b", "clearing", "alice", "UNIT", 1)

    def test_invalid_asset_case_rejected(self):
        with self.assertRaisesRegex(LedgerError, "invalid_asset"):
            self.ledger.create_account("tenant-a", "badasset", "usd")

    def test_invalid_clearing_kind_rejected(self):
        with self.assertRaisesRegex(LedgerError, "invalid_kind"):
            self.ledger.create_account("tenant-a", "new", "UNIT", kind="root")

    def test_reopened_store_preserves_balances_and_chain(self):
        self.fund()
        expected = self.ledger.audit("tenant-a")["chain_sha256"]
        reloaded = Ledger(self.db)
        self.assertEqual(reloaded.balances("tenant-a")["alice"], 1000)
        self.assertEqual(reloaded.audit("tenant-a")["chain_sha256"], expected)

    def test_transaction_rolls_back_without_partial_postings(self):
        self.fund()
        before = self.ledger.balances("tenant-a")
        with self.assertRaises(LedgerError):
            self.ledger.transfer("tenant-a", "too-big", "alice", "bob", "UNIT", 1001)
        self.assertEqual(self.ledger.balances("tenant-a"), before)
        self.assertEqual(self.ledger.audit("tenant-a")["transfers"], 1)

    def test_concurrent_same_request_posts_only_once(self):
        self.fund()
        def worker(_):
            return self.ledger.transfer("tenant-a", "shared", "alice", "bob", "UNIT", 30)["status"]
        with ThreadPoolExecutor(max_workers=6) as executor:
            statuses=list(executor.map(worker, range(12)))
        self.assertEqual(statuses.count("posted"), 1)
        self.assertEqual(statuses.count("replayed"), 11)
        self.assertEqual(self.ledger.balances("tenant-a")["bob"], 30)

    def test_concurrent_distinct_requests_serialize(self):
        self.fund()
        def worker(i):
            return self.ledger.transfer("tenant-a", "sequential-" + str(i), "alice", "bob",
                                        "UNIT", 10)["status"]
        with ThreadPoolExecutor(max_workers=8) as executor:
            self.assertEqual(list(executor.map(worker, range(30))), ["posted"]*30)
        self.assertEqual(self.ledger.balances("tenant-a")["bob"], 300)
        self.assertEqual(self.ledger.audit("tenant-a")["transfers"], 31)

    def test_concurrent_spending_never_overdraws_ordinary_balance(self):
        self.fund(100)
        def worker(i):
            try:
                return self.ledger.transfer("tenant-a", "spend-" + str(i),
                                            "alice", "bob", "UNIT", 20)["status"]
            except LedgerError as e:
                return e.code
        with ThreadPoolExecutor(max_workers=8) as executor:
            statuses=list(executor.map(worker, range(10)))
        self.assertEqual(statuses.count("posted"), 5)
        self.assertEqual(statuses.count("insufficient_funds"), 5)
        self.assertEqual(self.ledger.balances("tenant-a")["alice"], 0)
        self.assertEqual(self.ledger.audit("tenant-a")["transfers"], 6)

    def test_detection_of_modified_balance_cache(self):
        self.fund()
        with closing(sqlite3.connect(self.db)) as con, con:
            con.execute("UPDATE accounts SET balance=balance+1 WHERE tenant=? AND account=?",
                        ("tenant-a", "alice"))
        with self.assertRaisesRegex(LedgerError, "balance_cache_drift"):
            self.ledger.audit("tenant-a")

    def test_detection_of_corrupted_signed_posting(self):
        self.fund()
        with closing(sqlite3.connect(self.db)) as con, con:
            con.execute("UPDATE postings SET delta=delta+1 WHERE tenant=? AND leg=1",
                        ("tenant-a",))
        with self.assertRaisesRegex(LedgerError, "unbalanced_postings"):
            self.ledger.audit("tenant-a")

    def test_detection_of_corrupted_unkeyed_chain(self):
        self.fund()
        with closing(sqlite3.connect(self.db)) as con, con:
            con.execute("UPDATE transfers SET chain_sha=? WHERE tenant=?",
                        ("f"*64, "tenant-a"))
        with self.assertRaisesRegex(LedgerError, "journal_integrity"):
            self.ledger.audit("tenant-a")

    def test_bound_transfer_id_digest_differs_by_payload(self):
        self.fund()
        r = self.ledger.transfer("tenant-a", "newtx", "alice", "bob", "UNIT", 1)
        self.assertNotEqual(r["request_sha256"], self.fund()["request_sha256"])
        self.assertEqual(len(r["chain_sha256"]), 64)

    def test_audit_empty_tenant_does_not_leak_other_tenants(self):
        self.fund()
        self.assertEqual(self.ledger.audit("tenant-b")["transfers"], 0)
        self.assertEqual(self.ledger.balances("tenant-b"), {})


if __name__ == "__main__":
    unittest.main()
