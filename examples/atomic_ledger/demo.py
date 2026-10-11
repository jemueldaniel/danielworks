"""Synthetic ledger walkthrough; fictional units, never live funds."""
from pathlib import Path
from tempfile import TemporaryDirectory
from ledger import Ledger

with TemporaryDirectory() as td:
    ledger = Ledger(Path(td) / "ledger.sqlite")
    ledger.create_account("tenant-one", "clearing", "TOK", kind="clearing")
    ledger.create_account("tenant-one", "alice", "TOK")
    ledger.create_account("tenant-one", "bob", "TOK")
    ledger.transfer("tenant-one", "fund-0001", "clearing", "alice", "TOK", 1000)
    ledger.transfer("tenant-one", "payment-0001", "alice", "bob", "TOK", 300)
    print({"balances": ledger.balances("tenant-one"),
           "audit": ledger.audit("tenant-one")["status"]})
