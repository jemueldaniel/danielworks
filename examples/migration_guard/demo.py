"""Demonstrate idempotent schema updates on a temporary SQLite database."""
from tempfile import TemporaryDirectory
from pathlib import Path
from migration import Gate,define
with TemporaryDirectory() as work:
    store=Gate(Path(work)/"demo.sqlite")
    change=define("create_items","CREATE TABLE items(id INTEGER PRIMARY KEY)")
    print(store.apply([change]))
    print(store.apply([change]))
