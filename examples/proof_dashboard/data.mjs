// Public-only references, not private-source ownership claims.
export const REFERENCES=[
['Interface engineering','Responsive UI Atlas','Five original working interface experiences: commerce, workflow, messaging, onboarding and design tokens.','examples/ui_atlas/README.md',['JavaScript','CSS','UI/UX']],
['Interface engineering','Layout Foundry','Responsive task management interface with validation, keyboard commands and theme exports.','examples/layout_foundry/README.md',['HTML','CSS','Accessibility']],
['Interface engineering','Flow Laboratory','Interactive directed-graph editor with cycle prevention, undo and JSON exchange.','examples/flow_lab/README.md',['SVG','JavaScript','Interaction']],
['Interface engineering','Visual Analytics','Original SVG charts, synthetic cohorts and safe local annotations.','examples/data_studio/README.md',['SVG','Data visualization']],
['Interface engineering','Interface Laboratory','Responsive interactive components with deterministic state tests.','examples/interface_lab/README.md',['Frontend','Testing']],
['Developer tooling','Technology Atlas','Evidence-qualified navigation across observed and publicly tested technologies.','examples/technology_atlas/README.md',['Classification','UI']],
['Developer tooling','Proof Gallery','Interactive source-backed reference browser with bookmarks and safe exports.','examples/proof_gallery/README.md',['JavaScript','Evidence']],
['Developer tooling','Public Starter Composer','Offline source-pinned assembly of original public engineering reference projects.','tools/compose_public_solution.py',['Python','Reproducibility']],
['Developer tooling','Capability Mapper','Offline capability matrix with validation, bounded references and explicit evidence levels.','examples/capability_mapper/README.md',['Python','Validation']],
['Backend systems','Durable Jobs','SQLite-backed leases, retry logic and recovery tests.','examples/durable_jobs/README.md',['Python','SQLite']],
['Backend systems','Event Outbox','Signed events, idempotency and local HTTP verification.','examples/event_outbox/README.md',['HTTP','Security']],
['Backend systems','Tenant Policy','Explicit tenant authorization and audit evidence.','examples/tenant_policy/README.md',['Policy','Testing']],
['Backend systems','Atomic Ledger','Synthetic double-entry accounting with reconciliation invariants.','examples/atomic_ledger/README.md',['SQLite','Transactions']],
['Backend systems','Signed API','Request signature and replay-guard demonstration.','examples/signed_api/README.md',['Security','APIs']],
['Backend systems','Migration Guard','Bounded schema migration safety reference.','examples/migration_guard/README.md',['SQL','Testing']],
['AI and data','Hybrid Search','Lexical ranking, tenant-scoped indexing and retrieval metrics.','examples/hybrid_search/README.md',['Python','Search']],
['AI and data','Retrieval Lab','Synthetic retrieval and ranking experiments.','examples/retrieval_lab/README.md',['Retrieval','Evaluation']],
['AI and data','Model Evaluation','Deterministic synthetic ranking and evaluation tests.','examples/ranking_eval/README.md',['Evaluation','Metrics']],
['AI and data','Synthetic Training','Real CPU optimization on generated toy data.','examples/synthetic_training/README.md',['Machine learning','Python']],
['Systems engineering','Bounded Language','Rust compiler and virtual-machine reference.','projects/bounded-lang/README.md',['Rust','Compiler']],
['Systems engineering','Build Graph','Dependency DAG with bounded admission and retry logic.','examples/build_graph/README.md',['Python','Scheduling']],
['Systems engineering','MCP Agent','Bounded tool execution, agent planning and recovery.','examples/mcp_agent/README.md',['MCP','Agents']]
].map(([discipline,title,description,path,tags])=>({discipline,title,description,path,tags}));
export function filterReferences(rows,{search='',discipline='All',sort='title'}={}){
 const q=String(search).trim().toLowerCase().slice(0,100);
 return rows.filter(x=>(discipline==='All'||x.discipline===discipline)&&
 (!q||[x.title,x.description,x.discipline,...x.tags].some(v=>v.toLowerCase().includes(q))))
 .sort((a,b)=>sort==='discipline'?
 (a.discipline.localeCompare(b.discipline)||a.title.localeCompare(b.title)):
 a.title.localeCompare(b.title));
}
export function publicUrl(path){
 if(typeof path!=='string'||! /^(examples|projects|tools)\/[A-Za-z0-9_./-]+$/.test(path)||path.split('/').includes('..'))throw Error('unsafe_path');
 return 'https://github.com/jemueldaniel/danielworks/blob/main/'+path;
}
