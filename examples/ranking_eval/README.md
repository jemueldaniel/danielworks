# Offline ranking evaluation

## Problem and implementation

A small scoring script can report a convincing number while silently dropping empty results, counting duplicates, or normalizing by the wrong denominator. This example implements strict input validation and hand-checkable **macro recall@k** and **mean reciprocal rank@k** over supplied rankings.

It does not implement or call a retriever, embedding model, language model, database or hosted evaluation service. The implementation and tests were newly written with AI assistance.

## Architecture and definitions

`bounded UTF-8 JSON file → exact schema and identifier checks → per-query scores → macro means + input fingerprint`.

Recall@k is the number of relevant documents in the first `k` retrieved positions divided by the number of relevance labels for that query. Reciprocal rank@k is `1 / rank` of the first relevant item within the cutoff, or zero. Both summary metrics give every query equal weight, including queries with no retrieved results. Queries with no relevance labels are invalid rather than assigned an arbitrary score.

The SHA-256 fingerprint binds the parsed dataset's canonical JSON: object keys and whitespace are normalized; array order is preserved. It is not a digital signature or evidence that the labels are true. Reports sort query rows by identifier for stable inspection.

## Run and test

Prerequisite: Python 3.11+. Everything uses the standard library. From the repository root:

```sh
python examples/ranking_eval/evaluation.py examples/ranking_eval/synthetic.json --k 2
python -B -m unittest discover -s examples/ranking_eval -p 'test_*.py' -v
```

Sample input is [synthetic.json](synthetic.json). For the first query, a relevant item appears second and one of two relevant documents is in the cutoff; the second query finds its one relevant item first. Selected fields from the full computed output are:

```json
{"k": 2, "query_count": 2, "macro_recall_at_k": 0.75, "mrr_at_k": 0.75}
```

The CLI also prints the canonical dataset fingerprint and every query's scores. Invalid input returns exit code 2, prints a generic validation error to stderr, and emits no report on stdout. These are synthetic arithmetic examples, **not benchmark results about a model, customer workload or production system**.

## Validation and tradeoffs

Input files are limited to 65,536 bytes. The schema is exact: unknown and missing fields are rejected. JSON duplicate keys, non-finite literal constants, duplicate identifiers, unknown document references, duplicate rankings even beyond the cutoff, and training/evaluation query-ID overlap are rejected. The direct Python API also limits total identifier references to 5,000; this includes corpus, training and query identifiers and relevance/ranking entries. There may be 1–1,000 queries; the cutoff is an integer from 1 through 100.

Rankings are supplied in order, not derived from numeric scores. There is therefore no hidden score tie-breaking rule. The corpus and labels are validated before reporting metrics. The fingerprint makes changed inputs visible, but is not an immutable dataset service or a signed release artifact.

## Known limits

Disjoint query IDs detect **identifier overlap only**. They do not establish semantic decontamination, training-data provenance, held-out governance, or absence of near-duplicate content. Relevance labels are assumed to be supplied correctly. This example provides neither graded relevance/NDCG nor confidence intervals, significance tests, multilingual normalization or model comparisons.

No private prompts, user queries, customer documents or original evaluation datasets are included. Actual retrieval, model evaluation and training infrastructure require separately scoped evidence; this small scorer must not be used as a substitute for those claims.
