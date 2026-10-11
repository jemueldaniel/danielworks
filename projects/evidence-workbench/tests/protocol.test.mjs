import test,{before,after} from 'node:test';
import assert from 'node:assert/strict';
import {stack,rpc,initialize,initialized} from './helpers.mjs';
let system;
before(async()=>{system=await stack()});
after(async()=>{await system?.close()});

test('real initialize negotiates the pinned protocol over TCP',async()=>{
  const result=await initialize(system.url);
  assert.equal(result.status,200);
  assert.equal(result.body.id,1);
  assert.equal(result.body.result.protocolVersion,'2025-11-25');
  assert.match(result.session,/^[a-z0-9-]{16,100}$/i);
  const notice=await initialized(system.url,result.session);
  assert.equal(notice.status,202);assert.equal(notice.body,null);
});
test('read profile schemas and tool execution use the actual backend',async()=>{
  const init=await initialize(system.url,'reader');await initialized(system.url,init.session,'reader');
  const tools=await rpc(system.url,{jsonrpc:'2.0',id:2,method:'tools/list'},init.session,'reader');
  assert.equal(tools.body.result.tools.some(t=>t.name==='run_submit'),false);
  const search=tools.body.result.tools.find(t=>t.name==='search_preview');
  assert.equal(search.inputSchema.type,'object');assert.equal(search.inputSchema.additionalProperties,false);
  const result=await rpc(system.url,{jsonrpc:'2.0',id:3,method:'tools/call',params:{name:'search_preview',arguments:{query:'password',k:2}}},init.session,'reader');
  assert.equal(result.body.result.structuredContent.items[0].id,'alpha');
  const denied=await rpc(system.url,{jsonrpc:'2.0',id:4,method:'tools/call',params:{name:'run_submit',arguments:{key:'denied',engine:'fts5',k:2}}},init.session,'reader');
  assert.ok(denied.body.error||denied.body.result.isError);
  const list=await fetch(system.url+'/api/operator/jobs').then(x=>x.json());
  assert.equal(list.items.some(x=>x.key==='denied'),false);
});
test('sessions are profile-bound and initialization is required',async()=>{
  const init=await initialize(system.url,'reader');
  assert.equal((await rpc(system.url,{jsonrpc:'2.0',id:8,method:'tools/list'},init.session,'reader')).status,400);
  await initialized(system.url,init.session,'reader');
  assert.equal((await rpc(system.url,{jsonrpc:'2.0',id:9,method:'tools/list'},init.session,'operator')).status,403);
  assert.equal((await rpc(system.url,{jsonrpc:'2.0',id:10,method:'tools/list'},'unknown-session','reader')).status,404);
});
test('invalid arguments and unknown tools do not create work',async()=>{
  const init=await initialize(system.url);await initialized(system.url,init.session);
  for(const arguments_ of [{key:'invalid',engine:'fts5',k:0},{key:'invalid',engine:'fts5',k:2,tenant:'other'}]){
    const result=await rpc(system.url,{jsonrpc:'2.0',id:15,method:'tools/call',params:{name:'run_submit',arguments:arguments_}},init.session);
    assert.ok(result.body.error||result.body.result.isError);
  }
  const list=await fetch(system.url+'/api/operator/jobs').then(x=>x.json());
  assert.equal(list.items.some(x=>x.key==='invalid'),false);
});
test('SDK creates, executes, inspects, paginates and cancels real durable jobs',async()=>{
  const {WorkbenchMcpClient}=await import('../dist/mcp-client.js');
  const client=await WorkbenchMcpClient.connect(system.url+'/mcp/operator');
  try{
    const job=await client.submit({key:'sdk-run',engine:'fts5',k:2});assert.equal(job.state,'pending');
    assert.equal((await client.submit({key:'sdk-run',engine:'fts5',k:2})).key,'sdk-run');
    await assert.rejects(client.submit({key:'sdk-run',engine:'lexical',k:2}));
    assert.equal((await client.workOnce()).job.state,'done');
    const report=await client.inspect('sdk-run');assert.equal(report.result.mrr_at_k,0.8);
    await client.submit({key:'sdk-cancel',engine:'lexical',k:2});
    assert.equal((await client.cancel('sdk-cancel')).cancelled,true);
    assert.equal((await client.inspect('sdk-cancel')).state,'cancelled');
    const page=await client.list({limit:1});assert.equal(page.items.length,1);assert.ok(page.next_cursor);
    assert.notEqual((await client.list({limit:1,cursor:page.next_cursor})).items[0].key,page.items[0].key);
  }finally{await client.close()}
});
test('pre-aborted mutation does not dispatch and session close is explicit',async()=>{
  const {WorkbenchMcpClient}=await import('../dist/mcp-client.js');
  const client=await WorkbenchMcpClient.connect(system.url+'/mcp/operator');
  const controller=new AbortController();controller.abort();
  await assert.rejects(client.submit({key:'abort-test',engine:'fts5',k:2},{signal:controller.signal}));
  assert.equal((await fetch(system.url+'/api/operator/jobs/abort-test')).status,404);
  await client.close();await assert.rejects(client.list());
});
test('wire boundary rejects foreign origins, oversized bodies, batches and bad media',async()=>{
  const init={jsonrpc:'2.0',id:30,method:'initialize',params:{protocolVersion:'2025-11-25',capabilities:{},clientInfo:{name:'wire',version:'1'}}};
  assert.equal((await rpc(system.url,init,null,'operator',{Origin:'https://untrusted.example'})).status,403);
  assert.equal((await fetch(system.url+'/mcp/operator',{method:'POST',headers:{'Content-Type':'text/plain'},body:'{}'})).status,415);
  assert.equal((await fetch(system.url+'/mcp/operator',{method:'POST',headers:{'Content-Type':'application/json'},body:'x'.repeat(8193)})).status,413);
  const batch=await rpc(system.url,[init,init]);assert.equal(batch.status,400);
});
test('SDK read-only profile cannot bypass the actual tool permission boundary',async()=>{
  const {WorkbenchMcpClient}=await import('../dist/mcp-client.js');
  const client=await WorkbenchMcpClient.connect(system.url+'/mcp/reader');
  try{await assert.rejects(client.submit({key:'profile-bypass',engine:'fts5',k:2}))}finally{await client.close()}
  assert.equal((await fetch(system.url+'/api/operator/jobs/profile-bypass')).status,404);
});
test('backend loss is a recoverable error, not invented success',async()=>{
  await system.stopBackend();
  try{
    const response=await fetch(system.url+'/api/operator/jobs');assert.equal(response.status,503);
  }finally{await system.restartBackend()}
  const result=await fetch(system.url+'/api/operator/jobs/sdk-run').then(x=>x.json());
  assert.equal(result.state,'done');assert.equal(result.result.mrr_at_k,0.8);
});
