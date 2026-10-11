# Hybrid retrieval and reproducible quality evaluation

An original, dependency-free **Python + SQLite FTS5** public reference combining two real lexical ranking signals: built-in full-text BM25 and a deterministic 64-dimensional hashed bag-of-tokens cosine score. Reciprocal-rank fusion combines them while an exact token-overlap gate prevents a hash collision alone from inventing "semantic" matches.

This is **not a neural embedding model**, LLM retrieval, vector database, AI search quality claim, personal corpus extract or hosted RAG service. All fixtures are synthetic and there is no model API, network or company code. The hashed vector is deliberately lexical—not semantic. Inputs are bounded, FTS expressions are composed only from quoted normalized ASCII tokens, SQL queries use bound values, tenant labels are isolated, writes to canonical content and FTS are transactional, and updates require monotonic revision numbers.

Run from the repository root:

    python -B -m unittest discover -s examples/hybrid_search -v
    python -B examples/hybrid_search/demo.py

The tests exercise actual SQLite FTS5 indexing, safe query handling, cross-tenant isolation, concurrent writes, revision fences, index corruption, restart recovery, and meaningful **recall@k, MRR@k, nDCG@k** with positive and deliberately failed synthetic search cases.

**Deployment boundaries:** Tenant labels are supplied by the caller and **are not authenticated**; connect real identity and authorization before deployment. Retrieved strings are **untrusted text**; web UIs must escape them and downstream LLM instructions must not treat their content as authority. The index audit is a row mirror check, not an anti-tamper certificate or full internal FTS integrity scan. SQLite is not a production distributed search cluster. Relevance on generated samples is not evidence of quality on real employer datasets.
