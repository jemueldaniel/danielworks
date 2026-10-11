"""One-command, synthetic, offline outbox run with no actual credentials."""
from pathlib import Path
import json
import tempfile

from event_outbox import EventInbox, signature

TEST_KEY = b"synthetic-public-example-key-12345"
NOW = 1800000000

def main():
    with tempfile.TemporaryDirectory() as directory:
        inbox = EventInbox(Path(directory) / "reference.sqlite", TEST_KEY)
        raw = json.dumps({"id":"sample_1","type":"document.created",
                          "payload":{"label":"synthetic"}},
                         sort_keys=True, separators=(",", ":")).encode()
        signed = signature(TEST_KEY, raw, NOW)
        created = inbox.ingest(raw, str(NOW), signed, now=NOW)
        repeated = inbox.ingest(raw, str(NOW), signed, now=NOW)
        lease = inbox.claim("worker_1", now=NOW)[0]
        acked = inbox.ack(lease, now=NOW + 1)
        print(json.dumps({"first": created["status"], "retry": repeated["status"],
                          "acknowledged": acked,
                          "receipt": inbox.receipt("sample_1"),
                          "scope":"offline_synthetic"}, sort_keys=True))

if __name__ == "__main__":
    main()
