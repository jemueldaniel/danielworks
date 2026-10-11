"""Original local tenant-scoped hybrid lexical retrieval and quality evaluation.

Uses real SQLite FTS5 ranking plus deterministic hashed lexical-vector ranking.
No LLM, pretrained embeddings, private corpora, authentication, or network.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import math
from pathlib import Path
import re
import sqlite3
from typing import Iterable

_ID = re.compile(r"[a-z][a-z0-9_-]{1,47}\Z")
_TERMS = re.compile(r"[a-z0-9]{2,32}")
MAX_TEXT = 4000
MAX_DOCS = 512
MAX_CASES = 64
DIMENSIONS = 64
FUSION_K = 60


class SearchError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _fail(code: str):
    raise SearchError(code)


def _id(value: object) -> str:
    if type(value) is not str or not _ID.fullmatch(value):
        _fail("invalid_identifier")
    return value


def _text(value: object, *, limit: int = MAX_TEXT) -> str:
    if type(value) is not str or not 1 <= len(value) <= limit:
        _fail("invalid_text")
    if any(ord(c) < 32 and c not in "\n\t" for c in value):
        _fail("invalid_text")
    return value


def _terms(value: str) -> tuple[str, ...]:
    return tuple(_TERMS.findall(value.lower()))


def _vector(tokens: Iterable[str]) -> tuple[float, ...]:
    counts = Counter(tokens)
    raw = [0] * DIMENSIONS
    for term, count in counts.items():
        bucket = int.from_bytes(sha256(term.encode("ascii")).digest()[:4], "big") % DIMENSIONS
        raw[bucket] += count
    magnitude = math.sqrt(sum(v * v for v in raw))
    return tuple(x / magnitude for x in raw) if magnitude else tuple(0.0 for _ in raw)


def _similarity(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return sum(x * y for x, y in zip(a, b))


class HybridSearch:
    """Caller-provided tenant labels are NOT authenticated identities.

    Content is untrusted data and must be escaped in any browser rendering.
    The source uses one row per tenant/document, with FTS writes made in the
    SAME IMMEDIATE transaction as the canonical row.
    """

    def __init__(self, database: str | Path):
        if not isinstance(database, (str, Path)):
            _fail("invalid_database")
        self.path = Path(database).absolute()
        if not self.path.parent.is_dir():
            _fail("invalid_database_parent")
        con = self._connect()
        try:
            con.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                pk INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant TEXT NOT NULL,
                document_id TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                version INTEGER NOT NULL CHECK (version >= 1),
                UNIQUE (tenant, document_id)
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
                tenant UNINDEXED, document_id UNINDEXED, title, body,
                tokenize='unicode61'
            );
            """)
        finally:
            con.close()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        con.execute("PRAGMA busy_timeout=10000")
        return con

    def put(self, tenant: str, document_id: str, title: str, body: str, *, version: int) -> str:
        _id(tenant)
        _id(document_id)
        _text(title, limit=120)
        _text(body)
        if type(version) is not int or not 1 <= version <= 2**31-1:
            _fail("invalid_version")
        con = self._connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            existing = con.execute(
                "SELECT pk,title,body,version FROM documents WHERE tenant=? AND document_id=?",
                (tenant,document_id)).fetchone()
            if existing is not None:
                rowid, old_title, old_body, old_version = existing
                if old_version == version and old_title == title and old_body == body:
                    con.commit()
                    return "unchanged"
                if version != old_version + 1:
                    _fail("revision_conflict")
                con.execute("UPDATE documents SET title=?,body=?,version=? WHERE pk=?",
                            (title,body,version,rowid))
                con.execute("DELETE FROM search_index WHERE rowid=?", (rowid,))
                status = "updated"
            else:
                if version != 1:
                    _fail("revision_conflict")
                count = con.execute("SELECT COUNT(*) FROM documents WHERE tenant=?", (tenant,)).fetchone()[0]
                if count >= MAX_DOCS:
                    _fail("tenant_capacity")
                cur = con.execute(
                    "INSERT INTO documents(tenant,document_id,title,body,version) "
                    "VALUES(?,?,?,?,?)", (tenant,document_id,title,body,version))
                rowid = cur.lastrowid
                status = "created"
            con.execute(
                "INSERT INTO search_index(rowid,tenant,document_id,title,body) "
                "VALUES(?,?,?,?,?)", (rowid,tenant,document_id,title,body))
            con.commit()
            return status
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def delete(self, tenant: str, document_id: str, *, expected_version: int) -> str:
        _id(tenant)
        _id(document_id)
        if type(expected_version) is not int or expected_version < 1:
            _fail("invalid_version")
        con = self._connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute(
                "SELECT pk,version FROM documents WHERE tenant=? AND document_id=?",
                (tenant,document_id)).fetchone()
            if row is None:
                _fail("document_not_found")
            if row[1] != expected_version:
                _fail("revision_conflict")
            con.execute("DELETE FROM search_index WHERE rowid=?", (row[0],))
            con.execute("DELETE FROM documents WHERE pk=?", (row[0],))
            con.commit()
            return "deleted"
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def search(self, tenant: str, query: str, *, top_k: int = 5) -> list[dict]:
        _id(tenant)
        _text(query, limit=256)
        if type(top_k) is not int or not 1 <= top_k <= 20:
            _fail("invalid_k")
        tokens = _terms(query)
        if not tokens or len(tokens) > 12:
            _fail("invalid_query_terms")
        # Quote only bounded ASCII tokens. Never interpolate raw client input
        # into FTS syntax or SQL.
        expression = " OR ".join('"' + token + '"' for token in sorted(set(tokens)))
        con = self._connect()
        try:
            con.execute("BEGIN")
            lexical = con.execute(
                "SELECT rowid FROM search_index "
                "WHERE tenant=? AND search_index MATCH ? "
                "ORDER BY bm25(search_index),rowid LIMIT 512",
                (tenant, expression)).fetchall()
            lexical_ranks = {pk: i+1 for i,(pk,) in enumerate(lexical)}
            qvec = _vector(tokens)
            query_terms=set(tokens)
            vectors = []
            rows = con.execute(
                "SELECT pk,document_id,title,body FROM documents WHERE tenant=?",
                (tenant,)).fetchall()
            for pk,doc_id,title,body in rows:
                dtokens=_terms(title+" "+body)
                # Lexical overlap prevents hash collisions creating unsupported
                # "semantic" matches from otherwise unrelated content.
                if not query_terms.intersection(dtokens):
                    continue
                sim=_similarity(qvec, _vector(dtokens))
                vectors.append((pk, sim))
            vectors.sort(key=lambda item:(-item[1], item[0]))
            vector_ranks={pk:i+1 for i,(pk,_) in enumerate(vectors)}
            result=[]
            for pk,doc_id,title,body in rows:
                if pk not in lexical_ranks and pk not in vector_ranks:
                    continue
                lr=lexical_ranks.get(pk)
                vr=vector_ranks.get(pk)
                score=(1/(FUSION_K+lr) if lr else 0)+(1/(FUSION_K+vr) if vr else 0)
                result.append({
                    "document_id":doc_id,
                    "title":title,
                    "snippet":" ".join(body[:160].split()),
                    "score":round(score,9),
                    "lexical_rank":lr,
                    "hashed_token_rank":vr,
                })
            result.sort(key=lambda row:(-row["score"],row["document_id"]))
            return result[:top_k]
        finally:
            if con.in_transaction:
                con.rollback()
            con.close()

    def evaluate(self, tenant: str, cases: list[dict], *, top_k: int = 5) -> dict:
        _id(tenant)
        if type(cases) is not list or not 1 <= len(cases) <= MAX_CASES:
            _fail("invalid_cases")
        if type(top_k) is not int or not 1 <= top_k <= 20:
            _fail("invalid_k")
        # Benchmark labels belong to the caller's trusted synthetic dataset,
        # not to search results. Do not fetch other tenants' document IDs.
        recall=0.0
        mrr=0.0
        ndcg=0.0
        for case in cases:
            if type(case) is not dict or set(case)!={"query","expected"}:
                _fail("invalid_case")
            expected=case["expected"]
            if type(expected) is not list or not expected or len(expected)>20:
                _fail("invalid_expected")
            if any(_id(doc) != doc for doc in expected) or len(set(expected)) != len(expected):
                _fail("invalid_expected")
            results=self.search(tenant, case["query"], top_k=top_k)
            returned=[result["document_id"] for result in results]
            hit=[i for i,doc in enumerate(returned) if doc in expected]
            recall+=len(hit)/len(expected)
            if hit:
                mrr+=1/(hit[0]+1)
            ideal=sum(1/math.log2(i+2) for i in range(min(top_k,len(expected))))
            ndcg+=sum(1/math.log2(i+2) for i in hit)/ideal
        n=len(cases)
        return {"status":"MEASURED_LOCAL",
                "cases":n,
                "recall_at_k":round(recall/n,6),
                "mrr_at_k":round(mrr/n,6),
                "ndcg_at_k":round(ndcg/n,6),
                "k":top_k,
                "scope":"Synthetic lexical retrieval only, not semantic model quality"}

    def audit(self, tenant: str) -> dict:
        _id(tenant)
        con=self._connect()
        try:
            con.execute("BEGIN")
            canonical=con.execute(
                "SELECT pk,tenant,document_id,title,body FROM documents "
                "WHERE tenant=? ORDER BY pk", (tenant,)).fetchall()
            indexed=con.execute(
                "SELECT rowid,tenant,document_id,title,body FROM search_index "
                "WHERE tenant=? ORDER BY rowid", (tenant,)).fetchall()
            if canonical != indexed:
                _fail("index_drift")
            return {"status":"PASS", "tenant_documents":len(canonical),
                    "scope":"Canonical/FTS mirrored row check, not tamper-proof storage"}
        finally:
            if con.in_transaction:
                con.rollback()
            con.close()
