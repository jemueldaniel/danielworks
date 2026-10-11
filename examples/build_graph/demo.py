"""Small simulated DAG execution: no shell commands, private data or network."""
from hashlib import sha256
from graph import Graph, Coordinator, task

plan = Graph([task("ingest"), task("compile", ("ingest",), tokens=2),
              task("verify", ("compile",))])
coordinator = Coordinator(plan, capacity=3)
while lease := coordinator.claim("demo-worker"):
    output = sha256(("simulated " + lease["task"]).encode("ascii")).hexdigest()
    coordinator.complete(lease["task"], "demo-worker", lease["lease"], output)
receipt = coordinator.receipt()
print({"layers": plan.describe()["layers"], "status": receipt["status"],
       "receipt_sha256": receipt["receipt_sha256"]})
