import {z} from 'zod';
import {readJson,ClientError} from '../../../examples/read_client/client.mts';
import * as S from './schema.js';
export type Outcome='not_sent'|'rejected'|'unknown';
export class ApiError extends Error {
  constructor(readonly code:string,readonly status:number|undefined,readonly outcome:Outcome){super(code);this.name='ApiError'}
}
export function loopbackURL(value:string):URL {
  const url=new URL(value);
  if(url.protocol!=='http:'||url.hostname!=='127.0.0.1'||url.username||url.password||url.search||url.hash||!url.port)
    throw new ApiError('invalid_url',undefined,'not_sent');
  return url;
}
export async function boundedResponse(response:Response):Promise<unknown>{
  if(!response.headers.get('content-type')?.toLowerCase().startsWith('application/json'))throw new Error('media_type');
  const reader=response.body?.getReader();let total=0;const chunks:Uint8Array[]=[];
  if(reader){try{for(;;){const {done,value}=await reader.read();if(done)break;total+=value.length;
    if(total>65536){await reader.cancel();throw new Error('response_limit')}chunks.push(value)}}finally{reader.releaseLock()}}
  const bytes=new Uint8Array(total);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.length}
  return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes)) as unknown;
}
export class ApiClient {
  private readonly base:URL;
  constructor(base:string,private readonly profile:S.Profile='reader'){
    this.base=loopbackURL(base);
    if(!/^\/(v1|api\/(reader|operator|other-reader))\/$/.test(this.base.pathname))throw new ApiError('invalid_url',undefined,'not_sent');
  }
  private async get<T>(route:string,schema:z.ZodType<T>,signal?:AbortSignal):Promise<T>{
    try{return await readJson(new URL(route,this.base),input=>schema.parse(input),{
      allowLoopbackHttp:true,maxAttempts:2,deadlineMs:2500,retryDelayMs:50,maxBytes:65536,
      ...(signal?{signal}:{}),fetchImpl:(input,init)=>fetch(input,{...init,headers:{...init?.headers,'X-Workbench-Profile':this.profile}}),
    })}catch(error){if(error instanceof ClientError)throw new ApiError(error.code,error.status,'unknown');throw error}
  }
  private async post<T>(route:string,body:unknown,schema:z.ZodType<T>,signal?:AbortSignal):Promise<T>{
    if(signal?.aborted)throw new ApiError('aborted',undefined,'not_sent');
    const timeout=AbortSignal.timeout(5000);const combined=signal?AbortSignal.any([signal,timeout]):timeout;
    try{
      const response=await fetch(new URL(route,this.base),{method:'POST',credentials:'omit',redirect:'manual',cache:'no-store',
        headers:{'Content-Type':'application/json','Accept':'application/json','X-Workbench-Profile':this.profile},body:JSON.stringify(body),signal:combined});
      const data=await boundedResponse(response);
      if(!response.ok){
        const record=z.object({error:z.string().regex(/^[a-z_]{1,40}$/)}).safeParse(data);
        throw new ApiError(record.success?record.data.error:'request_failed',response.status,response.status>=400&&response.status<500?'rejected':'unknown');
      }
      return schema.parse(data);
    }catch(error){if(error instanceof ApiError)throw error;throw new ApiError(combined.aborted?'aborted_or_deadline':'outcome_unknown',undefined,'unknown')}
  }
  dataset(signal?:AbortSignal){return this.get('dataset',S.Dataset,signal)}
  list(input:z.infer<typeof S.PageInput>={},signal?:AbortSignal){
    const page=S.PageInput.parse(input);const query=new URLSearchParams();
    if(page.limit!==undefined)query.set('limit',String(page.limit));if(page.cursor!==undefined)query.set('cursor',page.cursor);
    return this.get('jobs'+(query.size?'?'+query:''),S.JobPage,signal);
  }
  inspect(key:string,signal?:AbortSignal){return this.get('jobs/'+S.Id.parse(key),S.Job,signal)}
  search(query:string,k=2,signal?:AbortSignal){const input=S.SearchInput.parse({query,k});return this.get('search?'+new URLSearchParams({q:input.query,k:String(input.k)}),S.Search,signal)}
  submit(input:S.SubmitInput,signal?:AbortSignal){
    const request=S.Submit.parse(input);
    return this.post('jobs',request,S.Job,signal).then(job=>{
      // Shape validation alone cannot bind a confirmation to this operation.
      if(job.key!==request.key||job.engine!==request.engine||job.k!==request.k)
        throw new ApiError('response_identity_mismatch',undefined,'unknown');
      return job;
    });
  }
  cancel(key:string,signal?:AbortSignal){return this.post('jobs/'+S.Id.parse(key)+'/cancel',{},S.Cancel,signal)}
  workOnce(maxCases=5,signal?:AbortSignal){return this.post('work',{max_cases:z.number().int().min(1).max(5).parse(maxCases)},S.Work,signal)}
}
