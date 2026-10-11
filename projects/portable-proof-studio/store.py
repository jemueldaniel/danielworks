"""Original, dependency-free, local-only workflow and lexical evaluation service.

This is a demonstrator, NOT an internet-facing authentication or hosting stack.
No proprietary project code, external API calls, wallet, AI provider or personal data.
"""
from __future__ import annotations

import hashlib
import json
import re
import secrets
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable

_TOKEN = re.compile(r"^[A-Za-z0-9_\-]{16,128}$")
_KEY = re.compile(r"^[A-Za-z0-9_\-]{8,64}$")
_ID = re.compile(r"^[a-f0-9]{32}$")
_WORDS = re.compile(r"[a-z0-9]+")


class DemoError(Exception):
    def __init__(self, code: str, status: int = 400):
        self.code, self.status = code, status
        super().__init__(code)


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _object(value: Any, fields: set[str]) -> dict:
    if not isinstance(value, dict) or set(value) - fields:
        raise DemoError("INVALID_FIELDS")
    return value


def _text(value: Any, max_bytes: int, *, min_length: int = 1) -> str:
    if not isinstance(value, str) or len(value.strip()) < min_length or len(value.encode("utf-8")) > max_bytes:
        raise DemoError("INVALID_TEXT")
    return value


def _id(value: Any) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise DemoError("INVALID_ID")
    return value


def _key(value: Any) -> str:
    if not isinstance(value, str) or not _KEY.fullmatch(value):
        raise DemoError("INVALID_OPERATION_KEY")
    return value


