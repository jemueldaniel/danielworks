import {MODES,SEGMENTS,CHANNELS,WEEKS,COLORS,DATA,initialState,transition,visibleRows,stats,channelShare,funnel,cohort,makeCSV,notesCSV,exportSnapshot,total} from './model.mjs';

const $=id=>document.getElementById(id);
let state=initialState(),focusReturn=null;
try{const saved=localStorage.getItem('signal-study:theme');if(['light','dark'].includes(saved))state=transition(state,{type:'THEME',value:saved});}catch{/* browser preferences optional */}
const ns='http://www.w3.org/2000/svg';
const number=n=>new Intl.NumberFormat('en-US').format(n);
function node(type,attrs={},text=null){
 const el=document.createElementNS(ns,type);
 for(const [name,value] of Object.entries(attrs))el.setAttribute(name,String(value));
 if(text!==null)el.textContent=String(text);
 return el;
}
function add(svg,type,attrs={},text=null){const el=node(type,attrs,text);svg.append(el);return el;}
function text(x,y,content,extra={}){return node('text',{x,y,fill:'var(--muted)', 'font-size':11,'font-family':'system-ui,Arial,sans-serif',...extra},content);}
function seriesColors(name){return COLORS[name]||'#146f69';}
function axes(svg,rows,max){
 const base=274,left=53,right=750,width=right-left;
 for(let i=0;i<=4;i++){
  const y=base-(i*52);add(svg,'line',{x1:left,y1:y,x2:right,y2:y,stroke:'var(--border)','stroke-width':1});
  svg.append(text(42,y+4,number(Math.round(max*i/4)),{'text-anchor':'end'}));
 }
 for(let i=0;i<rows.length;i++)svg.append(text(left+i*(width/Math.max(1,rows.length-1)),303,rows[i].week,{'text-anchor':'middle'}));
}
function renderTrend(svg){
 const rows=visibleRows(state),channels=state.segment==='All'?CHANNELS:[state.segment],high=Math.max(1,...rows.flatMap(row=>channels.map(ch=>row[ch])))*1.2;
 axes(svg,rows,high);
 const left=53,step=697/Math.max(1,rows.length-1),bottom=274,height=208;
 for(const name of channels){
  const pts=rows.map((row,i)=>[left+i*step,bottom-row[name]/high*height]);
  const path=pts.map((p,i)=>`${i===0?'M':'L'} ${p[0].toFixed(2)} ${p[1].toFixed(2)}`).join(' ');
  add(svg,'path',{d:path,fill:'none',stroke:seriesColors(name),'stroke-width':3,'stroke-linecap':'round','stroke-linejoin':'round'});
  pts.forEach(([x,y],i)=>{const active=rows[i].week===state.selected;const circle=add(svg,'circle',{cx:x,cy:y,r:active?6:3.2,fill:seriesColors(name),stroke:active?'var(--paper)':seriesColors(name),'stroke-width':active?3:0,role:'presentation'});circle.dataset.week=rows[i].week;});
 }
 const at=rows.findIndex(r=>r.week===state.selected);
 if(at>=0){const x=left+at*step;add(svg,'line',{x1:x,y1:58,x2:x,y2:275,stroke:'var(--muted)','stroke-dasharray':'3 5',opacity:'.55'});}
}
function renderMix(svg){
 const rows=visibleRows(state),hi=Math.max(...rows.map(r=>total(r)))*1.13;
 axes(svg,rows,hi);
 const bandwidth=Math.min(42,640/rows.length*.65),step=697/Math.max(1,rows.length-1);
 rows.forEach((row,i)=>{
  const x=53+i*step-bandwidth/2;let bottom=274;
  for(const name of CHANNELS){
   const height=row[name]/hi*208;
   const bar=add(svg,'rect',{x,y:bottom-height,width:bandwidth,height,rx:1,fill:seriesColors(name),opacity:state.segment==='All'||state.segment===name?1:.17});
   bar.dataset.week=row.week;bottom-=height;
  }
  if(row.week===state.selected)add(svg,'rect',{x:x-3,y:50,width:bandwidth+6,height:231,fill:'none',stroke:'var(--accent)','stroke-width':1.5,rx:4});
 });
}
function renderCohort(svg){
 const entries=cohort(state),count=entries.length,left=105,top=53,cellW=Math.min(85,580/count),cellH=30;
 for(let j=0;j<6;j++)svg.append(text(left+j*91+cellW/2,34,`M+${j}`,{'text-anchor':'middle'}));
 entries.forEach((item,i)=>{
  const rowY=top+i*34;svg.append(text(79,rowY+20,item.week,{'text-anchor':'end'}));
  item.values.forEach((v,j)=>{
   add(svg,'rect',{x:left+j*91,y:rowY,width:cellW,height:cellH,rx:4,fill:'#159d8b',opacity:(.13+v/100*.85).toFixed(2)});
   svg.append(text(left+j*91+cellW/2,rowY+20,`${v}%`,{'text-anchor':'middle',fill:v>62?'#fff':'var(--ink)','font-weight':700}));
  });
  if(item.week===state.selected)add(svg,'rect',{x:left-5,y:rowY-2,width:6*91,height:34,fill:'none',stroke:'var(--accent)','stroke-width':1.4,rx:4});
 });
 svg.append(text(105,327,'Illustrative retention only — not collected from users.'));
}
function renderFunnel(svg){
 const steps=funnel(state),left=70,maxwidth=590;
 steps.forEach((stage,i)=>{
  const width=maxwidth*(stage.percent/100),x=left+(maxwidth-width)/2,y=47+i*70;
  add(svg,'rect',{x,y,width,height:53,rx:6,fill:['#146f69','#329b89','#72c3b4','#b9ded5'][i]});
  svg.append(text(x+14,y+20,stage.name,{fill:i<3?'#fff':'#204540','font-size':13,'font-weight':700}));
  svg.append(text(x+14,y+38,`${number(stage.count)} events`,{fill:i<3?'#fff':'#204540','font-size':11}));
  svg.append(text(x+width+14,y+31,`${stage.percent}%`,{fill:'var(--ink)','font-weight':700}));
 });
}
function renderGraph(){
 const svg=$('viz');svg.replaceChildren();
 const title=add(svg,'title',{id:'svg-title'},'Visual analytics '+state.mode);
 const desc=add(svg,'desc',{id:'svg-desc'},`Synthetic dataset. ${state.window} weeks; segment ${state.segment}. Detailed values are available in the table.`);
 if(state.mode==='trend')renderTrend(svg);
 else if(state.mode==='mix')renderMix(svg);
 else if(state.mode==='cohort')renderCohort(svg);
 else renderFunnel(svg);
 const legend=$('legend');legend.replaceChildren();
 if(['trend','mix'].includes(state.mode)){
  for(const name of state.segment==='All'||state.mode==='mix'?CHANNELS:[state.segment]){
   const item=document.createElement('span');item.className='legend-item';
   const dot=document.createElement('span');dot.className='swatch';dot.style.background=seriesColors(name);
   item.append(dot,document.createTextNode(name));legend.append(item);
  }
 }
 const headings={trend:'Weekly trends',mix:'Channels by week',cohort:'Illustrative retention matrix',funnel:'Illustrative conversion funnel'};
 $('chart-description').textContent=headings[state.mode]+' · Synthetic data; no tracking or live source.';
 const s=stats(state);
 $('chartSummary').textContent=`${headings[state.mode]}. ${state.window} weeks, ${state.segment} segment, ${number(s.sum)} period events. Focus ${state.selected}.`;
}
function renderShares(){const box=$('shareBars');box.replaceChildren();for(const item of channelShare(state)){
 const wrap=document.createElement('div'),label=document.createElement('div'),name=document.createElement('span'),value=document.createElement('strong');
 label.className='share-label';name.textContent=item.channel;value.textContent=item.percent.toFixed(1)+'%';label.append(name,value);
 const rail=document.createElement('div');rail.className='share-rail';const bar=document.createElement('div');bar.className='share-bar';bar.style.width=item.percent+'%';bar.style.background=seriesColors(item.channel);rail.append(bar);wrap.append(label,rail);box.append(wrap);
}}
function renderNotes(){
 $('noteCount').textContent=String(state.notes.length);$('notesEmpty').hidden=state.notes.length>0;
 const list=$('notesList');list.replaceChildren();for(const note of state.notes){
  const li=document.createElement('li'),info=document.createElement('div'),week=document.createElement('strong'),body=document.createElement('p');week.textContent=note.week;body.textContent=note.text;info.append(week,body);
  const del=document.createElement('button');del.className='note-remove';del.type='button';del.textContent='×';del.setAttribute('aria-label',`Remove annotation ${note.id}`);del.addEventListener('click',()=>dispatch('NOTE_REMOVE',note.id));li.append(info,del);list.append(li);
 }
 $('notesExportBtn').disabled=state.notes.length===0;
}
function renderTable(){const body=$('rows');body.replaceChildren();for(const row of [...visibleRows(state)].reverse()){
 const tr=document.createElement('tr');tr.tabIndex=0;if(row.week===state.selected)tr.className='selected';
 for(const value of [row.week,...CHANNELS.map(k=>row[k]),total(row)]){const td=document.createElement('td');td.textContent=typeof value==='number'?number(value):value;tr.append(td)}
 const select=()=>dispatch('SELECT',row.week);tr.addEventListener('click',select);tr.addEventListener('keydown',event=>{if(['Enter',' '].includes(event.key)){event.preventDefault();select()}});body.append(tr);
}}
function options(select,rows,selected){select.replaceChildren();for(const value of rows){const el=document.createElement('option');el.value=value;el.textContent=value;select.append(el)}select.value=selected;}
function render(){
 document.body.dataset.theme=state.theme;document.body.dataset.density=state.density;
 $('segmentSelect').value=state.segment;$('windowSelect').value=String(state.window);
 options($('weekSelect'),visibleRows(state).map(x=>x.week),state.selected);
 const s=stats(state);$('metricTotal').textContent=number(s.sum);$('metricAverage').textContent=number(s.mean);$('metricLatest').textContent=number(s.latest);
 $('metricDelta').textContent=(s.delta>=0?'+':'')+s.changePct.toFixed(1)+'%';$('metricDeltaText').textContent=`${s.delta>=0?'+':''}${number(s.delta)} events from previous week`;
 for(const mode of MODES){const tab=$('tab-'+mode);tab.setAttribute('aria-selected',String(state.mode===mode));tab.tabIndex=state.mode===mode?0:-1;}
 renderGraph();renderShares();renderTable();renderNotes();
}
function announce(msg){$('toast').textContent=msg;$('toast').hidden=false;}
function dispatch(type,value){try{state=transition(state,{type,value});render();return true;}catch(error){announce('Action rejected: '+error.message);return false}}
function download(name,content,mime){const data=new Blob([content],{type:mime});const url=URL.createObjectURL(data);const a=document.createElement('a');a.href=url;a.download=name;a.hidden=true;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),4000);}
function showDialog(id,initial){focusReturn=document.activeElement;if(id==='noteDialog'){
  options($('noteWeek'),visibleRows(state).map(x=>x.week),state.selected);$('noteText').value='';$('noteError').hidden=true;
 }$(id).showModal();(initial?$(initial):$(id).querySelector('button'))?.focus();}
