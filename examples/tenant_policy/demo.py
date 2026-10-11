"""Offline synthetic demonstration; public fixture signing bytes are not credentials."""
from policy import AuditCodec, PolicyEngine, Principal, Resource, Rule

engine = PolicyEngine([
    Rule("read", "document", frozenset({"reader"}), "allow"),
    Rule("delete", "document", frozenset({"reader"}), "deny"),
])
principal = Principal("sample-tenant", "sample-person", frozenset({"reader"}))
resource = Resource("sample-tenant", "sample-document", "sample-person", "document")
decision = engine.decide(principal, resource, "read")
codec = AuditCodec(bytes(range(32)))  # PUBLIC fixture key; never production.
receipt = codec.seal(decision, "sample-request-00000001", issued_at=100, ttl=60)
proof = codec.inspect(
    receipt, now=130, tenant=principal.tenant, subject=principal.subject,
    resource=resource.resource_id, action="read", version=engine.version,
)
print({"access_allowed": decision.allowed, "receipt_verified": proof.decision == decision})
