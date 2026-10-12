"""Original public-only capability matrix. No private paths or source inputs."""
from __future__ import annotations
import json
from pathlib import Path

CATEGORIES = {
 "Frontend": ("HTML", "CSS", "JavaScript", "TypeScript", "React", "Next.js", "SVG", "Accessibility"),
 "Backend": ("Python", "Node.js", "REST APIs", "SQLite", "PostgreSQL", "SQL", "MCP"),
 "Systems": ("Rust", "Go", "CLI", "Compilers", "Virtual machines", "Docker", "CI/CD"),
 "AI": ("Retrieval", "Evaluation", "Agent workflows", "Machine learning", "Model training"),
 "Web3": ("Solidity", "Smart contracts", "Transaction simulation", "Cryptography"),
 "Cloud": ("Cloudflare", "Vercel", "Supabase", "Redis", "AWS"),
}
LEVELS = {"public-tested", "source-observed", "historical", "unverified"}
def validate(item):
 if not isinstance(item, dict) or set(item) != {"technology", "category", "level", "public_reference"}:
  return False
 if item["category"] not in CATEGORIES or item["technology"] not in CATEGORIES[item["category"]]:
  return False
 if item["level"] not in LEVELS:
  return False
 ref = item["public_reference"]
 return isinstance(ref, str) and (ref == "" or (
  ref.startswith("examples/") and ".." not in ref.split("/") and
  all(c.isalnum() or c in "/._-" for c in ref)
 ))
def build(rows):
 if not isinstance(rows, list) or len(rows)>100: raise ValueError("invalid_catalog")
 out, seen=[],set()
 for item in rows:
  if not validate(item): raise ValueError("invalid_entry")
  key=(item["category"],item["technology"])
  if key in seen: raise ValueError("duplicate_entry")
  seen.add(key)
  if item["level"] != "public-tested" and item["public_reference"]:
   raise ValueError("unqualified_link")
  out.append(dict(item))
 return sorted(out,key=lambda x:(x["category"],x["technology"]))
def summary(rows):
 data=build(rows)
 return {"total":len(data),**{level:sum(x["level"]==level for x in data) for level in sorted(LEVELS)}}
def export(rows):
 return json.dumps({"schema":1,"purpose":"public evidence, not proof of private ownership",
                    "summary":summary(rows),"entries":build(rows)},indent=2,sort_keys=True)+"\n"
def examples():
 return [
  {"technology":tech,"category":category,"level":"unverified","public_reference":""}
  for category,technologies in CATEGORIES.items() for tech in technologies
 ]
if __name__=="__main__":
 print(export(examples()),end="")
