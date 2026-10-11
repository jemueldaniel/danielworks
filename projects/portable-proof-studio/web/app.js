/** Original, local-only demo UI. All server/user values enter textContent only. */
const $ = id => document.getElementById(id);
let workspace = sessionStorage.getItem('portable-proof-workspace-v1') || '';
let lastRun = null;
let docs = [];
let busy = false;
const errorText = error => error?.message || 'Unexpected local request failure';
const newKey = () => crypto.randomUUID().replaceAll('-', '');

async function request(path, method = 'GET', payload, mutate = false) {
  const headers = {'Accept': 'application/json'};
  if (workspace) headers['X-Demo-Workspace'] = workspace;
  if (payload !== undefined) headers['Content-Type'] = 'application/json';
  if (mutate) headers['Idempotency-Key'] = newKey();
  const response = await fetch(path, {
    method, headers, credentials: 'same-origin', cache: 'no-store',
    body: payload === undefined ? undefined : JSON.stringify(payload)
  });
  let data;
  try { data = await response.json(); } catch { throw Error('UNREADABLE_RESPONSE'); }
  if (!response.ok) throw Error(data?.error?.code || `HTTP_${response.status}`);
  return data.data ?? data;
}
function show(id, value) { $(id).textContent = typeof value === 'string' ? value : JSON.stringify(value, null, 2); }
function setBusy(value) { busy = value; for (const b of document.querySelectorAll('button.primary')) b.disabled = value; }
function option(value, label) { const el = document.createElement('option'); el.value = value; el.textContent = label; return el; }

async function refresh() {
  if (!workspace) return;
  const [workflows, documents] = await Promise.all([request('/api/workflows'), request('/api/documents')]);
  const ws = $('workflows'), sel = ws.value;
  ws.replaceChildren(option('', workflows.length ? 'Select a saved workflow' : 'Save a workflow first'));
  workflows.forEach(w => ws.append(option(w.id, `${w.title} · rev ${w.revision}`)));
  if (workflows.some(w => w.id === sel)) ws.value = sel;
  else if (workflows.length) ws.value = workflows[0].id;
  docs = documents;
  const expected = $('expected-doc'), old = expected.value;
  expected.replaceChildren(option('', documents.length ? 'Select expected document' : 'Import a document first'));
  documents.forEach(d => expected.append(option(d.id, `${d.title} · rev ${d.revision}`)));
  if (documents.some(d => d.id === old)) expected.value = old;
  else if (documents.length) expected.value = documents[0].id;
  show('session', 'Local test workspace active. Source persists in SQLite after reload.');
}
async function perform(action, output) {
  if (busy) return;
  setBusy(true);
  try { await action(); }
  catch (err) {
    show(output, {status: 'error', code: errorText(err)});
    if (errorText(err) === 'SESSION_REQUIRED') {
      workspace = ''; sessionStorage.removeItem('portable-proof-workspace-v1');
      show('session', 'Workspace expired. Start a new test workspace.');
    }
  }
  finally { setBusy(false); }
}
$('new-space').addEventListener('click', () => perform(async () => {
  const result = await request('/api/workspaces', 'POST', {});
  workspace = result.workspaceToken; lastRun = null;
  sessionStorage.setItem('portable-proof-workspace-v1', workspace);
  $('import-artifact').disabled = true;
  show('workflow-output', 'Workspace ready. Save a workflow and run it.');
  show('knowledge-output', 'Workspace ready. Save or import a document.');
  await refresh();
}, 'session'));
$('workflow-form').addEventListener('submit', e => { e.preventDefault(); perform(async () => {
  const result = await request('/api/workflows', 'POST', {
    title: $('workflow-title').value,
    maxKeywords: Number($('max-keywords').value),
    minLength: Number($('min-length').value)
  }, true);
  await refresh(); $('workflows').value = result.workflowId;
  show('workflow-output', {saved: result, next: 'Run this revision to inspect step receipts.'});
}, 'workflow-output'); });
$('run-form').addEventListener('submit', e => {e.preventDefault(); perform(async () => {
  const result = await request('/api/runs', 'POST', {workflowId: $('workflows').value, text: $('run-input').value}, true);
  lastRun = result.runId; $('import-artifact').disabled = false;
  show('workflow-output', result);
}, 'workflow-output'); });
$('import-artifact').addEventListener('click', () => perform(async () => {
  if (!lastRun) throw Error('RUN_REQUIRED');
  const result = await request('/api/documents','POST', {
    title: `Workflow evidence ${lastRun.slice(0,8)}`,sourceRunId: lastRun
  },true);
  await refresh(); $('expected-doc').value = result.documentId;
  show('knowledge-output',{imported:result, next: 'Search for a keyword from the imported artifact.'});
}, 'knowledge-output'));
$('document-form').addEventListener('submit',e=>{e.preventDefault();perform(async()=>{
  const result=await request('/api/documents','POST', {title:$('doc-title').value,text:$('doc-text').value},true);
  await refresh();$('expected-doc').value=result.documentId;
  show('knowledge-output',{saved:result});
},'knowledge-output');});
$('search-form').addEventListener('submit',e=>{e.preventDefault();perform(async()=>{
  const result=await request('/api/search','POST',{query:$('search-query').value});
  show('knowledge-output',result);
},'knowledge-output');});
$('evaluation-form').addEventListener('submit',e=>{e.preventDefault();perform(async()=>{
  const result=await request('/api/evaluations','POST',{query:$('search-query').value,expectedDocumentId:$('expected-doc').value},true);
  show('knowledge-output',result);
},'knowledge-output');});
$('mode').addEventListener('click',()=>{
  const dark=document.documentElement.dataset.theme==='dark';
  document.documentElement.dataset.theme=dark?'light':'dark';
  $('mode').setAttribute('aria-pressed',String(!dark));
  $('mode').textContent=dark?'Dark appearance':'Light appearance';
});
if (workspace) refresh().catch(err=>{ show('session',`Saved session unavailable: ${errorText(err)}`); });
