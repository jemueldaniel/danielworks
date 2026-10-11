/* DanielWorks Proof Gallery: original public-only state and evidence model.
 * All identifiers map to already-public educational examples. No private input.
 */
export const CATEGORIES = Object.freeze(['All','Interfaces','AI & Data','Systems','Language','Security']);
export const LEVELS = Object.freeze(['All','Browser-tested','Local-tested','Historical']);
export const SORTS = Object.freeze(['featured','title','discipline']);
export const RECIPE_NAMES = Object.freeze(['ai-search','service-foundation','event-platform','workflow-engine','api-security','frontend-studio','ui-experiences','interaction-systems','visual-analytics','full-reference']);
const record = (id,title,category,level,source,test,blurb,focus,recipe) =>
  Object.freeze({id,title,category,level,source,test,blurb,focus,recipe});
export const EVIDENCE = Object.freeze([
  record('ui-atlas','Interactive UI Atlas','Interfaces','Browser-tested','examples/ui_atlas/README.md','projects/ui-atlas-tests/browser.test.mjs','Five original public experiences: commerce, task board, messaging, onboarding and components.','State transitions, interaction architecture and accessible controls.','ui-experiences'),
  record('interface-lab','Responsive Interface Lab','Interfaces','Browser-tested','examples/interface_lab/README.md','projects/interface-lab-tests/browser.test.mjs','Searchable tables, keyboard-driven dialogs, compact layouts and local CSV export.','Responsive layout, focus behavior and deterministic reducers.','frontend-studio'),
  record('flow-lab','Visual Flow Laboratory','Interfaces','Browser-tested','examples/flow_lab/README.md','projects/flow-lab-tests/browser.test.mjs','An original interactive directed graph with drag, connections, history and safe import/export.','Graph validation, undo/redo and touch-plus-keyboard editing.','interaction-systems'),
  record('data-studio','Visual Analytics Studio','Interfaces','Browser-tested','examples/data_studio/README.md','projects/data-studio-tests/browser.test.mjs','Original SVG visualizations, interactive data filters, annotations and real local downloads.','Data visualization, accessibility and browser acceptance.','visual-analytics'),
  record('react-workbench','React + MCP Workbench','Interfaces','Historical','projects/evidence-workbench/README.md','projects/evidence-workbench/tests/browser.test.mjs','A local React client joined to typed APIs, durable work and protocol transports.','Typed interfaces, error recovery and client/server boundaries.','frontend-studio'),
  record('proof-platform','Portable Proof Studio','Systems','Local-tested','projects/portable-proof-studio/README.md','projects/portable-proof-studio/test_http.py','A public HTTP + SQLite workflow-to-retrieval demonstration with inspectable receipts.','Persistence, HTTP behavior and recoverable work.','event-platform'),
  record('build-graph','Dependency Graph Planner','Systems','Local-tested','examples/build_graph/README.md','examples/build_graph/test_graph.py','Bounded dependency scheduling with stable layers, source fingerprints and lease tests.','Resource-aware orchestration and stale-work fencing.','workflow-engine'),
  record('durable-jobs','Durable Job Queue','Systems','Local-tested','examples/durable_jobs/README.md','examples/durable_jobs/test_jobs.py','A local job-processing reference for idempotent state and retry behavior.','Persistence, retries and failure transparency.','service-foundation'),
  record('event-outbox','Transactional Event Outbox','Systems','Local-tested','examples/event_outbox/README.md','examples/event_outbox/test_event_outbox.py','A synthetic signed-event delivery example with repeatable local tests.','Outbox delivery, receipts and HTTP safety.','event-platform'),
  record('migration','Schema Migration Guard','Systems','Local-tested','examples/migration_guard/README.md','examples/migration_guard/test_migration.py','A deterministic SQLite migration gate with transactional rollback.','Schema drift, atomicity and concurrent migrations.','service-foundation'),
  record('agent','Bounded Agent Runtime','AI & Data','Local-tested','examples/mcp_agent/README.md','examples/mcp_agent/test_runtime.mjs','A bounded local agent execution and recovery model without remote model calls.','Permissions, cancellation and state checkpoints.','ai-search'),
  record('hybrid-search','Hybrid Search Evaluation','AI & Data','Local-tested','examples/hybrid_search/README.md','examples/hybrid_search/test_hybrid.py','FTS5/BM25 with deterministic lexical ranking and measurable retrieval quality.','Ranking metrics, tenant boundaries and index revision.','ai-search'),
  record('retrieval','Retrieval Laboratory','AI & Data','Local-tested','examples/retrieval_lab/README.md','examples/retrieval_lab/test_retrieval.py','Reproducible synthetic document retrieval experiments.','Grounded results and explicit failures.','ai-search'),
  record('evaluation','Ranking Evaluation','AI & Data','Local-tested','examples/ranking_eval/README.md','examples/ranking_eval/test_evaluation.py','Synthetic ranking metrics with explicit pass and failure cases.','Recall, nDCG and regression testing.','ai-search'),
  record('training','CPU Learning Reference','AI & Data','Local-tested','examples/synthetic_training/README.md','examples/synthetic_training/test_training.py','A bounded training and evaluation example using synthetic data.','Train/test separation and repeatable measurements.','ai-search'),
  record('signed-api','Signed API Boundary','Security','Local-tested','examples/signed_api/README.md','examples/signed_api/test_signed_api.py','A localhost request-signing and replay-defense reference.','Canonical signatures, request bounds and quotas.','api-security'),
  record('policy','Tenant Policy Laboratory','Security','Local-tested','examples/tenant_policy/README.md','examples/tenant_policy/test_policy.py','An explicit-deny local tenant policy and observational signed audit reference.','Isolation, policy precedence and tamper rejection.','api-security'),
  record('ledger','Atomic SQLite Ledger','Systems','Local-tested','examples/atomic_ledger/README.md','examples/atomic_ledger/test_ledger.py','Fictional-unit double-entry accounting with concurrency and reconciliation tests.','Transaction integrity, rollback and idempotency.','service-foundation'),
  record('compiler','Rust Language Reference','Language','Historical','projects/bounded-lang/README.md','projects/bounded-lang/tests/pipeline.rs','A bounded lexer, parser, IR and VM reference with historically documented tests.','Language tooling and execution resource limits.','full-reference')
]);
export const ID_SET = new Set(EVIDENCE.map(item=>item.id));
export const SOURCE_PREFIX = 'https://github.com/jemueldaniel/danielworks/blob/main/';
export function publicUrl(path) {
  if(typeof path!=='string'||! /^(examples|projects|tools)\/[A-Za-z0-9_./-]+$/.test(path)||path.includes('..')||path.includes('//')) throw new Error('invalid_public_path');
  return SOURCE_PREFIX+path;
}
export function newState(){
 return {search:'',category:'All',level:'All',sort:'featured',saved:[],compare:[],selected:null,theme:'dark'};
}
function assertId(id){if(typeof id!=='string'||!ID_SET.has(id))throw new Error('unknown_public_example');}
export function reduce(state,action){
 if(!state||!action||typeof action.type!=='string')throw new Error('invalid_action');
 const next={...state,saved:[...state.saved],compare:[...state.compare]};
 switch(action.type){
  case 'SEARCH':
   if(typeof action.value!=='string')throw new Error('invalid_search');
   next.search=action.value.slice(0,120);break;
  case 'CATEGORY':
   if(!CATEGORIES.includes(action.value))throw new Error('invalid_category');
   next.category=action.value;break;
  case 'LEVEL':
   if(!LEVELS.includes(action.value))throw new Error('invalid_level');
   next.level=action.value;break;
  case 'SORT':
   if(!SORTS.includes(action.value))throw new Error('invalid_sort');
   next.sort=action.value;break;
  case 'SAVE':
   assertId(action.value);
   next.saved=next.saved.includes(action.value)?next.saved.filter(x=>x!==action.value):[...next.saved,action.value].sort();break;
  case 'COMPARE':
   assertId(action.value);
   if(next.compare.includes(action.value)) next.compare=next.compare.filter(x=>x!==action.value);
   else if(next.compare.length<3)next.compare.push(action.value);
   else throw new Error('compare_limit');
   break;
  case 'CLEAR_COMPARE':next.compare=[];break;
  case 'OPEN':assertId(action.value);next.selected=action.value;break;
  case 'CLOSE':next.selected=null;break;
  case 'THEME':
   if(!['light','dark'].includes(action.value))throw new Error('invalid_theme');
   next.theme=action.value;break;
  case 'RESTORE':
   if(!action.value||typeof action.value!=='object')throw new Error('invalid_restore');
   next.saved=normalizeSaved(action.value.saved);
   next.theme=['light','dark'].includes(action.value.theme)?action.value.theme:'dark';
   break;
  case 'RESET':return newState();
  default:throw new Error('unknown_action');
 }
 return next;
}
export function normalizeSaved(value){
 if(!Array.isArray(value))return [];
 return [...new Set(value.filter(x=>typeof x==='string'&&ID_SET.has(x)))].slice(0,30).sort();
}
export function visible(state){
 const q=state.search.toLocaleLowerCase('en').trim();
 const found=EVIDENCE.filter(item=>{
   const match=!q||[item.title,item.category,item.blurb,item.focus,item.id].some(value=>value.toLocaleLowerCase('en').includes(q));
   return match&&(state.category==='All'||item.category===state.category)&&(state.level==='All'||item.level===state.level);
 });
 return state.sort==='featured'?found:found.slice().sort((a,b)=>(state.sort==='title'?a.title.localeCompare(b.title):a.category.localeCompare(b.category)||a.title.localeCompare(b.title)));
}
export function tally(list=EVIDENCE){return Object.fromEntries(CATEGORIES.map(cat=>[cat,cat==='All'?list.length:list.filter(x=>x.category===cat).length]));}
export function byId(id){assertId(id);return EVIDENCE.find(x=>x.id===id);}
export function selectedComparisons(state){return state.compare.map(byId);}
export function quoteCsv(value){
 let s=String(value??'').replace(/\r\n?/g,'\n');
 if(/^[\s]*[=+\-@\t\r]/.test(s))s="'"+s;
 return '"'+s.replace(/"/g,'""')+'"';
}
export function exportCsv(state){
 const rows=[['Capability','Discipline','Evidence level','Source','Test','Boundary']];
 for(const item of visible(state))rows.push([item.title,item.category,item.level,publicUrl(item.source),publicUrl(item.test),'Local educational example; not independent authorship, license or production proof']);
 return rows.map(row=>row.map(quoteCsv).join(',')).join('\r\n')+'\r\n';
}
export function exportJson(state){
 return JSON.stringify({schema:1,purpose:'Original public educational engineering evidence only',qualification:'Source and local tests, not ownership or production certification',capabilities:visible(state).map(({id,title,category,level,source,test,focus})=>({id,title,category,level,source:publicUrl(source),test:publicUrl(test),focus}))},null,2)+'\n';
}
export function recipeCommand(recipe){
 if(!RECIPE_NAMES.includes(recipe))throw new Error('invalid_recipe');
 return 'python -B tools/compose_public_solution.py --root . --expected-source-sha256 YOUR_EXTERNALLY_VERIFIED_SOURCE_MANIFEST_SHA256 --recipe '+recipe+' --destination ../public-reference-'+recipe+' --receipt ../public-reference-'+recipe+'-proof.json';
}
export function validateCatalog(){
 const ids=new Set(),paths=new Set();
 for(const item of EVIDENCE){
  if(ids.has(item.id)||!CATEGORIES.includes(item.category)||item.category==='All'||!LEVELS.includes(item.level)||item.level==='All'||!RECIPE_NAMES.includes(item.recipe))throw new Error('invalid_catalog');
  ids.add(item.id);paths.add(publicUrl(item.source));publicUrl(item.test);
  if([item.title,item.blurb,item.focus].some(x=>typeof x!=='string'||x.length<12||x.length>250))throw new Error('invalid_metadata');
 }
 return {count:ids.size,sourcePaths:paths.size};
}
