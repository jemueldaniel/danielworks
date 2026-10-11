/** Original public interaction layer. DOM text nodes only, no external calls. */
import {
  PRODUCTS,PLANS,VIEWS,CATEGORIES,COLUMNS,PERSONAS,GOALS,
  createState,reduce,visibleProducts,cartTotal,taskCounts,selectedThread,
  planPrice,money,wizardProgress
} from './model.mjs';

const $=id=>document.getElementById(id);
let state=createState();
try{
 const saved=localStorage.getItem('ui-atlas.theme.v1');
 if(saved==='dark'||saved==='light')state=reduce(state,{type:'THEME',value:saved});
}catch{}
let lastFocus=null;
let toastHandle=0;
const cartDialog=$('cart-dialog');
const taskDialog=$('task-dialog');

function el(tag,cls='',text=''){
 const element=document.createElement(tag);
 if(cls)element.className=cls;
 element.textContent=text;
 return element;
}
function button(label,cls,handler){
 const b=el('button',cls,label);
 b.type='button';
 b.addEventListener('click',handler);
 return b;
}
function toast(text){
 $('toast').textContent=text;
 $('toast').hidden=false;
 clearTimeout(toastHandle);
 toastHandle=setTimeout(()=>{$('toast').hidden=true;},4500);
}
function dispatch(type,value){
 state=reduce(state,{type,value});
 render();
}
function focusHeading(view){
 const target=document.querySelector('[data-view="'+view+'"] h1');
 if(target){
  target.setAttribute('tabindex','-1');
  target.focus({preventScroll:true});
 }
}
function go(view){
 dispatch('NAV',view);
 window.scrollTo({top:0,behavior:'instant'});
 focusHeading(view);
}
function openModal(dialog,elementToFocus){
 lastFocus=document.activeElement;
 dialog.showModal();
 if(elementToFocus)elementToFocus.focus();
}
function closeModal(dialog){dialog.close();}
for(const dialog of [cartDialog,taskDialog]){
 dialog.addEventListener('close',()=>{
  if(lastFocus&&lastFocus.isConnected)lastFocus.focus({preventScroll:true});
  lastFocus=null;
 });
}
function paintNavigation(){
 for(const view of VIEWS)$ (view).hidden=state.view!==view;
 for(const b of document.querySelectorAll('[data-nav]')){
  if(b.dataset.nav===state.view)b.setAttribute('aria-current','page');
  else b.removeAttribute('aria-current');
 }
 document.body.dataset.theme=state.theme;
 $('theme-toggle').setAttribute('aria-label',state.theme==='dark'?'Switch to light theme':'Switch to dark theme');
 $('theme-toggle').firstElementChild.textContent=state.theme==='dark'?'☀':'☾';
}
function paintCommerce(){
 const products=visibleProducts(state);
 const grid=$('product-grid');
 grid.replaceChildren();
 for(const product of products){
  const card=el('article','product-card');
  const art=el('div','product-canvas');
  const figure=el('span','product-symbol');
  figure.dataset.graphic=product.graphic;
  figure.setAttribute('aria-hidden','true');
  art.append(el('span','product-id',product.id.toUpperCase()),figure);
  const head=el('div','product-card-head');
  const text=el('div');
  text.append(el('h3','',product.name),el('p','',product.label));
  head.append(text,el('span','product-price',money(product.price)));
  const add=button('Add to bag ＋','product-add',()=>{
   try{dispatch('CART_ADD',product.id);toast(product.name+' added to bag.');}
   catch{toast('The local bag is full for this item.');}
  });
  add.setAttribute('aria-label','Add '+product.name+' to bag');
  card.append(art,head,add);
  grid.append(card);
 }
 $('product-empty').hidden=products.length!==0;
 $('product-search').value=state.query;
 for(const b of document.querySelectorAll('[data-category]')){
  b.setAttribute('aria-pressed',String(b.dataset.category===state.category));
 }
 $('cart-count').textContent=String(cartTotal(state).items);
}
function paintCart(){
 const metrics=cartTotal(state);
 $('cart-subtotal').textContent=metrics.formatted;
 $('checkout-button').disabled=metrics.items===0;
 $('cart-empty').hidden=metrics.items!==0;
 const container=$('cart-items');container.replaceChildren();
 for(const product of PRODUCTS){
  const qty=state.cart[product.id]||0;
  if(!qty)continue;
  const item=el('div','cart-item');
  const art=el('div','cart-item-symbol',product.name.charAt(0));
  art.setAttribute('aria-hidden','true');
  const info=el('div','cart-item-info');
  info.append(el('strong','',product.name),el('small','',money(product.price)+' each'));
  const controls=el('div','qty-controls');
  const less=button('−','',()=>dispatch('CART_DEC',product.id));
  const more=button('+','',()=>{
   try{dispatch('CART_ADD',product.id);}catch{toast('Maximum of 12 for one item.');}
  });
  less.setAttribute('aria-label','Decrease quantity of '+product.name);
  more.setAttribute('aria-label','Increase quantity of '+product.name);
  controls.append(less,el('span','',String(qty)),more);
  info.append(controls);
  item.append(art,info,el('strong','',money(qty*product.price)));
  container.append(item);
 }
}
function paintBoard(){
 const counts=taskCounts(state);
 $('board-summary').textContent=state.tasks.length+' items across 3 stages';
 for(const column of COLUMNS){
  document.querySelector('[data-count="'+column+'"]').textContent=String(counts[column]);
  const list=document.querySelector('[data-list="'+column+'"]');
  list.replaceChildren();
  for(const item of state.tasks.filter(t=>t.status===column)){
   const card=el('article','task-card');
   const meta=el('div','task-meta');
   const priority=el('span','priority-chip',item.priority.toUpperCase());
   priority.dataset.priority=item.priority;
   meta.append(el('span','',item.id.toUpperCase()),priority);
   const title=el('h3','',item.title);
   const label=el('label','', 'Move to stage');
   const select=el('select');
   select.id='move-'+item.id;
   label.htmlFor=select.id;
   select.setAttribute('aria-label','Move '+item.title+' to stage');
   for(const stage of COLUMNS){
    const o=el('option','',stage==='planned'?'Planned':stage==='progress'?'In progress':'Done');
    o.value=stage;
    select.append(o);
   }
   select.value=item.status;
   select.addEventListener('change',()=>dispatch('BOARD_MOVE',{id:item.id,status:select.value}));
   card.append(meta,title,label,select);
   list.append(card);
  }
 }
}
function paintMessages(){
 const threads=$('thread-list');
 threads.replaceChildren();
 for(const thread of state.threads){
  const b=button('','thread',()=>dispatch('THREAD_SELECT',thread.id));
  b.setAttribute('aria-label','Open conversation with '+thread.name);
  b.setAttribute('aria-pressed',String(thread.id===state.selectedThread));
  const a=el('span','avatar',thread.avatar);a.dataset.tint=thread.tint;a.setAttribute('aria-hidden','true');
  const text=el('span','thread-text');
  text.append(el('strong','',thread.name),el('small','',thread.role));
  b.append(a,text);threads.append(b);
 }
 const active=selectedThread(state);
 const head=$('chat-header');head.replaceChildren();
 const avatar=el('span','avatar',active.avatar);
 avatar.dataset.tint=active.tint;avatar.setAttribute('aria-hidden','true');
 const names=el('div');
 names.append(el('strong','',active.name),el('small','',active.role+' · Local simulation'));
 head.append(avatar,names);
 const log=$('chat-log');log.replaceChildren();
 for(const msg of active.messages){
  const row=el('div','message-row');row.dataset.from=msg.from;
  row.append(el('div','message-bubble',msg.text),el('small','message-time',msg.time));
  log.append(row);
 }
 log.scrollTop=log.scrollHeight;
}
function paintPlans(){
 const out=$('pricing-grid');out.replaceChildren();
 for(const p of PLANS){
  const card=el('article','pricing-card');
  card.dataset.selected=String(state.chosenPlan===p.id);
  card.append(el('h3','',p.name));
  const price=el('div','price-number',money(planPrice(state,p.id)));
  price.append(el('span','',' / month'));
  card.append(price,el('p','',p.id==='starter'?'Explore the foundations':
   p.id==='studio'?'For a growing creative studio':'For coordinated teams'));
  const choice=button(state.chosenPlan===p.id?'Selected':'Choose '+p.name,'btn btn-outline',
    ()=>dispatch('PLAN',p.id));
  choice.setAttribute('aria-pressed',String(state.chosenPlan===p.id));
  card.append(choice);out.append(card);
 }
 for(const b of document.querySelectorAll('[data-period]')){
  b.setAttribute('aria-pressed',String(b.dataset.period===state.period));
 }
}
function wizardChoice(group,option,active,display){
  const control=button(display,'',()=>dispatch(group,option));
  control.setAttribute('aria-pressed',String(option===active));
  return control;
}
function paintWizard(){
 const w=state.boarding;
 const box=$('wizard-body');box.replaceChildren();
 $('wizard-step-label').textContent=w.complete?'COMPLETE / 03':'STEP 0'+w.step+' / 03';
 $('wizard-progress-label').textContent=(w.complete?100:wizardProgress(state))+'% COMPLETE';
 $('wizard-progress-fill').style.width=(w.complete?100:wizardProgress(state))+'%';
 $('wizard-back').disabled=w.step===1||w.complete;
 $('wizard-next').textContent=w.complete?'Start again':w.step===3?'Finish example':'Continue →';
 if(w.complete){
  box.append(el('h3','','You are all set.'));
  box.append(el('p','','This was a local demonstration. No account was created and no personal data was stored.'));
  return;
 }
 if(w.step===1){
  box.append(el('h3','','What describes your work?'),el('p','','Choose a direction. You can change it anytime.'));
  const options=el('div','wizard-options');
  options.append(wizardChoice('PERSONA','builder',w.persona,'Builder · Make it work'),
    wizardChoice('PERSONA','designer',w.persona,'Designer · Make it feel right'),
    wizardChoice('PERSONA','researcher',w.persona,'Researcher · Understand it first'));
  box.append(options);
 }else if(w.step===2){
  box.append(el('h3','','What would you like to do?'),el('p','','A useful interface asks only what matters.'));
  const options=el('div','wizard-options');
  options.append(wizardChoice('GOAL','launch',w.goal,'Launch a useful project'),
    wizardChoice('GOAL','collaborate',w.goal,'Collaborate with a team'),
    wizardChoice('GOAL','evaluate',w.goal,'Evaluate an idea'));
  box.append(options);
 }else{
  box.append(el('h3','','Your direction, at a glance.'),el('p','','Review the sample choices before finishing.'));
  const summary=el('div','wizard-summary');
  for(const [label,value] of [['Role',w.persona],['Goal',w.goal],
                             ['Selected demo plan',state.chosenPlan]]){
   const row=el('div');
   row.append(el('span','',label),el('strong','',value||'None'));
   summary.append(row);
  }
  box.append(summary);
 }
}
function render(){
 paintNavigation();paintCommerce();paintCart();paintBoard();paintMessages();paintPlans();paintWizard();
}
function download(filename,content,mime){
 const blob=new Blob([content],{type:mime});
 const url=URL.createObjectURL(blob);
 const a=document.createElement('a');a.href=url;a.download=filename;
 document.body.append(a);a.click();a.remove();
 setTimeout(()=>URL.revokeObjectURL(url),1000);
}
for(const b of document.querySelectorAll('[data-nav]')){
 b.addEventListener('click',()=>go(b.dataset.nav));
}
for(const b of document.querySelectorAll('[data-go]')){
 b.addEventListener('click',()=>go(b.dataset.go));
}
$('home-brand').addEventListener('click',event=>{event.preventDefault();go('gallery');});
$('theme-toggle').addEventListener('click',()=>{
 const next=state.theme==='light'?'dark':'light';
 dispatch('THEME',next);
 try{localStorage.setItem('ui-atlas.theme.v1',next);}catch{}
 toast(next==='dark'?'Dark theme enabled':'Light theme enabled');
});
$('product-search').addEventListener('input',event=>dispatch('QUERY',event.target.value));
for(const b of document.querySelectorAll('[data-category]')){
 b.addEventListener('click',()=>dispatch('CATEGORY',b.dataset.category));
}
$('reset-products').addEventListener('click',()=>{
 state=reduce(reduce(state,{type:'CATEGORY',value:'All'}),{type:'QUERY',value:''});
 render();$('product-search').focus();
});
$('open-cart').addEventListener('click',()=>openModal(cartDialog,$('close-cart')));
$('close-cart').addEventListener('click',()=>closeModal(cartDialog));
$('checkout-button').addEventListener('click',()=>{
 try{
  const subtotal=cartTotal(state).formatted;
  dispatch('CHECKOUT');
  closeModal(cartDialog);
  toast('Simulated checkout complete — '+subtotal+'. No payment occurred.');
 }catch{toast('Add a fictional product first.');}
});
$('add-task').addEventListener('click',()=>{
 $('task-form').reset();$('task-error').hidden=true;
 openModal(taskDialog,$('task-name'));
});
$('close-task').addEventListener('click',()=>closeModal(taskDialog));
$('cancel-task').addEventListener('click',()=>closeModal(taskDialog));
$('task-form').addEventListener('submit',event=>{
 event.preventDefault();
 try{
  dispatch('BOARD_ADD',{title:$('task-name').value,
    status:$('task-status').value,priority:$('task-priority').value});
  $('task-error').hidden=true;
  closeModal(taskDialog);
  toast('Task added to the local workflow.');
 }catch{
  $('task-error').textContent='Enter a meaningful task name (up to 74 characters).';
  $('task-error').hidden=false;
  $('task-name').focus();
 }
});
$('chat-form').addEventListener('submit',event=>{
 event.preventDefault();
 const field=$('chat-input');
 try{
  dispatch('CHAT_SEND',field.value);
  field.value='';field.focus();
 }catch{toast('Enter a message with 1 to 240 characters.');}
});
for(const b of document.querySelectorAll('[data-period]')){
 b.addEventListener('click',()=>dispatch('PERIOD',b.dataset.period));
}
$('jump-wizard').addEventListener('click',()=>$('wizard').scrollIntoView({behavior:'smooth',block:'start'}));
$('wizard-back').addEventListener('click',()=>dispatch('WIZARD_BACK'));
$('wizard-next').addEventListener('click',()=>{
 try{
  if(state.boarding.complete)dispatch('WIZARD_RESET');
  else if(state.boarding.step===3){dispatch('WIZARD_COMPLETE');toast('Local onboarding finished. No account created.');}
  else dispatch('WIZARD_NEXT');
 }catch{
  toast(state.boarding.step===1?'Choose a role to continue.':'Choose a goal to continue.');
 }
});
$('demo-confirm').addEventListener('click',()=>toast('Interaction confirmed. No external action.'));
$('demo-warning').addEventListener('click',()=>toast('Review the state before continuing.'));
$('demo-form').addEventListener('submit',event=>{
 event.preventDefault();
 const value=$('demo-field').value.trim();
 $('demo-feedback').textContent=value?
  'Validated locally: '+value:'Enter a project title first.';
});
$('download-tokens').addEventListener('click',()=>{
 const values={
  source:'Original UI Atlas reference, no private design source',
  colors:{canvas:'#f8f6f1',ink:'#202d2b',accent:'#e2775b',
          blue:'#667aa9',mint:'#acd0b9'},
  spacing:[4,8,12,16,24,32,48,64],
  radii:[8,12,16,24]
 };
 download('ui-atlas-tokens.json',JSON.stringify(values,null,2)+'\n','application/json');
 toast('Original design tokens exported.');
});
document.addEventListener('keydown',event=>{
 if(event.key==='Escape')return;
 const editable=event.target instanceof HTMLInputElement ||
   event.target instanceof HTMLTextAreaElement||event.target instanceof HTMLSelectElement ||
   Boolean(event.target?.isContentEditable);
 if(!editable&&!cartDialog.open&&!taskDialog.open&&event.key==='/'){
  event.preventDefault();go('commerce');$('product-search').focus();
 }
});
render();
