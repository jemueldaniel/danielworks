"""Persistent retrieval evaluation, composed with the preserved queue and grader.

All data is synthetic. SQLite is a real local database, not PostgreSQL and not an
identity provider. Each operation owns its connection; no connection crosses threads.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
import time
from typing import Any, Callable, Iterator

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from examples.durable_jobs.jobs import JobQueue, Lease, LeaseLost, Conflict, identifier, integer
from examples.ranking_eval.evaluation import evaluate, load_dataset
from examples.retrieval_lab.retrieval import index as lexical_index, retrieve as lexical_retrieve

FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures' / 'corpus.v1.json'

class InvalidInput(ValueError):
    """Public, fixed error code; never includes submitted content."""
    def __init__(self, code: str = 'invalid_input'):
        super().__init__(code)
        self.code = code

class CheckpointError(RuntimeError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def checked_id(value: Any) -> str:
    try:
        return identifier(value)
    except (ValueError, TypeError):
        raise InvalidInput() from None


def checked_int(value: Any, low: int, high: int) -> int:
    try:
        return integer(value, low, high)
    except (ValueError, TypeError):
        raise InvalidInput() from None


class Store:
    def __init__(self, path: str | Path, *, clock: Callable[[], int] | None = None):
        self.path = Path(path)
        self.clock = clock or (lambda: time.time_ns() // 1_000_000)
        self.dataset = load_dataset(FIXTURE)
        self.input_digest = digest(self.dataset)
        self._lexical = lexical_index(self.dataset['documents'])
        # The library owns its original table and state machine. No copied queue logic.
        with JobQueue(self.path):
            pass
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            try:
                version = db.execute('PRAGMA user_version').fetchone()[0]
                if version not in (0, 1):
                    raise CheckpointError('unknown_database_version')
                db.execute('CREATE TABLE IF NOT EXISTS workbench_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
                db.execute('''CREATE TABLE IF NOT EXISTS checkpoints (
                    tenant TEXT NOT NULL, job_key TEXT NOT NULL, query_id TEXT NOT NULL,
                    ranking TEXT NOT NULL, checksum TEXT NOT NULL, input_digest TEXT NOT NULL,
                    request_digest TEXT NOT NULL, generation INTEGER NOT NULL,
                    PRIMARY KEY(tenant,job_key,query_id),
                    FOREIGN KEY(tenant,job_key) REFERENCES jobs(tenant,key))''')
                db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(id UNINDEXED, text, tokenize='unicode61')")
                existing = db.execute("SELECT value FROM workbench_meta WHERE key='input_digest'").fetchone()
                if existing is not None and existing[0] != self.input_digest:
                    raise CheckpointError('dataset_version_mismatch')
                if existing is None:
                    for doc in self.dataset['documents']:
                        db.execute('INSERT INTO documents_fts(id,text) VALUES(?,?)', (doc['id'], doc['text']))
                    db.execute("INSERT INTO workbench_meta VALUES('input_digest',?)", (self.input_digest,))
                db.execute('PRAGMA user_version=1')
                db.commit()
            except BaseException:
                db.rollback()
                raise

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=1.0)
        db.row_factory = sqlite3.Row
        try:
            db.execute('PRAGMA foreign_keys=ON')
            with db:
                yield db
        finally:
            db.close()

    def description(self) -> dict[str, Any]:
        return {'version': self.dataset['version'], 'sha256': self.input_digest,
                'document_count': len(self.dataset['documents']), 'query_count': len(self.dataset['queries']),
                'engines': ['fts5', 'lexical'], 'known_failure': 'q-synonym', 'synthetic': True}

    def submit(self, tenant: str, body: Any) -> dict[str, Any]:
        tenant = checked_id(tenant)
        if type(body) is not dict or set(body) != {'key', 'engine', 'k'}:
            raise InvalidInput()
        key = checked_id(body['key'])
        if body['engine'] not in ('fts5', 'lexical'):
            raise InvalidInput()
        k = checked_int(body['k'], 1, 3)
        payload = {'engine': body['engine'], 'k': k, 'input_digest': self.input_digest,
                   'version': self.dataset['version']}
        try:
            with JobQueue(self.path) as queue:
                queue.submit(tenant, key, payload, now=self.clock())
        except Conflict:
            raise InvalidInput('idempotency_conflict') from None
        value = self.inspect(tenant, key)
        assert value is not None
        return value

    def inspect(self, tenant: str, key: str) -> dict[str, Any] | None:
        tenant, key = checked_id(tenant), checked_id(key)
        with JobQueue(self.path) as queue:
            row = queue.inspect(tenant, key)
        if row is None:
            return None
        with self._connect() as db:
            count = db.execute('SELECT count(*) FROM checkpoints WHERE tenant=? AND job_key=?', (tenant, key)).fetchone()[0]
        return {'key': key, 'state': row['state'], 'engine': row['payload']['engine'], 'k': row['payload']['k'],
                'input_digest': row['payload']['input_digest'], 'generation': row['generation'],
                'attempts': row['attempts'], 'checkpoint_count': count, 'result': row['result']}

    def list(self, tenant: str, *, cursor: str | None = None, limit: int = 10) -> dict[str, Any]:
        tenant, limit = checked_id(tenant), checked_int(limit, 1, 20)
        after = '' if cursor is None else checked_id(cursor)
        with self._connect() as db:
            rows = db.execute('SELECT key FROM jobs WHERE tenant=? AND key>? ORDER BY key LIMIT ?', (tenant, after, limit+1)).fetchall()
        keys = [row['key'] for row in rows[:limit]]
        return {'items': [self.inspect(tenant, key) for key in keys],
                'next_cursor': keys[-1] if len(rows) > limit else None}

    def cancel(self, tenant: str, key: str) -> bool:
        with JobQueue(self.path) as queue:
            return queue.cancel(checked_id(tenant), checked_id(key))

    def search(self, query: str, k: int = 2) -> list[dict[str, Any]]:
        k = checked_int(k, 1, 3)
        if type(query) is not str or not 1 <= len(query) <= 500:
            raise InvalidInput()
        # Literal terms only: no user-supplied FTS operators or SQL syntax.
        terms = list(dict.fromkeys(re.findall(r'[a-z0-9]+', query.lower())))[:12]
        if not terms:
            return []
        expression = ' OR '.join('"'+term+'"' for term in terms)
        with self._connect() as db:
            rows = db.execute('''SELECT id,text,bm25(documents_fts) AS score FROM documents_fts
                                 WHERE documents_fts MATCH ? ORDER BY score,id LIMIT ?''', (expression, k)).fetchall()
        return [dict(row) for row in rows]

    def _previous(self, lease: Lease) -> dict[str, list[str]]:
        expected_ids = {item['id'] for item in self.dataset['queries']}
        docs = {item['id'] for item in self.dataset['documents']}
        request_digest = digest(lease.payload)
        output: dict[str, list[str]] = {}
        with self._connect() as db:
            rows = db.execute('SELECT * FROM checkpoints WHERE tenant=? AND job_key=?', (lease.tenant, lease.key)).fetchall()
        for row in rows:
            try:
                ranking = json.loads(row['ranking'])
                valid = (row['query_id'] in expected_ids and type(ranking) is list
                         and all(type(x) is str and x in docs for x in ranking)
                         and len(ranking) <= lease.payload['k'] and len(set(ranking)) == len(ranking)
                         and row['input_digest'] == self.input_digest and row['request_digest'] == request_digest
                         and row['checksum'] == digest({'query_id': row['query_id'], 'ranking': ranking, 'request_digest': request_digest}))
                if not valid:
                    raise ValueError()
            except (ValueError, TypeError, KeyError):
                raise CheckpointError('checkpoint_corrupt') from None
            output[row['query_id']] = ranking
        return output

    def _checkpoint(self, lease: Lease, query_id: str, ranking: list[str]) -> None:
        request_digest = digest(lease.payload)
        checksum = digest({'query_id': query_id, 'ranking': ranking, 'request_digest': request_digest})
        now = self.clock()
        # This adapter deliberately couples to the preserved queue's table schema.
        # One SQL statement atomically checks its fence and writes a checkpoint.
        # It never updates lease/state columns owned by JobQueue.
        with self._connect() as db:
            result = db.execute('''INSERT INTO checkpoints
                (tenant,job_key,query_id,ranking,checksum,input_digest,request_digest,generation)
                SELECT tenant,key,?,?,?,?,?,generation FROM jobs
                WHERE tenant=? AND key=? AND generation=? AND state='running'
                  AND leased_at<=? AND lease_until>?''',
                (query_id, canonical(ranking), checksum, self.input_digest, request_digest,
                 lease.tenant, lease.key, lease.generation, now, now))
            if result.rowcount != 1:
                raise LeaseLost('checkpoint_fence_lost')

    def work(self, tenant: str, *, max_cases: int = 5, lease_ms: int = 30_000,
             observer: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
        tenant = checked_id(tenant)
        max_cases, lease_ms = checked_int(max_cases, 1, 5), checked_int(lease_ms, 1, 1_000_000)
        with JobQueue(self.path) as queue:
            lease = queue.claim(tenant, now=self.clock(), lease_ticks=lease_ms)
            if lease is None:
                return {'job': None, 'processed_cases': 0}
            if (type(lease.payload) is not dict or set(lease.payload) != {'engine','k','input_digest','version'}
                    or lease.payload['input_digest'] != self.input_digest
                    or lease.payload['version'] != self.dataset['version']
                    or lease.payload['engine'] not in ('fts5','lexical')
                    or type(lease.payload['k']) is not int or not 1 <= lease.payload['k'] <= 3):
                raise CheckpointError('request_corrupt')
            previous = self._previous(lease)
            resumed, processed = len(previous), 0
            try:
                for case in self.dataset['queries']:
                    if case['id'] in previous:
                        continue
                    if processed >= max_cases:
                        break  # finite work budget; expiry/reclaim enables recovery
                    hits = (self.search(case['query'], lease.payload['k']) if lease.payload['engine']=='fts5'
                            else lexical_retrieve(self._lexical, case['query'], lease.payload['k']))
                    ranking = [hit['id'] for hit in hits]
                    self._checkpoint(lease, case['id'], ranking)
                    previous[case['id']] = ranking
                    processed += 1
                    if observer:
                        observer({'event':'checkpoint','key':lease.key,'generation':lease.generation,'completed':len(previous)})
                if len(previous) == len(self.dataset['queries']):
                    dataset = {'schema':'ranking-eval.v1', 'corpus':[doc['id'] for doc in self.dataset['documents']],
                               'training_query_ids':[], 'queries':[
                                   {'id':case['id'],'relevant':case['relevant'],'retrieved':previous[case['id']]}
                                   for case in self.dataset['queries']]}
                    report = evaluate(dataset, k=lease.payload['k'])
                    report['failures'] = [case for case in dataset['queries'] if not set(case['relevant']).intersection(case['retrieved'][:1])]
                    report['input_digest'] = self.input_digest
                    report['resumed_cases'] = resumed
                    queue.complete(lease, report, now=self.clock())
            except LeaseLost:
                pass  # cancellation or another generation wins, never force completion
        return {'job':self.inspect(tenant,lease.key), 'processed_cases':processed}
