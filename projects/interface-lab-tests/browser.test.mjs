/** Real Chromium/Edge acceptance for an original static interface. No cloud access. */
import test,{before,after} from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile,stat} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {chromium} from 'playwright';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../examples/interface_lab');
const allow=new Map([
  ['/','index.html'],['/index.html','index.html'],
  ['/style.css','style.css'],['/model.mjs','model.mjs'],['/app.mjs','app.mjs']
]);
let server,browser,origin;
before(async()=>{
  server=createServer(async(req,res)=>{
    const route=req.url?.split('?')[0]||'/';
    const name=allow.get(route);
    if(!name){res.writeHead(404,{'Content-Length':'0'});res.end();return;}
    try{
      const file=await readFile(path.join(root,name));
      res.writeHead(200,{
        'Content-Type':name.endsWith('.css')?'text/css':name.endsWith('.mjs')?
          'text/javascript':'text/html; charset=utf-8',
        'Content-Length':file.length,
        'Cache-Control':'no-store',
        'X-Content-Type-Options':'nosniff',
        'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; object-src 'none'; base-uri 'none'"
      });
      res.end(file);
    }catch{res.writeHead(500);res.end();}
  });
  await new Promise((resolve,reject)=>{
    server.once('error',reject);
    server.listen(0,'127.0.0.1',resolve);
  });
  origin='http://127.0.0.1:'+server.address().port;
  const executablePath=process.env.BROWSER_PATH||
    (process.platform==='win32'?'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe':'/usr/bin/chromium');
  assert.ok(existsSync(executablePath),'A locally installed browser is required. No browser downloads.');
  browser=await chromium.launch({executablePath,headless:true,args:process.platform==='linux'?['--no-sandbox']:[]});
  console.log(JSON.stringify({interfaceLabBrowser:await browser.version(),source:'local public examples/interface_lab'}));
});
after(async()=>{
  await browser?.close();
  await new Promise(resolve=>server?.close(resolve)??resolve());
});
const setup=async(viewport={width:1280,height:800},options={})=>{
  const context=await browser.newContext({viewport,acceptDownloads:true,...options});
  const page=await context.newPage();
  page.setDefaultTimeout(5000);
  await page.goto(origin);
  await page.locator('#metric-total').waitFor();
  return {page,context};
};
const exit=async({context})=>context.close();

