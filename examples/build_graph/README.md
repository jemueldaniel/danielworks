# Bounded DAG planning with proof-bound local claims

This independently authored Python reference demonstrates canonical task
fingerprints, stable topological layers, cycle rejection, critical-path priority,
incremental dependency impact, bounded synthetic resource admission,
concurrent worker claims, expiring leases, stale-result fencing, retry limits,
and SHA-256 receipts. All test tasks and data are synthetic.

Run from repository root:

    python -B -m unittest discover -s examples/build_graph -v
    python -B examples/build_graph/demo.py

The coordinator DOES NOT execute programs. A fictional worker runs an action
outside the planner and submits an output digest. The lease is advisory, not
an authentication credential, distributed lock or exactly-once side-effect
guarantee. Receipts are unkeyed digests rather than signed external proofs.
State is held in memory; it cannot survive process loss. No company source,
internal data, credentials, cloud APIs or product-specific architecture is used.

The planner is limited to 64 tasks; each task requests 1-16 synthetic tokens.
A coordinator defaults to four tokens and two retries. Its bounded test cases
exercise actual multithreaded arbitration, deadline expiry and fail-closed
stale completions. Deployment requires independently built and verified
identity, persistence, broker fencing, execution sandboxing, telemetry and
cross-node recovery policies.
