/** Original public, dependency-free interface state machine and safe CSV export. */
export const STATUSES = Object.freeze(['active','review','complete']);
export const CATEGORIES = Object.freeze(['Interface','Accessibility','Systems','Research']);
export const PAGE_SIZE = 5;
const INITIAL = [
 ['item-001','Design token foundations','Alex Morgan','Interface','complete',8,'2026-10-08'],
 ['item-002','Keyboard navigation audit','Taylor Chen','Accessibility','active',5,'2026-10-09'],
 ['item-003','Responsive data patterns','Jordan Lee','Interface','review',6,'2026-10-07'],
 ['item-004','Visual regression checks','Sam Rivera','Systems','active',7,'2026-10-10'],
 ['item-005','Color contrast study','Casey Park','Accessibility','complete',4,'2026-10-04'],
 ['item-006','Documentation architecture','Morgan Ellis','Research','review',5,'2026-10-05'],
 ['item-007','Loading and empty states','Robin Patel','Interface','active',3,'2026-10-11'],
 ['item-008','Focus and dialog behavior','Avery Brooks','Accessibility','complete',4,'2026-10-06'],
 ['item-009','Search query quality','Jamie Kim','Research','active',6,'2026-10-03'],
 ['item-010','Reusable component contracts','Drew Parker','Systems','review',9,'2026-10-02'],
 ['item-011','Motion sensitivity review','Emery Stone','Accessibility','complete',5,'2026-10-01'],
 ['item-012','Data table state machine','Charlie Grey','Systems','active',7,'2026-09-30']
];
export const FIXTURES = Object.freeze(INITIAL.map(([id,title,owner,category,status,effort,updated])=>
 Object.freeze({id,title,owner,category,status,effort,updated})));
const SLUG=/^item-\d{3,6}$/;
const DATE=/^\d{4}-\d{2}-\d{2}$/;
const SORTS=['updated','title','effort'];
export const SECTIONS=Object.freeze(['overview','library','activity','settings']);
function printable(value,max){
 return typeof value==='string'&&value.trim().length>0&&value.trim().length<=max&&!/[\u0000-\u001f\u007f]/.test(value);
}
function valid(r){
 return r&&typeof r==='object'&&!Array.isArray(r)&&SLUG.test(r.id)&&
 printable(r.title,80)&&printable(r.owner,50)&&CATEGORIES.includes(r.category)&&
 STATUSES.includes(r.status)&&Number.isSafeInteger(r.effort)&&r.effort>=1&&r.effort<=40&&
 DATE.test(r.updated)&&!Number.isNaN(Date.parse(r.updated+'T12:00:00Z'));
}
export function readPreferences(raw){
 if(!raw||typeof raw!=='object'||Array.isArray(raw))raw={};
 return {theme:raw.theme==='dark'?'dark':'light',
         density:raw.density==='compact'?'compact':'comfortable'};
}
export function createState(records=FIXTURES,pref={}){
 if(!Array.isArray(records)||records.length>100||records.some(r=>!valid(r))||
    new Set(records.map(r=>r.id)).size!==records.length)throw new RangeError('invalid_records');
 return {records:records.map(r=>({...r})),query:'',status:'all',sort:'updated',page:1,
         section:'overview',...readPreferences(pref)};
}
export function savedPreferences(state){return {theme:state.theme,density:state.density};}
export function nextId(records){
 const ids=new Set(records.map(r=>r.id));
 for(let i=1;i<=999999;i++){const id='item-'+String(i).padStart(3,'0');if(!ids.has(id))return id;}
 throw new RangeError('id_capacity');
}
export function addRecord(state,input,date='2026-10-11'){
 if(!input||typeof input!=='object'||Array.isArray(input))throw new RangeError('invalid_record');
 const record={id:nextId(state.records),title:input.title?.trim(),owner:input.owner?.trim(),
   category:input.category,status:input.status,effort:Number(input.effort),updated:date};
 if(!valid(record)||state.records.length>=100)throw new RangeError('invalid_record');
 return {...state,records:[...state.records,record],query:'',status:'all',
         sort:'updated',page:1,section:'library'};
}
export function reduce(state,action){
 if(!action||typeof action!=='object')throw new RangeError('invalid_action');
 switch(action.type){
  case 'QUERY':return {...state,query:String(action.value??'').slice(0,160),page:1};
  case 'STATUS':if(!['all',...STATUSES].includes(action.value))throw new RangeError('invalid_status');
    return {...state,status:action.value,page:1};
  case 'SORT':if(!SORTS.includes(action.value))throw new RangeError('invalid_sort');
    return {...state,sort:action.value,page:1};
  case 'PAGE':if(!Number.isSafeInteger(action.value)||action.value<1)throw new RangeError('invalid_page');
    return {...state,page:action.value};
  case 'SECTION':if(!SECTIONS.includes(action.value))throw new RangeError('invalid_section');
    return {...state,section:action.value};
  case 'THEME':if(!['light','dark'].includes(action.value))throw new RangeError('invalid_theme');
    return {...state,theme:action.value};
  case 'DENSITY':if(!['comfortable','compact'].includes(action.value))throw new RangeError('invalid_density');
    return {...state,density:action.value};
  default:throw new RangeError('unknown_action');
 }
}
export function derive(state){
 const needle=state.query.toLocaleLowerCase('en-US').trim();
 let matches=state.records.filter(r=>(state.status==='all'||r.status===state.status)&&
   (!needle||[r.title,r.owner,r.category,r.id].some(t=>
     t.toLocaleLowerCase('en-US').includes(needle))));
 const compare={updated:(a,b)=>b.updated.localeCompare(a.updated),
   title:(a,b)=>a.title.localeCompare(b.title),
   effort:(a,b)=>b.effort-a.effort};
 matches=[...matches].sort((a,b)=>compare[state.sort](a,b)||a.id.localeCompare(b.id));
 const totalPages=Math.max(1,Math.ceil(matches.length/PAGE_SIZE));
 const page=Math.min(state.page,totalPages);
 const counters={total:state.records.length,active:0,review:0,complete:0};
 for(const r of state.records)counters[r.status]++;
 return {records:matches.slice((page-1)*PAGE_SIZE,page*PAGE_SIZE),
   filteredCount:matches.length,page,totalPages,counters,
   effort:state.records.reduce((s,r)=>s+r.effort,0),recordsTotal:state.records.length,
   showingFrom:matches.length?(page-1)*PAGE_SIZE+1:0,
   showingTo:Math.min(page*PAGE_SIZE,matches.length)};
}
export function csvCell(value){
 let s=String(value);
 if(/^\s*[=+\-@]/.test(s))s="'"+s;
 return '"'+s.replaceAll('"','""')+'"';
}
export function exportCsv(state){
 const header=['ID','Title','Owner','Category','Status','Effort','Updated'];
 const rows=[header,...state.records.map(({id,title,owner,category,status,effort,updated})=>
   [id,title,owner,category,status,effort,updated])];
 return rows.map(row=>row.map(csvCell).join(',')).join('\r\n')+'\r\n';
}
