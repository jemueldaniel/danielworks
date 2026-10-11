/** An independently authored, accessible UI controller. No network calls. */
import {
  FIXTURES,createState,derive,reduce,addRecord,readPreferences,savedPreferences,
  exportCsv,SECTIONS
} from './model.mjs';

const $=id=>document.getElementById(id);
const labels={
  overview:['Workspace overview','An interactive reference for thoughtful, accessible software.'],
  library:['Work item library','Search, filter and sort an entirely synthetic dataset.'],
  activity:['Activity and decisions','The human-readable history behind useful work.'],
  settings:['Interface settings','A more adaptable workspace, shaped around you.'],
};
const statusText={active:'In progress',review:'In review',complete:'Completed'};
let pref={};
try{pref=JSON.parse(localStorage.getItem('interface-lab.preferences.v1')||'{}');}catch{}
let state=createState(FIXTURES,readPreferences(pref));
let lastTrigger=null;
let toastTimer;
const recordDialog=$('record-dialog');
const commandDialog=$('command-dialog');
const sidebar=$('sidebar');
const backdrop=$('nav-backdrop');
const menuToggle=$('menu-toggle');

function element(tag,cls='',text=''){
 const node=document.createElement(tag);
 if(cls)node.className=cls;
 node.textContent=text;
 return node;
}
function statusPill(status){
 const pill=element('span','status-pill',statusText[status]);
 pill.dataset.status=status;
 return pill;
}
function renderRecent(view){
 const container=$('recent-list');
 container.replaceChildren();
 const records=[...state.records].sort((a,b)=>b.updated.localeCompare(a.updated)).slice(0,3);
 for(const record of records){
  const row=element('div','recent-item');
  const initial=element('span','recent-avatar',record.owner.split(' ').map(x=>x[0]).slice(0,2).join(''));
  initial.setAttribute('aria-hidden','true');
  const texts=element('div');
  texts.append(element('div','recent-title',record.title));
  texts.append(element('div','recent-owner',record.owner+' · '+record.category));
  row.append(initial,texts,statusPill(record.status));
  container.append(row);
 }
}
function renderTable(view){
 const table=$('table-body');
 table.replaceChildren();
 for(const record of view.records){
  const row=document.createElement('tr');
  const title=element('td');
  title.append(element('strong','',record.title),element('span','item-id',record.id));
  row.append(title,element('td','',record.owner),element('td','',record.category));
  const status=element('td');
  status.append(statusPill(record.status));
  row.append(status,element('td','right',String(record.effort)));
  table.append(row);
 }
 $('table-empty').hidden=view.filteredCount!==0;
 $('page-prev').disabled=view.page===1;
 $('page-next').disabled=view.page===view.totalPages;
 $('page-label').textContent='Page '+view.page+' of '+view.totalPages;
 $('range-info').textContent='Showing '+view.showingFrom+'–'+view.showingTo+' of '+view.filteredCount+' items';
 $('record-search').value=state.query;
 $('record-sort').value=state.sort;
 for(const control of document.querySelectorAll('[data-status]')){
  if(control.tagName==='BUTTON')control.setAttribute('aria-pressed',String(control.dataset.status===state.status));
 }
}
function renderActivity(){
 const list=$('activity-list');
 list.replaceChildren();
 for(const record of [...state.records].sort((a,b)=>b.updated.localeCompare(a.updated)).slice(0,9)){
  const row=document.createElement('li');
  row.append(element('strong','',record.title+' · '+statusText[record.status]));
  row.append(element('p','',record.updated+' — '+record.owner+' / '+record.category));
  list.append(row);
 }
}
function applyPreferences(){
 document.body.dataset.theme=state.theme;
 document.body.dataset.density=state.density;
 $('setting-theme').value=state.theme;
 $('setting-density').value=state.density;
 $('theme-switch').setAttribute('aria-label',
   state.theme==='dark'?'Switch to light theme':'Switch to dark theme');
 $('theme-switch').querySelector('.theme-icon').textContent=
   state.theme==='dark'?'☀':'☾';
 try{localStorage.setItem('interface-lab.preferences.v1',
                         JSON.stringify(savedPreferences(state)));}catch{}
}
function render(){
 const view=derive(state);
 $('metric-total').textContent=String(view.counters.total);
 $('metric-active').textContent=String(view.counters.active);
 $('metric-review').textContent=String(view.counters.review);
 $('metric-complete').textContent=String(view.counters.complete);
 for(const section of SECTIONS)$ (section).hidden=section!==state.section;
 $('page-title').textContent=labels[state.section][0];
 $('page-subtitle').textContent=labels[state.section][1];
 $('breadcrumb').textContent=state.section[0].toUpperCase()+state.section.slice(1);
 for(const nav of document.querySelectorAll('.nav-button')){
  if(nav.dataset.section===state.section)nav.setAttribute('aria-current','page');
  else nav.removeAttribute('aria-current');
 }
 renderRecent(view);
 renderTable(view);
 renderActivity();
 applyPreferences();
}
function dispatch(action){
 state=reduce(state,action);
 render();
}
function closeMobileMenu(){
 document.body.classList.remove('nav-open');
 menuToggle.setAttribute('aria-expanded','false');
 menuToggle.setAttribute('aria-label','Open navigation');
 backdrop.hidden=true;
}
function openMobileMenu(){
 document.body.classList.add('nav-open');
 menuToggle.setAttribute('aria-expanded','true');
 menuToggle.setAttribute('aria-label','Close navigation');
 backdrop.hidden=false;
}
function navigate(section){
 dispatch({type:'SECTION',value:section});
 closeMobileMenu();
 const heading=$('page-title');
 heading.setAttribute('tabindex','-1');
 heading.focus();
 window.scrollTo({top:0,behavior:'instant'});
}
let noticeToken=0;
function notice(message){
 const n=$('toast');
 n.textContent=message;
 n.hidden=false;
 clearTimeout(toastTimer);
 const token=++noticeToken;
 toastTimer=setTimeout(()=>{if(token===noticeToken)n.hidden=true;},5000);
}
function openDialog(dialog,focus){
 lastTrigger=document.activeElement;
 dialog.showModal();
 if(focus)focus.focus();
}
function restoreFocus(){
 const target=lastTrigger;
 lastTrigger=null;
 if(target&&target.isConnected)target.focus();
}
recordDialog.addEventListener('close',restoreFocus);
commandDialog.addEventListener('close',restoreFocus);
function openCreate(){
 $('new-record-form').reset();
 $('record-error').hidden=true;
 openDialog(recordDialog,$('new-title'));
}
function openCommands(){
 openDialog(commandDialog,commandDialog.querySelector('[data-command]'));
}
function changeTheme(){
 dispatch({type:'THEME',value:state.theme==='light'?'dark':'light'});
 notice(state.theme==='dark'?'Dark theme applied.':'Light theme applied.');
}
for(const nav of document.querySelectorAll('.nav-button')){
 nav.addEventListener('click',()=>navigate(nav.dataset.section));
}
for(const link of document.querySelectorAll('[data-go]')){
 link.addEventListener('click',()=>navigate(link.dataset.go));
}
$('home-link').addEventListener('click',event=>{event.preventDefault();navigate('overview');});
menuToggle.addEventListener('click',()=>document.body.classList.contains('nav-open')?closeMobileMenu():openMobileMenu());
backdrop.addEventListener('click',closeMobileMenu);
$('theme-switch').addEventListener('click',changeTheme);
$('create-top').addEventListener('click',openCreate);
$('open-command').addEventListener('click',openCommands);
for(const button of document.querySelectorAll('.close-dialog')){
 button.addEventListener('click',()=>button.closest('dialog').close());
}
$('cancel-record').addEventListener('click',()=>recordDialog.close());
for(const button of document.querySelectorAll('[data-command]')){
 button.addEventListener('click',()=>{
  const action=button.dataset.command;
  commandDialog.close();
  if(action==='new')openCreate();
  else if(action==='theme')changeTheme();
  else navigate(action);
 });
}
$('record-search').addEventListener('input',event=>dispatch({type:'QUERY',value:event.target.value}));
$('record-sort').addEventListener('change',event=>dispatch({type:'SORT',value:event.target.value}));
for(const button of document.querySelectorAll('button[data-status]')){
 button.addEventListener('click',()=>dispatch({type:'STATUS',value:button.dataset.status}));
}
$('page-prev').addEventListener('click',()=>dispatch({type:'PAGE',value:Math.max(1,derive(state).page-1)}));
$('page-next').addEventListener('click',()=>dispatch({type:'PAGE',value:derive(state).page+1}));
$('clear-filters').addEventListener('click',()=>{
 state=reduce(reduce(state,{type:'QUERY',value:''}),{type:'STATUS',value:'all'});
 render();
 $('record-search').focus();
});
$('setting-theme').addEventListener('change',event=>dispatch({type:'THEME',value:event.target.value}));
$('setting-density').addEventListener('change',event=>dispatch({type:'DENSITY',value:event.target.value}));
$('reset-preferences').addEventListener('click',()=>{
 state=reduce(reduce(state,{type:'THEME',value:'light'}),{type:'DENSITY',value:'comfortable'});
 render();
 notice('Preferences restored.');
});
$('new-record-form').addEventListener('submit',event=>{
 event.preventDefault();
 const form=event.currentTarget;
 const data=new FormData(form);
 try{
  const today=new Date().toISOString().slice(0,10);
  state=addRecord(state,{
   title:String(data.get('title')||'').trim(),
   owner:String(data.get('owner')||'').trim(),
   category:data.get('category'),
   status:data.get('status'),
   effort:data.get('effort')
  },today);
  $('record-error').hidden=true;
  recordDialog.close();
  render();
  notice('Work item created locally.');
 }catch{
  const error=$('record-error');
  error.textContent='Enter a title, owner and effort between 1 and 40.';
  error.hidden=false;
  $('new-title').focus();
 }
});
$('download-csv').addEventListener('click',()=>{
 const csv=exportCsv(state);
 const blob=new Blob([csv],{type:'text/csv;charset=utf-8'});
 const url=URL.createObjectURL(blob);
 const anchor=document.createElement('a');
 anchor.href=url;
 anchor.download='interface-laboratory-sample.csv';
 document.body.append(anchor);
 anchor.click();
 anchor.remove();
 setTimeout(()=>URL.revokeObjectURL(url),2000);
 notice('CSV exported from synthetic records.');
});
document.addEventListener('keydown',event=>{
 const target=event.target;
 const editable=target instanceof HTMLInputElement ||
   target instanceof HTMLTextAreaElement||target instanceof HTMLSelectElement ||
   Boolean(target?.isContentEditable);
 if(event.key==='Escape'&&document.body.classList.contains('nav-open')){
  closeMobileMenu();
  menuToggle.focus();
  return;
 }
 if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){
  event.preventDefault();
  if(!recordDialog.open&&!commandDialog.open)openCommands();
  return;
 }
 if(!editable&&!recordDialog.open&&!commandDialog.open){
  if(event.key==='/'){
   event.preventDefault();
   navigate('library');
   $('record-search').focus();
  }else if(event.key.toLowerCase()==='n'&&!event.altKey&&!event.ctrlKey&&!event.metaKey){
   event.preventDefault();
   openCreate();
  }
 }
});
render();
