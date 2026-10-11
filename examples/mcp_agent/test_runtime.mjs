import test from 'node:test'; import assert from 'node:assert/strict';
import {ToolRegistry,McpServer,AgentRunner} from './runtime.mjs';
function make(){ const r=new ToolRegistry(); r.register({name:'notes.append',permission:'write:notes',schema:a=>a&&typeof a.text==='string'&&a.text.length<=20,run:async a=>({ok:true,text:a.text})}); return {r,s:new McpServer(r)}; }
test('MCP lists schemas and permission metadata',async()=>{const {s}=make();const x=await s.handle({jsonrpc:'2.0',id:1,method:'tools/list'},{permissions:new Set()});assert.equal(x.result.tools[0].permission,'write:notes')});
test('tool execution enforces permission boundary',async()=>{const {s}=make();const x=await s.handle({jsonrpc:'2.0',id:1,method:'tools/call',params:{name:'notes.append',arguments:{text:'x'}}},{permissions:new Set()});assert.equal(x.error.message,'permission_denied')});
test('schema rejects oversized arguments',async()=>{const {s}=make();const x=await s.handle({jsonrpc:'2.0',id:1,method:'tools/call',params:{name:'notes.append',arguments:{text:'x'.repeat(21)}}},{permissions:new Set(['write:notes'])});assert.equal(x.error.message,'invalid_arguments')});
test('agent checkpoints and resumes without replaying completed steps',async()=>{const {s}=make();const store=new Map();const runner=new AgentRunner({server:s,checkpointStore:store});const steps=[{name:'notes.append',arguments:{text:'a'}},{name:'notes.append',arguments:{text:'b'}}];let abort=new AbortController(); const orig=s.handle.bind(s);let calls=0;s.handle=async(...args)=>{calls++;const out=await orig(...args);if(calls===1) abort.abort();return out};await assert.rejects(runner.run({runId:'r1',steps,permissions:new Set(['write:notes']),signal:abort.signal}),/cancelled/);assert.equal(store.get('r1').next,1);s.handle=orig;const done=await runner.run({runId:'r1',steps,permissions:new Set(['write:notes'])});assert.equal(done.results.length,2);assert.equal(done.next,2)});
test('pre-cancelled run performs no tool call',async()=>{const {s}=make();const runner=new AgentRunner({server:s,checkpointStore:new Map()});const c=new AbortController();c.abort();await assert.rejects(runner.run({runId:'x',steps:[{name:'notes.append',arguments:{text:'a'}}],permissions:new Set(['write:notes']),signal:c.signal}),/cancelled/)});

// Recovery regressions use the real in-process registry/server/runner, not a
// network, browser, database, or external side-effect adapter.
function recorded(run) {
  const calls = [];
  const registry = new ToolRegistry();
  registry.register({name: 'notes.append', permission: 'write:notes',
    schema: a => a && typeof a.text === 'string' && a.text.length <= 20,
    run: async a => { calls.push(a.text); return run ? run(a) : {text: a.text}; }});
  const server = new McpServer(registry), store = new Map();
  const runner = new AgentRunner({server, checkpointStore: store});
  return {calls, server, store, runner};
}
const note = text => ({name: 'notes.append', arguments: {text}});
const input = (steps, extra = {}) => ({runId: 'bound', steps,
  permissions: new Set(['write:notes']), ...extra});

test('resume rejects a changed plan before executing or overwriting a checkpoint', async () => {
  const {runner, store, calls} = recorded();
  await runner.run(input([note('old')]));
  const before = structuredClone(store.get('bound'));
  await assert.rejects(runner.run(input([note('new')])), /run_input_conflict/);
  assert.deepEqual(calls, ['old']);
  assert.deepEqual(store.get('bound'), before);
});

test('resume cannot reuse results with a changed permission set', async () => {
  const {runner, calls} = recorded();
  await runner.run(input([note('old')]));
  await assert.rejects(runner.run(input([note('old')], {permissions: new Set()})), /run_input_conflict/);
  assert.deepEqual(calls, ['old']);
});

test('resume rejects a modified checksum without a tool call', async () => {
  const {runner, store, calls} = recorded();
  await runner.run(input([note('old')]));
  store.get('bound').checkpointSha256 = '0'.repeat(64);
  await assert.rejects(runner.run(input([note('old')])), /invalid_checkpoint/);
  assert.deepEqual(calls, ['old']);
});

test('resume rejects a corrupt progress counter rather than skipping work', async () => {
  const {runner, store, calls} = recorded();
  await runner.run(input([note('old')]));
  store.get('bound').next = 900;
  await assert.rejects(runner.run(input([note('old')])), /invalid_checkpoint/);
  assert.deepEqual(calls, ['old']);
});

