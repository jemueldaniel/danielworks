# Reusable original public engineering recipes

Four fixed source-only recipes compose tested, self-contained examples.
They import no private repositories or accounts and deploy nothing.

| Recipe | Fixed public profiles | Demonstrates |
|---|---|---|
| ai-search | agent, hybrid-search, retrieval, evaluation, training | Bounded planning, search, synthetic model learning |
| service-foundation | jobs, ledger, migration, policy | Durable work, accounting invariants, policy decisions |
| event-platform | jobs, event-outbox, policy, proof-platform | Signed event ingestion, workflows, local HTTP |
| workflow-engine | build-graph, jobs, event-outbox, policy | In-memory DAG claims plus local durable jobs/events and policy |
| full-reference | all twelve executed public profiles | Broad engineering reference without private data |

From the exact published checkout, obtain its SOURCE_MANIFEST.json SHA-256
outside the repository and provide that verified 64-character value:

    python -B tools/compose_public_solution.py --root . --expected-source-sha256 YOUR_EXTERNAL_MANIFEST_SHA256 --recipe service-foundation --destination ../my-reference --receipt ../my-reference-proof.json

The output and receipt must not exist. A dry run creates nothing and makes no
test claim. The no-tests option labels its result verified-only. Fixed
allowlisted test commands run only from original source; editable manifest
strings cannot execute shell code. Output hashes are checked before/after
runtime tests. Historical profiles are never silently promoted.

Important limits: educational public source only; no untrusted-code sandbox,
license certification, actual login/IAM, real funds or custody, PostgreSQL
authorization, EVM settlement, or distributed GPU training. Real-world use
needs authenticated inputs, threat modeling, independent audits, deployment
and monitoring qualification, and careful source ownership review.
