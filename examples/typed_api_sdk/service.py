from __future__ import annotations
import hashlib, json
from dataclasses import dataclass
from typing import Any

class ApiError(Exception):
    def __init__(self, code: str, status: int = 400):
        super().__init__(code); self.code=code; self.status=status

@dataclass(frozen=True)
class Item:
    item_id: str
    owner_id: str
    name: str
    version: int = 1

class ItemService:
    def __init__(self):
        self._items: dict[str, Item] = {}
        self._idem: dict[tuple[str,str], tuple[str,str]] = {}

    @staticmethod
    def _digest(payload: dict[str, Any]) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def create(self, *, owner_id: str, idempotency_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not owner_id or not isinstance(owner_id, str): raise ApiError("invalid_owner")
        if not idempotency_key or not isinstance(idempotency_key, str): raise ApiError("invalid_idempotency_key")
        if set(payload) != {"name"} or not isinstance(payload["name"], str) or not payload["name"].strip():
            raise ApiError("invalid_payload")
        digest=self._digest(payload); scope=(owner_id,idempotency_key)
        if scope in self._idem:
            prior_digest,item_id=self._idem[scope]
            if prior_digest != digest: raise ApiError("idempotency_conflict",409)
            return {"status":"replayed","item":self._items[item_id].__dict__}
        item_id=f"itm_{len(self._items)+1:04d}"
        item=Item(item_id=item_id, owner_id=owner_id, name=payload["name"].strip())
        self._items[item_id]=item; self._idem[scope]=(digest,item_id)
        return {"status":"created","item":item.__dict__}

    def list(self, *, owner_id: str, cursor: str|None=None, limit: int=2) -> dict[str, Any]:
        if not isinstance(limit,int) or limit<1 or limit>5: raise ApiError("invalid_limit")
        rows=[x for x in self._items.values() if x.owner_id==owner_id]
        rows.sort(key=lambda x:x.item_id)
        start=0
        if cursor is not None:
            ids=[x.item_id for x in rows]
            if cursor not in ids: raise ApiError("invalid_cursor")
            start=ids.index(cursor)+1
        page=rows[start:start+limit]
        next_cursor=page[-1].item_id if start+limit < len(rows) and page else None
        return {"items":[x.__dict__ for x in page],"next_cursor":next_cursor}

class InProcessSdk:
    def __init__(self, service: ItemService, owner_id: str): self._s=service; self._owner=owner_id
    def create_item(self, name: str, idempotency_key: str):
        return self._s.create(owner_id=self._owner,idempotency_key=idempotency_key,payload={"name":name})
    def list_all(self, page_size: int=2):
        out=[]; cursor=None; seen=set()
        for _ in range(100):
            page=self._s.list(owner_id=self._owner,cursor=cursor,limit=page_size)
            out.extend(page["items"]); cursor=page["next_cursor"]
            if cursor is None: return out
            if cursor in seen: raise ApiError("cursor_cycle",500)
            seen.add(cursor)
        raise ApiError("page_limit",500)
