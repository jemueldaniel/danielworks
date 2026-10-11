/** Original public-only, deterministic UI state for an interactive pattern atlas. */
export const VIEWS = Object.freeze(['gallery','commerce','board','messages','launch','components']);
export const CATEGORIES = Object.freeze(['All','Lighting','Desk','Living']);
export const COLUMNS = Object.freeze(['planned','progress','done']);
export const PERSONAS = Object.freeze(['builder','designer','researcher']);
export const GOALS = Object.freeze(['launch','collaborate','evaluate']);
export const PERIODS = Object.freeze(['monthly','yearly']);
export const PRODUCTS = Object.freeze([
 Object.freeze({id:'lamp',name:'Arc study lamp',category:'Lighting',price:8400,label:'Soft glow / compact form',graphic:'lamp'}),
 Object.freeze({id:'clock',name:'Offset desk clock',category:'Desk',price:5600,label:'Tactile rhythm / analogue face',graphic:'clock'}),
 Object.freeze({id:'vase',name:'Form no. 02',category:'Living',price:4200,label:'Quiet sculptural volume',graphic:'vase'}),
 Object.freeze({id:'shelf',name:'Modular book stand',category:'Desk',price:6200,label:'A place for what matters',graphic:'shelf'}),
 Object.freeze({id:'stool',name:'Everyday side stool',category:'Living',price:11800,label:'Easy proportions / warm tone',graphic:'stool'}),
 Object.freeze({id:'light',name:'Ambient light bar',category:'Lighting',price:7500,label:'Evening glow / adaptable',graphic:'light'})
]);
export const TASKS = Object.freeze([
 Object.freeze({id:'task-01',title:'Map the information hierarchy',status:'planned',priority:'high'}),
 Object.freeze({id:'task-02',title:'Design the mobile navigation',status:'planned',priority:'medium'}),
 Object.freeze({id:'task-03',title:'Test focus and keyboard flow',status:'progress',priority:'high'}),
 Object.freeze({id:'task-04',title:'Prototype editorial product card',status:'progress',priority:'medium'}),
 Object.freeze({id:'task-05',title:'Validate contrast tokens',status:'done',priority:'high'}),
 Object.freeze({id:'task-06',title:'Document empty and error states',status:'done',priority:'low'})
]);
export const THREADS = Object.freeze([
 Object.freeze({id:'ada',name:'Ada Cole',role:'Design review',avatar:'AC',tint:'peach',
  messages:Object.freeze([Object.freeze({id:'a1',from:'them',text:'Does the new direction feel calmer?',time:'09:41'}),
                          Object.freeze({id:'a2',from:'me',text:'Yes. The system now has a clearer rhythm.',time:'09:42'}),
                          Object.freeze({id:'a3',from:'them',text:'Great. Let us test keyboard navigation next.',time:'09:43'})])}),
 Object.freeze({id:'leo',name:'Leo Park',role:'Engineering notes',avatar:'LP',tint:'blue',
  messages:Object.freeze([Object.freeze({id:'l1',from:'them',text:'The responsive breakpoints look good.',time:'Yesterday'}),
                          Object.freeze({id:'l2',from:'me',text:'I will check the smallest width too.',time:'Yesterday'})])}),
 Object.freeze({id:'sam',name:'Sam Rivera',role:'Research synthesis',avatar:'SR',tint:'mint',
  messages:Object.freeze([Object.freeze({id:'s1',from:'them',text:'We learned that clearer labels outperform icons alone.',time:'Monday'})])})
]);
export const PLANS = Object.freeze([
 Object.freeze({id:'starter',name:'Starter',monthly:0,yearly:0}),
 Object.freeze({id:'studio',name:'Studio',monthly:1900,yearly:1500}),
 Object.freeze({id:'team',name:'Team',monthly:4900,yearly:3900})
]);

