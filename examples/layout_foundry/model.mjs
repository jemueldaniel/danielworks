// Original public educational reference; synthetic-only data.
export const STATUSES = ['Planned','In progress','Review','Done'];
export const TEAMS = ['North','East','Central','West'];
export const PRIORITIES = ['Low','Medium','High'];
export const TOKENS = {hue:230,radius:14,density:'comfortable',theme:'light'};
export const FIXTURES = [
  {id:'T-101',title:'Document onboarding flow',team:'North',status:'Done',priority:'Medium',due:'2026-11-02',notes:''},
  {id:'T-102',title:'Audit keyboard interactions',team:'East',status:'In progress',priority:'High',due:'2026-11-04',notes:''},
  {id:'T-103',title:'Design empty states',team:'Central',status:'Review',priority:'Low',due:'2026-11-05',notes:''},
  {id:'T-104',title:'Build responsive navigation',team:'West',status:'In progress',priority:'High',due:'2026-11-07',notes:''}
];
FIXTURES.push(
 {id:'T-105',title:'Write interaction tests',team:'North',status:'Planned',priority:'Medium',due:'2026-11-08',notes:''},
 {id:'T-106',title:'Review localization',team:'East',status:'Planned',priority:'Low',due:'2026-11-10',notes:''},
 {id:'T-107',title:'Refine visual hierarchy',team:'Central',status:'Done',priority:'High',due:'2026-11-12',notes:''},
 {id:'T-108',title:'Publish token reference',team:'West',status:'Review',priority:'Medium',due:'2026-11-14',notes:''}
);
export const queryText = v => String(v ?? '').normalize('NFKC').trim().toLowerCase().slice(0,80);
export function safeDate(v) {
 if (typeof v !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(v)) return false;
 const date=new Date(v+'T00:00:00Z');
 return !Number.isNaN(date.getTime()) && date.toISOString().slice(0,10)===v;
}
export function safeRow(x){
 return x && typeof x==='object' && !Array.isArray(x) &&
 /^T-[0-9]{3,7}$/.test(x.id) && typeof x.title==='string' &&
 x.title.trim().length>=3 && x.title.length<=72 &&
 TEAMS.includes(x.team) && STATUSES.includes(x.status) &&
 PRIORITIES.includes(x.priority) && safeDate(x.due) &&
 typeof x.notes==='string' && x.notes.length<=240;
}
export function safeRows(rows) {
 const result=[],seen=new Set();
 if(!Array.isArray(rows))return result;
 for(const x of rows.slice(0,120)){
  if(!safeRow(x)||seen.has(x.id))continue;
  seen.add(x.id);
  result.push({id:x.id,title:x.title,team:x.team,status:x.status,priority:x.priority,due:x.due,notes:x.notes});
 }
 return result;
}
export function visibleRows(rows,{search='',team='All',status='All',sort='due',desc=false}={}) {
 const q=queryText(search),fields=['id','title','team','status','priority','due'];
 const key=fields.includes(sort)?sort:'due';
 const rank={Low:1,Medium:2,High:3};
 return safeRows(rows).filter(x=>(team==='All'||x.team===team)&&
   (status==='All'||x.status===status)&&
   (!q||fields.some(k=>queryText(x[k]).includes(q))))
   .sort((a,b)=>{
    const left=key==='priority'?rank[a.priority]:a[key],right=key==='priority'?rank[b.priority]:b[key];
    const n=typeof left==='number'?left-right:left.localeCompare(right,'en',{numeric:true});
    return (desc?-1:1)*(n||a.id.localeCompare(b.id,'en',{numeric:true}));
   });
}
export function totals(rows) {
 const items=safeRows(rows),count=s=>items.filter(x=>x.status===s).length;
 return {total:items.length,done:count('Done'),active:count('In progress'),
 review:count('Review'),urgent:items.filter(x=>x.priority==='High'&&x.status!=='Done').length,
 percent:items.length?Math.round(100*count('Done')/items.length):0};
}
export function validateDraft(raw,rows=[]){
 const x=raw&&typeof raw==='object'?raw:{};
 const title=String(x.title??'').trim(),notes=String(x.notes??'').trim();
 const errors={};
 if(title.length<3||title.length>72)errors.title='Title must be 3–72 characters.';
 if(!TEAMS.includes(x.team))errors.team='Choose a team.';
 if(!PRIORITIES.includes(x.priority))errors.priority='Choose a priority.';
 if(!safeDate(x.due))errors.due='Choose a valid date.';
 if(notes.length>240)errors.notes='Notes must be 240 characters or fewer.';
 const valid=safeRows(rows);
 if(valid.length>=120)errors.limit='Workspace is full.';
 if(Object.keys(errors).length)return {ok:false,errors};
 const id=Math.max(100,...valid.map(r=>Number(r.id.slice(2))))+1;
 if(id>9999999)return {ok:false,errors:{limit:'No identifiers available.'}};
 return {ok:true,errors:{},ticket:{id:'T-'+id,title,notes,team:x.team,
   status:'Planned',priority:x.priority,due:x.due}};
}
export function advance(rows,id){
 const items=safeRows(rows),at=items.findIndex(x=>x.id===id);
 if(at<0)return {ok:false,reason:'missing',rows:items};
 const position=STATUSES.indexOf(items[at].status);
 if(position===STATUSES.length-1)return {ok:false,reason:'done',rows:items};
 items[at]={...items[at],status:STATUSES[position+1]};
 return {ok:true,rows:items};
}
export function deleteTicket(rows,id){
 return safeRows(rows).filter(x=>x.id!==id);
}
export function safeTokens(raw={}){
 const x=raw&&typeof raw==='object'?raw:{};
 const bounded=(n,def,min,max)=>Number.isInteger(n)&&n>=min&&n<=max?n:def;
 return {hue:bounded(x.hue,230,0,360),radius:bounded(x.radius,14,2,28),
 density:['compact','comfortable'].includes(x.density)?x.density:'comfortable',
 theme:['light','dark'].includes(x.theme)?x.theme:'light'};
}
export function tokenJson(raw){
 return JSON.stringify({schema:1,label:'Public original UI tokens',tokens:safeTokens(raw)},null,2)+'\n';
}
export function tokenCss(raw){
 const t=safeTokens(raw);
 return ':root {\n  --brand-hue: '+t.hue+';\n  --corner: '+t.radius+
  'px;\n  --control-height: '+(t.density==='compact'?36:44)+'px;\n}\n';
}
function csvCell(value){
 let v=String(value??'').replace(/[\u0000-\u001f\u007f]/g,' ');
 if(/^\s*[=+@-]/.test(v))v="'"+v;
 return '"'+v.replace(/"/g,'""')+'"';
}
export function rowsCsv(rows){
 const fields=['id','title','team','status','priority','due','notes'];
 return [fields.join(','),...safeRows(rows).map(x=>fields.map(f=>csvCell(x[f])).join(','))].join('\r\n')+'\r\n';
}
export function saveWorkspace(rows,tokens){
 return JSON.stringify({schema:1,rows:safeRows(rows),tokens:safeTokens(tokens)});
}
export function restoreWorkspace(text){
 try{
  if(typeof text!=='string'||text.length>80000)throw Error('size');
  const raw=JSON.parse(text);
  if(raw.schema!==1||!Array.isArray(raw.rows)||raw.rows.length>120)throw Error('schema');
  return {ok:true,rows:safeRows(raw.rows),tokens:safeTokens(raw.tokens)};
 }catch{return {ok:false,rows:safeRows(FIXTURES),tokens:safeTokens(TOKENS)};}
}
