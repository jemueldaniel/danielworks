import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import {stack,initialize,rpc} from './helpers.mjs';
import {ApiClient} from '../dist/api-client.js';

test('a schema-valid response for another operation cannot confirm this write',{timeout:15000},async()=>{
  const system=await stack();let writes=0;
  const proxy=http.createServer(async(req,res)=>{
    writes++;const chunks=[];for await(const c of req)chunks.push(c);
    const response=await fetch(system.url+'/api/operator/jobs',{method:'POST',headers:{'content-type':'application/json'},body:Buffer.concat(chunks)});
    const actual=await response.json();
    res.writeHead(200,{'content-type':'application/json'});
    res.end(JSON.stringify({...actual,key:'different-operation'}));
  });
  await new Promise(resolve=>proxy.listen(0,'127.0.0.1',resolve));
  try{
    const client=new ApiClient(`http://127.0.0.1:${proxy.address().port}/v1/`,'operator');
    await assert.rejects(client.submit({key:'bound-request',engine:'fts5',k:2}),error=>error.code==='response_identity_mismatch'&&error.outcome==='unknown');
    assert.equal(writes,1);
    assert.equal((await fetch(system.url+'/api/operator/jobs/bound-request')).status,200);
  }finally{proxy.closeAllConnections();await new Promise(resolve=>proxy.close(resolve));await system.close()}
});

test('MCP session capacity is bounded and DELETE reclaims an actual session',{timeout:15000},async()=>{
  const system=await stack();
  try{
    const sessions=[];
    for(let i=0;i<16;i++){const result=await initialize(system.url);assert.equal(result.status,200);sessions.push(result.session)}
    const denied=await initialize(system.url);assert.equal(denied.status,503);assert.equal(denied.body.error,'session_limit');
    const deleted=await fetch(system.url+'/mcp/operator',{method:'DELETE',headers:{'mcp-session-id':sessions[0],'mcp-protocol-version':'2025-11-25'}});
    assert.equal(deleted.status,200);
    assert.equal((await rpc(system.url,{jsonrpc:'2.0',id:2,method:'tools/list'},sessions[0])).status,404);
    assert.equal((await initialize(system.url)).status,200);
    assert.equal((await fetch(system.url+'/mcp/operator')).status,405);
  }finally{await system.close()}
});
