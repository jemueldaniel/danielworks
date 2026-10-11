import {CATEGORIES,LEVELS,EVIDENCE,RECIPE_NAMES,newState,reduce,visible,tally,byId,publicUrl,normalizeSaved,exportCsv,exportJson,recipeCommand} from './model.mjs';
const $=id=>document.getElementById(id);
const text=(el,value)=>{el.textContent=String(value);return el;};
const elt=(tag,className='',value='')=>{const e=document.createElement(tag);if(className)e.className=className;if(value!==undefined)text(e,value);return e;};
const storage='danielworks-proof-gallery-v1';
let state=newState(),savedOnly=false,priorFocus=null,commandPrior=null;
const glyphs={Interfaces:'◫','AI & Data':'◇',Systems:'⌘',Security:'◈',Language:'λ'};
const announce=value=>text($('live'),value);
try{const old=JSON.parse(localStorage.getItem(storage)||'{}');state=reduce(state,{type:'RESTORE',value:{saved:old.saved,theme:old.theme}});}catch{}
document.body.dataset.theme=state.theme;
function persist(){try{localStorage.setItem(storage,JSON.stringify({saved:state.saved,theme:state.theme}));}catch{}}
function dispatch(type,value){state=reduce(state,{type,value});if(type==='SAVE'||type==='THEME')persist();render();}
function navigate(category){savedOnly=false;$('saved-only').checked=false;dispatch('CATEGORY',category);$('work').scrollIntoView({block:'start'});}
function reset(){savedOnly=false;$('saved-only').checked=false;dispatch('RESET');persist();$('search').value='';$('level-filter').value='All';$('sort').value='featured';}
function selectFromState(){return visible(state).filter(item=>!savedOnly||state.saved.includes(item.id));}
function renderTabs(){
 const host=$('category-tabs');host.replaceChildren();
 const counts=tally();
 for(const c of CATEGORIES){const b=elt('button','category-tab',c+' · '+counts[c]);b.type='button';b.dataset.category=c;b.setAttribute('aria-pressed',String(state.category===c));b.addEventListener('click',()=>navigate(c));host.append(b);}
}
function renderCards(){
 const data=selectFromState(),host=$('results');host.replaceChildren();
 data.forEach((item,idx)=>{
  const card=elt('article','proof-card');card.dataset.id=item.id;card.setAttribute('role','listitem');
  const visual=elt('div','card-visual');visual.append(elt('span','card-index',String(idx+1).padStart(2,'0')+' / '+item.category.toUpperCase()),elt('span','card-glyph',glyphs[item.category]));
  const inner=elt('div','card-inner'),top=elt('div','card-topline');
  top.append(elt('span','category-label',item.category),elt('span','level-label',item.level));
  const h=elt('h3','',item.title),p=elt('p','',item.blurb),controls=elt('div','card-controls'),other=elt('div','card-secondary');
  const open=elt('button','card-open','Inspect case study ↗');open.type='button';open.dataset.action='open';open.dataset.id=item.id;open.setAttribute('aria-label','Inspect '+item.title);open.addEventListener('click',()=>openDetail(item.id,open));
  const save=elt('button','mini-action',state.saved.includes(item.id)?'★':'☆');save.type='button';save.dataset.action='save';save.dataset.id=item.id;save.setAttribute('aria-pressed',String(state.saved.includes(item.id)));save.setAttribute('aria-label',(state.saved.includes(item.id)?'Remove saved ':'Save ')+item.title);save.title='Save evidence';
  save.addEventListener('click',()=>{dispatch('SAVE',item.id);const replacement=document.querySelector('[data-action="save"][data-id="'+item.id+'"]');replacement?.focus();announce('Updated saved evidence');});
  const compare=elt('button','mini-action','⊞');compare.type='button';compare.dataset.action='compare';compare.dataset.id=item.id;compare.setAttribute('aria-pressed',String(state.compare.includes(item.id)));compare.setAttribute('aria-label',(state.compare.includes(item.id)?'Remove from':'Add to')+' comparison: '+item.title);compare.title='Compare evidence';
  compare.addEventListener('click',()=>{try{dispatch('COMPARE',item.id);document.querySelector('[data-action="compare"][data-id="'+item.id+'"]')?.focus();announce('Updated comparison');}catch{announce('Compare up to three public references');}});
  other.append(save,compare);controls.append(open,other);inner.append(top,h,p,controls);card.append(visual,inner);host.append(card);
 });
 $('empty-state').hidden=data.length!==0;$('results').hidden=data.length===0;
 text($('results-summary'),data.length+' of '+EVIDENCE.length+' public references'+(savedOnly?' · saved only':''));
}
function renderCompare(){
 const h=$('compare-toolbar');h.hidden=state.compare.length===0;const container=$('compare-list');container.replaceChildren();
 text($('compare-count'),state.compare.length+' / 3 selected');
 for(const id of state.compare)container.append(elt('span','',byId(id).title));
}
function render(){
 document.body.dataset.theme=state.theme;
 renderTabs();renderCards();renderCompare();
 $('search').value=state.search;
 $('level-filter').value=state.level;$('sort').value=state.sort;
 $('metric-count').firstChild.textContent=EVIDENCE.length;
}
function openDialog(dialog,trigger){priorFocus=trigger||document.activeElement;dialog.showModal();}
function closeDialog(dialog){if(dialog.open)dialog.close();if(priorFocus&&document.contains(priorFocus))priorFocus.focus();priorFocus=null;}
function openDetail(id,trigger){
 const item=byId(id);text($('detail-category'),item.category);text($('detail-level'),item.level);text($('detail-title'),item.title);text($('detail-text'),item.blurb);text($('detail-focus'),item.focus);
 $('detail-source').href=publicUrl(item.source);$('detail-test').href=publicUrl(item.test);
 openDialog($('detail-dialog'),trigger);
}
for(const b of document.querySelectorAll('[data-close]'))b.addEventListener('click',()=>closeDialog($(b.dataset.close)));
for(const dialog of document.querySelectorAll('dialog')){dialog.addEventListener('click',e=>{if(e.target===dialog)closeDialog(dialog)});dialog.addEventListener('close',()=>{if(priorFocus&&document.contains(priorFocus))priorFocus.focus();priorFocus=null;});}
$('search').addEventListener('input',e=>dispatch('SEARCH',e.target.value));
$('level-filter').addEventListener('change',e=>dispatch('LEVEL',e.target.value));
$('sort').addEventListener('change',e=>dispatch('SORT',e.target.value));
$('saved-only').addEventListener('change',e=>{savedOnly=e.target.checked;render();});
$('clear-filters').addEventListener('click',reset);
$('empty-reset').addEventListener('click',reset);
$('theme-toggle').addEventListener('click',()=>{dispatch('THEME',state.theme==='dark'?'light':'dark');announce('Theme '+state.theme);});
function download(filename,body,type){
 const blob=new Blob([body],{type});const url=URL.createObjectURL(blob);const link=elt('a');link.href=url;link.download=filename;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
$('download-csv').addEventListener('click',()=>{download('danielworks-public-evidence.csv',exportCsv({...state}), 'text/csv;charset=utf-8');announce('Exported public evidence CSV');});
$('download-json').addEventListener('click',()=>{download('danielworks-public-evidence.json',exportJson({...state}), 'application/json;charset=utf-8');announce('Exported public evidence JSON');});
function populateRecipes(){
 for(const name of RECIPE_NAMES){const op=elt('option','',name.replaceAll('-',' '));op.value=name;$('recipe-picker').append(op);}
 $('recipe-picker').value='interaction-systems';showRecipe();
}
function showRecipe(){text($('recipe-command'),recipeCommand($('recipe-picker').value));}
$('recipe-picker').addEventListener('change',showRecipe);
$('copy-recipe').addEventListener('click',async()=>{
 const value=$('recipe-command').textContent;
 try{await navigator.clipboard.writeText(value);announce('Copied public recipe command');}
 catch{const s=window.getSelection(),r=document.createRange();r.selectNodeContents($('recipe-command'));s.removeAllRanges();s.addRange(r);announce('Clipboard unavailable; command selected for copying');}
});
$('compare-clear').addEventListener('click',()=>dispatch('CLEAR_COMPARE'));
$('compare-open').addEventListener('click',()=>{
 const host=$('compare-content');host.replaceChildren();
 for(const id of state.compare){
  const item=byId(id),piece=elt('section','compare-item');piece.append(elt('strong','',item.title),elt('small','',item.level),elt('p','',item.focus));
  const a=elt('a','','View source ↗');a.href=publicUrl(item.source);a.target='_blank';a.rel='noopener noreferrer';piece.append(a);host.append(piece);
 }
 openDialog($('compare-dialog'),$('compare-open'));
});
const commands=[
 ['Explore all','Show every public reference',()=>{reset();$('work').scrollIntoView();}],
 ['Interfaces','Filter working UI and frontend references',()=>navigate('Interfaces')],
 ['AI & Data','Browse learning, retrieval and evaluation',()=>navigate('AI & Data')],
 ['Systems','Browse durable backends and workflows',()=>navigate('Systems')],
 ['Security','Browse public security demonstrations',()=>navigate('Security')],
 ['Language','Browse bounded language tooling',()=>navigate('Language')],
 ['Saved references','Show bookmarked evidence',()=>{savedOnly=true;$('saved-only').checked=true;render();$('work').scrollIntoView();}],
 ['One-shot recipes','Choose a reusable reference bundle',()=>{$('reuse').scrollIntoView();$('recipe-picker').focus();}],
 ['Switch theme','Toggle light and dark display',()=>dispatch('THEME',state.theme==='dark'?'light':'dark')],
 ['Export JSON','Download the visible public evidence',()=>download('danielworks-public-evidence.json',exportJson(state),'application/json;charset=utf-8')]
];
function updateCommands(){
 const raw=$('command-input').value.toLowerCase().slice(0,80);const host=$('command-results');host.replaceChildren();
 const selected=commands.filter(([a,b])=>(a+' '+b).toLowerCase().includes(raw));
 for(const [name,help,action] of selected){
  const b=elt('button','command-option',name+' — '+help);b.type='button';b.addEventListener('click',()=>{closeDialog($('command-dialog'));action();});host.append(b);
 }
 if(!selected.length)host.append(elt('p','detail-note','No matching quick actions.'));
}
function openCommands(trigger){$('command-input').value='';updateCommands();openDialog($('command-dialog'),trigger);$('command-input').focus();}
$('quick-menu').addEventListener('click',()=>openCommands($('quick-menu')));
$('command-input').addEventListener('input',updateCommands);
document.addEventListener('keydown',e=>{
 const target=e.target,typing=target?.matches?.('input,textarea,select,[contenteditable="true"]');
 if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();if(!$('command-dialog').open)openCommands($('quick-menu'));else closeDialog($('command-dialog'));return;}
 if(e.key==='/'&&!typing&&!e.ctrlKey&&!e.altKey&&!e.metaKey&&!document.querySelector('dialog[open]')){e.preventDefault();$('search').focus();}
});
populateRecipes();render();
