# Public capability mapper

An independently authored, offline Python capability inventory. It categorizes 42 generic technologies without claiming personal mastery. Every entry defaults to **unverified** until independently supported by a public implementation and tests.

Run: `python -B -m unittest discover -s examples/capability_mapper -p test_catalog.py -v`

Generate a machine-readable generic matrix: `python -B examples/capability_mapper/catalog.py`

The validator rejects duplicate records, unsupported technology labels, path traversal, private links and unqualified references. No private repositories, credentials, customer records or employer code are read. This is a foundation for future evidence-based mapping, not a private-source scanner or an automatic skill certification.
