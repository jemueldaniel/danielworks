import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import type {Transport} from '@modelcontextprotocol/sdk/shared/transport.js';
import {StreamableHTTPClientTransport} from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import {CallToolResultSchema} from '@modelcontextprotocol/sdk/types.js';
import {z} from 'zod';
import {ApiError,loopbackURL} from './api-client.js';
import * as S from './schema.js';
export class WorkbenchMcpClient {
  private closed=false;
  private constructor(private readonly client:Client,private readonly transport:StreamableHTTPClientTransport){}
  static async connect(endpoint:string){
    const url=loopbackURL(endpoint);if(!/^\/mcp\/(reader|operator|other-reader)$/.test(url.pathname))throw new ApiError('invalid_url',undefined,'not_sent');
    const client=new Client({name:'workbench-typed-client',version:'0.1.0'});
    // SDK v1 models optional callbacks/sessionId with explicit undefined.
    // This narrow boundary assertion bridges its declaration mismatch; wire tests
    // exercise the unmodified official transport. Own input/output types stay strict.
    const transport=new StreamableHTTPClientTransport(url,{requestInit:{credentials:'omit',redirect:'manual'}});
    try{await client.connect(transport as Transport,{timeout:5000});return new WorkbenchMcpClient(client,transport)}
    catch{await client.close();throw new ApiError('connect_failed',undefined,'not_sent')}
  }
  private async call<T>(name:string,args:Record<string,unknown>,schema:z.ZodType<T>,options:{signal?:AbortSignal}={}):Promise<T>{
    if(this.closed||options.signal?.aborted)throw new ApiError(this.closed?'closed':'aborted',undefined,'not_sent');
    try{
      const value=CallToolResultSchema.parse(await this.client.callTool({name,arguments:args},CallToolResultSchema,{timeout:5000,...options}));
      if(value.isError){
        const text=value.content.find(item=>item.type==='text');
        let outcome:'unknown'|'rejected'|'not_sent'='unknown';
        if(text?.type==='text'){try{const parsed=JSON.parse(text.text) as {outcome?:unknown};if(parsed.outcome==='rejected'||parsed.outcome==='not_sent')outcome=parsed.outcome}catch{}}
        throw new ApiError('tool_error',undefined,outcome);
      }
      return schema.parse(value.structuredContent);
    }catch(error){if(error instanceof ApiError)throw error;throw new ApiError('protocol_or_transport_error',undefined,'unknown')}
  }
  dataset(){return this.call('dataset_info',{},S.Dataset)}
  list(input:z.infer<typeof S.PageInput>={}){return this.call('runs_list',S.PageInput.parse(input),S.JobPage)}
  inspect(key:string){return this.call('run_inspect',{key:S.Id.parse(key)},S.Job)}
  search(query:string,k=2){return this.call('search_preview',S.SearchInput.parse({query,k}),S.Search)}
  submit(input:S.SubmitInput,options:{signal?:AbortSignal}={}){return this.call('run_submit',S.Submit.parse(input),S.Job,options)}
  cancel(key:string){return this.call('run_cancel',{key:S.Id.parse(key)},S.Cancel)}
  workOnce(maxCases=5){return this.call('work_once',{max_cases:z.number().int().min(1).max(5).parse(maxCases)},S.Work)}
  async close(){if(this.closed)return;this.closed=true;try{await this.transport.terminateSession()}catch{}finally{await this.client.close()}}
}