const categorySet = new Set(CATEGORIES);
const columnSet = new Set(COLUMNS);
const viewSet = new Set(VIEWS);
function invalid(code){throw new RangeError(code);}
function cloneTasks(data){return data.map(x=>({...x}));}
function cloneThreads(data){return data.map(x=>({...x,messages:x.messages.map(m=>({...m}))}));}
export function createState(){
 return {view:'gallery',theme:'light',category:'All',query:'',cart:{},
  tasks:cloneTasks(TASKS),threads:cloneThreads(THREADS),selectedThread:'ada',
  checkout:'idle',boarding:{step:1,persona:null,goal:null,complete:false},
  period:'monthly',chosenPlan:'studio',notification:'',revision:0};
}
export function money(cents){
 if(!Number.isSafeInteger(cents)||cents<0)invalid('invalid_cents');
 return '$'+(cents/100).toFixed(2);
}
export function visibleProducts(state){
 const search=state.query.trim().toLowerCase();
 return PRODUCTS.filter(p=>(state.category==='All'||p.category===state.category)&&
   (!search||[p.name,p.label,p.category].some(v=>v.toLowerCase().includes(search))));
}
export function cartTotal(state){
 let items=0,subtotal=0;
 for(const p of PRODUCTS){
  const qty=state.cart[p.id]||0;
  items+=qty;
  subtotal+=qty*p.price;
 }
 return {items,subtotal,formatted:money(subtotal)};
}
export function taskCounts(state){
 return {planned:state.tasks.filter(x=>x.status==='planned').length,
  progress:state.tasks.filter(x=>x.status==='progress').length,
  done:state.tasks.filter(x=>x.status==='done').length};
}
export function selectedThread(state){
 return state.threads.find(t=>t.id===state.selectedThread);
}
export function planPrice(state,id){
 const p=PLANS.find(x=>x.id===id);
 if(!p)invalid('unknown_plan');
 return p[state.period];
}
export function wizardProgress(state){
 if(state.boarding.complete)return 100;
 return Math.round((state.boarding.step-1)/3*100);
}
export function renderSafeText(value,max=240){
 if(typeof value!=='string')invalid('invalid_text');
 const text=value.trim();
 if(!text||text.length>max||/[\x00-\x08\x0b\x0c\x0e-\x1f]/.test(text))invalid('invalid_text');
 return text;
}
export function reduce(state,action){
 if(!action||typeof action!=='object')invalid('invalid_action');
 const v=action.value;
 switch(action.type){
  case 'NAV':
   if(!viewSet.has(v))invalid('invalid_view');
   return {...state,view:v,notification:''};
  case 'THEME':
   if(v!=='light'&&v!=='dark')invalid('invalid_theme');
   return {...state,theme:v};
  case 'CATEGORY':
   if(!categorySet.has(v))invalid('invalid_category');
   return {...state,category:v};
  case 'QUERY':
   if(typeof v!=='string')invalid('invalid_query');
   return {...state,query:v.slice(0,90)};
  case 'CART_ADD':
  case 'CART_DEC':
  case 'CART_REMOVE':{
   if(typeof v!=='string'||!PRODUCTS.some(p=>p.id===v))invalid('unknown_product');
   const next={...state.cart};
   if(action.type==='CART_REMOVE')delete next[v];
   else{
    const amount=(next[v]||0)+(action.type==='CART_ADD'?1:-1);
    if(amount>12)invalid('cart_item_limit');
    if(amount<=0)delete next[v];else next[v]=amount;
   }
   return {...state,cart:next,checkout:'idle',revision:state.revision+1};
  }
  case 'CART_CLEAR':return {...state,cart:{},checkout:'idle',revision:state.revision+1};
  case 'CHECKOUT':
   if(cartTotal(state).items===0)invalid('empty_cart');
   return {...state,cart:{},checkout:'simulated',revision:state.revision+1};
  case 'BOARD_MOVE':{
   if(!v||typeof v!=='object'||!columnSet.has(v.status)||
      typeof v.id!=='string'||!state.tasks.some(t=>t.id===v.id))invalid('invalid_task_move');
   return {...state,tasks:state.tasks.map(t=>t.id===v.id?{...t,status:v.status}:t),
    revision:state.revision+1};
  }
  case 'BOARD_ADD':{
   if(!v||typeof v!=='object')invalid('invalid_task');
   const title=renderSafeText(v.title,74);
   if(!columnSet.has(v.status)||!['low','medium','high'].includes(v.priority)||
      state.tasks.length>=40)invalid('invalid_task');
   let id;
   for(let n=1;n<=999;n++){
    const candidate='task-'+String(n).padStart(2,'0');
    if(!state.tasks.some(t=>t.id===candidate)){id=candidate;break;}
   }
   if(!id)invalid('task_capacity');
   return {...state,tasks:[...state.tasks,{id,title,status:v.status,priority:v.priority}],
           revision:state.revision+1};
  }
  case 'THREAD_SELECT':
   if(!state.threads.some(t=>t.id===v))invalid('unknown_thread');
   return {...state,selectedThread:v};
  case 'CHAT_SEND':{
   const text=renderSafeText(v);
   const newMessage={id:'msg-'+String(state.revision+1),from:'me',text,time:'Now'};
   return {...state,threads:state.threads.map(t=>t.id===state.selectedThread?
    {...t,messages:[...t.messages,newMessage]}:t),revision:state.revision+1};
  }
  case 'PERSONA':
   if(!PERSONAS.includes(v))invalid('invalid_persona');
   return {...state,boarding:{step:1,persona:v,goal:null,complete:false}};
  case 'GOAL':
   if(!GOALS.includes(v))invalid('invalid_goal');
   return {...state,boarding:{...state.boarding,goal:v,complete:false}};
  case 'WIZARD_NEXT':{
   const w=state.boarding;
   if(w.complete||w.step>=3)invalid('invalid_wizard_step');
   if(w.step===1&&!w.persona)invalid('persona_required');
   if(w.step===2&&!w.goal)invalid('goal_required');
   return {...state,boarding:{...w,step:w.step+1}};
  }
  case 'WIZARD_BACK':
   return {...state,boarding:{...state.boarding,step:Math.max(1,state.boarding.step-1),complete:false}};
  case 'WIZARD_COMPLETE':
   if(state.boarding.step!==3||!state.boarding.persona||!state.boarding.goal)
    invalid('incomplete_onboarding');
   return {...state,boarding:{...state.boarding,complete:true},revision:state.revision+1};
  case 'WIZARD_RESET':return {...state,boarding:{step:1,persona:null,goal:null,complete:false}};
  case 'PERIOD':
   if(!PERIODS.includes(v))invalid('invalid_period');
   return {...state,period:v};
  case 'PLAN':
   if(!PLANS.some(p=>p.id===v))invalid('unknown_plan');
   return {...state,chosenPlan:v};
  case 'NOTICE':
   return {...state,notification:renderSafeText(v,150)};
  case 'CLEAR_NOTICE':return {...state,notification:''};
  default:invalid('unknown_action');
 }
}