class ProofStore:
    """SQLite-backed local exercise with transactionally bound replay receipts."""

    def __init__(self, db_path: str | Path, *, ttl_seconds: int = 3600):
        if not isinstance(ttl_seconds, int) or not 60 <= ttl_seconds <= 86400:
            raise ValueError("invalid ttl")
        self.path = str(db_path)
        self.ttl_seconds = ttl_seconds
        with self._db() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS workspaces(
              id TEXT PRIMARY KEY, token_hash TEXT NOT NULL UNIQUE,
              created REAL NOT NULL, expires REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS workflows(
              id TEXT PRIMARY KEY, workspace TEXT NOT NULL, title TEXT NOT NULL,
              revision INTEGER NOT NULL, config TEXT NOT NULL, created REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS runs(
              id TEXT PRIMARY KEY, workspace TEXT NOT NULL, workflow TEXT NOT NULL,
              workflow_revision INTEGER NOT NULL, input_digest TEXT NOT NULL,
              trace TEXT NOT NULL, artifact TEXT NOT NULL, created REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS artifacts(
              id TEXT PRIMARY KEY, workspace TEXT NOT NULL, run TEXT NOT NULL,
              content TEXT NOT NULL, content_digest TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS documents(
              id TEXT PRIMARY KEY, workspace TEXT NOT NULL, title TEXT NOT NULL,
              content TEXT NOT NULL, content_digest TEXT NOT NULL,
              revision INTEGER NOT NULL, source_run TEXT, created REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS evaluations(
              id TEXT PRIMARY KEY, workspace TEXT NOT NULL, query_digest TEXT NOT NULL,
              expected_document TEXT NOT NULL, observed_document TEXT,
              passed INTEGER NOT NULL, total INTEGER NOT NULL,
              corpus_digest TEXT NOT NULL, created REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS operations(
              workspace TEXT NOT NULL, operation_key TEXT NOT NULL,
              command TEXT NOT NULL, intent_digest TEXT NOT NULL,
              response TEXT NOT NULL,
              PRIMARY KEY(workspace, operation_key)
            );
            CREATE INDEX IF NOT EXISTS doc_ws ON documents(workspace);
            CREATE INDEX IF NOT EXISTS op_ws ON operations(workspace);
            """)

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.path, isolation_level=None, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA busy_timeout=5000")
            yield db
        finally:
            db.close()

    @staticmethod
    def _workspace(db: sqlite3.Connection, token: str) -> str:
        if not isinstance(token, str) or not _TOKEN.fullmatch(token):
            raise DemoError("SESSION_REQUIRED", 401)
        row = db.execute("SELECT id, expires FROM workspaces WHERE token_hash=?",
                         (_digest(token.encode("ascii")),)).fetchone()
        if row is None or row["expires"] < time.time():
            raise DemoError("SESSION_REQUIRED", 401)
        return str(row["id"])

    @staticmethod
    def _limit(db: sqlite3.Connection, table: str, workspace: str, cap: int):
        # Callers pass only internal constants, never user-controlled SQL names.
        if table not in {"workflows", "runs", "documents", "evaluations", "operations"}:
            raise AssertionError("table must be internal")
        n = db.execute(f"SELECT COUNT(*) FROM {table} WHERE workspace=?", (workspace,)).fetchone()[0]
        if n >= cap:
            raise DemoError("WORKSPACE_QUOTA", 429)

    def create_workspace(self) -> dict:
        # Guest IDs and bearer capabilities are random and opaque. Not human auth.
        token, workspace = secrets.token_urlsafe(32), uuid.uuid4().hex
        now = time.time()
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                if db.execute("SELECT COUNT(*) FROM workspaces").fetchone()[0] >= 64:
                    raise DemoError("SERVICE_QUOTA", 429)
                db.execute("INSERT INTO workspaces VALUES (?,?,?,?)",
                           (workspace, _digest(token.encode("ascii")), now, now+self.ttl_seconds))
                db.commit()
            except Exception:
                db.rollback()
                raise
        return {"workspaceToken": token, "expiresInSeconds": self.ttl_seconds,
                "mode": "local SQLite demo guest, not human identity"}

    def _write(self, token: str, key: str, command: str, payload: dict,
               operation: Callable[[sqlite3.Connection, str], dict]) -> dict:
        _key(key)
        intent = _digest(_json_bytes({"command": command, "payload": payload}))
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                w = self._workspace(db, token)  # Authority always precedes replay.
                old = db.execute("SELECT command, intent_digest, response FROM operations "
                                 "WHERE workspace=? AND operation_key=?", (w, key)).fetchone()
                if old is not None:
                    if old["command"] != command or old["intent_digest"] != intent:
                        raise DemoError("OPERATION_CONFLICT", 409)
                    response = json.loads(old["response"])
                    db.commit()
                    return response
                self._limit(db, "operations", w, 256)
                response = operation(db, w)
                db.execute("INSERT INTO operations VALUES (?,?,?,?,?)",
                           (w, key, command, intent, _json_bytes(response).decode("utf-8")))
                db.commit()
                return response
            except Exception:
                db.rollback()
                raise

    def list_workflows(self, token: str) -> list[dict]:
        with self._db() as db:
            w = self._workspace(db, token)
            return [dict(row) for row in db.execute(
                "SELECT id,title,revision,created FROM workflows WHERE workspace=? "
                "ORDER BY created DESC,id LIMIT 32", (w,))]

    def create_workflow(self, token: str, key: str, payload: dict) -> dict:
        _object(payload, {"title", "maxKeywords", "minLength"})
        title = _text(payload.get("title"), 160)
        maximum, minimum = payload.get("maxKeywords", 8), payload.get("minLength", 2)
        if type(maximum) is not int or not 1 <= maximum <= 16 or type(minimum) is not int or not 1 <= minimum <= 16:
            raise DemoError("INVALID_GRAPH_CONFIG")
        config = {"maxKeywords": maximum, "minLength": minimum,
                  "graph": ["input.text", "text.normalize", "text.keywords", "artifact.save"]}
        def effect(db, w):
            self._limit(db, "workflows", w, 32)
            i=uuid.uuid4().hex
            db.execute("INSERT INTO workflows VALUES (?,?,?,?,?,?)",
                       (i,w,title,1,_json_bytes(config).decode(),time.time()))
            return {"workflowId":i,"title":title,"revision":1,"config":config}
        return self._write(token,key,"workflow.create",{"title":title,"config":config},effect)

    def update_workflow(self, token: str, key: str, payload: dict) -> dict:
        _object(payload, {"workflowId", "title", "expectedRevision", "maxKeywords", "minLength"})
        workflow_id = _id(payload.get("workflowId"))
        title = _text(payload.get("title"), 160)
        revision = payload.get("expectedRevision")
        maximum, minimum = payload.get("maxKeywords", 8), payload.get("minLength", 2)
        if (type(revision) is not int or revision < 1 or type(maximum) is not int
                or not 1 <= maximum <= 16 or type(minimum) is not int or not 1 <= minimum <= 16):
            raise DemoError("INVALID_GRAPH_CONFIG")
        config = {"maxKeywords": maximum, "minLength": minimum,
                  "graph": ["input.text", "text.normalize", "text.keywords", "artifact.save"]}
        intent = {"workflowId": workflow_id, "title": title, "expectedRevision": revision, "config": config}
        def effect(db, w):
            row = db.execute("SELECT revision FROM workflows WHERE id=? AND workspace=?",
                             (workflow_id, w)).fetchone()
            if row is None: raise DemoError("WORKFLOW_NOT_FOUND", 404)
            if row["revision"] != revision: raise DemoError("STALE_REVISION", 409)
            db.execute("UPDATE workflows SET title=?,revision=?,config=? WHERE id=? AND workspace=?",
                       (title, revision+1, _json_bytes(config).decode(), workflow_id, w))
            return {"workflowId":workflow_id,"title":title,"revision":revision+1,"config":config}
        return self._write(token,key,"workflow.update",intent,effect)

    def run_workflow(self, token: str, key: str, payload: dict) -> dict:
        _object(payload, {"workflowId", "text"})
        workflow_id, input_text = _id(payload.get("workflowId")), _text(payload.get("text"), 4096)
        def effect(db,w):
            row=db.execute("SELECT revision,config FROM workflows WHERE id=? AND workspace=?",
                           (workflow_id,w)).fetchone()
            if row is None:raise DemoError("WORKFLOW_NOT_FOUND",404)
            self._limit(db,"runs",w,64)
            config=json.loads(row["config"])
            normalized=" ".join(input_text.casefold().split())
            seen=set(); words=[]
            for word in _WORDS.findall(normalized):
                if len(word)>=config["minLength"] and word not in seen:
                    seen.add(word);words.append(word)
                    if len(words)>=config["maxKeywords"]:break
            artifact_text="\n".join(words)
            trace=[{"step":"input.text","status":"succeeded","bytes":len(input_text.encode())},
                   {"step":"text.normalize","status":"succeeded","text":normalized},
                   {"step":"text.keywords","status":"succeeded","keywords":words},
                   {"step":"artifact.save","status":"succeeded","sha256":_digest(artifact_text.encode())}]
            run,artifact=uuid.uuid4().hex,uuid.uuid4().hex
            db.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?,?)",
                       (run,w,workflow_id,row["revision"],_digest(input_text.encode()),
                        _json_bytes(trace).decode(),artifact,time.time()))
            db.execute("INSERT INTO artifacts VALUES (?,?,?,?,?)",
                       (artifact,w,run,artifact_text,_digest(artifact_text.encode())))
            return {"runId":run,"workflowId":workflow_id,"revision":row["revision"],
                    "status":"succeeded","trace":trace,"artifactId":artifact,
                    "artifactText":artifact_text,"artifactSha256":_digest(artifact_text.encode()),
                    "limits":"four synchronous deterministic steps; no external tools"}
        return self._write(token,key,"workflow.run",{"workflowId":workflow_id,"text":input_text},effect)

    def get_run(self, token: str, run_id: str) -> dict:
        _id(run_id)
        with self._db() as db:
            w=self._workspace(db,token)
            row=db.execute("SELECT id,workflow,workflow_revision,input_digest,trace,artifact "
                           "FROM runs WHERE id=? AND workspace=?", (run_id,w)).fetchone()
            if row is None: raise DemoError("RUN_NOT_FOUND",404)
            a=db.execute("SELECT content,content_digest FROM artifacts WHERE id=? AND workspace=?",
                         (row["artifact"],w)).fetchone()
            if a is None:raise DemoError("ARTIFACT_NOT_FOUND",404)
            return {"runId":row["id"],"workflowId":row["workflow"],
                    "revision":row["workflow_revision"],"inputSha256":row["input_digest"],
                    "trace":json.loads(row["trace"]),"status":"succeeded",
                    "artifactText":a["content"],"artifactSha256":a["content_digest"]}

    def create_document(self, token: str, key: str, payload: dict) -> dict:
        _object(payload,{"title","text","sourceRunId"})
        title=_text(payload.get("title"),160)
        source=payload.get("sourceRunId")
        if source is not None:
            source=_id(source)
            if "text" in payload:raise DemoError("AMBIGUOUS_SOURCE")
            intent={"title":title,"sourceRunId":source}
        else:
            data=_text(payload.get("text"),4096)
            intent={"title":title,"text":data}
        def effect(db,w):
            self._limit(db,"documents",w,64)
            if source is not None:
                row=db.execute("SELECT a.content FROM artifacts a JOIN runs r ON a.run=r.id "
                               "WHERE r.id=? AND a.workspace=? AND r.workspace=?",(source,w,w)).fetchone()
                if row is None:raise DemoError("SOURCE_RUN_NOT_FOUND",404)
                text=row["content"]
                if not text:raise DemoError("EMPTY_SOURCE_ARTIFACT")
            else:text=data
            i=uuid.uuid4().hex
            dg=_digest(text.encode())
            db.execute("INSERT INTO documents VALUES (?,?,?,?,?,?,?,?)",
                       (i,w,title,text,dg,1,source,time.time()))
            return {"documentId":i,"title":title,"revision":1,"sha256":dg,
                    "sourceRunId":source,"bytes":len(text.encode())}
        return self._write(token,key,"document.create",intent,effect)

    def list_documents(self, token: str) -> list[dict]:
        with self._db() as db:
            w=self._workspace(db,token)
            return [dict(x) for x in db.execute("SELECT id,title,revision,content_digest,source_run "
                "FROM documents WHERE workspace=? ORDER BY created DESC,id LIMIT 64",(w,))]

    def update_document(self, token: str, key: str, payload: dict) -> dict:
        _object(payload, {"documentId", "title", "text", "expectedRevision"})
        doc = _id(payload.get("documentId"))
        title = _text(payload.get("title"), 160)
        value = _text(payload.get("text"), 4096)
        rev = payload.get("expectedRevision")
        if type(rev) is not int or rev < 1:
            raise DemoError("INVALID_REVISION")
        intent = {"documentId":doc, "title":title, "text":value,"expectedRevision":rev}
        def effect(db,w):
            row=db.execute("SELECT revision FROM documents WHERE id=? AND workspace=?",(doc,w)).fetchone()
            if row is None:raise DemoError("DOCUMENT_NOT_FOUND",404)
            if row["revision"] != rev:raise DemoError("STALE_REVISION",409)
            dg=_digest(value.encode())
            db.execute("UPDATE documents SET title=?,content=?,content_digest=?,revision=?,source_run=NULL "
                       "WHERE id=? AND workspace=?", (title,value,dg,rev+1,doc,w))
            return {"documentId":doc,"title":title,"sha256":dg,"revision":rev+1,
                    "sourceRunId":None,"bytes":len(value.encode())}
        return self._write(token,key,"document.update",intent,effect)

    def delete_document(self,token:str,key:str,payload:dict)->dict:
        _object(payload,{"documentId"})
        doc=_id(payload.get("documentId"))
        def effect(db,w):
            n=db.execute("DELETE FROM documents WHERE id=? AND workspace=?",(doc,w)).rowcount
            if n!=1:raise DemoError("DOCUMENT_NOT_FOUND",404)
            return {"documentId":doc,"deleted":True,"scope":"active SQLite documents only; no backup purge"}
        return self._write(token,key,"document.delete",{"documentId":doc},effect)

    @staticmethod
    def _rank(docs: list[sqlite3.Row], query: str) -> list[dict]:
        # ASCII lexical tokens and original-source offsets, not embeddings or semantics.
        terms=set(_WORDS.findall(query.casefold()))
        if not terms:raise DemoError("EMPTY_QUERY")
        ranked=[]
        for d in docs:
            tokens=[(m.group(0).lower(),m.start()) for m in
                    re.finditer(r"[A-Za-z0-9]+",d["content"])]
            hits=[(word,pos) for word,pos in tokens if word in terms]
            if hits:
                pos=min(p for _,p in hits)
                snippet=d["content"][max(0,pos-50):min(len(d["content"]),pos+100)]
                ranked.append({"documentId":d["id"],"title":d["title"],
                               "revision":d["revision"],"documentSha256":d["content_digest"],
                               "score":len(hits),"snippet":snippet})
        ranked.sort(key=lambda d:(-d["score"],d["documentId"]))
        return ranked[:10]

    def search(self,token:str, payload:dict)->dict:
        _object(payload,{"query"})
        q=_text(payload.get("query"),160)
        with self._db() as db:
            w=self._workspace(db,token)
            docs=list(db.execute("SELECT id,title,revision,content,content_digest FROM documents "
                                "WHERE workspace=? ORDER BY id",(w,)))
            ranked=self._rank(docs,q)
            corpus=_digest(_json_bytes([[r["id"],r["content_digest"],r["revision"]] for r in docs]))
            return {"candidate":"deterministic lexical token counts","query":q,"corpusSha256":corpus,
                    "results":ranked,"totalDocuments":len(docs)}

    def evaluate(self,token:str,key:str,payload:dict)->dict:
        _object(payload,{"query","expectedDocumentId"})
        q=_text(payload.get("query"),160)
        expected=_id(payload.get("expectedDocumentId"))
        def effect(db,w):
            self._limit(db,"evaluations",w,64)
            docs=list(db.execute("SELECT id,title,revision,content,content_digest FROM documents "
                                 "WHERE workspace=? ORDER BY id",(w,)))
            if not any(d["id"]==expected for d in docs):raise DemoError("EXPECTED_DOCUMENT_NOT_FOUND",404)
            ranked=self._rank(docs,q)
            observed=ranked[0]["documentId"] if ranked else None
            ok=observed==expected
            corpus=_digest(_json_bytes([[r["id"],r["content_digest"],r["revision"]] for r in docs]))
            i=uuid.uuid4().hex
            db.execute("INSERT INTO evaluations VALUES (?,?,?,?,?,?,?,?,?)",
                       (i,w,_digest(q.encode()),expected,observed,int(ok),1,corpus,time.time()))
            return {"evaluationId":i,"metric":"top-1 exact document ID", "passed":ok,
                    "correct":int(ok),"total":1,"coverage":"1/1", "expectedDocumentId":expected,
                    "observedDocumentId":observed,"corpusSha256":corpus}
        return self._write(token,key,"evaluation.run",{"query":q,"expectedDocumentId":expected},effect)

    def list_evaluations(self,token:str)->list[dict]:
        with self._db() as db:
            w=self._workspace(db,token)
            return [dict(x) for x in db.execute("SELECT id,expected_document,observed_document,passed,total,corpus_digest "
                 "FROM evaluations WHERE workspace=? ORDER BY created DESC,id LIMIT 64",(w,))]
