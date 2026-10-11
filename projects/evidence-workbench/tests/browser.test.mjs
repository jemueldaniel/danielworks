import test,{before,after} from 'node:test';
import assert from 'node:assert/strict';
import {existsSync} from 'node:fs';
import {stack} from './helpers.mjs';
let system,browser;
before(async()=>{
  system=await stack();
  const {chromium}=await import('playwright');
  const executablePath=process.env.BROWSER_PATH??(process.platform==='win32'?'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe':'/usr/bin/chromium');
  assert.ok(existsSync(executablePath),'an admitted installed browser is required; no automatic browser download');
  browser=await chromium.launch({executablePath,headless:true,args:process.platform==='linux'?['--no-sandbox']:[]});
  console.log(JSON.stringify({browser:await browser.version(),viewports:[{width:1280,height:800},{width:390,height:844}]}));
});
after(async()=>{await browser?.close();await system?.close()});

test('real browser renders the workbench, keyboard flow and mobile layout',async()=>{
  for(const viewport of [{width:1280,height:800},{width:390,height:844}]){
    const context=await browser.newContext({viewport});const page=await context.newPage();page.setDefaultTimeout(5000);
    try{
      await page.goto(system.url);await page.getByRole('heading',{name:'Evaluation workbench',exact:true}).waitFor();
      await page.getByLabel('Retrieval engine').focus();await page.keyboard.press('ArrowDown');await page.keyboard.press('Tab');await page.keyboard.press('Tab');
      assert.equal(await page.getByRole('button',{name:'Queue evaluation',exact:true}).evaluate(el=>el===document.activeElement),true);
      await page.keyboard.press('Enter');await page.getByText('Evaluation queued.',{exact:true}).waitFor();
      assert.ok(await page.locator('[data-job-key]').count()>=1);
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),true);
      const button=page.getByRole('button',{name:'Inspect run'}).first();await button.click();
      await page.getByRole('dialog').waitFor();await page.keyboard.press('Escape');
      assert.equal(await page.getByRole('dialog').count(),0);
      assert.equal(await button.evaluate(el=>el===document.activeElement),true);
    }finally{await context.close()}
  }
});
test('browser submission is completed through MCP and restored after backend restart',async()=>{
  const {WorkbenchMcpClient}=await import('../dist/mcp-client.js');
  const context=await browser.newContext();const page=await context.newPage();page.setDefaultTimeout(5000);
  const client=await WorkbenchMcpClient.connect(system.url+'/mcp/operator');
  try{
    await page.goto(system.url);await page.getByRole('button',{name:'Queue evaluation',exact:true}).click();
    await page.getByText('Evaluation queued.',{exact:true}).waitFor();
    // Drain at most three jobs submitted by this bounded suite, not an unbounded worker.
    for(let i=0;i<3;i++)await client.workOnce();
    await page.getByRole('button',{name:'Refresh runs',exact:true}).click();
    await page.locator('[data-state="done"]').first().waitFor();
    await page.locator('[data-state="done"]').first().getByRole('button',{name:'Inspect run'}).click();
    await page.getByText('MRR@2: 0.800',{exact:true}).waitFor();await page.keyboard.press('Escape');
    await system.stopBackend();await page.getByRole('button',{name:'Refresh runs',exact:true}).click();
    await page.getByText('Backend unavailable. Previous results are retained.',{exact:true}).waitFor();
    assert.ok(await page.locator('[data-state="done"]').count()>0);
    await system.restartBackend();await page.getByRole('button',{name:'Refresh runs',exact:true}).click();
    await page.getByText('Runs refreshed.',{exact:true}).waitFor();
    assert.ok(await page.locator('[data-state="done"]').count()>0);
  }finally{await client.close();await context.close()}
});
test('lost response after a real commit reconciles without duplicate writes',async()=>{
  const context=await browser.newContext();const page=await context.newPage();page.setDefaultTimeout(5000);let dropped=false;
  try{
    await page.route('**/api/operator/jobs',async route=>{
      if(route.request().method()==='POST'&&!dropped){dropped=true;const committed=await route.fetch();assert.equal(committed.status(),200);await route.abort('failed')}
      else await route.continue();
    });
    await page.goto(system.url);await page.getByRole('button',{name:'Queue evaluation',exact:true}).click();
    await page.getByText('Outcome unknown. Inspect the saved request before retrying.',{exact:true}).waitFor();
    const saved=await page.evaluate(()=>JSON.parse(localStorage.getItem('workbench.pending.v1')));
    await page.reload();await page.getByText('Unresolved request restored. Inspect before retrying.',{exact:true}).waitFor();
    await page.getByRole('button',{name:'Inspect saved request',exact:true}).click();
    await page.getByText('Saved request found. No duplicate was sent.',{exact:true}).waitFor();
    const response=await fetch(system.url+'/api/operator/jobs/'+saved.key);assert.equal(response.status,200);
    assert.equal(await page.evaluate(()=>localStorage.getItem('workbench.pending.v1')),null);
    const list=await fetch(system.url+'/api/operator/jobs?limit=20').then(x=>x.json());
    assert.equal(list.items.filter(x=>x.key===saved.key).length,1);
  }finally{await context.close()}
});
test('offline submission survives reload and requires an explicit same-key retry',async()=>{
  const context=await browser.newContext({viewport:{width:390,height:844}});const page=await context.newPage();page.setDefaultTimeout(5000);
  try{
    await page.goto(system.url);await page.getByRole('button',{name:'Queue evaluation',exact:true}).waitFor();
    await context.setOffline(true);await page.getByRole('button',{name:'Queue evaluation',exact:true}).click();
    await page.getByText('Outcome unknown. Inspect the saved request before retrying.',{exact:true}).waitFor();
    const saved=await page.evaluate(()=>JSON.parse(localStorage.getItem('workbench.pending.v1')));
    await context.setOffline(false);await page.reload();await page.getByRole('button',{name:'Inspect saved request',exact:true}).click();
    await page.getByText('Request not found. Retry uses the same key and payload.',{exact:true}).waitFor();
    await page.getByRole('button',{name:'Retry saved request',exact:true}).click();
    await page.getByText('Evaluation queued.',{exact:true}).waitFor();
    const response=await fetch(system.url+'/api/operator/jobs/'+saved.key);assert.equal(response.status,200);
  }finally{await context.close()}
});

