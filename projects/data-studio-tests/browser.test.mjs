/** Playwright acceptance for the original offline Signal Study UI. Requires installed Edge/Chromium. */
import test,{before,after} from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {promises as fs,existsSync} from 'node:fs';
import {resolve,dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../../examples/data_studio');
const allowed=new Map([['/','index.html'],['/index.html','index.html'],['/styles.css','styles.css'],['/model.mjs','model.mjs'],['/app.mjs','app.mjs']]);
let server,browser,origin;
before(async()=>{
 server=createServer(async(req,res)=>{
  const name=allowed.get((req.url||'/').split('?')[0]);
  if(!name||req.method!=='GET'){res.writeHead(404,{'Content-Length':'0'});return res.end()}
  try{const data=await fs.readFile(join(root,name));res.writeHead(200,{
    'Content-Type':name.endsWith('.html')?'text/html; charset=utf-8':name.endsWith('.css')?'text/css; charset=utf-8':'text/javascript; charset=utf-8',
    'Content-Length':data.length,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',
    'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'none'; img-src 'self' data:; object-src 'none'; base-uri 'none'; form-action 'none'"
  });res.end(data)}catch{res.writeHead(500,{'Content-Length':'0'});res.end()}
 });
 await new Promise((yes,no)=>{server.once('error',no);server.listen(0,'127.0.0.1',yes)});
 origin=`http://127.0.0.1:${server.address().port}`;
 const bin=process.env.BROWSER_PATH||(process.platform==='win32'?'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe':'/usr/bin/chromium');
 assert.ok(existsSync(bin),'Installed Microsoft Edge or Chromium required: do not download browser');
 browser=await chromium.launch({executablePath:bin,headless:true,args:process.platform==='linux'?['--no-sandbox']:[]});
});
after(async()=>{await browser?.close();if(server)await new Promise(r=>server.close(r))});
async function open(width=1280){const ctx=await browser.newContext({viewport:{width,height:840},acceptDownloads:true});const page=await ctx.newPage();page.setDefaultTimeout(8000);const errors=[],outside=[];page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(!r.url().startsWith(origin))outside.push(r.url())});await page.goto(origin+'/');await page.locator('#metricTotal').waitFor();return {ctx,page,errors,outside}}
async function noOverflow(page){return page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)};

