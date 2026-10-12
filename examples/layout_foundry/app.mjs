import { FIXTURES, TOKENS, safeRows, visibleRows, totals, validateDraft, advance,
  safeTokens, tokenJson, tokenCss, rowsCsv, saveWorkspace, restoreWorkspace } from './model.mjs';

const $=id=>document.getElementById(id);
const state={rows:safeRows(FIXTURES),tokens:safeTokens(TOKENS)};
const STORE='layout-foundry-public-v1';
function restore(){try{
 const saved=localStorage.getItem(STORE);
 if(saved){const data=restoreWorkspace(saved);if(data.ok){state.rows=data.rows;state.tokens=data.tokens;}}
}catch{/* Storage can be disabled; the reference stays functional. */}}
function persist(){try{localStorage.setItem(STORE,saveWorkspace(state.rows,state.tokens));}catch{/* nonfatal */}}
let toastTimer;
function notice(message){
 const t=$('toast');t.textContent=message;t.hidden=false;
 clearTimeout(toastTimer);toastTimer=setTimeout(()=>{t.hidden=true;},3700);
}
function download(name,content,type){
 const blob=new Blob([content],{type}),url=URL.createObjectURL(blob);
 const a=document.createElement('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();
 setTimeout(()=>URL.revokeObjectURL(url),500);
 notice('Export prepared locally: '+name);
}
function applyTokens(){
 state.tokens=safeTokens(state.tokens);
 const t=state.tokens,root=document.documentElement;
 root.dataset.theme=t.theme;root.dataset.density=t.density;
 root.style.setProperty('--brand-hue',String(t.hue));
 root.style.setProperty('--corner',t.radius+'px');
 root.style.setProperty('--control-height',(t.density==='compact'?36:44)+'px');
 $('hue').value=String(t.hue);$('radius').value=String(t.radius);
 $('density').value=t.density;$('hue-value').textContent=t.hue+'°';
 $('radius-value').textContent=t.radius+'px';
 $('theme').setAttribute('aria-label',t.theme==='light'?'Switch to dark theme':'Switch to light theme');
}
function cell(value,classname=''){
 const td=document.createElement('td');td.textContent=value;if(classname)td.className=classname;return td;
}
function paint(){
 const data=totals(state.rows);for(const key of ['total','active','urgent'])$(key).textContent=data[key];
 $('percent').textContent=data.percent+'%';$('progress-label').textContent=data.percent+'%';
 $('progress').setAttribute('aria-valuenow',String(data.percent));$('progress-fill').style.width=data.percent+'%';
 const view=visibleRows(state.rows,{search:$('search').value,team:$('team').value,
   status:$('status').value,sort:$('sort').value});
 const body=$('task-rows');body.replaceChildren();
 for(const item of view){
  const tr=document.createElement('tr'),title=cell('');
  const strong=document.createElement('strong');strong.textContent=item.title;
  const small=document.createElement('small');small.textContent=item.id;
  title.append(strong,small);tr.append(title,cell(item.team));
  tr.append(cell(item.priority,'priority-'+item.priority.toLowerCase()));
  const status=cell(''),chip=document.createElement('span');
  chip.className='chip '+(item.status==='Done'?'success-chip':item.status==='Planned'?'muted-chip':'');
  chip.textContent=item.status;status.append(chip);tr.append(status,cell(item.due));
  const action=cell(''),button=document.createElement('button');
  button.className='task-action';button.type='button';
  button.textContent=item.status==='Done'?'Completed':'Advance →';
  button.disabled=item.status==='Done';button.setAttribute('aria-label','Advance '+item.id);
  button.addEventListener('click',()=>{const result=advance(state.rows,item.id);
    if(result.ok){state.rows=result.rows;persist();paint();notice(item.id+' moved forward.');}
  });
  action.append(button);tr.append(action);body.append(tr);
 }
 $('shown').textContent=view.length+' of '+data.total+' tasks';
 $('empty').hidden=view.length!==0;$('task-rows').hidden=view.length===0;
}
const dialog=$('task-dialog');let priorFocus=null;
function showForm(){priorFocus=document.activeElement;$('task-form').reset();
 for(const key of ['title','team','priority','due','notes']){$('error-'+key).textContent='';}
 $('form-error').hidden=true;dialog.showModal();$('draft-title').focus();}
function closeForm(){dialog.close();if(priorFocus&&priorFocus.isConnected)priorFocus.focus();}
function formErrors(errors){
 for(const key of ['title','team','priority','due','notes']){
  const message=errors[key]||'';$('error-'+key).textContent=message;
  $('draft-'+key).setAttribute('aria-invalid',message?'true':'false');
 }
 $('form-error').hidden=false;$('form-error').textContent=errors.limit||'Correct the marked fields.';
 const first=Object.keys(errors).find(k=>['title','team','priority','due','notes'].includes(k));
 if(first)$('draft-'+first).focus();
}
$('task-form').addEventListener('submit',event=>{
 event.preventDefault();
 const form={title:$('draft-title').value,team:$('draft-team').value,
  priority:$('draft-priority').value,due:$('draft-due').value,notes:$('draft-notes').value};
 const result=validateDraft(form,state.rows);
 if(!result.ok){formErrors(result.errors);return;}
 state.rows.push(result.ticket);persist();closeForm();paint();notice('Task '+result.ticket.id+' created.');
});
for(const name of ['new-top','new-workspace'])$(name).addEventListener('click',showForm);
for(const name of ['close-task','cancel-task'])$(name).addEventListener('click',closeForm);
dialog.addEventListener('close',()=>{if(priorFocus&&priorFocus.isConnected)priorFocus.focus();});
for(const name of ['search','team','status','sort'])$(name).addEventListener('input',paint);
$('reset-data').addEventListener('click',()=>{
 state.rows=safeRows(FIXTURES);
 $('search').value='';$('team').value='All';$('status').value='All';$('sort').value='due';
 persist();paint();notice('Synthetic workspace restored.');
});
$('export-csv').addEventListener('click',()=>download('public-tasks.csv',rowsCsv(state.rows),'text/csv;charset=utf-8'));
$('download-css').addEventListener('click',()=>download('design-tokens.css',tokenCss(state.tokens),'text/css;charset=utf-8'));
$('download-json').addEventListener('click',()=>download('design-tokens.json',tokenJson(state.tokens),'application/json'));
for(const name of ['hue','radius','density'])$(name).addEventListener('input',()=>{
 state.tokens={...state.tokens,hue:Number($('hue').value),
   radius:Number($('radius').value),density:$('density').value};
 applyTokens();persist();
});
$('theme').addEventListener('click',()=>{state.tokens.theme=state.tokens.theme==='light'?'dark':'light';
 applyTokens();persist();notice(state.tokens.theme==='light'?'Light theme applied.':'Dark theme applied.');
});
$('preview-primary').addEventListener('click',()=>notice('Primary action: interactive.'));
$('preview-secondary').addEventListener('click',()=>notice('Secondary action: interactive.'));
const commands=[
 {name:'Go to overview',run:()=>location.hash='overview'},
 {name:'Open workspace',run:()=>location.hash='workspace'},
 {name:'Edit design tokens',run:()=>location.hash='tokens'},
 {name:'Create a new task',run:showForm},
 {name:'Export task data',run:()=>$('export-csv').click()},
 {name:'Switch light or dark theme',run:()=>$('theme').click()}
];
const palette=$('command-dialog');let commandOrigin;
function commandList(){
 const q=$('command-search').value.toLowerCase().trim();
 const list=$('command-list');list.replaceChildren();
 for(const command of commands.filter(c=>c.name.toLowerCase().includes(q))){
  const button=document.createElement('button');button.type='button';
  button.textContent=command.name;button.addEventListener('click',()=>{
   palette.close();command.run();
  });list.append(button);
 }
 if(!list.childElementCount){const empty=document.createElement('p');empty.textContent='No matching commands.';list.append(empty);}
}
function openCommands(){
 commandOrigin=document.activeElement;$('command-search').value='';commandList();
 palette.showModal();$('command-search').focus();
}
$('palette-open').addEventListener('click',openCommands);
$('close-command').addEventListener('click',()=>palette.close());
$('command-search').addEventListener('input',commandList);
palette.addEventListener('close',()=>{if(commandOrigin&&commandOrigin.isConnected)commandOrigin.focus();});
document.addEventListener('keydown',event=>{
 if(event.key==='Escape'&&palette.open){event.preventDefault();palette.close();return;}
 if((event.metaKey||event.ctrlKey)&&event.key.toLowerCase()==='k'){
  event.preventDefault();if(palette.open)palette.close();else if(!dialog.open)openCommands();
 }
});
restore();applyTokens();paint();
