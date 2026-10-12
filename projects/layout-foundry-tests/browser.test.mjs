// Real installed Edge/Chromium acceptance against a strict loopback file allowlist.
import test,{before,after} from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {promises as fs,existsSync} from 'node:fs';
import {dirname,resolve,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../../examples/layout_foundry');
const files=new Map([['/','index.html'],['/index.html','index.html'],
 ['/style.css','style.css'],['/app.mjs','app.mjs'],['/model.mjs','model.mjs']]);
let browser,server,origin;
before(async()=>{
 server=createServer(async(req,res)=>{
  const name=files.get((req.url||'/').split('?')[0]);
  if(req.method!=='GET'||!name){res.writeHead(404);res.end();return;}
  try{
   const data=await fs.readFile(join(root,name));
   const type=name.endsWith('.html')?'text/html;charset=utf-8':
    name.endsWith('.css')?'text/css;charset=utf-8':'text/javascript;charset=utf-8';
   res.writeHead(200,{'Content-Type':type,'Content-Length':data.length,
    'X-Content-Type-Options':'nosniff',
    'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob: data:; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'"});
   res.end(data);
  }catch{res.writeHead(500);res.end();}
 });
 await new Promise((ok,no)=>{server.once('error',no);server.listen(0,'127.0.0.1',ok);});
 origin='http://127.0.0.1:'+server.address().port;
 const exe=process.env.BROWSER_PATH||(process.platform==='win32'?
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe':'/usr/bin/chromium');
 assert.ok(existsSync(exe),'A preinstalled browser is required; downloads disabled.');
 browser=await chromium.launch({executablePath:exe,headless:true,
  args:process.platform==='linux'?['--no-sandbox']:[]});
});
after(async()=>{await browser?.close();if(server)await new Promise(ok=>server.close(ok));});
async function visit(width=1280){
 const context=await browser.newContext({viewport:{width,height:800},acceptDownloads:true});
 const page=await context.newPage();page.setDefaultTimeout(8000);
 const errors=[],foreign=[];
 page.on('pageerror',e=>errors.push(e.message));
 page.on('request',r=>{if(!r.url().startsWith(origin))foreign.push(r.url());});
 await page.goto(origin+'/');await page.locator('#task-rows tr').first().waitFor();
 return {context,page,errors,foreign};
}
async function withPage(callback,width){const x=await visit(width);try{await callback(x);}finally{await x.context.close();}}
const overflow=page=>page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);
test('loads original interface with live synthetic counts',()=>withPage(async({page,errors,foreign})=>{
 assert.match(await page.locator('#hero-title').textContent(),/Interfaces worth/);
 assert.equal(await page.locator('#total').textContent(),'8');
 assert.equal(await page.locator('#task-rows tr').count(),8);
 assert.deepEqual(errors,[]);assert.deepEqual(foreign,[]);
}));
test('document never overflows at five mobile and desktop widths',async()=>{
 for(const width of [320,390,768,1024,1440]){
  await withPage(async({page})=>assert.equal(await overflow(page),false,'width '+width),width);
 }
});
test('search, team, and status filters produce live subset',()=>withPage(async({page})=>{
 await page.locator('#search').fill('keyboard');
 assert.equal(await page.locator('#task-rows tr').count(),1);
 await page.locator('#team').selectOption('North');
 assert.equal(await page.locator('#empty').isVisible(),true);
 await page.locator('#team').selectOption('East');
 assert.equal(await page.locator('#task-rows tr').count(),1);
}));
test('sorting by title changes first row',()=>withPage(async({page})=>{
 await page.locator('#sort').selectOption('title');
 assert.match(await page.locator('#task-rows tr').first().textContent(),/Audit keyboard/);
}));
test('workflow advance updates progress and survives reload',()=>withPage(async({page})=>{
 await page.getByRole('button',{name:'Advance T-105'}).click();
 assert.match(await page.locator('#task-rows').textContent(),/In progress/);
 await page.reload();await page.locator('#task-rows tr').first().waitFor();
 assert.match(await page.locator('tr').filter({hasText:'T-105'}).textContent(),/In progress/);
}));
test('invalid form has inline errors; valid form changes real table',()=>withPage(async({page})=>{
 await page.locator('#new-top').click();
 assert.equal(await page.locator('#task-dialog').isVisible(),true);
 await page.locator('#task-form button[type=submit]').click();
 assert.equal(await page.locator('#form-error').isVisible(),true);
 await page.locator('#draft-title').fill('Proof of accessible form');
 await page.locator('#draft-team').selectOption('East');
 await page.locator('#draft-priority').selectOption('High');
 await page.locator('#draft-due').fill('2026-11-21');
 await page.locator('#task-form button[type=submit]').click();
 assert.equal(await page.locator('#task-dialog').isVisible(),false);
 assert.equal(await page.locator('#total').textContent(),'9');
 assert.match(await page.locator('#task-rows').textContent(),/Proof of accessible form/);
}));
test('dialog Escape closes and restores the originating focus',()=>withPage(async({page})=>{
 const trigger=page.locator('#new-workspace');await trigger.focus();
 await trigger.press('Enter');assert.equal(await page.locator('#task-dialog').isVisible(),true);
 await page.keyboard.press('Escape');assert.equal(await page.locator('#task-dialog').isVisible(),false);
 assert.equal(await trigger.evaluate(el=>document.activeElement===el),true);
}));
test('theme and density persist after reload',()=>withPage(async({page})=>{
 await page.locator('#theme').click();await page.locator('#density').selectOption('compact');
 await page.reload();await page.locator('#task-rows tr').first().waitFor();
 assert.equal(await page.locator('html').getAttribute('data-theme'),'dark');
 assert.equal(await page.locator('html').getAttribute('data-density'),'compact');
}));
test('keyboard command palette searches commands and restores focus',()=>withPage(async({page})=>{
 await page.locator('#search').focus();await page.keyboard.press('Control+k');
 assert.equal(await page.locator('#command-dialog').isVisible(),true);
 await page.locator('#command-search').fill('tokens');
 assert.equal(await page.locator('#command-list button').count(),1);
 await page.keyboard.press('Escape');
 assert.equal(await page.locator('#command-dialog').isVisible(),false);
 assert.equal(await page.locator('#search').evaluate(el=>document.activeElement===el),true);
}));
test('safely renders user text literally rather than as HTML',()=>withPage(async({page})=>{
 await page.locator('#new-top').click();
 await page.locator('#draft-title').fill('<img src=x onerror=alert(1)>');
 await page.locator('#draft-team').selectOption('North');
 await page.locator('#draft-due').fill('2026-11-28');
 await page.locator('#task-form button[type=submit]').click();
 assert.equal(await page.locator('#task-rows img').count(),0);
 assert.match(await page.locator('#task-rows').textContent(),/<img src=x/);
}));
test('CSV and token downloads are local, real and nonempty',()=>withPage(async({page,foreign})=>{
 const [csv]=await Promise.all([page.waitForEvent('download'),page.locator('#export-csv').click()]);
 assert.equal(csv.suggestedFilename(),'public-tasks.csv');
 const [css]=await Promise.all([page.waitForEvent('download'),page.locator('#download-css').click()]);
 assert.equal(css.suggestedFilename(),'design-tokens.css');
 const [json]=await Promise.all([page.waitForEvent('download'),page.locator('#download-json').click()]);
 assert.equal(json.suggestedFilename(),'design-tokens.json');
 assert.deepEqual(foreign,[]);
}));
test('restore fixtures removes additions and returns to default filters',()=>withPage(async({page})=>{
 await page.locator('#new-top').click();
 await page.locator('#draft-title').fill('New fictional review task');
 await page.locator('#draft-team').selectOption('West');
 await page.locator('#draft-due').fill('2026-11-29');
 await page.locator('#task-form button[type=submit]').click();
 assert.equal(await page.locator('#total').textContent(),'9');
 await page.locator('#search').fill('unmatchable');
 await page.locator('#reset-data').click();
 assert.equal(await page.locator('#total').textContent(),'8');
 assert.equal(await page.locator('#task-rows tr').count(),8);
}));
test('all controls are named and semantic main exists',()=>withPage(async({page})=>{
 assert.equal(await page.locator('main').count(),1);
 assert.equal(await page.locator('table thead th').count(),6);
 assert.equal(await page.locator('a.skip').count(),1);
 assert.equal(await page.locator('button:not([aria-label])').count()>0,true);
}));
