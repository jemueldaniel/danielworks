import {CATEGORIES,LEVELS,RECIPES,TECHNOLOGIES,publicUrl,initialState,reduce,byId,visible,categoryCounts,presentationCounts,buildPlan,recipeCommand,exportCSV,exportJSON} from './model.mjs';
const get=id=>document.getElementById(id),el=(tag,cls='',content)=>{const o=document.createElement(tag);if(cls)o.className=cls;if(content!==undefined)o.textContent=String(content);return o;};
const notices=get('live'),say=s=>notices.textContent=s;
let state=initialState();let returnFocus=null;
const storeKey='danielworks-tech-atlas-v1';
try{state=reduce(state,{type:'RESTORE',value:JSON.parse(localStorage.getItem(storeKey)||'{}')});}catch{}
function persist(){try{localStorage.setItem(storeKey,JSON.stringify({theme:state.theme,saved:state.saved}));}catch{}}
function dispatch(type,value){state=reduce(state,{type,value});if(['TOGGLE_SAVED','THEME','RESTORE'].includes(type))persist();render();}
function top(){return document.querySelector('#index')}
function categoryControl(){
 const host=get('category-tabs');host.replaceChildren();
 const counts=categoryCounts();
 for(const name of CATEGORIES){
  const b=el('button','',name+' · '+counts[name]);b.type='button';b.dataset.category=name;b.setAttribute('aria-pressed',String(state.category===name));b.addEventListener('click',()=>{dispatch('CATEGORY',name);});host.append(b);
 }
}
function cardFor(t,i){
 const item=el('article','tech-card');item.setAttribute('role','listitem');item.dataset.tech=t.id;
 const header=el('div','tech-top');
 header.append(el('span','tech-index',String(i+1).padStart(3,'0')+' / '+String(TECHNOLOGIES.length).padStart(3,'0')),el('span','tech-category',t.category));
 const h=el('h3','',t.name);
 const desc=el('p','',t.summary);
 const footer=el('div','tech-footer'),grade=el('span','level-label '+(t.level==='Public-tested'?'tested':t.level==='Public-historical'?'historical':'observed'));
 const dot=el('i');dot.setAttribute('aria-hidden','true');grade.append(dot,document.createTextNode(t.level));
 const controls=el('div','tech-actions');
 const open=el('button','','↗');open.type='button';open.title='Inspect evidence';open.dataset.action='open';open.setAttribute('aria-label','Inspect '+t.name);open.addEventListener('click',()=>openDetail(t.id,open));
 const save=el('button','',state.saved.includes(t.id)?'★':'☆');save.type='button';save.dataset.action='save';save.dataset.id=t.id;save.title='Save technology';save.setAttribute('aria-pressed',String(state.saved.includes(t.id)));save.setAttribute('aria-label',(state.saved.includes(t.id)?'Remove saved ':'Save ')+t.name);
 save.addEventListener('click',()=>{dispatch('TOGGLE_SAVED',t.id);document.querySelector('[data-action="save"][data-id="'+t.id+'"]')?.focus();say('Updated saved technology');});
 const select=el('button','','⊞');select.type='button';select.dataset.action='select';select.dataset.id=t.id;select.title='Add to a public stack review';select.setAttribute('aria-pressed',String(state.selected.includes(t.id)));select.setAttribute('aria-label',(state.selected.includes(t.id)?'Remove from':'Add to')+' selection: '+t.name);
 select.addEventListener('click',()=>{try{dispatch('TOGGLE_SELECT',t.id);document.querySelector('[data-action="select"][data-id="'+t.id+'"]')?.focus();say('Updated stack review selection');}catch{say('Select at most eight technologies');}});
 controls.append(open,save,select);footer.append(grade,controls);item.append(header,h,desc,footer);
 return item;
}
function renderResults(){
 const list=visible(state),host=get('tech-grid');host.replaceChildren(...list.map(cardFor));
 get('empty-state').hidden=list.length>0;host.hidden=list.length===0;
 get('result-label').textContent='Showing '+list.length+' of '+TECHNOLOGIES.length+' technologies'+(state.showSaved?' · saved only':'');
}
function renderSelected(){
 const tray=get('selection-tray'),items=state.selected.map(byId);
 tray.hidden=items.length===0;get('selection-label').textContent=items.length+' / 8 selected';
 const host=get('selected-tags');host.replaceChildren(...items.map(t=>el('span','',t.name)));
}
function render(){
 document.body.dataset.theme=state.theme;categoryControl();renderResults();renderSelected();
 get('search').value=state.search;get('level-filter').value=state.level;get('sort').value=state.sort;get('saved-only').checked=state.showSaved;
}
function reset(){dispatch('RESET_FILTERS');say('Filters reset');}
function openDialog(id,trigger){
 const dlg=get(id);returnFocus=trigger||document.activeElement;if(!dlg.open)dlg.showModal();
}
function closeDialog(id){
 const dlg=get(id);if(dlg.open)dlg.close();
 if(returnFocus?.isConnected)returnFocus.focus();returnFocus=null;
}
for(const x of document.querySelectorAll('[data-dialog-close]'))x.addEventListener('click',()=>closeDialog(x.dataset.dialogClose));
for(const dlg of document.querySelectorAll('dialog')){
 dlg.addEventListener('click',e=>{if(e.target===dlg)closeDialog(dlg.id);});
 dlg.addEventListener('close',()=>{if(returnFocus?.isConnected)returnFocus.focus();returnFocus=null;});
}
function openDetail(id,trigger){
 const t=byId(id);get('detail-grade').textContent=t.category+' / '+t.level;get('detail-title').textContent=t.name;get('detail-description').textContent=t.summary;
 const has=t.source!==null;
 get('detail-boundary').textContent=has?'This public educational source can be inspected. Its test level is limited to the stated suite; it is not production certification or proof of all private implementations.':'Only generic technology presence was verified in non-public material. No source file, internal path, private product name, or claimed runtime qualification is disclosed.';
 const links=get('detail-links');links.replaceChildren();
 if(has){
  const a=el('a','','Open public implementation ↗');a.href=publicUrl(t.source);a.target='_blank';a.rel='noopener noreferrer';links.append(a);
 }else links.append(el('p','','No public implementation link is available. This is a source observation, not a tested transferable module.'));
 openDialog('detail-dialog',trigger);
}
get('search').addEventListener('input',e=>dispatch('SEARCH',e.target.value));
get('level-filter').addEventListener('change',e=>dispatch('LEVEL',e.target.value));
get('sort').addEventListener('change',e=>dispatch('SORT',e.target.value));
get('saved-only').addEventListener('change',e=>dispatch('SAVED_ONLY',e.target.checked));
get('reset-filters').addEventListener('click',reset);get('empty-reset').addEventListener('click',reset);
get('theme-toggle').addEventListener('click',()=>{dispatch('THEME',state.theme==='dark'?'light':'dark');say('Theme: '+state.theme);});
function download(filename,contents,mime){
 const obj=new Blob([contents],{type:mime}),uri=URL.createObjectURL(obj),a=el('a');
 a.href=uri;a.download=filename;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(uri),1000);
}
get('download-json').addEventListener('click',()=>{download('danielworks-technology-evidence.json',exportJSON(state),'application/json;charset=utf-8');say('Downloaded public technology inventory');});
get('download-csv').addEventListener('click',()=>{download('danielworks-technology-evidence.csv',exportCSV(state),'text/csv;charset=utf-8');say('Downloaded public technology CSV');});
function populate(){
 const count=presentationCounts();
 get('total-count').textContent=count.total;get('verified-count').textContent=count.runnable;get('observed-count').textContent=count.observed;
 for(const name of RECIPES){
  const option=el('option','',name.replaceAll('-',' '));option.value=name;get('recipe-picker').append(option);
 }
 get('recipe-picker').value='career-portfolio';updateRecipe();
}
function updateRecipe(){get('recipe-command').textContent=recipeCommand(get('recipe-picker').value);}
get('recipe-picker').addEventListener('change',updateRecipe);
async function copyText(txt,selector){
 try{await navigator.clipboard.writeText(txt);say('Copied public recipe');}
 catch{const sel=window.getSelection(),range=document.createRange();range.selectNodeContents(selector);sel.removeAllRanges();sel.addRange(range);say('Select and copy the shown public recipe manually');}
}
get('copy-command').addEventListener('click',()=>copyText(get('recipe-command').textContent,get('recipe-command')));
get('clear-selection').addEventListener('click',()=>dispatch('CLEAR_SELECTION'));
function updatePlanRecipe(){get('plan-command').textContent=recipeCommand(get('plan-recipe').value);}
get('plan-recipe').addEventListener('change',updatePlanRecipe);
get('open-plan').addEventListener('click',()=>{
 const report=buildPlan(state),host=get('plan-items');host.replaceChildren();
 get('plan-summary').textContent=report.requested+' technologies selected · '+report.publicExamples+' with public source · '+report.sourceObserved+' observed only';
 for(const t of state.selected.map(byId)){
  const row=el('div','plan-row');row.append(el('span','',t.name),el('span','',t.level));host.append(row);
 }
 const recipes=report.recipes.length?report.recipes:['full-reference'];
 const select=get('plan-recipe');select.replaceChildren();
 for(const name of recipes){const opt=el('option','',name);opt.value=name;select.append(opt);}
 select.value=recipes[0];updatePlanRecipe();openDialog('plan-dialog',get('open-plan'));
});
const commandActions=[
 ['Show all technologies',()=>{reset();top().scrollIntoView({block:'start'});}],
 ['Languages',()=>{dispatch('CATEGORY','Languages');top().scrollIntoView();}],
 ['Frontend & UX',()=>{dispatch('CATEGORY','Frontend & UX');top().scrollIntoView();}],
 ['Backend & Data',()=>{dispatch('CATEGORY','Backend & Data');top().scrollIntoView();}],
 ['AI & Automation',()=>{dispatch('CATEGORY','AI & Automation');top().scrollIntoView();}],
 ['Web3 & Contracts',()=>{dispatch('CATEGORY','Web3 & Contracts');top().scrollIntoView();}],
 ['Cloud & DevOps',()=>{dispatch('CATEGORY','Cloud & DevOps');top().scrollIntoView();}],
 ['Quality & Tooling',()=>{dispatch('CATEGORY','Quality & Tooling');top().scrollIntoView();}],
 ['Public-tested only',()=>{dispatch('LEVEL','Public-tested');top().scrollIntoView();}],
 ['Show saved',()=>{dispatch('SAVED_ONLY',true);top().scrollIntoView();}],
 ['Switch theme',()=>dispatch('THEME',state.theme==='dark'?'light':'dark')],
 ['Jump to one-shot recipes',()=>{get('reuse').scrollIntoView();get('recipe-picker').focus();}]
];
function updateCommands(){
 const needle=get('command-search').value.toLowerCase().trim().slice(0,60),host=get('command-results');host.replaceChildren();
 const entries=commandActions.filter(x=>x[0].toLowerCase().includes(needle));
 for(const [label,act] of entries){
  const b=el('button','command-option',label);b.type='button';b.addEventListener('click',()=>{closeDialog('command-dialog');act();});host.append(b);
 }
 if(!entries.length)host.append(el('p','fine-print','No matching actions.'));
}
function openCommands(trigger){get('command-search').value='';updateCommands();openDialog('command-dialog',trigger);get('command-search').focus();}
get('command-open').addEventListener('click',()=>openCommands(get('command-open')));
get('command-search').addEventListener('input',updateCommands);
document.addEventListener('keydown',e=>{
 const typed=e.target?.matches?.('input,textarea,select,[contenteditable="true"]');
 if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){
  e.preventDefault();if(get('command-dialog').open)closeDialog('command-dialog');else openCommands(get('command-open'));return;
 }
 if(e.key==='/'&&!typed&&!e.altKey&&!e.metaKey&&!e.ctrlKey&&!document.querySelector('dialog[open]')){
  e.preventDefault();get('search').focus();
 }
});
populate();render();
