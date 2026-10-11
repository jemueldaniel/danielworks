/** Browser acceptance for original interactive UI pattern collection. */
import test,{before,after} from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {promises as fs,existsSync} from 'node:fs';
import {dirname,resolve,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';

const root=resolve(dirname(fileURLToPath(import.meta.url)),'../../examples/ui_atlas');
const files=new Map([['/','index.html'],['/index.html','index.html'],
 ['/styles.css','styles.css'],['/app.mjs','app.mjs'],['/model.mjs','model.mjs']]);
const VIEWS=['gallery','commerce','board','messages','launch','components'];
let browser,server,origin;
before(async()=>{
 server=createServer(async(req,res)=>{
  const path=(req.url||'/').split('?')[0],name=files.get(path);
  if(!name||req.method!=='GET'){res.writeHead(404,{'Content-Length':'0'});return res.end();}
  try{
   const buf=await fs.readFile(join(root,name));
   res.writeHead(200,{
    'Content-Type':name.endsWith('.html')?'text/html; charset=utf-8':
      name.endsWith('.css')?'text/css; charset=utf-8':'text/javascript; charset=utf-8',
    'Content-Length':buf.length,'Cache-Control':'no-store',
    'X-Content-Type-Options':'nosniff',
    'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'none'; img-src 'self' data:; object-src 'none'; base-uri 'none'; form-action 'none'"
   });res.end(buf);
  }catch{res.writeHead(500,{'Content-Length':'0'});res.end();}
 });
 await new Promise((yes,no)=>{server.once('error',no);server.listen(0,'127.0.0.1',yes)});
 origin='http://127.0.0.1:'+server.address().port;
 const bin=process.env.BROWSER_PATH||
  (process.platform==='win32'?'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe':'/usr/bin/chromium');
 assert.ok(existsSync(bin),'Installed Edge/Chromium is required; do not download browsers');
 browser=await chromium.launch({executablePath:bin,headless:true,args:process.platform==='linux'?['--no-sandbox']:[]});
 console.log(JSON.stringify({browser:await browser.version(),target:'local-only'}));
});
after(async()=>{await browser?.close();if(server)await new Promise(yes=>server.close(yes))});
async function visit(width=1280,opts={}){
 const context=await browser.newContext({viewport:{width,height:800},acceptDownloads:true,...opts});
 const page=await context.newPage();page.setDefaultTimeout(7000);
 const errors=[];page.on('pageerror',x=>errors.push(x.message));
 await page.goto(origin+'/');await page.locator('#gallery:visible').waitFor();
 return {page,context,errors};
}
async function goto(page,name){await page.locator('[data-nav='+name+']').click();await page.locator('#'+name+':visible').waitFor();}
async function noOverflow(page){return page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1);}

