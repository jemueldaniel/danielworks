import {useEffect,useRef,useState,type FormEvent} from 'react';
import {ApiClient,ApiError} from '../src/api-client.js';
import {Submit,type SubmitInput,type JobView} from '../src/schema.js';

const STORAGE='workbench.pending.v1';
const api=new ApiClient(`${location.origin}/api/operator/`,'operator');
type Notice={text:string;error:boolean};
function restore():{request:SubmitInput|null;invalid:boolean}{
  try{
    const raw=localStorage.getItem(STORAGE);
    if(raw===null)return {request:null,invalid:false};
    if(raw.length>1024)return {request:null,invalid:true};
    const result=Submit.safeParse(JSON.parse(raw));
    return result.success?{request:result.data,invalid:false}:{request:null,invalid:true};
  }catch{return {request:null,invalid:true}}
}
function Details({job,close,opener}:{job:JobView;close:()=>void;opener:HTMLElement|null}){
  const dialog=useRef<HTMLDialogElement>(null);
  useEffect(()=>{dialog.current?.showModal();return()=>{opener?.focus()}},[opener]);
  return <dialog ref={dialog} aria-labelledby="details-heading" onCancel={event=>{event.preventDefault();close()}}>
    <header className="dialog-header"><h2 id="details-heading">Run details</h2><button onClick={close} autoFocus>Close details</button></header>
    <code className="break">{job.key}</code>
    <dl className="details"><dt>State</dt><dd>{job.state}</dd><dt>Engine</dt><dd>{job.engine}</dd>
      <dt>Attempts / generation</dt><dd>{job.attempts} / {job.generation}</dd><dt>Persisted cases</dt><dd>{job.checkpoint_count} / 5</dd></dl>
    {job.result?<section aria-label="Evaluation results">
      <p className="score">MRR@{job.k}: {job.result.mrr_at_k.toFixed(3)}</p>
      <p>Recall@{job.k}: {job.result.macro_recall_at_k.toFixed(3)}</p>
      <p>{job.result.resumed_cases} cases restored from earlier checkpoints.</p>
      <h3>Reproducible failures</h3>
      <ul>{job.result.failures.map(item=><li key={item.id}><strong>{item.id}</strong><br/>Expected: {item.relevant.join(', ')}<br/>Retrieved: {item.retrieved.join(', ')||'No match'}</li>)}</ul>
    </section>:<p>No completed result. Running jobs can be reclaimed after their lease expires; cancellation is explicit.</p>}
    <h3>Input identity</h3><code className="break">{job.input_digest}</code>
    <p className="muted">Five synthetic queries test plumbing and known failure cases, not real-world retrieval quality.</p>
  </dialog>;
}
export default function App(){
  const [initial]=useState(restore);
  const [pending,setPending]=useState<SubmitInput|null>(initial.request);
  const [invalidDraft,setInvalidDraft]=useState(initial.invalid);
  const [retryAllowed,setRetryAllowed]=useState(false);
  const [engine,setEngine]=useState<'fts5'|'lexical'>('fts5');const [k,setK]=useState(2);
  const [jobs,setJobs]=useState<JobView[]>([]);const [cursor,setCursor]=useState<string|null>(null);
  const [dataset,setDataset]=useState<Awaited<ReturnType<ApiClient['dataset']>>|null>(null);
  const [busy,setBusy]=useState(false);const [loading,setLoading]=useState(true);
  const [notice,setNotice]=useState<Notice>({text:initial.invalid?'Saved request is invalid. No request was sent.':initial.request?'Unresolved request restored. Inspect before retrying.':'Loading runs.',error:initial.invalid});
  const [selected,setSelected]=useState<JobView|null>(null);const opener=useRef<HTMLElement|null>(null);
  const [query,setQuery]=useState('password');const [results,setResults]=useState<Awaited<ReturnType<ApiClient['search']>>|null>(null);
  const [searching,setSearching]=useState(false);
  const announce=(text:string,error=false)=>setNotice({text,error});
  async function load(announceSuccess=false,append=false){
    setLoading(true);
    try{
      const page=await api.list({limit:20,...(append&&cursor?{cursor}:{})});
      setJobs(old=>append?[...old,...page.items.filter(item=>!old.some(existing=>existing.key===item.key))]:page.items);
      setCursor(page.next_cursor);if(announceSuccess)announce('Runs refreshed.');
    }catch{announce('Backend unavailable. Previous results are retained.',true)}
    finally{setLoading(false)}
  }
  useEffect(()=>{
    const controller=new AbortController();let live=true;
    void Promise.all([api.dataset(controller.signal),api.list({limit:20},controller.signal)]).then(([info,page])=>{
      if(!live)return;setDataset(info);setJobs(page.items);setCursor(page.next_cursor);
      if(!initial.request&&!initial.invalid)announce('Ready. All inputs are synthetic.');
    }).catch(()=>{if(live&&!initial.request&&!initial.invalid)announce('Backend unavailable. Previous results are retained.',true)})
      .finally(()=>{if(live)setLoading(false)});
    return()=>{live=false;controller.abort()};
  },[initial]);
  function clearSaved(){localStorage.removeItem(STORAGE);setPending(null);setRetryAllowed(false);setInvalidDraft(false)}
  async function send(request:SubmitInput){
    setBusy(true);setRetryAllowed(false);announce('Submitting evaluation.');
    try{
      await api.submit(request);clearSaved();await load();announce('Evaluation queued.');
    }catch(error){
      if(error instanceof ApiError&&error.outcome==='rejected')announce(`Request rejected (${error.code}). Inspect the saved request before changing it.`,true);
      else announce('Outcome unknown. Inspect the saved request before retrying.',true);
    }finally{setBusy(false)}
  }
  async function enqueue(event:FormEvent){
    event.preventDefault();if(busy||pending||invalidDraft)return;
    const request=Submit.parse({key:'run-'+crypto.randomUUID(),engine,k});
    // Persist the exact operation identity BEFORE any mutation is sent.
    try{localStorage.setItem(STORAGE,JSON.stringify(request));setPending(request)}
    catch{announce('Browser storage is unavailable. No request was sent.',true);return}
    await send(request);
  }
  async function reconcile(){
    if(!pending||busy)return;setBusy(true);announce('Inspecting saved request.');
    try{
      const found=await api.inspect(pending.key);
      if(found.engine!==pending.engine||found.k!==pending.k){announce('Saved key belongs to a different request. No retry was sent.',true);return}
      clearSaved();await load();announce('Saved request found. No duplicate was sent.');
    }catch(error){
      if(error instanceof ApiError&&error.status===404){setRetryAllowed(true);announce('Request not found. Retry uses the same key and payload.')}
      else announce('Inspection unavailable. The saved request is retained; no retry was sent.',true);
    }finally{setBusy(false)}
  }
  async function operate(action:()=>Promise<unknown>,success:string){
    if(busy)return;setBusy(true);announce('Operation in progress.');
    try{await action();await load();announce(success)}catch{announce('Operation outcome unavailable. Refresh and inspect before retrying.',true)}finally{setBusy(false)}
  }
  async function search(event:FormEvent){
    event.preventDefault();setSearching(true);try{setResults(await api.search(query,2));announce('Search completed.')}catch{announce('Search unavailable. Previous matches are retained.',true)}finally{setSearching(false)}
  }
  return <main>
    <header className="masthead"><p className="eyebrow">RUNNABLE ENGINEERING / LOCAL DEMONSTRATION</p><h1>Evaluation workbench</h1>
      <p>One durable workflow. A browser for people, MCP for tools, and the same persisted results.</p>
      <p className="scope">Loopback only · Synthetic data · Demo permission profiles, not authentication</p></header>
    <section className="notice" role={notice.error?'alert':'status'} aria-live="polite" aria-atomic="true"><span>{notice.text}</span></section>
    <div className="columns">
      <section className="panel" aria-labelledby="queue-heading"><h2 id="queue-heading">Queue an evaluation</h2>
        <p>Compare a lexical baseline with SQLite FTS5. Work is bounded to five queries per run.</p>
        <form onSubmit={event=>{void enqueue(event)}} aria-busy={busy}>
          <label htmlFor="engine">Retrieval engine</label><select id="engine" value={engine} onChange={event=>setEngine(event.target.value as 'fts5'|'lexical')} disabled={busy||Boolean(pending)||invalidDraft}>
            <option value="fts5">FTS5 · BM25 ranking</option><option value="lexical">Lexical baseline</option></select>
          <label htmlFor="cutoff">Result cutoff</label><select id="cutoff" value={k} onChange={event=>setK(Number(event.target.value))} disabled={busy||Boolean(pending)||invalidDraft}>
            {[1,2,3].map(value=><option key={value} value={value}>Top {value}</option>)}</select>
          <button className="primary" type="submit" disabled={busy||Boolean(pending)||invalidDraft}>Queue evaluation</button>
        </form>
        {pending&&<aside className="recovery" aria-label="Saved request"><h3>Resolve the saved request</h3><code className="break">{pending.key}</code>
          <p>{pending.engine} · top {pending.k}. No automatic mutation retry.</p>
          <button disabled={busy} onClick={()=>{void reconcile()}}>Inspect saved request</button>
          {retryAllowed&&<button disabled={busy} onClick={()=>{void send(pending)}}>Retry saved request</button>}
        </aside>}
        {invalidDraft&&<aside className="recovery"><p>The local draft cannot be trusted. Discard it explicitly before creating a new run.</p><button onClick={()=>{clearSaved();announce('Invalid saved request discarded.')}}>Discard invalid saved request</button></aside>}
        <div className="dataset"><h3>Versioned input</h3><p>{dataset?`${dataset.document_count} documents / ${dataset.query_count} held-out queries / ${dataset.version}`:'Input identity unavailable.'}</p>
          {dataset&&<code className="break">{dataset.sha256}</code>}<p className="muted">Known failure: “purchase reversal” does not match the refund document. Inspect failure cases rather than treating five queries as a benchmark.</p></div>
      </section>
      <section className="panel" aria-labelledby="runs-heading" aria-busy={loading}>
        <div className="section-header"><h2 id="runs-heading">Persistent runs</h2><button disabled={loading||busy} onClick={()=>{void load(true)}}>Refresh runs</button></div>
        <p>Queueing does not start an unbounded worker. Execute one bounded batch here or through MCP.</p>
        <button disabled={busy||loading} onClick={()=>{void operate(()=>api.workOnce(),'Bounded worker finished.')}}>Work next run</button>
        {loading&&<p role="status">Loading runs…</p>}
        {!loading&&jobs.length===0&&<p className="empty">No runs yet. Queue an evaluation to start.</p>}
        <ul className="runs">{jobs.map(job=><li key={job.key} data-job-key={job.key} data-state={job.state}>
          <div className="run-header"><strong>{job.engine} / top {job.k}</strong><span className={'state state-'+job.state}>{job.state}</span></div>
          <code className="break">{job.key}</code><p className="muted">{job.checkpoint_count}/5 checkpoints · attempt {job.attempts}</p>
          <div className="actions"><button onClick={event=>{opener.current=event.currentTarget;setSelected(job)}}>Inspect run</button>
            <button disabled={busy||!['pending','running'].includes(job.state)} onClick={()=>{void operate(()=>api.cancel(job.key),'Run cancellation recorded.')}}>Cancel run</button></div>
        </li>)}</ul>
        {cursor&&<button disabled={loading||busy} onClick={()=>{void load(false,true)}}>Load more runs</button>}
      </section>
    </div>
    <section className="panel preview" aria-labelledby="search-heading"><h2 id="search-heading">Inspect the real retrieval path</h2>
      <form className="search-form" onSubmit={event=>{void search(event)}}><label htmlFor="query">Search query</label><input id="query" value={query} onChange={event=>setQuery(event.target.value)} required maxLength={500}/><button disabled={searching}>{searching?'Searching…':'Search documents'}</button></form>
      {results&&<ul>{results.items.map(item=><li key={item.id}><strong>{item.id}</strong> — {item.text}</li>)}{results.items.length===0&&<li>No match. This is a reproducible retrieval failure, not a transport error.</li>}</ul>}
    </section>
    <footer><p>AI-assisted educational implementation. Real HTTP, MCP, SQLite and browser behavior; no live accounts, model calls, funds or deployment.</p></footer>
    {selected&&<Details job={selected} close={()=>setSelected(null)} opener={opener.current}/>}
  </main>;
}
