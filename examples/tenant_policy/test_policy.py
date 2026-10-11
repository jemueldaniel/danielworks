"""Synthetic security-boundary and integrity regression tests."""
from __future__ import annotations

import base64
from dataclasses import FrozenInstanceError
import hashlib
import hmac
import json
import random
import unittest

from policy import (
    AuditCodec, Decision, PolicyEngine, PolicyError, Principal, ReceiptError,
    Resource, Rule, _encoded,
)

PUBLIC_TEST_KEY = bytes(range(32))
NONCE = "sample-request-00000001"


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.alice = Principal("tenant-a", "alice", frozenset({"reader", "editor"}))
        self.bob = Principal("tenant-a", "bob", frozenset({"reader"}))
        self.admin = Principal("tenant-b", "root", frozenset({"admin", "editor"}))
        self.doc = Resource("tenant-a", "document-a", "alice", "document")
        self.rules = [
            Rule("read", "document", frozenset({"reader"}), "allow"),
            Rule("edit", "document", frozenset({"editor"}), "allow", owner_only=True),
            Rule("delete", "document", frozenset({"admin"}), "allow"),
        ]
        self.engine = PolicyEngine(self.rules, version=5)
        self.codec = AuditCodec(PUBLIC_TEST_KEY)
        self.decision = self.engine.decide(self.alice, self.doc, "read")
        self.token = self.codec.seal(self.decision, NONCE, 100, 60)

    def inspect(self, token=None, **overrides):
        params = dict(now=130, tenant="tenant-a", subject="alice",
                      resource="document-a", action="read", version=5)
        params.update(overrides)
        return self.codec.inspect(self.token if token is None else token, **params)

    def forge(self, raw: bytes) -> str:
        signature = hmac.new(PUBLIC_TEST_KEY, b"public-policy-audit-v1\x00" + raw, hashlib.sha256).digest()
        return _encoded(raw) + "." + _encoded(signature)

    def body(self):
        raw = base64.urlsafe_b64decode(self.token.split(".")[0] + "===")
        return json.loads(raw)

    def test_explicit_same_tenant_reader_granted(self):
        self.assertEqual(self.decision.reason, "allow")
        self.assertTrue(self.decision.allowed)
        self.assertEqual(self.decision.policy_version, 5)

    def test_empty_policy_denies(self):
        result = PolicyEngine([], version=8).decide(self.alice, self.doc, "read")
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "default_deny")

    def test_action_not_in_rules_denied(self):
        self.assertFalse(self.engine.decide(self.alice, self.doc, "publish").allowed)

    def test_admin_cross_tenant_always_denied(self):
        result = self.engine.decide(self.admin, self.doc, "delete")
        self.assertEqual(result.reason, "cross_tenant")
        self.assertFalse(result.allowed)

    def test_cross_tenant_admin_has_no_implicit_superuser_override(self):
        engine = PolicyEngine([Rule("read", "document", frozenset({"admin"}), "allow")])
        result = engine.decide(self.admin, self.doc, "read")
        self.assertEqual(result.reason, "cross_tenant")

    def test_owner_required_for_edit(self):
        self.assertTrue(self.engine.decide(self.alice, self.doc, "edit").allowed)
        another = Principal("tenant-a", "mallory", frozenset({"editor"}))
        self.assertFalse(self.engine.decide(another, self.doc, "edit").allowed)

    def test_wrong_resource_kind_denied(self):
        other = Resource("tenant-a", "d-a", "alice", "wallet")
        self.assertFalse(self.engine.decide(self.alice, other, "read").allowed)

    def test_no_admin_role_even_if_subject_named_root(self):
        root_name = Principal("tenant-a", "root", frozenset({"reader"}))
        self.assertFalse(self.engine.decide(root_name, self.doc, "delete").allowed)

    def test_explicit_deny_overrides_allow_independent_of_order(self):
        deny = Rule("read", "document", frozenset({"reader"}), "deny")
        for rules in (self.rules + [deny], [deny] + self.rules):
            with self.subTest(rules=rules[0].effect):
                out = PolicyEngine(rules).decide(self.alice, self.doc, "read")
                self.assertEqual(out.reason, "explicit_deny")
                self.assertFalse(out.allowed)

    def test_scoped_deny_only_hits_matching_owner(self):
        deny = Rule("read", "document", frozenset({"reader"}), "deny", owner_only=True)
        p = PolicyEngine(self.rules + [deny])
        self.assertFalse(p.decide(self.alice, self.doc, "read").allowed)
        self.assertTrue(p.decide(self.bob, self.doc, "read").allowed)

    def test_no_roles_means_no_grant(self):
        nobody = Principal("tenant-a", "alice", frozenset())
        self.assertFalse(self.engine.decide(nobody, self.doc, "read").allowed)

    def test_invalid_identity_and_action_rejected(self):
        for invalid in ("../tenant", "tenant/a", "tenant a", "", "\u03c0", "a"*65):
            with self.subTest(invalid=invalid), self.assertRaises(PolicyError):
                Principal(invalid, "bob", frozenset())
        with self.assertRaises(PolicyError):
            self.engine.decide(self.alice, self.doc, "read\n")

    def test_roles_are_strict_immutable_set_not_user_supplied_list(self):
        with self.assertRaises(PolicyError):
            Principal("tenant-a", "mallory", ["admin"])
        with self.assertRaises(PolicyError):
            Principal("tenant-a", "mallory", frozenset({"admin\n"}))
        with self.assertRaises(FrozenInstanceError):
            self.alice.tenant = "tenant-b"

    def test_invalid_policy_rules_refused(self):
        with self.assertRaises(PolicyError):
            Rule("read", "document", frozenset(), "allow")
        with self.assertRaises(PolicyError):
            Rule("read", "document", frozenset({"reader"}), "overwrite")
        with self.assertRaises(PolicyError):
            PolicyEngine([self.rules[0], self.rules[0]])
        with self.assertRaises(PolicyError):
            PolicyEngine([], version=True)

    def test_wrong_principal_type_rejected_before_decision(self):
        with self.assertRaises(PolicyError):
            self.engine.decide({"tenant": "tenant-a", "roles": ["reader"]}, self.doc, "read")

    def test_proof_valid_and_bound(self):
        evidence = self.inspect()
        self.assertEqual(evidence.decision, self.decision)
        self.assertEqual(evidence.request_id, NONCE)
        self.assertEqual((evidence.issued_at, evidence.expires_at), (100, 160))

    def test_signature_tampering_refused(self):
        body, sig = self.token.split(".")
        altered = body + "." + ("A" if sig[0] != "A" else "B") + sig[1:]
        with self.assertRaises(ReceiptError):
            self.inspect(altered)

    def test_wrong_signing_key_refused(self):
        bad_codec = AuditCodec(bytes(reversed(range(32))))
        with self.assertRaises(ReceiptError):
            bad_codec.inspect(self.token, now=130, tenant="tenant-a",
                              subject="alice", resource="document-a",
                              action="read", version=5)

    def test_receipt_is_context_bound(self):
        for overrides in (
            {"tenant": "tenant-b"}, {"subject": "mallory"},
            {"resource": "document-b"}, {"action": "delete"},
        ):
            with self.subTest(overrides=overrides), self.assertRaises(ReceiptError):
                self.inspect(**overrides)

    def test_version_change_invalidates_prior_receipt(self):
        with self.assertRaises(ReceiptError):
            self.inspect(version=6)
        revoked = PolicyEngine([], version=6).decide(self.alice, self.doc, "read")
        self.assertFalse(revoked.allowed)

    def test_expired_or_future_receipt_refused(self):
        for now in (99, 160, 999):
            with self.subTest(now=now), self.assertRaises(ReceiptError):
                self.inspect(now=now)
        self.assertEqual(self.inspect(now=159).decision, self.decision)

    def test_invalid_or_weak_key_refused(self):
        for key in ("12345678901234567890123456789012", b"short", bytearray(32)):
            with self.subTest(type=type(key)), self.assertRaises(PolicyError):
                AuditCodec(key)

    def test_receipt_ttl_and_nonce_bounds(self):
        with self.assertRaises(PolicyError):
            self.codec.seal(self.decision, "short", 100)
        for ttl in (0, -1, True, 901):
            with self.subTest(ttl=ttl), self.assertRaises(PolicyError):
                self.codec.seal(self.decision, NONCE, 100, ttl)

    def test_refuse_signed_allow_reason_disagreement(self):
        fake = Decision(True, "cross_tenant", "tenant-a", "alice", "document-a", "read", 5)
        with self.assertRaises(PolicyError):
            self.codec.seal(fake, NONCE, 100)

    def test_authenticated_unknown_field_fails(self):
        body = self.body()
        body["extra"] = "injection"
        with self.assertRaises(ReceiptError):
            self.inspect(self.forge(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()))

    def test_authenticated_unknown_schema_fails(self):
        body = self.body()
        body["schema"] = 2
        with self.assertRaises(ReceiptError):
            self.inspect(self.forge(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()))

    def test_duplicate_json_fields_fails_even_with_valid_signature(self):
        raw = base64.urlsafe_b64decode(self.token.split(".")[0] + "===")
        malicious = raw.replace(b'"schema":1,', b'"schema":1,"schema":1,')
        with self.assertRaises(ReceiptError):
            self.inspect(self.forge(malicious))

    def test_noncanonical_json_fails_even_with_valid_signature(self):
        malicious = json.dumps(self.body(), indent=2, sort_keys=True).encode()
        with self.assertRaises(ReceiptError):
            self.inspect(self.forge(malicious))

    def test_python_bool_is_not_integer_timestamp(self):
        with self.assertRaises(PolicyError):
            self.codec.seal(self.decision, NONCE, issued_at=True)
        with self.assertRaises(ReceiptError):
            self.inspect(now=True)
        body = self.body()
        body["expires_at"] = True
        with self.assertRaises(ReceiptError):
            self.inspect(self.forge(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()))

    def test_oversized_and_malformed_token_fails(self):
        for bad in ("", "abc", "a.b.c", "a=" + self.token, "a"*3000):
            with self.subTest(bad=bad[:10]), self.assertRaises(ReceiptError):
                self.inspect(bad)

    def test_tampered_denial_cannot_become_allow_without_key(self):
        denied = self.engine.decide(self.admin, self.doc, "read")
        proof = self.codec.seal(denied, NONCE, 100)
        body, signature = proof.split(".")
        modified = json.loads(base64.urlsafe_b64decode(body + "==="))
        modified["allowed"] = True
        modified["reason"] = "allow"
        forged_body = _encoded(json.dumps(modified, sort_keys=True, separators=(",", ":")).encode())
        with self.assertRaises(ReceiptError):
            self.codec.inspect(forged_body + "." + signature, now=130,
                               tenant="tenant-b", subject="root",
                               resource="document-a", action="read", version=5)

    def test_randomized_500_cross_tenant_probes(self):
        rng = random.Random(11835)
        engine = PolicyEngine([Rule("read", "document", frozenset({"admin"}), "allow")])
        for _ in range(500):
            a, b = rng.sample(range(10000), 2)
            principal = Principal("t" + str(a), "root", frozenset({"admin"}))
            resource = Resource("t" + str(b), "r1", "root", "document")
            self.assertEqual(engine.decide(principal, resource, "read").reason, "cross_tenant")


if __name__ == "__main__":
    unittest.main()
