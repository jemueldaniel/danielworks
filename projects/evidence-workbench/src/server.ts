import http,{type IncomingMessage,type ServerResponse} from 'node:http';
import type {AddressInfo} from 'node:net';
import {readFile} from 'node:fs/promises';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {randomUUID} from 'node:crypto';
import type {Transport} from '@modelcontextprotocol/sdk/shared/transport.js';
import {StreamableHTTPServerTransport} from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import {isInitializeRequest} from '@modelcontextprotocol/sdk/types.js';
import {createMcp} from './mcp.js';
import {loopbackURL,boundedResponse} from './api-client.js';
import type {Profile} from './schema.js';

type Session={transport:StreamableHTTPServerTransport,mcp:ReturnType<typeof createMcp>,profile:Profile,initialized:boolean,last:number};
class Boundary extends Error{constructor(readonly status:number,readonly code:string){super(code)}}
async function body(req:IncomingMessage):Promise<Buffer>{
  const chunks:Buffer[]=[];let size=0;
  for await(const chunk of req){const bytes=Buffer.isBuffer(chunk)?chunk:Buffer.from(chunk);size+=bytes.length;
    if(size>8192)throw new Boundary(413,'body_too_large');chunks.push(bytes)}
  return Buffer.concat(chunks);
}
function send(res:ServerResponse,status:number,value:unknown){
  if(res.headersSent){res.end();return}
  const data=JSON.stringify(value);res.writeHead(status,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});res.end(data);
}
export async function startGateway(options:{backend:string,port?:number,diagnostics?:boolean}){
  const backend=loopbackURL(options.backend);if(backend.pathname!=='/v1/')throw new Error('backend_path');
  const sessions=new Map<string,Session>();let pending=0;let stopping=false;
  const server=http.createServer({maxHeaderSize:8192},(req,res)=>{
    const requestId=randomUUID(),started=performance.now();
    res.setHeader('X-Request-Id',requestId);res.setHeader('X-Content-Type-Options','nosniff');res.setHeader('Cache-Control','no-store');
    if(options.diagnostics)res.once('finish',()=>console.error(JSON.stringify({event:'gateway',request_id:requestId,status:res.statusCode,elapsed_ms:Math.round(performance.now()-started)})));
    void handle(req,res).catch(error=>send(res,error instanceof Boundary?error.status:503,{error:error instanceof Boundary?error.code:'backend_unavailable'}));
  });
  server.requestTimeout=6000;server.headersTimeout=5000;server.keepAliveTimeout=1000;server.maxConnections=24;
  server.on('clientError',(_,socket)=>socket.end('HTTP/1.1 400 Bad Request\r\nConnection: close\r\nContent-Length: 0\r\n\r\n'));
  async function handle(req:IncomingMessage,res:ServerResponse){
    if(stopping)throw new Boundary(503,'stopping');
    const host=`127.0.0.1:${(server.address() as AddressInfo).port}`;
    if(req.headers.host!==host)throw new Boundary(403,'host_denied');
    if(req.headers.origin!==undefined&&req.headers.origin!==`http://${host}`)throw new Boundary(403,'origin_denied');
    const url=new URL(req.url??'/',`http://${host}`);
    if(url.origin!==`http://${host}`||url.href.length>2048)throw new Boundary(400,'invalid_url');
    const apiMatch=/^\/api\/(reader|operator|other-reader)\/(dataset|search|jobs(?:\/[a-z][a-z0-9_-]{0,63}(?:\/cancel)?)?|work)$/.exec(url.pathname);
    if(apiMatch){
      if(req.method!=='GET'&&req.method!=='POST')throw new Boundary(405,'method_not_allowed');
      const write=req.method==='POST';
      if(write&&apiMatch[1]!=='operator')throw new Boundary(403,'permission_denied');
      if(write&&req.headers['content-type']?.split(';')[0]?.trim().toLowerCase()!=='application/json')throw new Boundary(415,'media_type');
      const bytes=write?await body(req):undefined;
      const response=await fetch(new URL(apiMatch[2]!+url.search,backend),{method:req.method,redirect:'manual',credentials:'omit',signal:AbortSignal.timeout(5000),
        headers:{'Content-Type':'application/json','X-Workbench-Profile':apiMatch[1]!},...(bytes?{body:new Uint8Array(bytes)}:{})});
      return send(res,response.status,await boundedResponse(response));
    }
    const mcpMatch=/^\/mcp\/(reader|operator|other-reader)$/.exec(url.pathname);
    if(mcpMatch){
      const profile=mcpMatch[1] as Profile;
      if(url.search)throw new Boundary(400,'invalid_url');
      const id=req.headers['mcp-session-id'];
      if(id!==undefined&&(typeof id!=='string'||id.length>100))throw new Boundary(400,'invalid_session');
      let session=typeof id==='string'?sessions.get(id):undefined;
      if(id&&!session)throw new Boundary(404,'unknown_session');
      if(session&&session.profile!==profile)throw new Boundary(403,'session_profile_mismatch');
      let input:unknown;
      if(req.method==='POST'){
        if(req.headers['content-type']?.split(';')[0]?.trim().toLowerCase()!=='application/json')throw new Boundary(415,'media_type');
        const bytes=await body(req);try{input=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes))}catch{throw new Boundary(400,'invalid_json')}
        if(!input||typeof input!=='object'||Array.isArray(input))throw new Boundary(400,'invalid_request');
      }else if(req.method==='GET'){
        // No standalone SSE stream. JSON responses are a standard Streamable HTTP mode.
        throw new Boundary(405,'standalone_sse_not_supported');
      }else if(req.method!=='DELETE')throw new Boundary(405,'method_not_allowed');
      if(!session){
        if(req.method!=='POST'||!isInitializeRequest(input))throw new Boundary(400,'initialization_required');
        if(sessions.size+pending>=16)throw new Boundary(503,'session_limit');
        pending++;
        const mcp=createMcp(backend.href,profile);
        const transport=new StreamableHTTPServerTransport({sessionIdGenerator:()=>randomUUID(),enableJsonResponse:true,
          onsessioninitialized:sessionId=>{sessions.set(sessionId,created)}});
        const created:Session={transport,mcp,profile,initialized:false,last:Date.now()};
        transport.onclose=()=>{if(transport.sessionId)sessions.delete(transport.sessionId)};
        // SDK v1 optional callback declarations require the same narrow bridge as the client.
        try{await mcp.connect(transport as Transport);await transport.handleRequest(req,res,input)}
        finally{pending--;if(!transport.sessionId)await mcp.close()}
        return;
      }
      session.last=Date.now();
      const notification=input as {jsonrpc?:unknown,method?:unknown,id?:unknown}|undefined;
      const ready=notification?.jsonrpc==='2.0'&&notification.method==='notifications/initialized'&&!('id' in notification);
      if(req.method==='POST'&&!ready&&!session.initialized)throw new Boundary(400,'initialized_notification_required');
      await session.transport.handleRequest(req,res,input);
      if(ready)session.initialized=true;
      return;
    }
    if(req.method!=='GET'||url.search)throw new Boundary(404,'not_found');
    const assets:Record<string,[string,string]>={'/':['index.html','text/html; charset=utf-8'],'/app.js':['app.js','text/javascript; charset=utf-8'],'/style.css':['style.css','text/css; charset=utf-8']};
    const asset=assets[url.pathname];if(!asset)throw new Boundary(404,'not_found');
    const data=await readFile(new URL('./web/'+asset[0],import.meta.url));
    res.writeHead(200,{'Content-Type':asset[1],'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"});res.end(data);
  }
  const expiry=setInterval(()=>{for(const [id,session] of sessions)if(Date.now()-session.last>120000){sessions.delete(id);void session.mcp.close()}},10000);expiry.unref();
  await new Promise<void>((resolve,reject)=>{server.once('error',reject);server.listen(options.port??8765,'127.0.0.1',resolve)});
  return {url:`http://127.0.0.1:${(server.address() as AddressInfo).port}`,async close(){if(stopping)return;stopping=true;clearInterval(expiry);
    await Promise.allSettled([...sessions.values()].map(session=>session.mcp.close()));sessions.clear();
    await new Promise<void>(resolve=>{server.closeAllConnections();server.close(()=>resolve())})}};
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){
  const backend=process.argv[2];if(!backend)throw new Error('Explicit backend URL required');
  const gateway=await startGateway({backend,port:Number(process.argv[3]??8765),diagnostics:true});
  console.log(JSON.stringify({event:'ready',url:gateway.url}));
  for(const signal of ['SIGINT','SIGTERM'] as const)process.once(signal,()=>{void gateway.close().then(()=>process.exit(0))});
}
