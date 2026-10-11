# SQLite migration reliability gate

Original educational Python 3 + SQLite code for transactional schema updates.
A migration is trusted release SQL pinned by a SHA-256 digest. The first run
atomically applies any missing prefix; a retry refuses changed historical SQL,
detects modified recorded digests, and serializes concurrent writers.

Run `python -B -m unittest discover -s examples/migration_guard -v`.
The example handles only trusted local schema changes. It does not authenticate
database users, permit safe use of untrusted SQL, provide cloud PostgreSQL
migrations, cross-service transactions, PITR/backup, or a production migration
rollback strategy. The digest catches ordinary accidental change drift but
is not a signature against malicious database owners.