test('gallery is a real navigable experience with semantic landmarks',async()=>{
 const a=await visit();
 try{
  assert.equal(await a.page.getByRole('main').count(),1);
  assert.equal(await a.page.getByRole('navigation',{name:'Patterns'}).count(),1);
  assert.equal(await a.page.getByRole('link',{name:'Skip to content'}).count(),1);
  assert.equal(await a.page.locator('.pattern-card').count(),5);
  assert.equal(await noOverflow(a.page),true);
  assert.deepEqual(a.errors,[]);
 }finally{await a.context.close();}
});
test('320, 390, 768, 1024 and 1440 pixel responsive layouts',async()=>{
 for(const width of [320,390,768,1024,1440]){
  const a=await visit(width);
  try{assert.equal(await noOverflow(a.page),true,'gallery '+width)}
  finally{await a.context.close();}
 }
});
test('every pattern view avoids page-level overflow on narrow phones',async()=>{
 const a=await visit(320);
 try{for(const view of VIEWS){await goto(a.page,view);assert.equal(await noOverflow(a.page),true,view);}}
 finally{await a.context.close();}
});
test('navigation changes selected section without refreshing',async()=>{
 const a=await visit();
 try{
  await goto(a.page,'commerce');
  assert.equal(await a.page.locator('[data-nav=commerce]').getAttribute('aria-current'),'page');
  await goto(a.page,'board');
  assert.equal(await a.page.locator('[data-nav=commerce]').getAttribute('aria-current'),null);
 }finally{await a.context.close();}
});
test('commerce search, category filtering and empty state',async()=>{
 const a=await visit();
 try{
  await goto(a.page,'commerce');assert.equal(await a.page.locator('.product-card').count(),6);
  await a.page.locator('[data-category=Lighting]').click();assert.equal(await a.page.locator('.product-card').count(),2);
  await a.page.locator('#product-search').fill('bar');assert.equal(await a.page.locator('.product-card').count(),1);
  await a.page.locator('#product-search').fill('unmatched-xxxx');
  assert.equal(await a.page.locator('#product-empty').isVisible(),true);
  await a.page.locator('#reset-products').click();assert.equal(await a.page.locator('.product-card').count(),6);
 }finally{await a.context.close();}
});
test('local cart arithmetic uses real increment and decrement controls',async()=>{
 const a=await visit();
 try{
  await goto(a.page,'commerce');
  await a.page.getByRole('button',{name:'Add Arc study lamp to bag'}).click();
  await a.page.getByRole('button',{name:'Add Form no. 02 to bag'}).click();
  assert.equal(await a.page.locator('#cart-count').textContent(),'2');
  await a.page.locator('#open-cart').click();
  assert.equal(await a.page.locator('#cart-subtotal').textContent(),'$126.00');
  await a.page.getByRole('button',{name:'Increase quantity of Arc study lamp'}).click();
  assert.equal(await a.page.locator('#cart-subtotal').textContent(),'$210.00');
  await a.page.getByRole('button',{name:'Decrease quantity of Arc study lamp'}).click();
  assert.equal(await a.page.locator('#cart-subtotal').textContent(),'$126.00');
 }finally{await a.context.close();}
});
test('checkout explicitly simulates a transaction, never charging money',async()=>{
 const a=await visit();const foreign=[];
 a.page.on('request',r=>{if(!r.url().startsWith(origin))foreign.push(r.url())});
 try{
  await goto(a.page,'commerce');await a.page.locator('#open-cart').click();
  assert.equal(await a.page.locator('#checkout-button').isDisabled(),true);
  await a.page.locator('#close-cart').click();
  await a.page.getByRole('button',{name:'Add Arc study lamp to bag'}).click();
  await a.page.locator('#open-cart').click();await a.page.locator('#checkout-button').click();
  assert.match(await a.page.locator('#toast').textContent(),/No payment occurred/);
  assert.equal(await a.page.locator('#cart-count').textContent(),'0');
  assert.deepEqual(foreign,[]);
 }finally{await a.context.close();}
});
test('Escape closes cart dialog and restores focus',async()=>{
 const a=await visit();
 try{
  await goto(a.page,'commerce');await a.page.locator('#open-cart').focus();
  await a.page.keyboard.press('Enter');
  await a.page.locator('#cart-dialog:visible').waitFor();await a.page.keyboard.press('Escape');
  assert.equal(await a.page.locator('#cart-dialog').isVisible(),false);
  assert.equal(await a.page.locator('#open-cart').evaluate(e=>e===document.activeElement),true);
 }finally{await a.context.close();}
});
test('workflow cards move between stages using native selects',async()=>{
 const a=await visit();
 try{
  await goto(a.page,'board');
  const task=a.page.locator('.task-card').filter({hasText:'Map the information hierarchy'});
  await task.locator('select').selectOption('done');
  assert.equal(await a.page.locator('[data-list=done] .task-card').count(),3);
  assert.equal(await a.page.locator('[data-list=planned] .task-card').count(),1);
 }finally{await a.context.close();}
});
test('workflow task creation validates then inserts a live card',async()=>{
 const a=await visit();
 try{
  await goto(a.page,'board');await a.page.locator('#add-task').click();
  await a.page.locator('#task-form button[type=submit]').click();
  assert.equal(await a.page.locator('#task-error').isVisible(),true);
  await a.page.locator('#task-name').fill('Test focus states');
  await a.page.locator('#task-form button[type=submit]').click();
  assert.equal(await a.page.locator('#task-dialog').isVisible(),false);
  assert.match(await a.page.locator('#board-summary').textContent(),/7 items/);
  assert.match(await a.page.locator('[data-list=planned]').textContent(),/Test focus states/);
 }finally{await a.context.close();}
});
test('messaging switches threads and sends a locally stored message',async()=>{
 const a=await visit();
 try{
  await goto(a.page,'messages');assert.equal(await a.page.locator('.message-row').count(),3);
  await a.page.getByRole('button',{name:'Open conversation with Leo Park'}).click();
  assert.equal(await a.page.locator('.message-row').count(),2);
  await a.page.locator('#chat-input').fill('A direct, local message');
  await a.page.locator('#chat-input').press('Enter');
  assert.equal(await a.page.locator('.message-row').count(),3);
  assert.match(await a.page.locator('#chat-log').textContent(),/A direct, local message/);
 }finally{await a.context.close();}
});
test('hostile markup remains literal text in sent messages',async()=>{
 const a=await visit();
 try{
  await goto(a.page,'messages');
  await a.page.locator('#chat-input').fill('<img src=x onerror=alert(1)>');
  await a.page.locator('#chat-input').press('Enter');
  assert.equal(await a.page.locator('#chat-log img').count(),0);
  assert.match(await a.page.locator('#chat-log').textContent(),/<img src=x/);
 }finally{await a.context.close();}
});
test('pricing period and selected demo plan are functional',async()=>{
 const a=await visit();
 try{
  await goto(a.page,'launch');assert.match(await a.page.locator('#pricing-grid').textContent(),/\$19.00/);
  await a.page.locator('[data-period=yearly]').click();
  assert.match(await a.page.locator('#pricing-grid').textContent(),/\$15.00/);
  await a.page.getByRole('button',{name:'Choose Team'}).click();
  assert.match(await a.page.locator('.pricing-card[data-selected=true]').textContent(),/Team/);
 }finally{await a.context.close();}
});
test('onboarding is guided, validates and completes without collecting personal data',async()=>{
 const a=await visit();
 try{
  await goto(a.page,'launch');await a.page.locator('#wizard-next').click();
  assert.match(await a.page.locator('#toast').textContent(),/Choose a role/);
  await a.page.getByRole('button',{name:/Builder · Make it work/}).click();
  await a.page.locator('#wizard-next').click();
  await a.page.getByRole('button',{name:/Launch a useful project/}).click();
  await a.page.locator('#wizard-next').click();
  await a.page.locator('#wizard-next').click();
  assert.match(await a.page.locator('#wizard-body').textContent(),/No account was created/);
  await a.page.locator('#wizard-next').click();
  assert.match(await a.page.locator('#wizard-step-label').textContent(),/STEP 01/);
 }finally{await a.context.close();}
});
test('component demo provides real feedback and text field validation',async()=>{
 const a=await visit();
 try{
  await goto(a.page,'components');await a.page.locator('#demo-confirm').click();
  assert.match(await a.page.locator('#toast').textContent(),/Interaction confirmed/);
  await a.page.locator('#demo-field').fill('Sample system');
  await a.page.locator('#demo-form button[type=submit]').click();
  assert.match(await a.page.locator('#demo-feedback').textContent(),/Validated locally/);
 }finally{await a.context.close();}
});
test('token export creates a JSON file with original design values',async()=>{
 const a=await visit();
 try{
  await goto(a.page,'components');
  const downloadPromise=a.page.waitForEvent('download');
  await a.page.locator('#download-tokens').click();
  const download=await downloadPromise;
  assert.equal(download.suggestedFilename(),'ui-atlas-tokens.json');
  const stream=await download.createReadStream();let content='';
  for await(const part of stream)content+=part.toString('utf8');
  const parsed=JSON.parse(content);
  assert.equal(parsed.colors.accent,'#e2775b');
  assert.equal(parsed.colors.ink,'#202d2b');
 }finally{await a.context.close();}
});
test('dark mode survives reload; synthetic cart state does not',async()=>{
 const a=await visit();
 try{
  await goto(a.page,'commerce');
  await a.page.getByRole('button',{name:'Add Arc study lamp to bag'}).click();
  await a.page.locator('#theme-toggle').click();
  assert.equal(await a.page.locator('body').getAttribute('data-theme'),'dark');
  await a.page.reload();await goto(a.page,'commerce');
  assert.equal(await a.page.locator('body').getAttribute('data-theme'),'dark');
  assert.equal(await a.page.locator('#cart-count').textContent(),'0');
  const keys=await a.page.evaluate(()=>Object.keys(localStorage));
  assert.deepEqual(keys,['ui-atlas.theme.v1']);
 }finally{await a.context.close();}
});
test('slash shortcut focuses product search without clicking',async()=>{
 const a=await visit();
 try{
  await a.page.locator('body').click({position:{x:3,y:3}});
  await a.page.keyboard.press('/');
  await a.page.locator('#product-search:visible').waitFor();
  assert.equal(await a.page.locator('#product-search').evaluate(e=>e===document.activeElement),true);
 }finally{await a.context.close();}
});
test('all visible buttons have accessible names and no external assets load',async()=>{
 const a=await visit(390),external=[];
 a.page.on('request',req=>{if(!req.url().startsWith(origin))external.push(req.url())});
 try{
  for(const view of VIEWS){
   await goto(a.page,view);
   const unknown=await a.page.locator('button:visible').evaluateAll(nodes=>nodes.filter(e=>
     !(e.getAttribute('aria-label')||e.getAttribute('title')||e.textContent||'').trim()).map(e=>e.outerHTML.slice(0,90)));
   assert.deepEqual(unknown,[],view);
  }
  assert.deepEqual(external,[]);
  assert.deepEqual(a.errors,[]);
 }finally{await a.context.close();}
});
test('reduced motion preference remains usable on small phones',async()=>{
 const a=await visit(320,{reducedMotion:'reduce'});
 try{
  assert.equal(await a.page.evaluate(()=>matchMedia('(prefers-reduced-motion: reduce)').matches),true);
  await goto(a.page,'launch');
  assert.equal(await noOverflow(a.page),true);
  assert.deepEqual(a.errors,[]);
 }finally{await a.context.close();}
});