test('loading is visible while a real list request is delayed',{timeout:15000},async()=>{
  const context=await browser.newContext();const page=await context.newPage();page.setDefaultTimeout(5000);
  let release;const gate=new Promise(resolve=>{release=resolve});
  try{
    await page.route('**/api/operator/jobs?limit=20',async route=>{await gate;await route.continue()});
    await page.goto(system.url);
    await page.getByText('Loading runs…',{exact:true}).waitFor();
    assert.equal(await page.getByRole('button',{name:'Refresh runs',exact:true}).isDisabled(),true);
    assert.equal(await page.getByRole('button',{name:'Work next run',exact:true}).isDisabled(),true);
    release();await page.getByText('Ready. All inputs are synthetic.',{exact:true}).waitFor();
    assert.equal(await page.getByRole('button',{name:'Refresh runs',exact:true}).isEnabled(),true);
  }finally{release();await context.close()}
});

test('an invalid persisted browser request cannot become a mutation',{timeout:15000},async()=>{
  const context=await browser.newContext();const page=await context.newPage();page.setDefaultTimeout(5000);let writes=0;
  await context.addInitScript(()=>localStorage.setItem('workbench.pending.v1',JSON.stringify({key:'damaged',engine:'fts5',k:2,tenant:'other'})));
  page.on('request',request=>{if(request.method()==='POST'&&request.url().endsWith('/jobs'))writes++});
  try{
    await page.goto(system.url);await page.getByText('Saved request is invalid. No request was sent.',{exact:true}).waitFor();
    assert.equal(await page.getByRole('button',{name:'Queue evaluation',exact:true}).isDisabled(),true);
    await page.getByRole('button',{name:'Discard invalid saved request',exact:true}).click();
    assert.equal(writes,0);assert.equal(await page.evaluate(()=>localStorage.getItem('workbench.pending.v1')),null);
    assert.equal(await page.getByRole('button',{name:'Queue evaluation',exact:true}).isEnabled(),true);
  }finally{await context.close()}
});

test('mobile cancellation persists and the modal makes background controls inert',{timeout:15000},async()=>{
  const context=await browser.newContext({viewport:{width:390,height:844}});const page=await context.newPage();page.setDefaultTimeout(5000);
  try{
    await page.goto(system.url);
    const response=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/api/operator/jobs'));
    await page.getByRole('button',{name:'Queue evaluation',exact:true}).click();
    const key=(await (await response).json()).key;
    await page.getByText('Evaluation queued.',{exact:true}).waitFor();
    const row=page.locator(`[data-job-key="${key}"]`);
    await row.getByRole('button',{name:'Inspect run'}).click();await page.getByRole('dialog').waitFor();
    await page.getByLabel('Retrieval engine').evaluate(element=>element.focus());
    assert.equal(await page.getByRole('dialog').evaluate(element=>element.contains(document.activeElement)),true);
    await page.keyboard.press('Escape');await row.getByRole('button',{name:'Cancel run'}).click();
    await page.getByText('Run cancellation recorded.',{exact:true}).waitFor();
    assert.equal((await fetch(system.url+'/api/operator/jobs/'+key).then(r=>r.json())).state,'cancelled');
    await page.reload();await page.locator(`[data-job-key="${key}"][data-state="cancelled"]`).waitFor();
  }finally{await context.close()}
});
