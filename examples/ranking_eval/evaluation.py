"""Validate and score supplied rankings. This module does not run a retriever or model."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any

MAX_BYTES = 65_536
ID = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")


def identifier(value: Any) -> str:
    if type(value) is not str or not ID.fullmatch(value):
        raise ValueError("invalid identifier")
    return value


def unique_ids(value: Any, *, minimum: int = 0, maximum: int = 5000) -> list[str]:
    if type(value) is not list or not minimum <= len(value) <= maximum:
        raise ValueError("identifier list has invalid size or type")
    result = [identifier(item) for item in value]
    if len(set(result)) != len(result):
        raise ValueError("duplicate identifier")
    return result


def object_keys(value: Any, expected: set[str]) -> None:
    if type(value) is not dict or set(value) != expected:
        raise ValueError("object fields do not match the schema")


def evaluate(dataset: Any, *, k: int = 2) -> dict[str, Any]:
    """Macro recall@k and mean reciprocal rank@k; every query has equal weight."""
    if type(k) is not int or not 1 <= k <= 100:
        raise ValueError("k must be an integer from 1 through 100")
    object_keys(dataset, {"schema", "corpus", "training_query_ids", "queries"})
    if dataset["schema"] != "ranking-eval.v1":
        raise ValueError("unsupported dataset schema")
    corpus = set(unique_ids(dataset["corpus"], minimum=1))
    training_ids = set(unique_ids(dataset["training_query_ids"]))
    queries = dataset["queries"]
    if type(queries) is not list or not 1 <= len(queries) <= 1000:
        raise ValueError("queries must contain 1 through 1000 items")
    seen: set[str] = set()
    rows = []
    reference_count = len(corpus) + len(training_ids)
    for query in queries:
        object_keys(query, {"id", "relevant", "retrieved"})
        if type(query["relevant"]) is not list or type(query["retrieved"]) is not list:
            raise ValueError("relevance and ranking fields must be lists")
        reference_count += 1 + len(query["relevant"]) + len(query["retrieved"])
        if reference_count > 5000:
            raise ValueError("total identifier reference budget exceeded")
        query_id = identifier(query["id"])
        if query_id in seen:
            raise ValueError("duplicate query identifier")
        if query_id in training_ids:
            raise ValueError("training and evaluation query identifiers overlap")
        seen.add(query_id)
        relevant = set(unique_ids(query["relevant"], minimum=1))
        retrieved = unique_ids(query["retrieved"])
        if not relevant <= corpus or not set(retrieved) <= corpus:
            raise ValueError("ranking or relevance label references an unknown document")
        top = retrieved[:k]
        first_hit = next((rank for rank, doc in enumerate(top, 1) if doc in relevant), None)
        rows.append({
            "id": query_id,
            "recall_at_k": len(relevant.intersection(top)) / len(relevant),
            "reciprocal_rank_at_k": 1 / first_hit if first_hit is not None else 0.0,
        })
    canonical = json.dumps(dataset, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")
    if len(canonical) > MAX_BYTES:
        raise ValueError("canonical dataset exceeds byte limit")
    rows.sort(key=lambda row: row["id"])
    return {
        "schema": "ranking-report.v1",
        "dataset_sha256": hashlib.sha256(canonical).hexdigest(),
        "k": k,
        "query_count": len(rows),
        "macro_recall_at_k": math.fsum(row["recall_at_k"] for row in rows) / len(rows),
        "mrr_at_k": math.fsum(row["reciprocal_rank_at_k"] for row in rows) / len(rows),
        "queries": rows,
    }


def load_dataset(path: str | Path) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON object key")
            result[key] = value
        return result

    def constant(_: str) -> Any:
        raise ValueError("non-finite JSON constant")

    with Path(path).open("rb") as handle:
        data = handle.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("input file exceeds byte limit")
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as error:
        raise ValueError("invalid UTF-8 JSON") from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--k", type=int, default=2)
    args = parser.parse_args()
    try:
        result = evaluate(load_dataset(args.dataset), k=args.k)
    except (ValueError, OSError):
        # Do not echo arbitrary file contents or local paths in diagnostic output.
        print("Dataset could not be read or did not pass validation.", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