function closeDialog(id){$(id).close();focusReturn?.focus();focusReturn=null;}
for(const button of document.querySelectorAll('[data-mode]'))button.addEventListener('click',()=>dispatch('MODE',button.dataset.mode));
$('segmentSelect').addEventListener('change',e=>dispatch('SEGMENT',e.target.value));
$('windowSelect').addEventListener('change',e=>dispatch('WINDOW',Number(e.target.value)));
$('weekSelect').addEventListener('change',e=>dispatch('SELECT',e.target.value));
$('themeBtn').addEventListener('click',()=>{const next=state.theme==='dark'?'light':'dark';if(dispatch('THEME',next)){try{localStorage.setItem('signal-study:theme',next)}catch{/* optional */}}});
$('densityBtn').addEventListener('click',()=>dispatch('DENSITY',state.density==='compact'?'comfortable':'compact'));
$('resetBtn').addEventListener('click',()=>{dispatch('RESET');announce('Analysis reset to example defaults');});
$('downloadBtn').addEventListener('click',()=>download('signal-study-synthetic-data.csv',makeCSV(state),'text/csv;charset=utf-8'));
$('svgBtn').addEventListener('click',()=>{
 const svg=$('viz').cloneNode(true);svg.setAttribute('xmlns',ns);svg.setAttribute('width','780');svg.setAttribute('height','345');
 // SVG export must not rely on page-local CSS variables.
 const ink=state.theme==='dark'?'#e9f0ef':'#1f303a',muted=state.theme==='dark'?'#9faeaf':'#78848c';
 for(const element of svg.querySelectorAll('*'))for(const attr of ['fill','stroke']){
  const raw=element.getAttribute(attr);if(raw==='var(--muted)')element.setAttribute(attr,muted);
  if(raw==='var(--ink)')element.setAttribute(attr,ink);
  if(raw==='var(--border)')element.setAttribute(attr,state.theme==='dark'?'#334143':'#e4e9e9');
  if(raw==='var(--accent)')element.setAttribute(attr,state.theme==='dark'?'#79d4c2':'#146f69');
  if(raw==='var(--paper)')element.setAttribute(attr,state.theme==='dark'?'#243033':'#ffffff');
 }
 download('signal-study-'+state.mode+'.svg',new XMLSerializer().serializeToString(svg),'image/svg+xml;charset=utf-8');
});
$('notesExportBtn').addEventListener('click',()=>download('signal-study-notes.csv',notesCSV(state),'text/csv;charset=utf-8'));
$('openNoteBtn').addEventListener('click',()=>showDialog('noteDialog','noteText'));
$('closeNoteBtn').addEventListener('click',()=>closeDialog('noteDialog'));
$('cancelNoteBtn').addEventListener('click',()=>closeDialog('noteDialog'));
$('noteForm').addEventListener('submit',event=>{event.preventDefault();if(dispatch('NOTE_ADD',{week:$('noteWeek').value,text:$('noteText').value})){closeDialog('noteDialog');announce('Annotation saved locally');}else{$('noteError').textContent='Please enter a valid note up to 120 characters.';$('noteError').hidden=false;}});
$('guideBtn').addEventListener('click',()=>showDialog('guideDialog','guideDoneBtn'));
$('closeGuideBtn').addEventListener('click',()=>closeDialog('guideDialog'));
$('guideDoneBtn').addEventListener('click',()=>closeDialog('guideDialog'));
for(const dialog of document.querySelectorAll('dialog'))dialog.addEventListener('close',()=>{if(focusReturn){focusReturn.focus();focusReturn=null}});
document.addEventListener('keydown',event=>{
 const element=document.activeElement;
 if(element?.matches('input,textarea,select,[contenteditable="true"]')||document.querySelector('dialog[open]'))return;
 if(['1','2','3','4'].includes(event.key)&&!event.ctrlKey&&!event.metaKey&&!event.altKey){event.preventDefault();const mode=MODES[Number(event.key)-1];dispatch('MODE',mode);$('tab-'+mode).focus()}
 if(event.key.toLowerCase()==='n'&&!event.ctrlKey&&!event.metaKey&&!event.altKey){event.preventDefault();showDialog('noteDialog','noteText')}
});
render();
