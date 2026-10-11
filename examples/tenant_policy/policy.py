"""Original offline tenant-isolated policy decisions and signed AUDIT EVIDENCE.
No authentication, external service, token authorization or employer code.
Audit evidence is NOT a capability to access the protected resource.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import hmac
import json
import re
from typing import Iterable

_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
_ACTION = re.compile(r"[a-z][a-z0-9_-]{0,31}\Z")
_NONCE = re.compile(r"[A-Za-z0-9_-]{16,80}\Z")
_TOKEN = re.compile(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\Z")
_REASONS = frozenset({"cross_tenant", "explicit_deny", "allow", "default_deny"})
_FIELDS = frozenset({
    "schema", "policy_version", "tenant", "subject", "resource", "action",
    "allowed", "reason", "request_id", "issued_at", "expires_at",
})
MAX_TOKEN_LENGTH = 2048


class PolicyError(ValueError):
    """Invalid input, never a grant."""


class ReceiptError(ValueError):
    """Invalid or nonmatching audit evidence."""


def _identifier(value: object, name: str) -> str:
    if type(value) is not str or not _ID.fullmatch(value):
        raise PolicyError("invalid_" + name)
    return value


def _action(value: object) -> str:
    if type(value) is not str or not _ACTION.fullmatch(value):
        raise PolicyError("invalid_action")
    return value


@dataclass(frozen=True)
class Principal:
    tenant: str
    subject: str
    roles: frozenset[str]

    def __post_init__(self) -> None:
        _identifier(self.tenant, "tenant")
        _identifier(self.subject, "subject")
        if type(self.roles) is not frozenset or any(
            type(r) is not str or not _ACTION.fullmatch(r) for r in self.roles
        ):
            raise PolicyError("invalid_roles")


@dataclass(frozen=True)
class Resource:
    tenant: str
    resource_id: str
    owner: str
    kind: str

    def __post_init__(self) -> None:
        _identifier(self.tenant, "tenant")
        _identifier(self.resource_id, "resource")
        _identifier(self.owner, "owner")
        _action(self.kind)


@dataclass(frozen=True)
class Rule:
    action: str
    kind: str
    roles: frozenset[str]
    effect: str
    owner_only: bool = False

    def __post_init__(self) -> None:
        _action(self.action)
        _action(self.kind)
        if type(self.roles) is not frozenset or not self.roles or any(
            type(r) is not str or not _ACTION.fullmatch(r) for r in self.roles
        ):
            raise PolicyError("invalid_rule_roles")
        if self.effect not in ("allow", "deny") or type(self.owner_only) is not bool:
            raise PolicyError("invalid_rule")


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str
    tenant: str
    subject: str
    resource: str
    action: str
    policy_version: int


class PolicyEngine:
    """Deny by default; an explicit deny wins independent of rule order."""

    def __init__(self, rules: Iterable[Rule], version: int = 1) -> None:
        if type(version) is not int or not 1 <= version <= 2**31 - 1:
            raise PolicyError("invalid_version")
        self.version = version
        self.rules = tuple(rules)
        if any(type(rule) is not Rule for rule in self.rules):
            raise PolicyError("invalid_rule")
        if len(set(self.rules)) != len(self.rules):
            raise PolicyError("duplicate_rule")

    def decide(self, principal: Principal, resource: Resource, action: str) -> Decision:
        if type(principal) is not Principal or type(resource) is not Resource:
            raise PolicyError("invalid_input")
        _action(action)
        reason = "default_deny"
        if principal.tenant != resource.tenant:
            reason = "cross_tenant"
        else:
            effects = set()
            for rule in self.rules:
                if rule.action != action or rule.kind != resource.kind:
                    continue
                if not (principal.roles & rule.roles):
                    continue
                if rule.owner_only and principal.subject != resource.owner:
                    continue
                effects.add(rule.effect)
            if "deny" in effects:
                reason = "explicit_deny"
            elif "allow" in effects:
                reason = "allow"
        return Decision(
            reason == "allow", reason, principal.tenant, principal.subject,
            resource.resource_id, action, self.version,
        )


def _encoded(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decoded(value: str) -> bytes:
    try:
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, base64.binascii.Error) as exc:
        raise ReceiptError("invalid_encoding") from exc
    if _encoded(raw) != value:
        raise ReceiptError("noncanonical_encoding")
    return raw


def _unique(pairs: list[tuple[str, object]]) -> dict:
    obj: dict = {}
    for key, value in pairs:
        if key in obj:
            raise ReceiptError("duplicate_field")
        obj[key] = value
    return obj


def _bytes(body: dict) -> bytes:
    return json.dumps(body, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("ascii")


@dataclass(frozen=True)
class ReceiptEvidence:
    decision: Decision
    request_id: str
    issued_at: int
    expires_at: int


class AuditCodec:
    """HMAC observational receipts bound to exact subject and resource.
    Caller authenticates principal and protects signing key separately.
    """

    def __init__(self, key: bytes) -> None:
        if type(key) is not bytes or len(key) < 32:
            raise PolicyError("invalid_signing_key")
        self._key = key

    def _mac(self, raw: bytes) -> bytes:
        return hmac.new(self._key, b"public-policy-audit-v1\x00" + raw, hashlib.sha256).digest()

    def seal(self, decision: Decision, request_id: str, issued_at: int, ttl: int = 300) -> str:
        if type(decision) is not Decision:
            raise PolicyError("invalid_decision")
        if type(request_id) is not str or not _NONCE.fullmatch(request_id):
            raise PolicyError("invalid_request_id")
        if type(issued_at) is not int or not 0 <= issued_at <= 2**53 - 1:
            raise PolicyError("invalid_issued_at")
        if type(ttl) is not int or not 1 <= ttl <= 900 or issued_at + ttl > 2**53 - 1:
            raise PolicyError("invalid_ttl")
        _identifier(decision.tenant, "tenant")
        _identifier(decision.subject, "subject")
        _identifier(decision.resource, "resource")
        _action(decision.action)
        if (
            type(decision.allowed) is not bool or decision.reason not in _REASONS
            or decision.allowed != (decision.reason == "allow")
            or type(decision.policy_version) is not int
            or not 1 <= decision.policy_version <= 2**31 - 1
        ):
            raise PolicyError("invalid_decision")
        body = {
            "schema": 1, "policy_version": decision.policy_version,
            "tenant": decision.tenant, "subject": decision.subject,
            "resource": decision.resource, "action": decision.action,
            "allowed": decision.allowed, "reason": decision.reason,
            "request_id": request_id, "issued_at": issued_at,
            "expires_at": issued_at + ttl,
        }
        raw = _bytes(body)
        token = _encoded(raw) + "." + _encoded(self._mac(raw))
        if len(token) > MAX_TOKEN_LENGTH:
            raise PolicyError("receipt_too_large")
        return token

    def inspect(self, token: str, *, now: int, tenant: str, subject: str,
                resource: str, action: str, version: int) -> ReceiptEvidence:
        """Observational evidence only; never authorize access from a receipt."""
        if type(token) is not str or len(token) > MAX_TOKEN_LENGTH or not _TOKEN.fullmatch(token):
            raise ReceiptError("invalid_token")
        if type(now) is not int or now < 0 or now > 2**53 - 1:
            raise ReceiptError("invalid_now")
        _identifier(tenant, "tenant")
        _identifier(subject, "subject")
        _identifier(resource, "resource")
        _action(action)
        if type(version) is not int or version < 1:
            raise ReceiptError("invalid_version")
        encoded_body, encoded_signature = token.split(".")
        raw = _decoded(encoded_body)
        signature = _decoded(encoded_signature)
        if not hmac.compare_digest(signature, self._mac(raw)):
            raise ReceiptError("invalid_signature")
        try:
            doc = json.loads(raw.decode("ascii"), object_pairs_hook=_unique)
        except (ValueError, UnicodeError, RecursionError) as exc:
            raise ReceiptError("invalid_body") from exc
        if type(doc) is not dict or set(doc) != _FIELDS or _bytes(doc) != raw:
            raise ReceiptError("noncanonical_body")
        if type(doc["schema"]) is not int or doc["schema"] != 1:
            raise ReceiptError("invalid_schema")
        if any(type(doc[key]) is not str for key in ("tenant","subject","resource","action","reason","request_id")):
            raise ReceiptError("invalid_field")
        if type(doc["allowed"]) is not bool or doc["reason"] not in _REASONS or (
            doc["allowed"] != (doc["reason"] == "allow")
        ):
            raise ReceiptError("inconsistent_decision")
        if any(type(doc[key]) is not int for key in ("policy_version", "issued_at", "expires_at")):
            raise ReceiptError("invalid_timestamp")
        if doc["policy_version"] != version:
            raise ReceiptError("version_mismatch")
        if (doc["tenant"], doc["subject"], doc["resource"], doc["action"]) != (
            tenant, subject, resource, action
        ):
            raise ReceiptError("binding_mismatch")
        if not _NONCE.fullmatch(doc["request_id"]):
            raise ReceiptError("invalid_request_id")
        if not (0 <= doc["issued_at"] <= now < doc["expires_at"] <= 2**53 - 1):
            raise ReceiptError("outside_validity_window")
        if not 1 <= doc["expires_at"] - doc["issued_at"] <= 900:
            raise ReceiptError("invalid_ttl")
        return ReceiptEvidence(
            Decision(doc["allowed"], doc["reason"], tenant, subject, resource,
                     action, version),
            doc["request_id"], doc["issued_at"], doc["expires_at"],
        )
