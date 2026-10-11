"""Synthetic, offline, double-entry SQLite ledger reference.

Journal postings are zero-sum per transfer, balance cache updates are atomic,
and request IDs are bound to their exact arguments. No real money or identity.
"""
from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re
import sqlite3
from typing import Callable, TypeVar

_ID = re.compile(r"[a-z][a-z0-9_-]{1,47}\Z")
_ASSET = re.compile(r"[A-Z][A-Z0-9]{0,7}\Z")
MAX_AMOUNT = 1_000_000_000_000
MAX_BALANCE = 1_000_000_000_000_000
ZERO = "0" * 64
T = TypeVar("T")


class LedgerError(ValueError):
    """A safe symbolic failure, not a financial or authorization decision."""
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _fail(code: str) -> None:
    raise LedgerError(code)


def _id(value: object, label: str) -> str:
    if type(value) is not str or not _ID.fullmatch(value):
        _fail("invalid_" + label)
    return value


def _asset(value: object) -> str:
    if type(value) is not str or not _ASSET.fullmatch(value):
        _fail("invalid_asset")
    return value


def _amount(value: object) -> int:
    if type(value) is not int or not 1 <= value <= MAX_AMOUNT:
        _fail("invalid_amount")
    return value


def _payload(tenant: str, txid: str, source: str, target: str, asset: str,
             amount: int) -> bytes:
    return json.dumps([tenant, txid, source, target, asset, amount],
                      separators=(",", ":"), ensure_ascii=True).encode("ascii")