test('desktop and mobile layouts never overflow',async()=>{
  for(const viewport of [
    {width:1440,height:900},{width:1024,height:768},
    {width:768,height:900},{width:390,height:844},{width:320,height:640}
  ]){
    const app=await setup(viewport);
    try{
      assert.equal(await app.page.locator('#page-title').textContent(),'Workspace overview');
      assert.equal(await app.page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),
                   true,'unexpected horizontal overflow at '+viewport.width);
      assert.equal(await app.page.locator('#metric-total').textContent(),'12');
      assert.equal(await app.page.locator('#metric-active').textContent(),'5');
    }finally{await exit(app);}
  }
});
test('mobile navigation opens, routes and closes',async()=>{
  const app=await setup({width:390,height:844});
  try{
    const {page}=app;
    const menu=page.getByRole('button',{name:'Open navigation'});
    assert.equal(await menu.isVisible(),true);
    await menu.click();
    assert.equal(await page.getByRole('button',{name:'Close navigation'}).getAttribute('aria-expanded'),'true');
    await page.getByRole('navigation',{name:'Primary navigation'}).getByRole('button',{name:/Library/}).click();
    assert.equal(await page.locator('#page-title').textContent(),'Work item library');
    assert.equal(await page.getByRole('button',{name:'Open navigation'}).getAttribute('aria-expanded'),'false');
    assert.equal(await page.locator('#nav-backdrop').isVisible(),false);
  }finally{await exit(app);}
});
test('keyboard navigation and search shortcut are reachable',async()=>{
  const app=await setup();
  try{
    const {page}=app;
    await page.keyboard.press('/');
    assert.equal(await page.evaluate(()=>document.activeElement?.id),'record-search');
    await page.getByRole('searchbox',{name:'Search work items'}).fill('contrast');
    assert.equal(await page.locator('#table-body tr').count(),1);
    assert.match(await page.locator('#table-body').textContent(),/Color contrast study/);
  }finally{await exit(app);}
});
test('filter, sort and pagination modify real table state',async()=>{
  const app=await setup();
  try{
    const {page}=app;
    await page.getByRole('button',{name:/Library/}).click();
    assert.equal(await page.locator('#table-body tr').count(),5);
    await page.getByRole('button',{name:'Next page'}).click();
    assert.match(await page.locator('#range-info').textContent(),/6–10 of 12/);
    await page.locator('#record-sort').selectOption('effort');
    assert.match(await page.locator('#table-body tr').first().textContent(),/Reusable component contracts/);
    await page.locator('button[data-status="review"]').click();
    assert.equal(await page.locator('#table-body tr').count(),3);
    await page.getByRole('searchbox',{name:'Search work items'}).fill('missing-item-xyz');
    assert.equal(await page.getByText('No matching work items').count(),1);
    await page.getByRole('button',{name:'Clear filters'}).click();
    assert.equal(await page.locator('#table-body tr').count(),5);
  }finally{await exit(app);}
});
test('form validation and created item update interface without a backend',async()=>{
  const app=await setup();
  try{
    const {page}=app;
    await page.getByRole('button',{name:'New work item'}).click();
    assert.equal(await page.getByRole('dialog',{name:'New work item'}).isVisible(),true);
    await page.locator('#new-title').fill('Focal contrast checks');
    await page.locator('#new-owner').fill('Demo Engineer');
    await page.locator('#new-category').selectOption('Accessibility');
    await page.locator('#new-status').selectOption('active');
    await page.locator('#new-effort').fill('5');
    await page.getByRole('button',{name:'Create work item'}).click();
    assert.equal(await page.getByRole('dialog',{name:'New work item'}).count(),0);
    assert.equal(await page.locator('#metric-total').textContent(),'13');
    assert.equal(await page.locator('#metric-active').textContent(),'6');
    assert.match(await page.locator('#table-body').textContent(),/Focal contrast checks/);
    assert.equal(await page.getByText('Work item created locally.').count(),1);
  }finally{await exit(app);}
});
test('invalid form submission provides a visible, nonleaking error',async()=>{
  const app=await setup();
  try{
    const {page}=app;
    await page.getByRole('button',{name:'New work item'}).click();
    await page.locator('#new-title').fill('');
    await page.locator('#new-owner').fill('');
    await page.getByRole('button',{name:'Create work item'}).click();
    assert.equal(await page.locator('#record-error').isVisible(),true);
    assert.equal(await page.locator('#metric-total').textContent(),'12');
  }finally{await exit(app);}
});
test('native dialog Escape restores focus to originating button',async()=>{
  const app=await setup();
  try{
    const {page}=app;
    const open=page.getByRole('button',{name:'New work item'});
    await open.focus();
    await page.keyboard.press('Enter');
    await page.getByRole('dialog',{name:'New work item'}).waitFor();
    await page.keyboard.press('Escape');
    assert.equal(await page.getByRole('dialog',{name:'New work item'}).count(),0);
    assert.equal(await open.evaluate(el=>el===document.activeElement),true);
  }finally{await exit(app);}
});
test('command palette keyboard access and focus handling',async()=>{
  const app=await setup();
  try{
    const {page}=app;
    await page.keyboard.press('Control+k');
    assert.equal(await page.getByRole('dialog',{name:'Quick actions'}).isVisible(),true);
    await page.getByRole('dialog',{name:'Quick actions'}).getByRole('button',{name:/Explore the library/}).click();
    assert.equal(await page.locator('#page-title').textContent(),'Work item library');
    await page.keyboard.press('n');
    assert.equal(await page.getByRole('dialog',{name:'New work item'}).isVisible(),true);
  }finally{await exit(app);}
});
test('theme and compact preferences survive reload only',async()=>{
  const app=await setup();
  try{
    const {page}=app;
    await page.getByRole('button',{name:'Switch to dark theme'}).click();
    assert.equal(await page.locator('body').getAttribute('data-theme'),'dark');
    await page.getByRole('button',{name:/Settings/}).click();
    await page.locator('#setting-density').selectOption('compact');
    await page.reload();
    assert.equal(await page.locator('body').getAttribute('data-theme'),'dark');
    assert.equal(await page.locator('body').getAttribute('data-density'),'compact');
    const values=await page.evaluate(()=>JSON.parse(localStorage.getItem('interface-lab.preferences.v1')));
    assert.deepEqual(values,{theme:'dark',density:'compact'});
  }finally{await exit(app);}
});
test('settings restore defaults and do not persist private records',async()=>{
  const app=await setup();
  try{
    const {page}=app;
    await page.getByRole('button',{name:/Settings/}).click();
    await page.locator('#setting-theme').selectOption('dark');
    await page.getByRole('button',{name:'Restore defaults'}).click();
    assert.equal(await page.locator('body').getAttribute('data-theme'),'light');
    assert.equal(await page.locator('body').getAttribute('data-density'),'comfortable');
    const persisted=await page.evaluate(()=>localStorage.getItem('interface-lab.preferences.v1'));
    assert.ok(!persisted.includes('owner')&&!persisted.includes('records'));
  }finally{await exit(app);}
});
test('CSV export is a real browser download',async()=>{
  const app=await setup();
  try{
    const {page}=app;
    await page.getByRole('button',{name:/Library/}).click();
    const ready=page.waitForEvent('download');
    await page.getByRole('button',{name:/Export CSV/}).click();
    const file=await ready;
    assert.equal(file.suggestedFilename(),'interface-laboratory-sample.csv');
    const stream=await file.createReadStream();
    let data='';
    for await(const chunk of stream)data+=chunk.toString('utf8');
    assert.match(data,/"ID","Title","Owner"/);
    assert.match(data,/Keyboard navigation audit/);
  }finally{await exit(app);}
});
test('untrusted markup renders as text, not executable HTML',async()=>{
  const app=await setup();
  try{
    const {page}=app;
    await page.getByRole('button',{name:'New work item'}).click();
    await page.locator('#new-title').fill('<img src=x onerror=alert(1)>');
    await page.locator('#new-owner').fill('Synthetic Author');
    await page.getByRole('button',{name:'Create work item'}).click();
    assert.equal(await page.locator('#table-body img').count(),0);
    assert.match(await page.locator('#table-body').textContent(),/<img src=x onerror=alert\(1\)>/);
  }finally{await exit(app);}
});
test('all visible control buttons have an accessible name',async()=>{
  const app=await setup({width:390,height:844});
  try{
    const {page}=app;
    const unnamed=await page.locator('button:visible').evaluateAll(nodes=>
      nodes.filter(el=>!((el.getAttribute('aria-label')||el.getAttribute('title')||el.textContent||'').trim()))
        .map(el=>el.outerHTML.slice(0,120)));
    assert.deepEqual(unnamed,[]);
  }finally{await exit(app);}
});
test('no external origins or third-party scripts are loaded',async()=>{
  const app=await setup();
  try{
    const {page}=app,resources=await page.evaluate(()=>
      performance.getEntriesByType('resource').map(entry=>entry.name));
    assert.ok(resources.length>0);
    assert.ok(resources.every(uri=>new URL(uri).origin===origin));
    assert.equal(await page.locator('script[src^="https"]').count(),0);
  }finally{await exit(app);}
});
