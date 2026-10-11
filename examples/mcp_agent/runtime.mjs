import { createHash } from 'node:crypto';

function sha(value){ return createHash('sha256').update(JSON.stringify(value)).digest('hex'); }

export class ToolRegistry {
  constructor(){ this.tools=new Map(); }
  register({name,schema,permission,run}){ if(this.tools.has(name)) throw new Error('duplicate_tool'); this.tools.set(name,{name,schema,permission,run}); }
  list(){ return [...this.tools.values()].map(({name,schema,permission})=>({name,schema,permission})); }
  async call({name,args,permissions,signal}){
    const t=this.tools.get(name); if(!t) throw new Error('unknown_tool');
    if(!permissions.has(t.permission)) throw new Error('permission_denied');
    if(signal?.aborted) throw new Error('cancelled');
    if(!t.schema(args)) throw new Error('invalid_arguments');
    return t.run(args,{signal});
  }
}

export class McpServer {
  constructor(registry){ this.registry=registry; }
  async handle(req,ctx){
    if(req?.jsonrpc!=='2.0') return {jsonrpc:'2.0',id:req?.id??null,error:{code:-32600,message:'invalid request'}};
    if(req.method==='tools/list') return {jsonrpc:'2.0',id:req.id,result:{tools:this.registry.list()}};
    if(req.method==='tools/call'){
      try { const result=await this.registry.call({name:req.params?.name,args:req.params?.arguments??{},permissions:ctx.permissions,signal:ctx.signal});
        return {jsonrpc:'2.0',id:req.id,result:{content:[{type:'json',json:result}]}};
      } catch(e){ return {jsonrpc:'2.0',id:req.id,error:{code:-32000,message:e.message}}; }
    }
    return {jsonrpc:'2.0',id:req.id,error:{code:-32601,message:'unsupported method'}};
  }
}

// This remains an in-process exercise. A checksum detects accidental changes;
// it is not authentication, a signature, durable storage, or exactly-once I/O.
const MAX_STEPS = 64;
const MAX_JSON_BYTES = 65_536;
const activeRuns = new WeakMap();
const hex = /^[0-9a-f]{64}$/;

function snapshotJson(value, errorCode) {
  let nodes = 0;
  const ancestors = new Set();
  const fail = () => { throw new Error(errorCode); };
  function copy(item, depth) {
    if (++nodes > 2048 || depth > 16) fail();
    if (item === null || typeof item === 'boolean') return item;
    if (typeof item === 'string') {
      if (item.length > MAX_JSON_BYTES) fail();
      return item;
    }
    if (typeof item === 'number') {
      if (!Number.isFinite(item)) fail();
      return item;
    }
    if (typeof item !== 'object' || ancestors.has(item)) fail();
    const array = Array.isArray(item);
    if (!array && ![Object.prototype, null].includes(Object.getPrototypeOf(item))) fail();
    const keys = Reflect.ownKeys(item);
    if (keys.length > 2048 || keys.some(k => typeof k !== 'string')) fail();
    const descriptors = Object.getOwnPropertyDescriptors(item);
    ancestors.add(item);
    let output;
    if (array) {
      if (item.length > 2048 || keys.length !== item.length + 1) fail();
      output = [];
      for (let i = 0; i < item.length; i++) {
        const d = descriptors[String(i)];
        if (!d || !d.enumerable || !Object.hasOwn(d, 'value')) fail();
        output.push(copy(d.value, depth + 1));
      }
    } else {
      output = Object.create(null);
      for (const key of keys.sort()) {
        const d = descriptors[key];
        if (!d.enumerable || !Object.hasOwn(d, 'value')) fail();
        output[key] = copy(d.value, depth + 1);
      }
    }
    ancestors.delete(item);
    return output;
  }
  const encoded = JSON.stringify(copy(value, 0));
  if (Buffer.byteLength(encoded, 'utf8') > MAX_JSON_BYTES) fail();
  return JSON.parse(encoded);
}

function checkpoint(runId, requestSha256, next, results) {
  const core = {version: 1, runId, requestSha256, next,
    results: snapshotJson(results, 'invalid_tool_result')};
  return {...core, checkpointSha256: sha(core)};
}