class Ledger:
    """A trusted caller supplies a tenant; this example DOES NOT authenticate it.

    Ordinary accounts cannot go negative. Clearing accounts can issue synthetic
    training balances; they are not real funds or safe external funding rails.
    """

    def __init__(self, database: str | Path) -> None:
        if not isinstance(database, (str, Path)):
            _fail("invalid_database")
        self.database = Path(database).absolute()
        if not self.database.parent.is_dir():
            _fail("invalid_database_parent")
        con = self._connect()
        try:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS accounts (
                    tenant TEXT NOT NULL,
                    account TEXT NOT NULL,
                    asset TEXT NOT NULL,
                    kind TEXT NOT NULL CHECK (kind IN ('ordinary','clearing')),
                    balance INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (tenant, account)
                );
                CREATE TABLE IF NOT EXISTS transfers (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant TEXT NOT NULL,
                    txid TEXT NOT NULL,
                    source TEXT NOT NULL,
                    target TEXT NOT NULL,
                    asset TEXT NOT NULL,
                    amount INTEGER NOT NULL CHECK (amount > 0),
                    request_sha TEXT NOT NULL,
                    previous_sha TEXT NOT NULL,
                    chain_sha TEXT NOT NULL,
                    UNIQUE (tenant, txid),
                    FOREIGN KEY (tenant, source) REFERENCES accounts(tenant,account),
                    FOREIGN KEY (tenant, target) REFERENCES accounts(tenant,account)
                );
                CREATE TABLE IF NOT EXISTS postings (
                    tenant TEXT NOT NULL,
                    txid TEXT NOT NULL,
                    leg INTEGER NOT NULL CHECK (leg IN (0,1)),
                    account TEXT NOT NULL,
                    asset TEXT NOT NULL,
                    delta INTEGER NOT NULL CHECK (delta != 0),
                    PRIMARY KEY (tenant,txid,leg),
                    FOREIGN KEY (tenant,txid) REFERENCES transfers(tenant,txid),
                    FOREIGN KEY (tenant,account) REFERENCES accounts(tenant,account)
                );
            """)
        finally:
            con.close()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(str(self.database), timeout=10, isolation_level=None)
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("PRAGMA busy_timeout=10000")
        return con

    def _tx(self, action: Callable[[sqlite3.Connection], T]) -> T:
        con = self._connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            result = action(con)
            con.commit()
            return result
        except sqlite3.IntegrityError as exc:
            con.rollback()
            raise LedgerError("storage_constraint") from exc
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def create_account(self, tenant: str, account: str, asset: str,
                       *, kind: str = "ordinary") -> str:
        _id(tenant, "tenant")
        _id(account, "account")
        _asset(asset)
        if kind not in ("ordinary", "clearing") or type(kind) is not str:
            _fail("invalid_kind")

        def insert(con: sqlite3.Connection) -> str:
            present = con.execute(
                "SELECT asset,kind FROM accounts WHERE tenant=? AND account=?",
                (tenant, account)).fetchone()
            if present is not None:
                if present != (asset, kind):
                    _fail("account_definition_conflict")
                return "existing"
            con.execute(
                "INSERT INTO accounts(tenant,account,asset,kind) VALUES(?,?,?,?)",
                (tenant, account, asset, kind))
            return "created"
        return self._tx(insert)

    def transfer(self, tenant: str, txid: str, source: str, target: str,
                 asset: str, amount: int) -> dict:
        _id(tenant, "tenant")
        _id(txid, "request")
        _id(source, "source")
        _id(target, "target")
        _asset(asset)
        _amount(amount)
        if source == target:
            _fail("same_account")
        payload = _payload(tenant, txid, source, target, asset, amount)
        request_sha = sha256(payload).hexdigest()

        def commit(con: sqlite3.Connection) -> dict:
            prior = con.execute(
                "SELECT request_sha,chain_sha FROM transfers WHERE tenant=? AND txid=?",
                (tenant, txid)).fetchone()
            if prior is not None:
                if prior[0] != request_sha:
                    _fail("idempotency_conflict")
                return {"status": "replayed", "request_sha256": prior[0],
                        "chain_sha256": prior[1]}
            accounts = con.execute(
                "SELECT account,asset,kind,balance FROM accounts "
                "WHERE tenant=? AND account IN (?,?)",
                (tenant, source, target)).fetchall()
            found = {name: (item_asset, kind, balance)
                     for name, item_asset, kind, balance in accounts}
            if set(found) != {source, target}:
                _fail("account_not_found")
            if found[source][0] != asset or found[target][0] != asset:
                _fail("asset_mismatch")
            start = found[source][2]
            end = found[target][2]
            if found[source][1] == "ordinary" and start < amount:
                _fail("insufficient_funds")
            if abs(start - amount) > MAX_BALANCE or abs(end + amount) > MAX_BALANCE:
                _fail("balance_limit")
            prev_row = con.execute(
                "SELECT chain_sha FROM transfers WHERE tenant=? ORDER BY seq DESC LIMIT 1",
                (tenant,)).fetchone()
            previous_sha = prev_row[0] if prev_row else ZERO
            chain_sha = sha256(bytes.fromhex(previous_sha) + payload).hexdigest()
            con.execute(
                "INSERT INTO transfers(tenant,txid,source,target,asset,amount,"
                "request_sha,previous_sha,chain_sha) VALUES(?,?,?,?,?,?,?,?,?)",
                (tenant, txid, source, target, asset, amount, request_sha,
                 previous_sha, chain_sha))
            con.executemany(
                "INSERT INTO postings(tenant,txid,leg,account,asset,delta) "
                "VALUES(?,?,?,?,?,?)",
                [(tenant, txid, 0, source, asset, -amount),
                 (tenant, txid, 1, target, asset, amount)])
            con.execute(
                "UPDATE accounts SET balance=balance-? WHERE tenant=? AND account=?",
                (amount, tenant, source))
            con.execute(
                "UPDATE accounts SET balance=balance+? WHERE tenant=? AND account=?",
                (amount, tenant, target))
            return {"status": "posted", "request_sha256": request_sha,
                    "chain_sha256": chain_sha}
        return self._tx(commit)

    def balances(self, tenant: str) -> dict[str, int]:
        _id(tenant, "tenant")
        con = self._connect()
        try:
            return {name: bal for name,bal in con.execute(
                "SELECT account,balance FROM accounts WHERE tenant=? ORDER BY account",
                (tenant,))}
        finally:
            con.close()

    def audit(self, tenant: str) -> dict:
        """Detect ordinary storage inconsistencies; not a keyed anti-tamper audit."""
        _id(tenant, "tenant")
        con = self._connect()
        try:
            con.execute("BEGIN")
            accounts = {
                row[0]: {"asset": row[1], "kind": row[2], "balance": row[3]}
                for row in con.execute(
                    "SELECT account,asset,kind,balance FROM accounts WHERE tenant=?",
                    (tenant,))}
            expected = defaultdict(int)
            current = ZERO
            count = 0
            for txid,source,target,asset,amount,request_hash,prev,chain in con.execute(
                "SELECT txid,source,target,asset,amount,request_sha,previous_sha,chain_sha "
                "FROM transfers WHERE tenant=? ORDER BY seq", (tenant,)):
                count += 1
                payload = _payload(tenant, txid, source, target, asset, amount)
                if request_hash != sha256(payload).hexdigest() or prev != current:
                    _fail("journal_integrity")
                current = sha256(bytes.fromhex(current) + payload).hexdigest()
                if chain != current or source not in accounts or target not in accounts:
                    _fail("journal_integrity")
                if source == target or accounts[source]["asset"] != asset or accounts[target]["asset"] != asset:
                    _fail("journal_integrity")
                legs = con.execute(
                    "SELECT leg,account,asset,delta FROM postings "
                    "WHERE tenant=? AND txid=? ORDER BY leg", (tenant, txid)).fetchall()
                if legs != [(0, source, asset, -amount), (1, target, asset, amount)]:
                    _fail("unbalanced_postings")
                expected[source] -= amount
                expected[target] += amount
            for account, row in accounts.items():
                if row["balance"] != expected[account]:
                    _fail("balance_cache_drift")
            totals = defaultdict(int)
            for account, row in accounts.items():
                totals[row["asset"]] += row["balance"]
            if any(total != 0 for total in totals.values()):
                _fail("asset_not_balanced")
            orphan = con.execute(
                "SELECT COUNT(*) FROM postings p LEFT JOIN transfers t "
                "ON p.tenant=t.tenant AND p.txid=t.txid "
                "WHERE p.tenant=? AND t.txid IS NULL", (tenant,)).fetchone()[0]
            if orphan:
                _fail("orphan_postings")
            return {"status": "PASS", "tenant_accounts": len(accounts),
                    "transfers": count, "asset_count": len(totals),
                    "all_assets_zero_sum": True, "chain_sha256": current,
                    "scope": "internal SQLite consistency only; not a security or financial certification"}
        except (sqlite3.DatabaseError, ValueError) as exc:
            if isinstance(exc, LedgerError):
                raise
            raise LedgerError("journal_integrity") from exc
        finally:
            # Explicitly close the read transaction before releasing the
            # database handle, including deliberate-corruption test paths.
            if con.in_transaction:
                con.rollback()
            con.close()