test('unbound legacy checkpoints are preserved and rejected instead of upgraded silently', async () => {
  const {runner, store, calls} = recorded();
  const legacy = {runId: 'bound', next: 1, results: [{text: 'old'}]};
  store.set('bound', legacy);
  await assert.rejects(runner.run(input([note('new')])), /invalid_checkpoint/);
  assert.equal(store.get('bound'), legacy);
  assert.deepEqual(calls, []);
});

test('a checkpoint copied under another run ID is rejected', async () => {
  const {runner, store, calls} = recorded();
  await runner.run(input([note('old')]));
  store.set('other', structuredClone(store.get('bound')));
  await assert.rejects(runner.run(input([note('old')], {runId: 'other'})), /invalid_checkpoint/);
  assert.deepEqual(calls, ['old']);
});

test('returned results cannot mutate the stored checkpoint through aliases', async () => {
  const {runner, store} = recorded();
  const done = await runner.run(input([note('old')]));
  done.results[0].text = 'changed'; done.next = 0;
  assert.equal(store.get('bound').results[0].text, 'old');
  assert.equal(store.get('bound').next, 1);
});

test('caller mutation during an awaited tool does not change the bound plan', async () => {
  let release, entered;
  const started = new Promise(resolve => { entered = resolve; });
  const gate = new Promise(resolve => { release = resolve; });
  const {runner, calls} = recorded(async a => {
    if (a.text === 'first') { entered(); await gate; }
    return {text: a.text};
  });
  const steps = [note('first'), note('original')];
  const running = runner.run(input(steps));
  await started;
  steps[1].arguments.text = 'changed';
  release(); await running;
  assert.deepEqual(calls, ['first', 'original']);
});

test('two runners sharing one Map cannot execute the same run concurrently', async () => {
  let release, entered;
  const started = new Promise(resolve => { entered = resolve; });
  const gate = new Promise(resolve => { release = resolve; });
  const {runner, store, server, calls} = recorded(async a => { entered(); await gate; return {text: a.text}; });
  const other = new AgentRunner({server, checkpointStore: store});
  const running = runner.run(input([note('once')]));
  await started;
  try {
    // Attach the rejection assertion immediately so an old-runtime second run
    // cannot remain unobserved while the test releases both tool invocations.
    const rejected = assert.rejects(other.run(input([note('once')])), /run_in_progress/);
    release(); await running; await rejected;
  } finally { release(); }
  assert.deepEqual(calls, ['once']);
});

test('tool failure releases the guard and retains input identity for an explicit retry', async () => {
  let first = true;
  const {runner, calls} = recorded(a => {
    if (first) { first = false; throw new Error('known_failure'); }
    return {text: a.text};
  });
  await assert.rejects(runner.run(input([note('same')])), /known_failure/);
  await assert.rejects(runner.run(input([note('changed')])), /run_input_conflict/);
  const done = await runner.run(input([note('same')]));
  assert.equal(done.next, 1);
  assert.deepEqual(calls, ['same', 'same']);
});

test('invalid and oversized plans are rejected without tool effects', async () => {
  const cyclic = note('cycle'); cyclic.arguments.self = cyclic;
  for (const steps of [Array.from({length: 65}, () => note('many')),
    [{name: 'notes.append', arguments: {text: 'ok', bad: NaN}}],
    [{name: 'notes.append', arguments: {text: 'ok', bad: undefined}}],
    [{name: 'notes.append', arguments: {text: 'ok', big: 'x'.repeat(65537)}}], [cyclic]]) {
    const {runner, calls, store} = recorded();
    await assert.rejects(runner.run(input(steps)), /invalid_run_input/);
    assert.deepEqual(calls, []); assert.equal(store.size, 0);
  }
});

test('pre-cancelled empty runs do not create a checkpoint or return success', async () => {
  const {runner, store} = recorded(); const controller = new AbortController(); controller.abort();
  await assert.rejects(runner.run(input([], {signal: controller.signal})), /cancelled/);
  assert.equal(store.size, 0);
});

test('JSON key order and permission insertion order do not change request identity', async () => {
  const {runner, calls} = recorded();
  await runner.run(input([note('same')], {permissions: new Set(['unused', 'write:notes'])}));
  const done = await runner.run(input([{arguments: {text: 'same'}, name: 'notes.append'}],
    {permissions: new Set(['write:notes', 'unused'])}));
  assert.equal(done.next, 1); assert.deepEqual(calls, ['same']);
});

