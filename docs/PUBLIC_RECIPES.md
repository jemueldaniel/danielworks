# Reusable original public engineering recipes

Twelve fixed source-only recipes compose tested, self-contained examples.
They import no private repositories or accounts and deploy nothing.

| Recipe | Fixed public profiles | Demonstrates |
|---|---|---|
| ai-search | agent, hybrid-search, retrieval, evaluation, training | Bounded planning, search, synthetic model learning |
| service-foundation | jobs, ledger, migration, policy | Durable work, accounting invariants, policy decisions |
| event-platform | jobs, event-outbox, policy, proof-platform | Signed event ingestion, workflows, local HTTP |
| workflow-engine | build-graph, jobs, event-outbox, policy | In-memory DAG claims plus local durable jobs/events and policy |
| api-security | signed-api, policy, jobs | Key-bound signatures, nonce replay and local backend policy |
| frontend-studio | interface-lab, jobs, policy | Responsive local UI, durable jobs and policy examples; separately tested |
| ui-experiences | interface-lab, ui-atlas | Two separate fully interactive frontend implementations; pure Node model suites |
| interaction-systems | flow-lab, interface-lab, ui-atlas | Editable graph canvas, responsive table and multi-domain interfaces with separate executable state suites |
| visual-analytics | data-studio, flow-lab, interface-lab | Real interactive SVG chart modes, graph editing and responsive UI, each with executed state tests |
| career-portfolio | proof-gallery, ui-atlas, interface-lab, flow-lab, data-studio | Interview evidence browser and four runnable independent UI demonstrations |
| tech-and-interface | technology-atlas, proof-gallery, ui-atlas, interface-lab, flow-lab, data-studio | Curated technology evidence and five original UI examples; six separately testable profiles |
| full-reference | all nineteen executed public profiles | Broad engineering reference without private data |

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
