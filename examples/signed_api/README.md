# Local signed API with replay rejection

An independently written public Python reference for *request-bound HMAC-SHA256 authentication*. It includes a loopback-only real HTTP endpoint, synthetic 32-byte signing secrets, tenant scopes bound to configured key IDs, canonical request signatures, bounded request bodies, timestamp windows, SQLite persistence, atomic nonce replay checks, rolling per-key quotas and conservative error responses.

The implementation tests real network requests on 127.0.0.1, duplicate/invalid headers, method/path/body/timestamp forgery, replays after reopening the store and concurrent request contention. The test suite also deliberately demonstrates rejection of invalid credentials and out-of-window signatures.

Run from the repository root:

    python -B -m unittest discover -s examples/signed_api -v
    python -B examples/signed_api/demo.py

This is **not** a production authentication or security system. It does not implement HTTPS, identity enrollment, MFA, key rotation, KMS/HSM, browser cookie protection, OAuth/OIDC, independent penetration testing, distributed nonce consensus, untrusted code execution, tenant resource authorization or external cloud integration. The signing key should be stored securely out-of-band in real applications; this repository uses only fictional demonstration bytes. SQLite may serialize requests on one host but is not a multi-region replay system. A successful signature proves *possession of one configured shared key*, not personal identity or permission for unrelated resources. HTTP transport intentionally binds only to loopback, and the client must not send real secrets across plaintext connections.

To reuse this reference in a future employer project, independently adapt and review it; connect approved credential lifecycle, scope mapping, TLS termination, durable secure storage, abuse controls, audit events, access logs without secrets and platform-native key management before any deployment.