function restoreCheckpoint(saved, runId, requestSha256, stepCount) {
  const cp = snapshotJson(saved, 'invalid_checkpoint');
  const fields = ['version', 'runId', 'requestSha256', 'next', 'results', 'checkpointSha256'];
  if (!cp || Array.isArray(cp) || Object.keys(cp).length !== fields.length ||
      fields.some(k => !Object.hasOwn(cp, k)) || cp.version !== 1 || cp.runId !== runId ||
      typeof cp.requestSha256 !== 'string' || !hex.test(cp.requestSha256) ||
      typeof cp.checkpointSha256 !== 'string' || !hex.test(cp.checkpointSha256) ||
      !Number.isInteger(cp.next) || cp.next < 0 || cp.next > MAX_STEPS ||
      !Array.isArray(cp.results) || cp.results.length !== cp.next) {
    throw new Error('invalid_checkpoint');
  }
  const core = {version: cp.version, runId: cp.runId, requestSha256: cp.requestSha256,
    next: cp.next, results: cp.results};
  if (sha(core) !== cp.checkpointSha256) throw new Error('invalid_checkpoint');
  if (cp.requestSha256 !== requestSha256) throw new Error('run_input_conflict');
  if (cp.next > stepCount) throw new Error('invalid_checkpoint');
  return cp;
}

export class AgentRunner {
  constructor({server, checkpointStore}) {
    if (!(checkpointStore instanceof Map)) throw new Error('invalid_checkpoint_store');
    this.server = server;
    this.store = checkpointStore;
  }

  async run({runId, steps, permissions, signal}) {
    // A suspended run retains its starting dependencies even when callers
    // reconfigure this runner for a later invocation. This is not store authentication.
    const {server, store} = this;
    if (signal?.aborted) throw new Error('cancelled');
    if (typeof runId !== 'string' || !/^[A-Za-z0-9_-]{1,64}$/.test(runId) ||
        !Array.isArray(steps) || steps.length > MAX_STEPS || !(permissions instanceof Set) ||
        permissions.size > 64 || [...permissions].some(p =>
          typeof p !== 'string' || !/^[A-Za-z0-9_.:-]{1,64}$/.test(p))) {
      throw new Error('invalid_run_input');
    }
    const request = snapshotJson({version: 1, runId, steps,
      permissions: [...permissions].sort()}, 'invalid_run_input');
    if (request.steps.some(step => !step || Array.isArray(step) || typeof step !== 'object' ||
        Object.keys(step).some(k => !['name', 'arguments'].includes(k)) ||
        typeof step.name !== 'string' || !/^[A-Za-z0-9_.:-]{1,64}$/.test(step.name))) {
      throw new Error('invalid_run_input');
    }
    const requestSha256 = sha(request);
    const locks = activeRuns.get(store) ?? new Set();
    if (locks.has(runId)) throw new Error('run_in_progress');
    locks.add(runId);
    activeRuns.set(store, locks);
    try {
      const saved = store.get(runId);
      let cp = saved === undefined && !store.has(runId)
        ? checkpoint(runId, requestSha256, 0, [])
        : restoreCheckpoint(saved, runId, requestSha256, request.steps.length);
      // Bind identity before the first effect, including attempts that fail.
      // Old, unbound checkpoints are rejected above and never silently replaced.
      store.set(runId, snapshotJson(cp, 'invalid_checkpoint'));
      for (let i = cp.next; i < request.steps.length; i++) {
        if (signal?.aborted) throw new Error('cancelled');
        // Snapshot arguments, but fail closed when the caller revokes or changes
        // its live capability set between steps. An in-flight tool still owns
        // cooperative cancellation through the signal it already received.
        const livePermissions = [...permissions].sort();
        if (livePermissions.length !== request.permissions.length ||
            livePermissions.some((p, n) => p !== request.permissions[n])) {
          throw new Error('run_input_conflict');
        }
        const req = {jsonrpc: '2.0', id: i + 1, method: 'tools/call',
          params: snapshotJson(request.steps[i], 'invalid_run_input')};
        const res = await server.handle(req,
          {permissions: new Set(request.permissions), signal});
        if (res.error) throw new Error(res.error.message);
        cp = checkpoint(runId, requestSha256, i + 1,
          [...cp.results, res.result.content[0].json]);
        store.set(runId, snapshotJson(cp, 'invalid_checkpoint'));
      }
      return snapshotJson(cp, 'invalid_checkpoint');
    } finally {
      locks.delete(runId);
      if (locks.size === 0) activeRuns.delete(store);
    }
  }
}
