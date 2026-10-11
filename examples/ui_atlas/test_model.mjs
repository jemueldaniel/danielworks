/** Independent deterministic regression checks for five synthetic frontend patterns. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {
 VIEWS,CATEGORIES,COLUMNS,PERSONAS,GOALS,PERIODS,PRODUCTS,TASKS,THREADS,PLANS,
 createState,reduce,visibleProducts,cartTotal,taskCounts,selectedThread,
 planPrice,money,wizardProgress,renderSafeText
} from './model.mjs';
const fresh=()=>createState();
const step=(state,type,value)=>reduce(state,{type,value});
const fakeTask={title:'Test the navigation',status:'planned',priority:'medium'};

test('five interactive experiences and gallery are explicit public views',()=>{
 assert.deepEqual(VIEWS,['gallery','commerce','board','messages','launch','components']);
});
test('synthetic fixture sizes are stable',()=>{
 assert.equal(PRODUCTS.length,6);assert.equal(TASKS.length,6);assert.equal(THREADS.length,3);
});
test('fixture product identifiers are unique',()=>{
 assert.equal(new Set(PRODUCTS.map(p=>p.id)).size,6);
});
test('no shared task objects are mutated between runs',()=>{
 const a=fresh(),b=fresh();a.tasks[0].title='Different';
 assert.notEqual(a.tasks[0].title,b.tasks[0].title);
});
test('default state is gallery, light theme, empty cart',()=>{
 const s=fresh();assert.equal(s.view,'gallery');assert.equal(s.theme,'light');assert.deepEqual(s.cart,{});
});
test('navigation accepts each public view',()=>{
 for(const view of VIEWS)assert.equal(step(fresh(),'NAV',view).view,view);
});
test('unknown view fails closed',()=>{
 assert.throws(()=>step(fresh(),'NAV','/admin'),/invalid_view/);
});
test('theme toggles through allowlisted values',()=>{
 assert.equal(step(fresh(),'THEME','dark').theme,'dark');
 assert.equal(step(fresh(),'THEME','light').theme,'light');
});
test('unknown theme fails closed',()=>assert.throws(()=>step(fresh(),'THEME','purple'),/invalid_theme/));
test('catalog starts with six products',()=>assert.equal(visibleProducts(fresh()).length,6));
test('category filters catalog',()=>{
 const s=step(fresh(),'CATEGORY','Lighting');
 assert.deepEqual(visibleProducts(s).map(p=>p.id),['lamp','light']);
});
test('search catalog by label',()=>{
 const s=step(fresh(),'QUERY','analogue');
 assert.deepEqual(visibleProducts(s).map(p=>p.id),['clock']);
});
test('search is case insensitive',()=>{
 assert.deepEqual(visibleProducts(step(fresh(),'QUERY','DESK')).map(p=>p.id),['clock','shelf']);
});
test('category and query compose',()=>{
 const s=step(step(fresh(),'CATEGORY','Desk'),'QUERY','clock');
 assert.deepEqual(visibleProducts(s).map(p=>p.id),['clock']);
});
test('empty search reports no product, without throwing',()=>{
 assert.deepEqual(visibleProducts(step(fresh(),'QUERY','nothing-will-match-098')),[]);
});
test('query input length is bounded',()=>{
 assert.equal(step(fresh(),'QUERY','x'.repeat(300)).query.length,90);
});
test('malformed query/category rejected',()=>{
 assert.throws(()=>step(fresh(),'QUERY',123),/invalid_query/);
 assert.throws(()=>step(fresh(),'CATEGORY','private'),/invalid_category/);
});
test('currency rendering is deterministic for fictional cents',()=>{
 assert.equal(money(8400),'$84.00');assert.equal(money(19),'$0.19');
});
test('invalid cents rejected',()=>{
 for(const value of [-1,1.5,NaN,'100',true])assert.throws(()=>money(value),/invalid_cents/);
});
test('adding one item updates total',()=>{
 const s=step(fresh(),'CART_ADD','lamp');
 assert.deepEqual(cartTotal(s),{items:1,subtotal:8400,formatted:'$84.00'});
});
test('different products aggregate correctly',()=>{
 let s=step(fresh(),'CART_ADD','lamp');
 s=step(s,'CART_ADD','vase');
 assert.deepEqual(cartTotal(s),{items:2,subtotal:12600,formatted:'$126.00'});
});
test('adding same product changes quantity without mutating previous state',()=>{
 const a=step(fresh(),'CART_ADD','lamp'),b=step(a,'CART_ADD','lamp');
 assert.equal(a.cart.lamp,1);assert.equal(b.cart.lamp,2);
});
test('decrementing final item removes zero entry',()=>{
 const s=step(step(fresh(),'CART_ADD','lamp'),'CART_DEC','lamp');
 assert.equal(cartTotal(s).items,0);assert.deepEqual(s.cart,{});
});
test('decrement empty product remains at zero',()=>{
 assert.deepEqual(step(fresh(),'CART_DEC','lamp').cart,{});
});
test('remove and clear operations empty bag',()=>{
 let s=step(step(fresh(),'CART_ADD','lamp'),'CART_ADD','vase');
 s=step(s,'CART_REMOVE','lamp');assert.equal(cartTotal(s).items,1);
 assert.equal(cartTotal(step(s,'CART_CLEAR')).items,0);
});
test('unknown product rejected for cart actions',()=>{
 for(const name of ['CART_ADD','CART_DEC','CART_REMOVE']){
  assert.throws(()=>step(fresh(),name,'missing'),/unknown_product/);
 }
});
test('per-product cart capacity is fixed at twelve',()=>{
 let state=fresh();
 for(let i=0;i<12;i++)state=step(state,'CART_ADD','lamp');
 assert.equal(state.cart.lamp,12);
 assert.throws(()=>step(state,'CART_ADD','lamp'),/cart_item_limit/);
});
test('empty checkout cannot claim success',()=>assert.throws(()=>step(fresh(),'CHECKOUT'),/empty_cart/));
test('fictional checkout clears cart and marks simulated',()=>{
 const s=step(step(fresh(),'CART_ADD','lamp'),'CHECKOUT');
 assert.equal(s.checkout,'simulated');assert.equal(cartTotal(s).items,0);
});
test('board has stable initial totals',()=>{
 assert.deepEqual(taskCounts(fresh()),{planned:2,progress:2,done:2});
});
test('moving task changes its column',()=>{
 const s=step(fresh(),'BOARD_MOVE',{id:'task-01',status:'done'});
 assert.deepEqual(taskCounts(s),{planned:1,progress:2,done:3});
});
test('moving task does not mutate earlier snapshot',()=>{
 const a=fresh(),b=step(a,'BOARD_MOVE',{id:'task-01',status:'done'});
 assert.equal(a.tasks[0].status,'planned');assert.equal(b.tasks[0].status,'done');
});
test('invalid stage and unknown task cannot move',()=>{
 for(const v of [{id:'task-01',status:'missing'},{id:'not-a-task',status:'done'},null]){
  assert.throws(()=>step(fresh(),'BOARD_MOVE',v),/invalid_task_move/);
 }
});
test('adding task assigns a new deterministic id',()=>{
 const s=step(fresh(),'BOARD_ADD',fakeTask);
 assert.equal(s.tasks.length,7);assert.equal(s.tasks.at(-1).id,'task-07');
});
test('added task can move to any allowed status',()=>{
 let s=step(fresh(),'BOARD_ADD',fakeTask);
 s=step(s,'BOARD_MOVE',{id:'task-07',status:'progress'});
 assert.equal(s.tasks.at(-1).status,'progress');
});
test('invalid task titles are rejected',()=>{
 for(const title of ['', '  ', 'x'.repeat(75),'\x00bad']){
  assert.throws(()=>step(fresh(),'BOARD_ADD',{...fakeTask,title}),/invalid_text/);
 }
});
test('invalid task priority rejected',()=>{
 assert.throws(()=>step(fresh(),'BOARD_ADD',{...fakeTask,priority:'urgent'}),/invalid_task/);
});
test('board maximum capacity refuses overflow',()=>{
 let s=fresh();
 for(let i=0;i<34;i++)s=step(s,'BOARD_ADD',fakeTask);
 assert.equal(s.tasks.length,40);
 assert.throws(()=>step(s,'BOARD_ADD',fakeTask),/invalid_task/);
});
test('selected thread starts at first synthetic conversation',()=>{
 assert.equal(selectedThread(fresh()).name,'Ada Cole');
});
test('switching thread shows different messages',()=>{
 const s=step(fresh(),'THREAD_SELECT','leo');
 assert.equal(selectedThread(s).name,'Leo Park');
 assert.equal(selectedThread(s).messages.length,2);
});
test('unknown conversation refused',()=>assert.throws(()=>step(fresh(),'THREAD_SELECT','unknown'),/unknown_thread/));
test('sending message appends only to active thread',()=>{
 const s=step(fresh(),'CHAT_SEND','Hello from a real state transition');
 assert.equal(selectedThread(s).messages.length,4);
 assert.equal(s.threads.find(t=>t.id==='leo').messages.length,2);
});
test('sending text creates literal message, not HTML',()=>{
 const s=step(fresh(),'CHAT_SEND','<img src=x onerror=alert(1)>');
 assert.equal(selectedThread(s).messages.at(-1).text,'<img src=x onerror=alert(1)>');
});
test('oversized and empty messages rejected',()=>{
 for(const v of ['', ' '.repeat(8),'x'.repeat(241),42]){
  assert.throws(()=>step(fresh(),'CHAT_SEND',v),/invalid_text/);
 }
});
test('message strips outer whitespace',()=>{
 const s=step(fresh(),'CHAT_SEND','   Hello   ');
 assert.equal(selectedThread(s).messages.at(-1).text,'Hello');
});
test('messages are independently copied from frozen fixtures',()=>{
 let s=fresh();s.threads[0].messages[0].text='Changed';
 assert.notEqual(THREADS[0].messages[0].text,s.threads[0].messages[0].text);
});
test('wizard starts with no personal data fields',()=>{
 assert.deepEqual(fresh().boarding,{step:1,persona:null,goal:null,complete:false});
});
test('wizard requires a persona at step one',()=>{
 assert.throws(()=>step(fresh(),'WIZARD_NEXT'),/persona_required/);
});
test('persona selection stores only a closed generic choice',()=>{
 const s=step(fresh(),'PERSONA','designer');
 assert.equal(s.boarding.persona,'designer');
});
test('wizard requires goal at step two',()=>{
 const s=step(step(fresh(),'PERSONA','builder'),'WIZARD_NEXT');
 assert.equal(s.boarding.step,2);
 assert.throws(()=>step(s,'WIZARD_NEXT'),/goal_required/);
});
test('goal selection and step three are deterministic',()=>{
 let s=step(fresh(),'PERSONA','builder');
 s=step(s,'WIZARD_NEXT');
 s=step(s,'GOAL','launch');
 s=step(s,'WIZARD_NEXT');
 assert.equal(s.boarding.step,3);
 assert.equal(wizardProgress(s),67);
});
test('onboarding cannot complete early',()=>assert.throws(()=>step(fresh(),'WIZARD_COMPLETE'),/incomplete_onboarding/));
test('full wizard completes without a user identity',()=>{
 let s=step(fresh(),'PERSONA','builder');
 s=step(s,'WIZARD_NEXT');s=step(s,'GOAL','launch');
 s=step(s,'WIZARD_NEXT');s=step(s,'WIZARD_COMPLETE');
 assert.equal(s.boarding.complete,true);
 assert.equal(wizardProgress(s),100);
 assert.equal(s.boarding.email,undefined);
});
test('completed wizard requires a reset to restart',()=>{
 let s=step(fresh(),'PERSONA','researcher');s=step(s,'WIZARD_NEXT');
 s=step(s,'GOAL','evaluate');s=step(s,'WIZARD_NEXT');s=step(s,'WIZARD_COMPLETE');
 assert.throws(()=>step(s,'WIZARD_NEXT'),/invalid_wizard_step/);
 assert.equal(step(s,'WIZARD_RESET').boarding.step,1);
});
test('wizard back stops at first step',()=>{
 assert.equal(step(fresh(),'WIZARD_BACK').boarding.step,1);
});
test('persona and goal reject unauthorized values',()=>{
 assert.throws(()=>step(fresh(),'PERSONA','private_role'),/invalid_persona/);
 assert.throws(()=>step(fresh(),'GOAL','get_secrets'),/invalid_goal/);
});
test('pricing periods alter fictional price only',()=>{
 const a=fresh(),b=step(a,'PERIOD','yearly');
 assert.equal(planPrice(a,'studio'),1900);
 assert.equal(planPrice(b,'studio'),1500);
});
test('pricing plan selection is bounded and reversible',()=>{
 const s=step(fresh(),'PLAN','team');
 assert.equal(s.chosenPlan,'team');
 assert.equal(planPrice(s,'team'),4900);
});
test('invalid pricing selections rejected',()=>{
 assert.throws(()=>step(fresh(),'PERIOD','weekly'),/invalid_period/);
 assert.throws(()=>step(fresh(),'PLAN','confidential'),/unknown_plan/);
});
test('token-like notice only allows bounded clean text',()=>{
 const s=step(fresh(),'NOTICE','Ready');
 assert.equal(s.notification,'Ready');
 assert.equal(step(s,'CLEAR_NOTICE').notification,'');
 assert.throws(()=>step(fresh(),'NOTICE','x'.repeat(151)),/invalid_text/);
});
test('invalid reducer action fails without implicit dispatch',()=>{
 assert.throws(()=>step(fresh(),'EVAL','alert(1)'),/unknown_action/);
});
test('invalid message control characters are refused',()=>{
 assert.throws(()=>renderSafeText('bad\x00input'),/invalid_text/);
});
test('all public fixtures explicitly have bounded product costs',()=>{
 assert.ok(PRODUCTS.every(p=>Number.isInteger(p.price)&&p.price>0&&p.price<15000));
});
test('all public catalogs are closed enumerations',()=>{
 assert.deepEqual(CATEGORIES,['All','Lighting','Desk','Living']);
 assert.deepEqual(COLUMNS,['planned','progress','done']);
 assert.deepEqual(PERSONAS,['builder','designer','researcher']);
 assert.deepEqual(GOALS,['launch','collaborate','evaluate']);
 assert.deepEqual(PERIODS,['monthly','yearly']);
});
test('fictitious plan prices remain positive except trial',()=>{
 assert.equal(PLANS[0].monthly,0);
 assert.ok(PLANS.slice(1).every(p=>p.yearly<p.monthly));
});
