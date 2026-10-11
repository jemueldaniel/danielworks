# Portable policy and audit-evidence reference

This original, dependency-free Python reference demonstrates explicit tenant isolation, deny-overrides rules, owner-scoped checks, immutable decisions, and canonical HMAC-SHA256 audit evidence bound to the exact tenant, subject, resource, action, policy version and expiry.

It is not a company extract, authentication provider, JWT implementation, hosted identity service or production security boundary. The caller must authenticate the subject, resolve roles and resources from trusted storage, manage real signing keys separately and recompute a live policy decision for every sensitive action. A receipt is only observational evidence: NEVER a bearer permission, access token, replay prevention mechanism or proof of identity. No live keys are included.

## Run

From this directory: python -B demo.py

Test suite from the full repository root: python -B -m unittest discover -s examples/tenant_policy -v

## Reusable workflow

1. Authenticate and verify the subject, tenant membership, roles and resource metadata.
2. Build Principal, Resource, and versioned Rule values. Call PolicyEngine.decide for each current request.
3. Enforce the result before reading or mutating any protected data. Cross-tenant attempts are always denied, even for administrators.
4. Optionally use AuditCodec with a deployment-provided signing key to issue short-lived tamper-detecting evidence for an internal audit. Inspect checks the exact bindings but never grants access.
5. Add actual authentication, persisted grants and revocation, key rotation, replay-safe effects, rate limits, CSRF controls where relevant, reliable audit logs, authorization testing and independent security review before production use.

Tests cover unauthorized tenants, deny precedence, ownership, role validation, forged and stale evidence, malformed canonical encoding, binding mismatch and deterministic randomized tenant isolation. All identity and key values in tests are synthetic.
