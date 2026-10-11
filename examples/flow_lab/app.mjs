import {createState,reduce,exportGraph,validateGraph,graphFrom,stats,nodeConnections,position,positionY,LIMITS,NODE_TYPES} from './model.mjs';

const $=id=>document.getElementById(id);
const STORAGE='flow-laboratory-public-v1';
let state=createState();
let toastTimer=0;
const restore=()=>{
  try {
    const value=localStorage.getItem(STORAGE);
    if(!value)return;
    const data=JSON.parse(value);
    const graph=validateGraph(data.graph);
    state={...state,...graph,theme:['light','dark'].includes(data.theme)?data.theme:'light',
      compact:typeof data.compact==='boolean'?data.compact:false,
      grid:typeof data.grid==='boolean'?data.grid:true};
  }catch{try{localStorage.removeItem(STORAGE)}catch{/* private context */}}
};
restore();
function persist(){try{localStorage.setItem(STORAGE,JSON.stringify({graph:graphFrom(state),theme:state.theme,grid:state.grid,compact:state.compact}))}catch{/* storage optional */}}
function announce(message,bad=false){
  $('toast').textContent=message;
  $('toast').style.background=bad?'#85372f':'#173a33';
  $('toast').classList.add('show');
  window.clearTimeout(toastTimer);
  toastTimer=window.setTimeout(()=>$('toast').classList.remove('show'),3000);
}
function update(type,value,{silent=false}={}){
  try{
    const before=state;
    state=reduce(state,{type,value});
    if(state!==before){persist();render()}
    if(!silent&&state!==before && ['ADD_NODE','UPDATE_NODE','CONNECT','DISCONNECT','DELETE_NODE','UNDO','REDO','IMPORT','RESET'].includes(type))announce(state.notice||'Graph updated');
    return true;
  }catch(err){announce(err instanceof Error?err.message:'Invalid edit',true);return false}
}
const el=(tag,classes,textContent)=>{
  const e=document.createElement(tag);
  if(classes)e.className=classes;
  if(textContent!==undefined)e.textContent=textContent;
  return e;
};
function render(){
  const metrics=stats(state);
  $('metricNodes').textContent=String(metrics.nodes);
  $('metricEdges').textContent=String(metrics.connections);
  $('metricStages').textContent=String(metrics.stages);
  $('liveCount').textContent=`${metrics.nodes} components`;
  $('undoBtn').disabled=state.past.length===0;
  $('redoBtn').disabled=state.future.length===0;
  $('zoomLabel').textContent=`${Math.round(state.zoom*100)}%`;
  $('gridBtn').setAttribute('aria-pressed',String(state.grid));
  $('canvasStage').classList.toggle('grid-on',state.grid);
  $('canvasStage').style.width=`${1300*state.zoom}px`;
  $('canvasStage').style.height=`${760*state.zoom}px`;
  $('canvasTransform').style.transform=`scale(${state.zoom})`;
  document.body.dataset.theme=state.theme;
  document.body.classList.toggle('compact',state.compact);
  $('themeToggle').setAttribute('aria-label',state.theme==='light'?'Switch to dark theme':'Switch to light theme');
  renderEdges();renderNodes();renderInspector();
}
function renderEdges(overrides=new Map()){
  const svg=$('edges');svg.replaceChildren();
  const ns='http://www.w3.org/2000/svg';
  const defs=document.createElementNS(ns,'defs');
  const marker=document.createElementNS(ns,'marker');
  marker.setAttribute('id','flowArrow');marker.setAttribute('viewBox','0 0 10 10');marker.setAttribute('refX','8');marker.setAttribute('refY','5');
  marker.setAttribute('markerWidth','6');marker.setAttribute('markerHeight','6');marker.setAttribute('orient','auto-start-reverse');
  const arrow=document.createElementNS(ns,'path');arrow.setAttribute('d','M 0 0 L 10 5 L 0 10 z');arrow.setAttribute('fill','#7b9a9f');marker.append(arrow);defs.append(marker);svg.append(defs);
  const nodes=new Map(state.nodes.map(node=>[node.id,{...node,...(overrides.get(node.id)||{})}]));
  for(const edge of state.edges){
    const source=nodes.get(edge.from), target=nodes.get(edge.to);
    const x1=source.x+220,y1=source.y+63,x2=target.x,y2=target.y+63;
    const bend=Math.max(60,Math.abs(x2-x1)/2);
    const path=document.createElementNS(ns,'path');
    path.setAttribute('d',`M ${x1} ${y1} C ${x1+bend} ${y1}, ${x2-bend} ${y2}, ${x2} ${y2}`);
    path.setAttribute('fill','none');path.setAttribute('stroke','#7b9a9f');path.setAttribute('stroke-width',edge.from===state.selected||edge.to===state.selected?'3.1':'2');
    path.setAttribute('stroke-dasharray',edge.from===state.selected?'0':'7 5');path.setAttribute('marker-end','url(#flowArrow)');
    svg.append(path);
  }
}
function renderNodes(){
  const holder=$('nodes');
  const active=document.activeElement?.dataset?.id;
  holder.replaceChildren();
  for(const node of state.nodes){
    const b=el('button','node-card');b.type='button';b.dataset.id=node.id;b.dataset.type=node.type;
    b.setAttribute('aria-label',`${node.title}, ${node.type} component, position ${node.x} by ${node.y}. Use arrow keys to move.`);
    b.setAttribute('aria-pressed',String(state.selected===node.id));
    b.style.left=`${node.x}px`;b.style.top=`${node.y}px`;
    const head=el('span','node-head');head.append(el('span','node-type-dot'),document.createTextNode(node.type));
    b.append(head,el('strong','node-title',node.title),el('span','node-detail',node.detail||'No description'));
    holder.append(b);
  }
  if(active){const focused=[...holder.children].find(e=>e.dataset.id===active);focused?.focus({preventScroll:true})}
}
const field=(root,textLabel,value,max,id,multi=false)=>{
  const label=el('label','',textLabel);label.htmlFor=id;
  const input=el(multi?'textarea':'input');input.id=id;input.value=value;
  input.maxLength=max;if(multi)input.rows=3;else input.required=true;
  root.append(label,input);return input;
};
function renderInspector(){
  const host=$('inspectorContent');host.replaceChildren();
  const selected=state.nodes.find(n=>n.id===state.selected);
  if(!selected){const div=el('div','inspector-body inspector-empty');div.append(el('p','', 'Nothing selected. Choose a component on the canvas, or create one to inspect its settings.'));const b=el('button','button primary','＋ Add a component');b.addEventListener('click',()=>openDialog('addDialog'));div.append(b);host.append(div);return}
  const div=el('div','inspector-body');
  div.append(el('div',`detail-type ${selected.type}`,selected.type),el('h3','',selected.title),el('p','detail-description',selected.detail||'No description has been added.'));
  const form=el('form');form.id='inspectorForm';
  const title=field(form,'NAME',selected.title,LIMITS.title,'inspectTitle');
  const detail=field(form,'DESCRIPTION',selected.detail,LIMITS.detail,'inspectDetail',true);
  const save=el('button','button primary','Save properties');save.type='submit';form.append(save);
  form.addEventListener('submit',e=>{e.preventDefault();update('UPDATE_NODE',{id:selected.id,title:title.value,detail:detail.value})});
  div.append(form);
  const incoming=nodeConnections(state,selected.id);
  const meta=el('div','detail-meta');meta.append(el('span','', 'Connections'),el('strong','',`${incoming.incoming.length} in / ${incoming.outgoing.length} out`));div.append(meta);
  const xy=el('div','detail-meta');xy.append(el('span','', 'Canvas position'),el('strong','',`${selected.x}, ${selected.y}`));div.append(xy);
  const nudgeLabel=el('label','', 'NUDGE POSITION');div.append(nudgeLabel);
  const nudges=el('div','nudge-row');
  for(const [key,dx,dy] of [['←',-20,0],['↑',0,-20],['↓',0,20],['→',20,0]]){
    const b=el('button','',key);b.type='button';b.setAttribute('aria-label',`Move ${key==='←'?'left':key==='→'?'right':key==='↑'?'up':'down'}`);
    b.addEventListener('click',()=>update('MOVE_NODE',{id:selected.id,x:Math.min(LIMITS.x,Math.max(0,selected.x+dx)),y:Math.min(LIMITS.y,Math.max(0,selected.y+dy))},{silent:true}));nudges.append(b);
  }
  div.append(nudges);
  const options=state.nodes.filter(n=>n.id!==selected.id);
  const label=el('label','','CONNECT TO');label.htmlFor='targetNode';
  const select=el('select');select.id='targetNode';for(const n of options){const option=el('option','',n.title);option.value=n.id;select.append(option)}
  const connect=el('button','button quiet','Create connection');connect.type='button';connect.disabled=!options.length;
  connect.addEventListener('click',()=>update('CONNECT',{from:selected.id,to:select.value}));
  div.append(label,select,connect);
  if(incoming.outgoing.length){const dislabel=el('label','','REMOVE AN OUTGOING CONNECTION');dislabel.htmlFor='edgeSelect';const es=el('select');es.id='edgeSelect';
    for(const edge of incoming.outgoing){const option=el('option','',state.nodes.find(n=>n.id===edge.to)?.title??edge.to);option.value=edge.to;es.append(option)}
    const disconnect=el('button','button quiet','Disconnect selected');disconnect.type='button';disconnect.addEventListener('click',()=>update('DISCONNECT',{from:selected.id,to:es.value}));
    div.append(dislabel,es,disconnect)
  }
  const remove=el('button','button quiet danger','Delete component');remove.type='button';remove.addEventListener('click',()=>update('DELETE_NODE',selected.id));div.append(remove);
  host.append(div);
}
function openDialog(id){
  const dialog=$(id);if(dialog.open)return;
  dialog._opener=document.activeElement;
  dialog.showModal();
  if(id==='addDialog'){$('addForm').reset();$('nodeTitle').focus()}
  else if(id==='commandDialog'){$('commandQuery').value='';renderCommands();$('commandQuery').focus()}
}
for(const dialog of document.querySelectorAll('dialog')){
  dialog.addEventListener('close',()=>{if(dialog._opener?.isConnected)dialog._opener.focus();dialog._opener=null});
  dialog.querySelectorAll('.dialog-close').forEach(b=>b.addEventListener('click',()=>dialog.close()));
}
$('addForm').addEventListener('submit',e=>{
  e.preventDefault();const value={type:$('nodeType').value,title:$('nodeTitle').value,detail:$('nodeDetail').value};
  if(update('ADD_NODE',value))$('addDialog').close();
});
const commands=[
  ['Add a new component',()=>openDialog('addDialog')],
  ['Import diagram from JSON',()=>$('importFile').click()],
  ['Export diagram as JSON',download],
  ['Undo previous change',()=>update('UNDO')],
  ['Redo change',()=>update('REDO')],
  ['Switch color theme',()=>update('THEME',state.theme==='light'?'dark':'light')],
  ['Toggle compact layout',()=>update('COMPACT',!state.compact)],
  ['Toggle canvas grid',()=>update('GRID',!state.grid)],
  ['Restore synthetic sample',()=>update('RESET')],
  ['Show keyboard shortcuts',()=>openDialog('helpDialog')]
];
function renderCommands(){
  const needle=$('commandQuery').value.toLowerCase().trim();const box=$('commandItems');box.replaceChildren();
  for(const [label,fn] of commands.filter(([title])=>title.toLowerCase().includes(needle))){
    const button=el('button','command-item',label);button.type='button';
    button.addEventListener('click',()=>{$('commandDialog').close();fn()});box.append(button);
  }
  if(!box.children.length)box.append(el('p','command-hint','No matching actions'));
}
$('commandQuery').addEventListener('input',renderCommands);
$('commandQuery').addEventListener('keydown',e=>{if(e.key==='Enter'){const first=$('commandItems').querySelector('button');if(first){e.preventDefault();first.click()}}});
function download(){
  const blob=new Blob([exportGraph(state)],{type:'application/json'});const url=URL.createObjectURL(blob);
  const anchor=el('a');anchor.href=url;anchor.download='flow-lab-public-diagram.json';
  document.body.append(anchor);anchor.click();anchor.remove();window.setTimeout(()=>URL.revokeObjectURL(url),0);announce('Versioned JSON downloaded');
}
$('importFile').addEventListener('change',async e=>{
  const file=e.target.files?.[0];if(!file)return;
  try{if(file.size>LIMITS.file)throw Error('invalid_import');const content=await file.text();update('IMPORT',content)}catch{announce('Invalid JSON file',true)}finally{e.target.value=''}
});
for(const id of ['addBtn','railAdd'])$(id).addEventListener('click',()=>openDialog('addDialog'));
for(const id of ['railExport'])$(id).addEventListener('click',download);
$('railImport').addEventListener('click',()=>$('importFile').click());
$('commandBtn').addEventListener('click',()=>openDialog('commandDialog'));
$('helpBtn').addEventListener('click',()=>openDialog('helpDialog'));
$('undoBtn').addEventListener('click',()=>update('UNDO'));
$('redoBtn').addEventListener('click',()=>update('REDO'));
$('zoomOut').addEventListener('click',()=>update('ZOOM',Math.max(.6,Math.round((state.zoom-.1)*10)/10),{silent:true}));
$('zoomIn').addEventListener('click',()=>update('ZOOM',Math.min(1.5,Math.round((state.zoom+.1)*10)/10),{silent:true}));
$('gridBtn').addEventListener('click',()=>update('GRID',!state.grid,{silent:true}));
$('themeToggle').addEventListener('click',()=>update('THEME',state.theme==='light'?'dark':'light',{silent:true}));
$('resetBtn').addEventListener('click',()=>update('RESET'));
let drag=null;
$('nodes').addEventListener('pointerdown',e=>{
  const card=e.target.closest('.node-card');if(!card||e.button!==0)return;
  const node=state.nodes.find(n=>n.id===card.dataset.id);if(!node)return;
  drag={id:node.id,card,startX:e.clientX,startY:e.clientY,x:node.x,y:node.y,moved:false};
  card.setPointerCapture(e.pointerId);
});
$('nodes').addEventListener('pointermove',e=>{
  if(!drag)return;
  const dx=(e.clientX-drag.startX)/state.zoom,dy=(e.clientY-drag.startY)/state.zoom;
  if(Math.abs(dx)+Math.abs(dy)<4&&!drag.moved)return;
  drag.moved=true;
  const x=position(drag.x+dx),y=positionY(drag.y+dy);
  drag.card.style.left=`${x}px`;drag.card.style.top=`${y}px`;
  renderEdges(new Map([[drag.id,{x,y}]]));
});
$('nodes').addEventListener('pointerup',e=>{
  if(!drag)return;const current=drag;drag=null;
  if(current.moved){const x=Number.parseInt(current.card.style.left),y=Number.parseInt(current.card.style.top);
    if(update('MOVE_NODE',{id:current.id,x,y},{silent:true}))update('SELECT',current.id,{silent:true});
  } else update('SELECT',current.id,{silent:true});
});
$('nodes').addEventListener('pointercancel',()=>{drag=null;render()});
$('nodes').addEventListener('click',e=>{const card=e.target.closest('.node-card');if(card)update('SELECT',card.dataset.id,{silent:true})});
window.addEventListener('keydown',e=>{
  const editable=e.target.matches?.('input,textarea,select,[contenteditable=true]');
  const mod=e.ctrlKey||e.metaKey;
  if(mod&&e.key.toLowerCase()==='k'){e.preventDefault();openDialog('commandDialog');return}
  if(!editable&&mod&&e.key.toLowerCase()==='z'){e.preventDefault();update(e.shiftKey?'REDO':'UNDO');return}
  if(document.querySelector('dialog[open]'))return;
  if(!editable&&e.key==='?'&&!mod){e.preventDefault();openDialog('helpDialog');return}
  const card=e.target.closest?.('.node-card');
  if(card && ['ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(e.key)){
    e.preventDefault();const n=state.nodes.find(n=>n.id===card.dataset.id);if(!n)return;
    const dx=e.key==='ArrowLeft'?-20:e.key==='ArrowRight'?20:0;
    const dy=e.key==='ArrowUp'?-20:e.key==='ArrowDown'?20:0;
    update('MOVE_NODE',{id:n.id,x:Math.min(LIMITS.x,Math.max(0,n.x+dx)),y:Math.min(LIMITS.y,Math.max(0,n.y+dy))},{silent:true});
  }
  if(!editable && e.key==='Delete' && (card||e.target===$('canvasViewport')) && state.selected){
    e.preventDefault();update('DELETE_NODE',state.selected)
  }
});
render();
