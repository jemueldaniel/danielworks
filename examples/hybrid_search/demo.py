"""Run a real, offline SQLite FTS5 + hashed-lexical hybrid ranking example."""
from pathlib import Path
from tempfile import TemporaryDirectory
from hybrid import HybridSearch

with TemporaryDirectory() as folder:
    search=HybridSearch(Path(folder)/"sample.sqlite")
    search.put("example-tenant","doc-alpha","Recovery design",
               "Reliable transactions and crash recovery",version=1)
    search.put("example-tenant","doc-beta","Evaluation guide",
               "Ranking, recall and evaluation",version=1)
    found=search.search("example-tenant","crash recovery",top_k=3)
    report=search.evaluate("example-tenant",[
        {"query":"crash recovery","expected":["doc-alpha"]},
        {"query":"ranking recall","expected":["doc-beta"]},
    ],top_k=1)
    print({"hits":[r["document_id"] for r in found],
           "recall_at_1":report["recall_at_k"],
           "audit":search.audit("example-tenant")["status"]})
