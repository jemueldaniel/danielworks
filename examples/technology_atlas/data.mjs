/** Technology Atlas, independently authored public classification and skill evidence.
 * Evidence levels are intentionally not endorsements of personal authorship or proficiency.
 * A private-source observation never becomes a public implementation link.
 */
export const CATEGORIES=Object.freeze(['All','Languages','Frontend & UX','Backend & Data','AI & Automation','Web3 & Contracts','Cloud & DevOps','Quality & Tooling']);
export const LEVELS=Object.freeze(['All','Public-tested','Public-historical','Source-observed']);
export const RECIPES=Object.freeze(['ai-search','service-foundation','event-platform','workflow-engine','api-security','frontend-studio','ui-experiences','interaction-systems','visual-analytics','career-portfolio','full-reference']);
const R=[
 // Languages, markup and portable runtimes
 ['JavaScript','Languages','Public-tested','examples/proof_gallery/model.mjs','Deterministic UI state and browser interactions.','career-portfolio'],
 ['TypeScript','Languages','Public-tested','projects/evidence-workbench/src/api-client.ts','Typed SDK interfaces and strict TypeScript compilation.','full-reference'],
 ['Python','Languages','Public-tested','examples/hybrid_search/hybrid.py','SQLite-backed indexing, HTTP and deterministic tests.','ai-search'],
 ['Rust','Languages','Public-historical','projects/bounded-lang/src/lib.rs','A bounded lexer, parser, intermediate representation and VM.','full-reference'],
 ['SQL','Languages','Public-tested','examples/migration_guard/migration.py','Transactions, migrations, ledger and full-text storage.','service-foundation'],
 ['HTML','Languages','Public-tested','examples/proof_gallery/index.html','Semantic, keyboard-operable browser interfaces.','career-portfolio'],
 ['CSS','Languages','Public-tested','examples/proof_gallery/styles.css','Responsive layout, design tokens and adaptive themes.','career-portfolio'],
 ['Solidity','Languages','Source-observed',null,'Smart-contract source is present in non-public repositories; on-chain proof not claimed.',null],
 ['Go','Languages','Source-observed',null,'Go source files and/or module artifacts observed in non-public source.',null],
 ['C','Languages','Source-observed',null,'C source observed; no public portable C acceptance included.',null],
 ['PowerShell','Languages','Source-observed',null,'Windows automation scripts observed; not independently republished.',null],
 ['Shell scripting','Languages','Source-observed',null,'Shell scripts observed in repository history.',null],
 ['WebAssembly','Languages','Source-observed',null,'Compiled WebAssembly artifacts observed; original build not publicly verified.',null],
 ['ECMAScript modules','Languages','Public-tested','examples/ui_atlas/model.mjs','Native ES modules with explicit exports and pure state models.','ui-experiences'],
 // Frontend engineering and interactions
 ['React','Frontend & UX','Public-tested','projects/evidence-workbench/web/App.tsx','A React UI bound to a typed local API and browser acceptance.','frontend-studio'],
 ['Three.js','Frontend & UX','Source-observed',null,'3D-rendering source artifacts observed privately; no independent public browser render.',null],
 ['Next.js','Frontend & UX','Source-observed',null,'Framework configuration and TypeScript page code observed privately.',null],
 ['Vite','Frontend & UX','Source-observed',null,'Frontend build configuration and packages observed privately.',null],
 ['Tailwind CSS','Frontend & UX','Source-observed',null,'Utility CSS dependency and build configuration observed privately.',null],
 ['TanStack Query','Frontend & UX','Source-observed',null,'Client-side query library present in inspected manifests.',null],
 ['Zustand','Frontend & UX','Source-observed',null,'Client state-management package present in inspected manifests.',null],
 ['React Hook Form','Frontend & UX','Source-observed',null,'Form-state tooling is present in inspected frontend manifests.',null],
 ['Radix UI','Frontend & UX','Source-observed',null,'Accessible component primitives present in source dependency manifests.',null],
 ['Recharts','Frontend & UX','Source-observed',null,'React chart dependency present in private frontend manifests.',null],
 ['Lucide icons','Frontend & UX','Source-observed',null,'Icon/component package observed in inspected manifests.',null],
 ['Responsive layout','Frontend & UX','Public-tested','examples/interface_lab/style.css','Real 320–1440 px browser layout and overflow acceptance.','frontend-studio'],
 ['SVG visualization','Frontend & UX','Public-tested','examples/data_studio/app.mjs','Original chart rendering and real SVG/CSV downloads.','visual-analytics'],
 ['Design tokens','Frontend & UX','Public-tested','examples/ui_atlas/styles.css','Reusable theme variables and a design-system demonstration.','ui-experiences'],
 ['Interactive graph editor','Frontend & UX','Public-tested','examples/flow_lab/app.mjs','Directed-graph editing, pointer/keyboard actions and undo/redo.','interaction-systems'],
 ['Accessible dialog behavior','Frontend & UX','Public-tested','projects/proof-gallery-tests/browser.test.mjs','Browser-tested keyboard shortcuts, modal focus restoration and labels.','career-portfolio'],
 ['Browser Web APIs','Frontend & UX','Public-tested','examples/proof_gallery/app.mjs','Local storage, Blob downloads and safe DOM element creation.','career-portfolio'],
 ['Filterable data tables','Frontend & UX','Public-tested','examples/interface_lab/app.mjs','Search, sort, pagination, validation and CSV export.','frontend-studio'],
 ['UI state reducers','Frontend & UX','Public-tested','examples/ui_atlas/model.mjs','Pure deterministic state transitions and negative tests.','ui-experiences'],
 ['Client-side routing patterns','Frontend & UX','Public-tested','examples/ui_atlas/app.mjs','Accessible in-page navigation between five synthetic views.','ui-experiences'],
 ['Component-driven interfaces','Frontend & UX','Public-tested','projects/evidence-workbench/web/App.tsx','Typed React component/state boundaries.','frontend-studio'],
 // Backend and data, intentionally split local evidence from cloud claims
 ['Node.js','Backend & Data','Public-tested','projects/evidence-workbench/src/server.ts','Real local HTTP and protocol testing on a Node runtime.','full-reference'],
 ['HTTP APIs','Backend & Data','Public-tested','projects/portable-proof-studio/server.py','Loopback API, input checking and request-response acceptance.','event-platform'],
 ['Typed API SDKs','Backend & Data','Public-tested','projects/evidence-workbench/src/api-client.ts','Typed client requests, bounded results and recovery semantics.','full-reference'],
 ['Model Context Protocol','Backend & Data','Public-tested','projects/evidence-workbench/src/mcp.ts','Actual local MCP SDK tools and Streamable HTTP tests.','full-reference'],
 ['SQLite','Backend & Data','Public-tested','examples/atomic_ledger/ledger.py','Transactional persistent journaling and concurrent writers.','service-foundation'],
 ['Redis','Backend & Data','Source-observed',null,'Redis integration artifacts observed; no independently tested public cache service.',null],
 ['Supabase','Backend & Data','Source-observed',null,'Supabase-related source artifacts observed; no public hosted auth, data or RLS claim.',null],
 ['PostgreSQL','Backend & Data','Source-observed',null,'Postgres drivers and SQL files are observed; live managed database not verified.',null],
 ['SQLite FTS5','Backend & Data','Public-tested','examples/hybrid_search/hybrid.py','Real BM25 lexical index updates and query evaluation.','ai-search'],
 ['Schema migrations','Backend & Data','Public-tested','examples/migration_guard/migration.py','Atomic SQL migrations and drift/replay checks.','service-foundation'],
 ['Job queues','Backend & Data','Public-tested','examples/durable_jobs/jobs.py','Persisted work, bounded retries and idempotency.','service-foundation'],
 ['Transactional outbox','Backend & Data','Public-tested','examples/event_outbox/event_outbox.py','Local delivery state, signed events and replay defense.','event-platform'],
 ['Double-entry ledgers','Backend & Data','Public-tested','examples/atomic_ledger/ledger.py','Fictional-unit journal conservation and reconciliation.','service-foundation'],
 ['Zod validation','Backend & Data','Public-tested','projects/evidence-workbench/src/schema.ts','Typed protocol schemas and input constraints.','api-security'],
 ['HMAC request signing','Backend & Data','Public-tested','examples/signed_api/signed_api.py','Request-bound signatures and SQLite replay fencing.','api-security'],
 ['Request rate limits','Backend & Data','Public-tested','examples/signed_api/signed_api.py','Synthetic per-key quotas backed by local transactions.','api-security'],
 ['Tenant policy decisions','Backend & Data','Public-tested','examples/tenant_policy/policy.py','Explicit deny, owner checks and tamper-resistant observations.','api-security'],
 // AI, ML and automation
 ['Bounded tool agents','AI & Automation','Public-tested','examples/mcp_agent/runtime.mjs','Local permissioned tool calls, cancellation and checkpoints.','ai-search'],
 ['Hybrid retrieval','AI & Automation','Public-tested','examples/hybrid_search/hybrid.py','FTS5 BM25, lexical hashed-vector signal and rank fusion.','ai-search'],
 ['Retrieval evaluation','AI & Automation','Public-tested','examples/ranking_eval/evaluation.py','Recall, precision-style metrics and measured ranking quality.','ai-search'],
 ['Document search','AI & Automation','Public-tested','examples/retrieval_lab/retrieval.py','Repeatable synthetic knowledge search and negative cases.','ai-search'],
 ['CPU model training','AI & Automation','Public-tested','examples/synthetic_training/training.py','Bounded synthetic training with repeatable evaluation.','ai-search'],
 ['Dependency DAG scheduling','AI & Automation','Public-tested','examples/build_graph/graph.py','Topological planning, leases and stale-work fencing.','workflow-engine'],
 ['Proof-carrying outputs','AI & Automation','Public-tested','tools/verify_exported_starter.py','Source-pinned export receipts and post-test byte verification.','full-reference'],
 ['Neural GPU training','AI & Automation','Source-observed',null,'Some source relates to training infrastructure; no reproducible public GPU proof.',null],
 // Smart contracts, EVM client tooling
 ['EVM contract development','Web3 & Contracts','Source-observed',null,'Contract files present; no public on-chain execution qualification.',null],
 ['viem','Web3 & Contracts','Source-observed',null,'EVM TypeScript client dependency observed privately.',null],
 ['wagmi','Web3 & Contracts','Source-observed',null,'Wallet connection hooks dependency observed privately.',null],
 ['Hardhat','Web3 & Contracts','Source-observed',null,'Contract development configuration observed privately.',null],
 ['Foundry','Web3 & Contracts','Source-observed',null,'Solidity testing tool configuration observed privately.',null],
 ['Wallet UX patterns','Web3 & Contracts','Source-observed',null,'Wallet-interface source present privately; no public transaction claim.',null],
 // Infrastructure, packaging and deployment
 ['Git','Cloud & DevOps','Public-tested','tools/verify_git_commit.py','Commit-tree and file-byte verification for reproducible source.','full-reference'],
 ['Docker','Cloud & DevOps','Source-observed',null,'Dockerfiles and service-container configuration are present privately.',null],
 ['GitHub Actions','Cloud & DevOps','Source-observed',null,'Workflow configuration paths observed in private repositories.',null],
 ['Tauri','Cloud & DevOps','Source-observed',null,'Native desktop runtime files observed; no independently qualified public installer.',null],
 ['Vercel','Cloud & DevOps','Source-observed',null,'Deployment configuration artifacts observed in private projects.',null],
 ['Cloudflare Workers','Cloud & DevOps','Source-observed',null,'Worker platform integration reflected in private implementation material.',null],
 ['AWS infrastructure','Cloud & DevOps','Source-observed',null,'AWS-oriented tooling appears privately; this is not deployed certification.',null],
 ['Infrastructure scripts','Cloud & DevOps','Source-observed',null,'Cross-platform operational shell and PowerShell scripts observed.',null],
 ['npm packages','Cloud & DevOps','Public-tested','package.json','Exact dependency lock and repeatable npm build/test workflow.','full-reference'],
 ['Source manifests','Cloud & DevOps','Public-tested','tools/verify_source.py','SHA-256 inventory, paths, bounds and tamper rejection.','full-reference'],
 ['One-command project assembly','Cloud & DevOps','Public-tested','tools/one_shot_public_project.py','Public-only fixed profiles with post-test hashes.','full-reference'],
 // Testing
 ['Playwright','Quality & Tooling','Public-tested','projects/proof-gallery-tests/browser.test.mjs','Actual installed Edge HTTP browser acceptance at five widths.','career-portfolio'],
 ['Node test runner','Quality & Tooling','Public-tested','examples/proof_gallery/test_model.mjs','Deterministic pure state-model tests.','career-portfolio'],
 ['Python unittest','Quality & Tooling','Public-tested','examples/hybrid_search/test_hybrid.py','Real data, concurrency and negative regression tests.','ai-search'],
 ['TypeScript typecheck','Quality & Tooling','Public-tested','projects/evidence-workbench/tsconfig.json','Strict compile-time safety checks integrated into npm test.','full-reference'],
 ['Browser accessibility acceptance','Quality & Tooling','Public-tested','projects/interface-lab-tests/browser.test.mjs','Real keyboard, focus restoration and named-control checks.','frontend-studio'],
 ['API protocol testing','Quality & Tooling','Public-tested','projects/evidence-workbench/tests/protocol.test.mjs','Real local HTTP/MCP transport and SDK behavior.','full-reference'],
 ['Source integrity verification','Quality & Tooling','Public-tested','tools/verify_source.py','Deterministic file inventories and external SHA-256 pins.','full-reference'],
 ['Test failure diagnostics','Quality & Tooling','Public-tested','tools/diagnose_public_profiles.py','Preserve failed local profile attempts and redacted receipts.','full-reference'],
 ['Rust Cargo tests','Quality & Tooling','Public-historical','projects/bounded-lang/tests/pipeline.rs','Historically tested compiler reference, not rerun in this release.','full-reference'],
 ['Security negative tests','Quality & Tooling','Public-tested','examples/signed_api/test_signed_api.py','Tamper, quota, tenant and nonce replay denial.','api-security']
];
const make=(row)=>{
 const [name,category,level,source,summary,recipe]=row;
 const id=name.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');
 return Object.freeze({id,name,category,level,source,summary,recipe});
};
export const TECHNOLOGIES=Object.freeze(R.map(make));
export const CATALOG_SIZE=TECHNOLOGIES.length;
export const PUBLIC_BASE='https://github.com/jemueldaniel/danielworks/blob/main/';
export function publicUrl(path){
 if(typeof path!=='string'||! /^(examples|projects|tools|package\.json)[A-Za-z0-9_./-]*$/.test(path)||path.includes('..')||path.includes('//')||path.startsWith('/'))throw new Error('invalid_public_path');
 return PUBLIC_BASE+path;
}
export function catalogProofCheck(){
 const ids=new Set();
 for(const t of TECHNOLOGIES){
  if(ids.has(t.id))throw new Error('duplicate_technology');
  ids.add(t.id);
  if(!CATEGORIES.includes(t.category)||t.category==='All'||!LEVELS.includes(t.level)||t.level==='All'||!t.summary||t.summary.length>210)throw new Error('invalid_technology');
  if(t.level==='Source-observed' && (t.source!==null || t.recipe!==null))throw new Error('private_source_link_forbidden');
  if(t.level!=='Source-observed' && (!t.source||!RECIPES.includes(t.recipe)))throw new Error('missing_public_proof');
  if(t.source)publicUrl(t.source);
 }
 return Object.freeze({count:ids.size,withPublicSource:TECHNOLOGIES.filter(t=>t.source).length,sourceObserved:TECHNOLOGIES.filter(t=>t.level==='Source-observed').length});
}
