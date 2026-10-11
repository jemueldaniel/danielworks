import test,{before,after} from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import {stack} from './helpers.mjs';
import {ApiClient,ApiError} from '../dist/api-client.js';
let system;
before(async()=>{system=await stack()});after(async()=>{await system?.close()});
const operator=()=>new ApiClient(system.url+'/api/operator/','operator');
test('HTTP SDK rejects caller-selected tenant and invalid input before mutation',async()=>{
  assert.throws(()=>operator().submit({key:'bad',engine:'fts5',k:2,tenant:'other'}));
  assert.throws(()=>operator().submit({key:'bad',engine:'fts5',k:0}));
  assert.equal((await operator().list()).items.length,0);
});
test('HTTP SDK pre-aborted mutation is not sent',async()=>{
  const controller=new AbortController();controller.abort();
  await assert.rejects(operator().submit({key:'abort',engine:'fts5',k:2},controller.signal),e=>e instanceof ApiError&&e.outcome==='not_sent');
  await assert.rejects(operator().inspect('abort'),e=>e.status===404);
});
test('permission profile is pinned by gateway route, not supplied request header',async()=>{
  const reader=new ApiClient(system.url+'/api/reader/','operator');
  await assert.rejects(reader.submit({key:'denied',engine:'fts5',k:2}),e=>e.status===403&&e.outcome==='rejected');
  assert.equal((await operator().list()).items.length,0);
});
test('real concurrent SDK idempotency, changed-payload conflict and tenant partition',async()=>{
  const input={key:'concurrent',engine:'fts5',k:2};
  const results=await Promise.all(Array.from({length:6},()=>operator().submit(input)));
  assert.ok(results.every(x=>x.key==='concurrent'));
  await assert.rejects(operator().submit({...input,k:1}),e=>e.status===409&&e.code==='idempotency_conflict'&&e.outcome==='rejected');
  assert.equal((await new ApiClient(system.url+'/api/other-reader/').list()).items.length,0);
  await assert.rejects(new ApiClient(system.url+'/api/other-reader/').inspect(input.key),e=>e.status===404);
});
test('one real POST can commit then lose its response; SDK never automatically replays it',async()=>{
  let writes=0;const proxy=http.createServer(async(req,res)=>{
    writes++;const chunks=[];for await(const c of req)chunks.push(c);
    const reply=await fetch(system.url+'/api/operator/jobs',{method:'POST',headers:{'content-type':'application/json'},body:Buffer.concat(chunks)});
    assert.equal(reply.status,200);await reply.text();res.destroy();
  });await new Promise(r=>proxy.listen(0,'127.0.0.1',r));
  try{
    const client=new ApiClient(`http://127.0.0.1:${proxy.address().port}/v1/`,'operator');
    await assert.rejects(client.submit({key:'lost',engine:'fts5',k:2}),e=>e.outcome==='unknown');
    assert.equal(writes,1);assert.equal((await operator().inspect('lost')).state,'pending');
    assert.equal((await operator().list()).items.filter(x=>x.key==='lost').length,1);
  }finally{proxy.closeAllConnections();await new Promise(r=>proxy.close(r))}
});
test('an oversized real server response is bounded and never interpreted as confirmation',async()=>{
  const server=http.createServer((req,res)=>{req.resume();res.writeHead(200,{'content-type':'application/json'});res.end(JSON.stringify({padding:'x'.repeat(70000)}))});
  await new Promise(r=>server.listen(0,'127.0.0.1',r));
  try{await assert.rejects(new ApiClient(`http://127.0.0.1:${server.address().port}/v1/`,'operator').submit({key:'large',engine:'fts5',k:2}),e=>e.outcome==='unknown')}
  finally{server.closeAllConnections();await new Promise(r=>server.close(r))}
});
test('safe diagnostic failures do not contain payload text or exception details',async()=>{
  const response=await fetch(system.url+'/api/operator/jobs',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({key:'invalid',engine:'fts5',k:2,secret_field:'synthetic-private-marker'})});
  const body=await response.text();assert.equal(response.status,400);assert.ok(!body.includes('synthetic-private-marker'));assert.ok(!body.includes('Traceback'));
});
