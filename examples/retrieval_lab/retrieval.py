from __future__ import annotations
import json, math, re, hashlib
TOKEN=re.compile(r"[a-z0-9]+")
def toks(s): return TOKEN.findall(s.lower())
def index(docs):
    out=[]
    for d in docs:
        if set(d)!={"id","text"}: raise ValueError("invalid_doc")
        out.append((d["id"],d["text"],set(toks(d["text"]))))
    return out
def retrieve(idx,q,k=3):
    if not 1<=k<=10: raise ValueError("invalid_k")
    qt=set(toks(q)); scored=[]
    for did,text,dt in idx:
        overlap=len(qt&dt); score=overlap/(math.sqrt(len(qt) or 1)*math.sqrt(len(dt) or 1)); scored.append((score,did,text))
    scored.sort(key=lambda x:(-x[0],x[1])); return [{"id":d,"score":round(s,6),"text":t} for s,d,t in scored[:k]]
def evaluate(dataset):
    idx=index(dataset["documents"]); failures=[]; reciprocal=[]
    for case in dataset["queries"]:
        got=retrieve(idx,case["query"],case.get("k",3)); ids=[x["id"] for x in got]; target=case["relevant_id"]
        rank=ids.index(target)+1 if target in ids else None; reciprocal.append(0 if rank is None else 1/rank)
        if rank!=1: failures.append({"query_id":case["id"],"expected":target,"retrieved":ids,"rank":rank})
    fp=hashlib.sha256(json.dumps(dataset,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return {"dataset_sha256":fp,"mrr":sum(reciprocal)/len(reciprocal),"failures":failures}
