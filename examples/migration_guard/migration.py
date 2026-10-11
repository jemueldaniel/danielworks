"""Original educational SQLite migration gate, for trusted release SQL only."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib,re,sqlite3
ID=re.compile(r"[a-z][a-z0-9_]{1,39}\Z")
class MigrationError(ValueError):
    def __init__(self,code):
        self.code=code
        super().__init__(code)
@dataclass(frozen=True)
class Change:
    key:str
    sql:str
    sha256:str
def define(key,sql):
    if type(key) is not str or not ID.fullmatch(key):raise MigrationError("invalid_change_id")
    if type(sql) is not str or not 1<=len(sql)<=10000 or "\x00" in sql:
        raise MigrationError("invalid_sql")
    return Change(key,sql,hashlib.sha256(sql.encode("utf-8")).hexdigest())
class Gate:
    """Atomic migrations with append-only history; not a production manager."""
    def __init__(self,path):
        if not isinstance(path,(str,Path)) or not Path(path).absolute().parent.is_dir():
            raise MigrationError("invalid_database_path")
        self.path=Path(path).absolute()
        con=self._connect()
        try:
            con.execute("""CREATE TABLE IF NOT EXISTS _public_migrations (
                seq INTEGER PRIMARY KEY, change_id TEXT NOT NULL UNIQUE,
                sha256 TEXT NOT NULL, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")
        finally:con.close()
    def _connect(self):
        con=sqlite3.connect(self.path,timeout=8,isolation_level=None)
        con.execute("PRAGMA busy_timeout=8000")
        return con
    def apply(self,changes):
        if type(changes) is not list or not changes or len(changes)>100 or any(type(c) is not Change for c in changes):
            raise MigrationError("invalid_plan")
        if len(set(c.key for c in changes))!=len(changes):raise MigrationError("duplicate_change_id")
        if any(define(c.key,c.sql).sha256!=c.sha256 for c in changes):
            raise MigrationError("invalid_change_digest")
        con=self._connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            current=con.execute("SELECT seq,change_id,sha256 FROM _public_migrations ORDER BY seq").fetchall()
            if len(current)>len(changes):raise MigrationError("missing_historical_changes")
            for i,(_,key,digest) in enumerate(current):
                if changes[i].key!=key or changes[i].sha256!=digest:
                    raise MigrationError("historical_change_drift")
            fresh=[]
            for i in range(len(current),len(changes)):
                change=changes[i]
                con.execute(change.sql)
                con.execute("INSERT INTO _public_migrations(seq,change_id,sha256) VALUES(?,?,?)",
                            (i+1,change.key,change.sha256))
                fresh.append(change.key)
            con.commit()
            return {"status":"PASS","new":fresh,"total":len(changes),
                    "applied_count":len(fresh),"scope":"local trusted SQLite SQL only"}
        except sqlite3.DatabaseError as exc:
            if con.in_transaction:con.rollback()
            raise MigrationError("sql_execution_failed") from exc
        except Exception:
            if con.in_transaction:con.rollback()
            raise
        finally:con.close()
    def version(self):
        con=self._connect()
        try:return con.execute("SELECT change_id,sha256 FROM _public_migrations ORDER BY seq").fetchall()
        finally:con.close()