test('JSON-serialized checkpoint resumes with no borrowed object identity', async () => {
  const {runner, store, server, calls} = recorded();
  await runner.run(input([note('same')]));
  const restored = new Map(JSON.parse(JSON.stringify([...store.entries()])));
  const second = new AgentRunner({server, checkpointStore: restored});
  assert.equal((await second.run(input([note('same')]))).next, 1);
  assert.deepEqual(calls, ['same']);
});

test('permission revocation during a tool prevents the next step', async () => {
  const permissions = new Set(['write:notes']);
  const {runner, store, calls} = recorded(a => {
    permissions.clear(); return {text: a.text};
  });
  await assert.rejects(runner.run(input([note('first'), note('second')], {permissions})), /run_input_conflict/);
  assert.deepEqual(calls, ['first']);
  assert.equal(store.get('bound').next, 1);
});

test('unknown checkpoint schema versions are rejected without mutation', async () => {
  const {runner, store, calls} = recorded();
  await runner.run(input([note('same')]));
  store.get('bound').version = 2;
  const before = structuredClone(store.get('bound'));
  await assert.rejects(runner.run(input([note('same')])), /invalid_checkpoint/);
  assert.deepEqual(store.get('bound'), before); assert.deepEqual(calls, ['same']);
});

test('modified recorded result bytes fail checkpoint integrity validation', async () => {
  const {runner, store, calls} = recorded();
  await runner.run(input([note('same')]));
  store.get('bound').results[0].text = 'forged';
  await assert.rejects(runner.run(input([note('same')])), /invalid_checkpoint/);
  assert.deepEqual(calls, ['same']);
});

test('a tool retaining its result object cannot later rewrite stored results', async () => {
  const value = {text: 'original'};
  const {runner, store} = recorded(() => value);
  await runner.run(input([note('same')])); value.text = 'modified';
  assert.equal(store.get('bound').results[0].text, 'original');
  assert.equal((await runner.run(input([note('same')]))).results[0].text, 'original');
});

test('a suspended run does not block a different run ID in the same Map', async () => {
  let release, entered;
  const started = new Promise(resolve => { entered = resolve; });
  const gate = new Promise(resolve => { release = resolve; });
  const {runner, calls} = recorded(async a => {
    if (a.text === 'first') { entered(); await gate; }
    return {text: a.text};
  });
  const first = runner.run(input([note('first')])); await started;
  try {
    assert.equal((await runner.run(input([note('second')], {runId: 'other'}))).next, 1);
  } finally { release(); await first; }
  assert.deepEqual(calls, ['first', 'second']);
});

// Per-run dependencies must remain stable across suspension. These tests only
// use in-process registries and Maps; no external services or side effects.
test('a suspended run keeps its original checkpoint store after runner field reassignment', async () => {
  let release, entered;
  const started = new Promise(resolve => { entered = resolve; });
  const gate = new Promise(resolve => { release = resolve; });
  const {runner, server, store, calls} = recorded(async a => {
    entered(); await gate; return {text: a.text};
  });
  const replacement = new Map();
  const other = new AgentRunner({server, checkpointStore: store});
  const running = runner.run(input([note('once')]));
  await started;
  try {
    runner.store = replacement;
    await assert.rejects(other.run(input([note('once')])), /run_in_progress/);
  } finally { release(); await running; }
  assert.equal(store.get('bound').next, 1);
  assert.equal(replacement.size, 0);
  assert.equal((await other.run(input([note('once')]))).next, 1);
  assert.deepEqual(calls, ['once']);
});

test('a suspended run keeps its original server after runner field reassignment', async () => {
  let release, entered;
  const started = new Promise(resolve => { entered = resolve; });
  const gate = new Promise(resolve => { release = resolve; });
  const original = recorded(async a => {
    if (a.text === 'first') { entered(); await gate; }
    return {text: a.text};
  });
  const replacement = recorded();
  const running = original.runner.run(input([note('first'), note('second')]));
  await started;
  try { original.runner.server = replacement.server; }
  finally { release(); await running; }
  assert.deepEqual(original.calls, ['first', 'second']);
  assert.deepEqual(replacement.calls, []);
});

test('a partially completed JSON checkpoint resumes only remaining steps after cancellation', async () => {
  const controller = new AbortController();
  const {runner, server, store, calls} = recorded(a => {
    if (a.text === 'first') controller.abort();
    return {text: a.text};
  });
  const steps = [note('first'), note('second'), note('third')];
  await assert.rejects(runner.run(input(steps, {signal: controller.signal})), /cancelled/);
  const restored = new Map(JSON.parse(JSON.stringify([...store])));
  const next = new AgentRunner({server, checkpointStore: restored});
  assert.equal((await next.run(input(steps))).next, 3);
  assert.deepEqual(calls, ['first', 'second', 'third']);
  assert.equal(store.get('bound').next, 1);
});