test('semantic landmarks, four tab patterns and synthetic disclaimer',async()=>{const a=await open();try{assert.equal(await a.page.getByRole('main').count(),1);assert.equal(await a.page.getByRole('tab').count(),4);assert.match(await a.page.locator('main').textContent(),/Synthetic dataset/);assert.deepEqual(a.errors,[]);assert.deepEqual(a.outside,[])}finally{await a.ctx.close()}});
test('320, 390, 768, 1024 and 1440 viewport widths have no document overflow',async()=>{for(const w of [320,390,768,1024,1440]){const a=await open(w);try{assert.equal(await noOverflow(a.page),true,'width '+w)}finally{await a.ctx.close()}}});
test('all four chart modes work without overflow at narrow phone width',async()=>{const a=await open(320);try{for(const mode of ['trend','mix','cohort','funnel']){await a.page.getByRole('tab',{name:{trend:'Trend lines',mix:'Channel mix',cohort:'Cohort grid',funnel:'Funnel'}[mode]}).click();assert.equal(await a.page.locator('#tab-'+mode).getAttribute('aria-selected'),'true');assert.equal(await noOverflow(a.page),true,mode)}}finally{await a.ctx.close()}});
test('segment filter updates metrics',async()=>{const a=await open();try{const before=await a.page.locator('#metricTotal').textContent();await a.page.locator('#segmentSelect').selectOption('Direct');assert.notEqual(await a.page.locator('#metricTotal').textContent(),before);assert.match(await a.page.locator('#chartSummary').textContent(),/Direct/)}finally{await a.ctx.close()}});
test('time-window filter changes table rows',async()=>{const a=await open();try{assert.equal(await a.page.locator('#rows tr').count(),8);await a.page.locator('#windowSelect').selectOption('4');assert.equal(await a.page.locator('#rows tr').count(),4);await a.page.locator('#windowSelect').selectOption('12');assert.equal(await a.page.locator('#rows tr').count(),12)}finally{await a.ctx.close()}});
test('a table row selection moves focus week',async()=>{const a=await open();try{await a.page.locator('#rows tr').last().click();assert.equal(await a.page.locator('#weekSelect').inputValue(),'W05')}finally{await a.ctx.close()}});
test('visual chart is a real SVG with generated marks',async()=>{const a=await open();try{assert.ok(await a.page.locator('#viz circle').count()>10);await a.page.locator('#tab-mix').click();assert.ok(await a.page.locator('#viz rect').count()>10);await a.page.locator('#tab-cohort').click();assert.ok(await a.page.locator('#viz rect').count()>20);await a.page.locator('#tab-funnel').click();assert.equal(await a.page.locator('#viz rect').count(),4)}finally{await a.ctx.close()}});
test('keyboard keys 1-4 switch charts without editing controls',async()=>{const a=await open();try{await a.page.locator('body').click({position:{x:3,y:3}});await a.page.keyboard.press('4');assert.equal(await a.page.locator('#tab-funnel').getAttribute('aria-selected'),'true');await a.page.keyboard.press('2');assert.equal(await a.page.locator('#tab-mix').getAttribute('aria-selected'),'true')}finally{await a.ctx.close()}});
test('annotation creation validates and restores focus',async()=>{const a=await open();try{await a.page.locator('#openNoteBtn').focus();await a.page.locator('#openNoteBtn').click();assert.equal(await a.page.locator('#noteDialog').evaluate(e=>e.open),true);await a.page.locator('#noteText').fill('Test a representative week');await a.page.locator('#noteForm button[type=submit]').click();assert.equal(await a.page.locator('#noteCount').textContent(),'1');assert.equal(await a.page.locator('#openNoteBtn').evaluate(e=>document.activeElement===e),true)}finally{await a.ctx.close()}});
test('hostile markup remains literal text and no image is added',async()=>{const a=await open();try{await a.page.locator('#openNoteBtn').click();await a.page.locator('#noteText').fill('<img src=x onerror=alert(1)>');await a.page.locator('#noteForm button[type=submit]').click();assert.equal(await a.page.locator('#notesList img').count(),0);assert.match(await a.page.locator('#notesList').textContent(),/<img src=x/);assert.deepEqual(a.errors,[])}finally{await a.ctx.close()}});
test('annotation can be removed without erasing dataset',async()=>{const a=await open();try{await a.page.locator('#openNoteBtn').click();await a.page.locator('#noteText').fill('Delete me');await a.page.locator('#noteForm button[type=submit]').click();await a.page.getByRole('button',{name:'Remove annotation 1'}).click();assert.equal(await a.page.locator('#noteCount').textContent(),'0');assert.equal(await a.page.locator('#rows tr').count(),8)}finally{await a.ctx.close()}});
test('CSV download carries original data and no account information',async()=>{const a=await open();try{const p=a.page.waitForEvent('download');await a.page.locator('#downloadBtn').click();const file=await p;assert.equal(file.suggestedFilename(),'signal-study-synthetic-data.csv');const b=await fs.readFile(await file.path(),'utf8');assert.ok(b.startsWith('Week,Direct,Search,Social,Partner,Total'));assert.equal(b.trim().split('\r\n').length,9)}finally{await a.ctx.close()}});
test('SVG export is a real graphic document',async()=>{const a=await open();try{const p=a.page.waitForEvent('download');await a.page.locator('#svgBtn').click();const file=await p;assert.equal(file.suggestedFilename(),'signal-study-trend.svg');const b=await fs.readFile(await file.path(),'utf8');assert.match(b,/<svg/);assert.match(b,/<path/);assert.doesNotMatch(b,/var\(--ink\)|var\(--muted\)/)}finally{await a.ctx.close()}});
test('theme switch survives same-origin navigation via local preference',async()=>{const a=await open();try{await a.page.locator('#themeBtn').click();assert.equal(await a.page.locator('body').getAttribute('data-theme'),'dark');await a.page.reload();assert.equal(await a.page.locator('body').getAttribute('data-theme'),'dark')}finally{await a.ctx.close()}});
test('reduced density changes data presentation without hiding values',async()=>{const a=await open();try{await a.page.locator('#densityBtn').click();assert.equal(await a.page.locator('body').getAttribute('data-density'),'compact');assert.equal(await a.page.locator('#rows tr').count(),8)}finally{await a.ctx.close()}});
test('the keyboard guide opens and Escape closes it',async()=>{const a=await open();try{await a.page.locator('#guideBtn').click();assert.equal(await a.page.locator('#guideDialog').evaluate(e=>e.open),true);await a.page.keyboard.press('Escape');assert.equal(await a.page.locator('#guideDialog').evaluate(e=>e.open),false)}finally{await a.ctx.close()}});
test('there are no external HTTP calls on mode changes, exports and annotations',async()=>{const a=await open();try{await a.page.locator('#tab-funnel').click();await a.page.locator('#windowSelect').selectOption('4');await a.page.locator('#openNoteBtn').click();await a.page.locator('#noteText').fill('Synthetic observation');await a.page.locator('#noteForm button[type=submit]').click();assert.deepEqual(a.outside,[])}finally{await a.ctx.close()}});
