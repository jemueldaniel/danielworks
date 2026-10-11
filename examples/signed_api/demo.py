"""Offline HMAC signing and durable anti-replay walkthrough using synthetic keys."""
from pathlib import Path
from tempfile import TemporaryDirectory
from signed_api import credential, sign, Verifier, RequestError, PATH

with TemporaryDirectory() as folder:
    key = credential("demo-key", "demo-tenant", b"X"*32)
    service = Verifier(Path(folder)/"requests.sqlite", [key], clock=lambda: 2000000000)
    request = sign(key, "POST", PATH, b"synthetic payload",
                   timestamp=2000000000, nonce="public-demo-nonce-001")
    print(service.verify(request))
    try:
        service.verify(request)
    except RequestError as exc:
        print({"second_attempt": exc.code})
