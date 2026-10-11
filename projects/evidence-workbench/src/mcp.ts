import {McpServer} from '@modelcontextprotocol/sdk/server/mcp.js';
import type {CallToolResult} from '@modelcontextprotocol/sdk/types.js';
import {z} from 'zod';
import {ApiClient,ApiError} from './api-client.js';
import * as S from './schema.js';
async function result(work:()=>Promise<object>):Promise<CallToolResult>{
  try{const value=await work();return {content:[{type:'text',text:JSON.stringify(value)}],structuredContent:value as Record<string,unknown>}}
  catch(error){const value=error instanceof ApiError?{error:error.code,outcome:error.outcome}:{error:'tool_failed',outcome:'unknown'};
    return {isError:true,content:[{type:'text',text:JSON.stringify(value)}]}}
}
export function createMcp(backend:string,profile:S.Profile){
  const api=new ApiClient(backend,profile);
  const server=new McpServer({name:'evaluation-workbench',version:'0.1.0'},{instructions:'Synthetic local evaluation. Transport abort is not durable cancellation. Inspect the saved key after an uncertain mutation; use run_cancel to cancel queued work.'});
  const read={readOnlyHint:true,destructiveHint:false,idempotentHint:true,openWorldHint:false};
  server.registerTool('dataset_info',{description:'Inspect the pinned synthetic evaluation input.',inputSchema:z.object({}).strict(),outputSchema:S.Dataset,annotations:read},
    async(_,extra)=>result(()=>api.dataset(extra.signal)));
  server.registerTool('runs_list',{description:'List durable runs using bounded keyset pagination.',inputSchema:S.PageInput,outputSchema:S.JobPage,annotations:read},
    async(input,extra)=>result(()=>api.list(input,extra.signal)));
  server.registerTool('run_inspect',{description:'Inspect durable state before deciding whether to retry.',inputSchema:z.object({key:S.Id}).strict(),outputSchema:S.Job,annotations:read},
    async(input,extra)=>result(()=>api.inspect(input.key,extra.signal)));
  server.registerTool('search_preview',{description:'Execute an actual SQLite FTS5 query against the synthetic corpus.',inputSchema:S.SearchInput,outputSchema:S.Search,annotations:read},
    async(input,extra)=>result(()=>api.search(input.query,input.k,extra.signal)));
  if(profile==='operator'){
    server.registerTool('run_submit',{description:'Persist a run. Reusing a key binds the identical request; changed requests conflict.',inputSchema:S.Submit,outputSchema:S.Job,
      annotations:{readOnlyHint:false,destructiveHint:false,idempotentHint:true,openWorldHint:false}},async(input,extra)=>result(()=>api.submit(input,extra.signal)));
    server.registerTool('run_cancel',{description:'Durably cancel pending/running work and fence stale completion. No undo of external effects is implied.',inputSchema:z.object({key:S.Id}).strict(),outputSchema:S.Cancel,
      annotations:{readOnlyHint:false,destructiveHint:true,idempotentHint:true,openWorldHint:false}},async(input,extra)=>result(()=>api.cancel(input.key,extra.signal)));
    server.registerTool('work_once',{description:'Claim at most one queued evaluation; process at most five cases and persist checkpoints. No continuous worker.',inputSchema:z.object({max_cases:z.number().int().min(1).max(5).default(5)}).strict(),outputSchema:S.Work,
      annotations:{readOnlyHint:false,destructiveHint:false,idempotentHint:false,openWorldHint:false}},async(input,extra)=>result(()=>api.workOnce(input.max_cases,extra.signal)));
  }
  return server;
}
