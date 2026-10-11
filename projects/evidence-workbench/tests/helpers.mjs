import {spawn} from 'node:child_process';
import {mkdtemp,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createInterface} from 'node:readline';
import {once} from 'node:events';
import {startGateway} from '../dist/server.js';
export const project=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
export async function backend(db,port=0){
  const proc=spawn(process.env.PYTHON??(process.platform==='win32'?'python':'python3'),
    ['-B',path.join(project,'backend/server.py'),'serve','--db',db,'--port',String(port)],
    {stdio:['ignore','pipe','pipe'],windowsHide:true});
  let errors=''; proc.stderr.on('data',chunk=>{errors=(errors+chunk).slice(-4096)});
  const reader=createInterface({input:proc.stdout});
  const ready=await new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>{proc.kill();reject(new Error('backend_start_timeout'));},7000);
    proc.once('error',error=>{clearTimeout(timer);reject(error)});
    proc.once('exit',code=>{clearTimeout(timer);if(code!==null)reject(new Error('backend_exited_'+code+': '+errors))});
    reader.once('line',line=>{clearTimeout(timer);try{resolve(JSON.parse(line))}catch(error){reject(error)}});
  });
  let closing;
  return {url:`http://127.0.0.1:${ready.port}/v1/`,port:ready.port,
    close(){
      closing??=(async()=>{
        // A signal-terminated Windows child can have null exitCode after exit.
        // Repeated cleanup must not wait for an event already received.
        if(proc.exitCode===null&&proc.signalCode===null){const done=once(proc,'exit');proc.kill();await done}
        reader.close();
      })();
      return closing;
    }};
}
export async function stack(){
  const directory=await mkdtemp(path.join(tmpdir(),'evidence-workbench-'));
  const db=path.join(directory,'data.sqlite3'); let child=await backend(db);
  const gateway=await startGateway({backend:child.url,port:0});
  return {url:gateway.url,db,
    async stopBackend(){await child.close()},
    async restartBackend(){const port=child.port;await child.close();child=await backend(db,port)},
    async close(){await gateway.close();await child.close();await rm(directory,{recursive:true,force:true})}};
}
export async function rpc(url,body,session,profile='operator',extra={}){
  const response=await fetch(`${url}/mcp/${profile}`,{method:'POST',headers:{
    'content-type':'application/json',Accept:'application/json, text/event-stream',
    ...(session?{'mcp-session-id':session,'mcp-protocol-version':'2025-11-25'}:{}),...extra},body:JSON.stringify(body)});
  const text=await response.text();
  return {status:response.status,session:response.headers.get('mcp-session-id'),body:text?JSON.parse(text):null};
}
export async function initialize(url,profile='operator'){
  const result=await rpc(url,{jsonrpc:'2.0',id:1,method:'initialize',params:{protocolVersion:'2025-11-25',capabilities:{},clientInfo:{name:'wire-tests',version:'1'}}},null,profile);
  return result;
}
export async function initialized(url,session,profile='operator'){
  return rpc(url,{jsonrpc:'2.0',method:'notifications/initialized'},session,profile);
}
