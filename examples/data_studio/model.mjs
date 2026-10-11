/** Original, offline analytics example. All numeric series and people-free notes are synthetic. */
export const MODES=Object.freeze(['trend','mix','cohort','funnel']);
export const SEGMENTS=Object.freeze(['All','Direct','Search','Social','Partner']);
export const WINDOWS=Object.freeze([4,8,12]);
export const COLORS=Object.freeze({Direct:'#637bd8',Search:'#16a394',Social:'#e1a655',Partner:'#a580c2'});
export const WEEKS=Object.freeze(Array.from({length:12},(_,i)=>`W${String(i+1).padStart(2,'0')}`));
export const CHANNELS=Object.freeze(SEGMENTS.slice(1));
export const DATA=Object.freeze(WEEKS.map((week,i)=>Object.freeze({
 week,Direct:180+i*13+(i%3)*17,Search:142+i*18+(i%4)*11,
 Social:91+i*9+(i%5)*19,Partner:72+i*7+(i%2)*23,
})));
export const MAX_NOTES=24;
function fail(code){throw new Error(code)}
export function cleanText(value,maximum=120){
 if(typeof value!=='string'||!Number.isInteger(maximum)||maximum<1)fail('invalid_text');
 const text=value.trim();if(!text||text.length>maximum||/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(text))fail('invalid_text');
 return text;
}
export function initialState(){return {mode:'trend',segment:'All',window:8,selected:'W12',theme:'light',density:'comfortable',notes:[],revision:0};}
export function normalizeState(state){
 if(!state||!MODES.includes(state.mode)||!SEGMENTS.includes(state.segment)||!WINDOWS.includes(state.window)||!WEEKS.includes(state.selected)||!['light','dark'].includes(state.theme)||!['comfortable','compact'].includes(state.density)||!Array.isArray(state.notes))fail('invalid_state');
 return state;
}
export function total(row,segment='All'){
 if(!SEGMENTS.includes(segment)||!row||typeof row!=='object')fail('invalid_segment');
 return segment==='All'?CHANNELS.reduce((sum,key)=>sum+row[key],0):row[segment];
}
export function visibleRows(state){normalizeState(state);return DATA.slice(-state.window);}
export function stats(state){
 const rows=visibleRows(state),values=rows.map(r=>total(r,state.segment));
 const sum=values.reduce((a,b)=>a+b,0),last=values.at(-1),prior=values.at(-2);
 return {sum,mean:Math.round(sum/values.length),latest:last,delta:last-prior,
  changePct:prior===0?0:Math.round(((last-prior)/prior)*1000)/10,
  high:Math.max(...values),low:Math.min(...values)};
}
export function channelShare(state){
 const rows=visibleRows(state),values=CHANNELS.map(channel=>({
  channel,value:rows.reduce((n,r)=>n+r[channel],0)
 }));const sum=values.reduce((n,x)=>n+x.value,0);
 return values.map(x=>({...x,percent:Math.round(x.value/sum*1000)/10}));
}
export function funnel(state){
 const sum=stats(state).sum;
 const p=[['Visits',100],['Engaged',61],['Qualified',27],['Completed',9]];
 return p.map(([name,percent])=>({name,count:Math.floor(sum*percent/100),percent}));
}
export function cohort(state){
 const rows=visibleRows(state);return rows.map((row,i)=>({
  week:row.week,values:Array.from({length:6},(_,j)=>Math.max(15,Math.min(100,Math.round(83-i*.5-j*9+((i+j*3)%4)*3))))
 }));
}
export function makeCSV(state){
 const rows=visibleRows(state),header=['Week',...CHANNELS,'Total'];
 const lines=[header.join(',')];
 for(const row of rows)lines.push([row.week,...CHANNELS.map(k=>row[k]),total(row)].join(','));
 return lines.join('\r\n')+'\r\n';
}
export function exportSnapshot(state){
 normalizeState(state);
 return JSON.stringify({schema:1,kind:'offline-synthetic-data-studio',state:{
  mode:state.mode,segment:state.segment,window:state.window,selected:state.selected,
  notes:state.notes.map(n=>({id:n.id,week:n.week,text:n.text}))
 },data:visibleRows(state)},null,2)+'\n';
}
export function safeCSVCell(value){
 const clean=String(value).replace(/[\r\n]+/g,' ').trim();
 const safe=/^[=+@\-\t\r]/.test(clean)?"'"+clean:clean;
 return /[",\r\n]/.test(safe)?'"'+safe.replace(/"/g,'""')+'"':safe;
}
export function notesCSV(state){normalizeState(state);return 'Week,Note\r\n'+state.notes.map(n=>`${safeCSVCell(n.week)},${safeCSVCell(n.text)}`).join('\r\n')+(state.notes.length?'\r\n':'');}
export function transition(state,event){
 normalizeState(state);if(!event||typeof event!=='object'||typeof event.type!=='string')fail('invalid_event');
 const s={...state,notes:state.notes.map(x=>({...x}))};
 switch(event.type){
  case 'MODE':if(!MODES.includes(event.value))fail('invalid_mode');s.mode=event.value;break;
  case 'SEGMENT':if(!SEGMENTS.includes(event.value))fail('invalid_segment');s.segment=event.value;break;
  case 'WINDOW':if(!WINDOWS.includes(event.value))fail('invalid_window');s.window=event.value;if(!visibleRows(s).some(x=>x.week===s.selected))s.selected=visibleRows(s)[0].week;break;
  case 'SELECT':if(!visibleRows(s).some(x=>x.week===event.value))fail('invalid_week');s.selected=event.value;break;
  case 'THEME':if(!['light','dark'].includes(event.value))fail('invalid_theme');s.theme=event.value;break;
  case 'DENSITY':if(!['comfortable','compact'].includes(event.value))fail('invalid_density');s.density=event.value;break;
  case 'NOTE_ADD':{
   const text=cleanText(event.value?.text);const week=event.value?.week;
   if(!WEEKS.includes(week)||!visibleRows(s).some(r=>r.week===week))fail('invalid_week');
   if(s.notes.length>=MAX_NOTES)fail('note_limit');
   const id=s.notes.length?Math.max(...s.notes.map(n=>n.id))+1:1;
   s.notes.push({id,week,text});break;}
  case 'NOTE_REMOVE':{
   if(!Number.isInteger(event.value)||!s.notes.some(n=>n.id===event.value))fail('unknown_note');
   s.notes=s.notes.filter(n=>n.id!==event.value);break;}
  case 'RESET':return initialState();
  default:fail('unknown_event');
 }
 s.revision=state.revision+1;return s;
}
