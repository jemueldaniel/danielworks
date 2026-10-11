/** HTTP browser regression suite; requires installed Chromium/Edge and root Playwright dependency.
 * Do not count these tests as passed until they have executed on a supported host. */
import test,{before,after} from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {promises as fs,existsSync} from 'node:fs';
import {dirname,resolve,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../../examples/flow_lab');
const allow=new Map([['/','index.html'],['/index.html','index.html'],['/styles.css','styles.css'],['/app.mjs','app.mjs'],['/model.mjs','model.mjs']]);
let browser,server,origin;
before(async()=>{
 server=createServer(async(req,res)=>{
  const pathname=(req.url||'/').split('?')[0],name=allow.get(pathname);
  if(!name||req.method!=='GET'){res.writeHead(404,{'Content-Length':'0'});return res.end()}
  try{const bytes=await fs.readFile(join(root,name));
   res.writeHead(200,{'Content-Type':name.endsWith('.html')?'text/html; charset=utf-8':name.endsWith('.css')?'text/css; charset=utf-8':'text/javascript; charset=utf-8',
    'Content-Length':bytes.length,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',
    'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'none'; img-src 'self' data:; object-src 'none'; base-uri 'none'; form-action 'none'"});res.end(bytes)
  }catch{res.writeHead(500,{'Content-Length':'0'});res.end()}
 });
 await new Promise((resolveStart,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolveStart)});
 origin='http://127.0.0.1:'+server.address().port;
 const binary=process.env.BROWSER_PATH||(process.platform==='win32'?'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe':'/usr/bin/chromium');
 assert.ok(existsSync(binary),'A locally installed browser is required; do not download one');
 browser=await chromium.launch({executablePath:binary,headless:true,args:process.platform==='linux'?['--no-sandbox']:[]});
 console.log(JSON.stringify({browser:await browser.version(),origin:'loopback-only'}));
});
after(async()=>{await browser?.close();if(server)await new Promise(done=>server.close(done))});
async function visit(width=1280){
 const context=await browser.newContext({viewport:{width,height:900},acceptDownloads:true});
 const page=await context.newPage();page.setDefaultTimeout(8000);
 const errors=[],foreign=[];
 page.on('pageerror',error=>errors.push(error.message));
 page.on('request',request=>{if(!request.url().startsWith(origin))foreign.push(request.url())});
 await page.goto(origin+'/');await page.locator('.node-card').first().waitFor();
 return {context,page,errors,foreign};
}
async function noPageOverflow(page){return page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)}
test('responsive 320 / 390 / 768 / 1024 / 1440 without document overflow',async()=>{
 for(const width of [320,390,768,1024,1440]){const a=await visit(width);
  try{assert.equal(await noPageOverflow(a.page),true,`overflow at ${width}`);assert.deepEqual(a.errors,[])}finally{await a.context.close()}}
});
test('semantic editor, actions, original graph and no network dependencies',async()=>{
 const a=await visit();try{
  assert.equal(await a.page.getByRole('main').count(),1);
  assert.equal(await a.page.getByRole('complementary',{name:'Node inspector'}).count(),1);
  assert.equal(await a.page.locator('.node-card').count(),5);
  assert.equal(await a.page.locator('#metricEdges').textContent(),'4');
  assert.deepEqual(a.errors,[]);assert.deepEqual(a.foreign,[]);
 }finally{await a.context.close()}
});
test('accessible modal creates real node and restores focus on submit',async()=>{
 const a=await visit();try{
  await a.page.locator('#addBtn').focus();await a.page.locator('#addBtn').click();
  await a.page.locator('#nodeTitle').fill('Synthetic system check');
  await a.page.locator('#nodeDetail').fill('Safe data only');
  await a.page.locator('#addForm button[type=submit]').click();
  assert.equal(await a.page.locator('.node-card').count(),6);
  assert.equal(await a.page.locator('#addBtn').evaluate(e=>e===document.activeElement),true);
 }finally{await a.context.close()}
});
test('Escape dismisses native dialog and restores focus',async()=>{
 const a=await visit();try{
  await a.page.locator('#helpBtn').focus();await a.page.locator('#helpBtn').click();
  assert.equal(await a.page.locator('#helpDialog').evaluate(e=>e.open),true);
  await a.page.keyboard.press('Escape');
  assert.equal(await a.page.locator('#helpDialog').evaluate(e=>e.open),false);
  assert.equal(await a.page.locator('#helpBtn').evaluate(e=>e===document.activeElement),true);
 }finally{await a.context.close()}
});
test('invalid cycle cannot modify the graph',async()=>{
 const a=await visit();try{
  await a.page.locator('[data-id=n5]').click();
  await a.page.locator('#targetNode').selectOption('n1');
  await a.page.getByRole('button',{name:'Create connection'}).click();
  assert.match(await a.page.locator('#toast').textContent(),/graph_cycle/);
  assert.equal(await a.page.locator('#metricEdges').textContent(),'4');
 }finally{await a.context.close()}
});
test('node property edits render untrusted markup only as literal text',async()=>{
 const a=await visit();try{
  await a.page.locator('[data-id=n3]').click();
  await a.page.locator('#inspectTitle').fill('<img src=x onerror=alert(1)>');
  await a.page.locator('#inspectorForm button[type=submit]').click();
  assert.equal(await a.page.locator('#nodes img').count(),0);
  assert.match(await a.page.locator('[data-id=n3]').textContent(),/<img src=x/);
  assert.deepEqual(a.errors,[]);
 }finally{await a.context.close()}
});
test('node movement through keyboard and undo/redo preserves graph state',async()=>{
 const a=await visit();try{
  const node=a.page.locator('[data-id=n3]');await node.focus();
  const previous=await node.evaluate(e=>parseInt(e.style.left));
  await a.page.keyboard.press('ArrowRight');
  assert.equal(await node.evaluate(e=>parseInt(e.style.left)),previous+20);
  await a.page.keyboard.press('Control+z');
  assert.equal(await node.evaluate(e=>parseInt(e.style.left)),previous);
  await a.page.keyboard.press('Control+Shift+z');
  assert.equal(await node.evaluate(e=>parseInt(e.style.left)),previous+20);
 }finally{await a.context.close()}
});
test('dragged card updates its coordinate and can be undone',async()=>{
 const a=await visit();try{
  const node=a.page.locator('[data-id=n3]');
  const before=await node.evaluate(e=>parseInt(e.style.left));
  const box=await node.boundingBox();assert.ok(box);
  await a.page.mouse.move(box.x+20,box.y+20);
  await a.page.mouse.down();await a.page.mouse.move(box.x+88,box.y+50,{steps:6});await a.page.mouse.up();
  const after=await node.evaluate(e=>parseInt(e.style.left));
  assert.ok(after>before,`${before} -> ${after}`);
  await a.page.locator('#undoBtn').click();assert.equal(await node.evaluate(e=>parseInt(e.style.left)),before);
 }finally{await a.context.close()}
});
test('command palette supports keyboard filtering and compact mode',async()=>{
 const a=await visit();try{
  await a.page.keyboard.press('Control+k');
  assert.equal(await a.page.locator('#commandDialog').evaluate(e=>e.open),true);
  await a.page.locator('#commandQuery').fill('compact');
  assert.equal(await a.page.locator('#commandItems button').count(),1);
  await a.page.keyboard.press('Enter');
  assert.equal(await a.page.locator('body').evaluate(e=>e.classList.contains('compact')),true);
 }finally{await a.context.close()}
});
test('preferences survive reload in the same browser context',async()=>{
 const a=await visit();try{
  await a.page.locator('#themeToggle').click();
  await a.page.reload();await a.page.locator('.node-card').first().waitFor();
  assert.equal(await a.page.locator('body').getAttribute('data-theme'),'dark');
 }finally{await a.context.close()}
});
test('downloads a real, parseable versioned JSON graph',async()=>{
 const a=await visit();try{
  const event=a.page.waitForEvent('download');await a.page.locator('#railExport').click();
  const download=await event;
  assert.equal(download.suggestedFilename(),'flow-lab-public-diagram.json');
  const json=JSON.parse(await fs.readFile(await download.path(),'utf8'));
  assert.equal(json.version,1);assert.equal(json.nodes.length,5);
  assert.equal(json.edges.length,4);assert.deepEqual(a.foreign,[]);
 }finally{await a.context.close()}
});
test('file import rejects malformed content and preserves graph',async()=>{
 const a=await visit();try{
  await a.page.locator('#importFile').setInputFiles({name:'malformed.json',mimeType:'application/json',buffer:Buffer.from('{no')});
  assert.match(await a.page.locator('#toast').textContent(),/invalid_import/);
  assert.equal(await a.page.locator('#metricNodes').textContent(),'5');
 }finally{await a.context.close()}
});
test('valid roundtrip import recreates generated graph',async()=>{
 const a=await visit();try{
  await a.page.locator('#addBtn').click();await a.page.locator('#nodeTitle').fill('Added original step');
  await a.page.locator('#addForm button[type=submit]').click();
  const blob=await a.page.evaluate(async()=>{
   const link=document.createElement('a');link.id='temp-download';link.href='x';return localStorage.getItem('flow-laboratory-public-v1')
  });
  assert.ok(blob);
  const obj=JSON.parse(blob).graph;
  await a.page.locator('#resetBtn').click();
  await a.page.locator('#importFile').setInputFiles({name:'safe.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(obj))});
  assert.equal(await a.page.locator('#metricNodes').textContent(),'6');
 }finally{await a.context.close()}
});
