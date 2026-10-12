/** Real browser acceptance for the public-only technology evidence index.
 * Synthetic classification, no private source, 127.0.0.1 loopback, no network.
 */
import test,{before,after} from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {promises as fs,existsSync} from 'node:fs';
import {dirname,resolve,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';
const folder=resolve(dirname(fileURLToPath(import.meta.url)),'../../examples/technology_atlas');
const allowed=new Map([['/','index.html'],['/index.html','index.html'],['/styles.css','styles.css'],['/app.mjs','app.mjs'],['/model.mjs','model.mjs'],['/data.mjs','data.mjs']]);
let browser,server,origin;
before(async()=>{
 server=createServer(async(req,res)=>{
  const name=allowed.get((req.url||'/').split('?')[0]);
  if(req.method!=='GET'||!name){res.writeHead(404,{'Content-Length':'0'});res.end();return;}
  try{
   const body=await fs.readFile(join(folder,name));
   const type=name.endsWith('html')?'text/html;charset=utf-8':name.endsWith('css')?'text/css;charset=utf-8':'text/javascript;charset=utf-8';
   res.writeHead(200,{'Content-Type':type,'Content-Length':body.length,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'"});
   res.end(body);
  }catch{res.writeHead(500,{'Content-Length':'0'});res.end();}
 });
 await new Promise((yes,no)=>{server.once('error',no);server.listen(0,'127.0.0.1',yes)});
 origin='http://127.0.0.1:'+server.address().port;
 const bin=process.env.BROWSER_PATH||(process.platform==='win32'?'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe':'/usr/bin/chromium');
 assert.ok(existsSync(bin),'Installed Edge/Chromium required; no downloads');
 browser=await chromium.launch({executablePath:bin,headless:true,args:process.platform==='linux'?['--no-sandbox']:[]});
 console.log(JSON.stringify({browser:await browser.version(),origin:'loopback-only'}));
});
after(async()=>{await browser?.close();if(server)await new Promise(yes=>server.close(yes));});
async function visit(width=1280){
 const context=await browser.newContext({viewport:{width,height:800},acceptDownloads:true});
 const page=await context.newPage();page.setDefaultTimeout(7000);
 const errors=[],foreign=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(!r.url().startsWith(origin))foreign.push(r.url());});
 await page.goto(origin+'/');await page.locator('.tech-card').first().waitFor();
 return {page,context,errors,foreign};
}
async function withPage(fn,width=1280){const x=await visit(width);try{await fn(x);}finally{await x.context.close();}}
async function overflow(page){return page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);}
async function cards(page){return page.locator('.tech-card').count();}
test('all public source references exist in the full repository checkout',async()=>{
 const {TECHNOLOGIES}=await import('../../examples/technology_atlas/data.mjs');
 for(const t of TECHNOLOGIES){if(t.source)assert.ok(existsSync(resolve(folder,'../..',t.source)),t.source);}
});
test('catalog renders 87 original classification entries, semantic main and navigation',async()=>withPage(async({page,errors})=>{
 assert.equal(await cards(page),87);assert.equal(await page.locator('main').count(),1);assert.equal(await page.getByRole('navigation',{name:'Primary'}).count(),1);
 assert.equal(await page.locator('#total-count').textContent(),'87');assert.equal(await page.locator('#verified-count').textContent(),'52');
 assert.deepEqual(errors,[]);
}));
test('320, 390, 768, 1024 and 1440 viewport coverage',async()=>{
 for(const width of [320,390,768,1024,1440])await withPage(async({page})=>assert.equal(await overflow(page),false,'overflow at '+width),width);
});
test('narrow phone category controls and dialogs remain within viewport',async()=>withPage(async({page})=>{
 await page.locator('#category-tabs [data-category="AI & Automation"]').click();
 assert.equal(await overflow(page),false);
 await page.getByRole('button',{name:'Inspect Bounded tool agents'}).click();
 assert.equal(await page.locator('#detail-dialog').isVisible(),true);
 assert.equal(await overflow(page),false);
},320));
test('search filters by exact technology without adding markup',async()=>withPage(async({page})=>{
 await page.locator('#search').fill('Solidity');
 assert.ok(await cards(page)>=1);
 assert.match(await page.locator('#result-label').textContent(),/of 87 technologies/);
}));
test('search matches source summaries and is case insensitive',async()=>withPage(async({page})=>{
 await page.locator('#search').fill('bm25');assert.ok(await cards(page)>=1);
 assert.match((await page.locator('.tech-card h3').allTextContents()).join(' '),/Hybrid retrieval/);
}));
test('empty search state is functional and resets without browser reload',async()=>withPage(async({page})=>{
 await page.locator('#search').fill('unfindable-4937258');
 assert.equal(await page.locator('#empty-state').isVisible(),true);
 await page.locator('#empty-reset').click();assert.equal(await cards(page),87);
}));
test('category filter shows only requested discipline',async()=>withPage(async({page})=>{
 const button=page.locator('#category-tabs [data-category="Web3 & Contracts"]');await button.click();
 assert.equal(await button.getAttribute('aria-pressed'),'true');assert.equal(await cards(page),6);
 assert.equal((await page.locator('.tech-category').allTextContents()).every(t=>t==='Web3 & Contracts'),true);
}));
test('tested-level filter excludes source observations',async()=>withPage(async({page})=>{
 await page.locator('#level-filter').selectOption('Public-tested');assert.equal(await cards(page),52);
 assert.equal(await page.locator('.level-label.observed').count(),0);
}));
test('source-observed filter includes only unqualified items',async()=>withPage(async({page})=>{
 await page.locator('#level-filter').selectOption('Source-observed');assert.equal(await cards(page),33);
 assert.equal(await page.locator('.level-label.tested').count(),0);
}));
test('historical qualification remains two references',async()=>withPage(async({page})=>{
 await page.locator('#level-filter').selectOption('Public-historical');assert.equal(await cards(page),2);
}));
test('sort alphabetically by technology name',async()=>withPage(async({page})=>{
 await page.locator('#sort').selectOption('name');
 const names=await page.locator('.tech-card h3').allTextContents();
 assert.deepEqual(names,[...names].sort((a,b)=>a.localeCompare(b)));
}));
test('saved technology survives reload, but untrusted selection does not persist',async()=>withPage(async({page})=>{
 await page.locator('[data-tech="python"] [data-action="save"]').click();
 await page.locator('[data-tech="solidity"] [data-action="select"]').click();
 await page.reload();await page.locator('.tech-card').first().waitFor();
 assert.equal(await page.locator('#selection-tray').isVisible(),false);
 await page.locator('#saved-only').check();assert.equal(await cards(page),1);
 assert.match(await page.locator('.tech-card h3').textContent(),/Python/);
}));
test('light theme persists across same-context page reload',async()=>withPage(async({page})=>{
 await page.locator('#theme-toggle').click();assert.equal(await page.locator('body').getAttribute('data-theme'),'light');
 await page.reload();await page.locator('.tech-card').first().waitFor();assert.equal(await page.locator('body').getAttribute('data-theme'),'light');
}));
test('public technology dialog has real code link and Escape restores focus',async()=>withPage(async({page})=>{
 const trigger=page.getByRole('button',{name:'Inspect TypeScript',exact:true});
 await trigger.focus();await trigger.press('Enter');
 assert.equal(await page.locator('#detail-dialog').isVisible(),true);
 assert.match(await page.locator('#detail-links a').getAttribute('href'),/^https:\/\/github\.com\/jemueldaniel\/danielworks\/blob\/main\//);
 await page.keyboard.press('Escape');
 assert.equal(await page.locator('#detail-dialog').isVisible(),false);
 assert.equal(await trigger.evaluate(x=>x===document.activeElement),true);
}));
test('observed-only technology never reveals a private source link',async()=>withPage(async({page})=>{
 await page.getByRole('button',{name:'Inspect Solidity',exact:true}).click();
 assert.equal(await page.locator('#detail-dialog').isVisible(),true);
 assert.equal(await page.locator('#detail-links a').count(),0);
 assert.match(await page.locator('#detail-links').textContent(),/No public implementation link/);
}));
test('selected mixed stack differentiates public proof from observed code',async()=>withPage(async({page})=>{
 await page.locator('[data-tech="python"] [data-action="select"]').click();
 await page.locator('[data-tech="solidity"] [data-action="select"]').click();
 assert.equal(await page.locator('#selection-tray').isVisible(),true);
 await page.locator('#open-plan').click();
 assert.match(await page.locator('#plan-summary').textContent(),/1 with public source · 1 observed only/);
 assert.equal(await page.locator('#plan-recipe option').count(),1);
 assert.match(await page.locator('#plan-command').textContent(),/--recipe ai-search/);
}));
test('clearing selected stack dismisses selection tray',async()=>withPage(async({page})=>{
 await page.locator('[data-tech="python"] [data-action="select"]').click();
 await page.locator('#clear-selection').click();
 assert.equal(await page.locator('#selection-tray').isVisible(),false);
}));
test('observed-only stack still requires public reference evidence, not fabricated code',async()=>withPage(async({page})=>{
 await page.locator('[data-tech="solidity"] [data-action="select"]').click();
 await page.locator('#open-plan').click();
 assert.match(await page.locator('#plan-summary').textContent(),/0 with public source · 1 observed only/);
 assert.match(await page.locator('#plan-dialog .fine-print').textContent(),/not proof of every selected technology/);
}));
test('keyboard command palette filters actions and navigates categories',async()=>withPage(async({page})=>{
 await page.keyboard.press('Control+k');
 assert.equal(await page.locator('#command-dialog').isVisible(),true);
 await page.locator('#command-search').fill('Backend');
 await page.locator('#command-results').getByRole('button',{name:'Backend & Data'}).click();
 assert.equal(await page.locator('#command-dialog').isVisible(),false);
 assert.equal((await page.locator('.tech-category').allTextContents()).every(t=>t==='Backend & Data'),true);
}));
test('slash shortcut focuses the search input when not typing',async()=>withPage(async({page})=>{
 await page.locator('body').click({position:{x:3,y:3}});
 await page.keyboard.press('/');assert.equal(await page.locator('#search').evaluate(x=>x===document.activeElement),true);
}));
test('browser JSON download contains 87 categorized records and no private paths',async()=>withPage(async({page})=>{
 const pending=page.waitForEvent('download');await page.locator('#download-json').click();const file=await pending;
 assert.equal(file.suggestedFilename(),'danielworks-technology-evidence.json');
 const obj=JSON.parse(await fs.readFile(await file.path(),'utf8'));
 assert.equal(obj.records.length,87);
 assert.ok(obj.records.filter(x=>x.qualification==='Source-observed').every(x=>x.public_source===null));
 assert.equal(obj.private_source_exported,false);
}));
test('browser CSV download quotes headers, source columns and 87 rows',async()=>withPage(async({page})=>{
 const pending=page.waitForEvent('download');await page.locator('#download-csv').click();const file=await pending;
 assert.equal(file.suggestedFilename(),'danielworks-technology-evidence.csv');
 const raw=await fs.readFile(await file.path(),'utf8');
 assert.equal(raw.split('\r\n').filter(Boolean).length,88);
 assert.match(raw,/"Technology","Discipline","Qualification"/);
}));
test('fixed source-pinned one-shot command has no private input',async()=>withPage(async({page})=>{
 await page.locator('#recipe-picker').selectOption('career-portfolio');
 const cmd=await page.locator('#recipe-command').textContent();
 assert.match(cmd,/--recipe career-portfolio/);
 assert.match(cmd,/YOUR_EXTERNALLY_VERIFIED_MANIFEST_SHA256/);
 assert.equal(cmd.includes('private:'),false);
}));
test('hostile search markup is rendered as literal text',async()=>withPage(async({page,errors})=>{
 await page.locator('#search').fill('<img src=x onerror=alert(1)>');
 assert.equal(await page.locator('#tech-grid img').count(),0);
 assert.deepEqual(errors,[]);
}));
test('new native, 3D, data and cache technologies remain source-observed only',async()=>withPage(async({page})=>{
 for(const name of ['Three.js','Redis','Supabase','Tauri']){
  await page.locator('#search').fill(name);
  const card=page.locator('.tech-card').filter({has:page.locator('h3', {hasText:name})});
  assert.ok(await card.count()>=1);
  const exact=page.locator('.tech-card').filter({has:page.getByRole('heading',{name,exact:true})});
  assert.equal(await exact.locator('.level-label.observed').count(),1);
 }
}));
test('all visible buttons have an accessible label or text',async()=>withPage(async({page})=>{
 const blank=await page.locator('button:visible').evaluateAll(elems=>elems.filter(e=>!((e.getAttribute('aria-label')||e.textContent||'').trim())).map(e=>e.outerHTML));
 assert.deepEqual(blank,[]);
}));
test('runtime interactions never call external hosts or analytics',async()=>withPage(async({page,foreign,errors})=>{
 await page.locator('#search').fill('sql');
 await page.locator('#theme-toggle').click();
 await page.locator('#level-filter').selectOption('Public-tested');
 await page.locator('#download-json').click();
 assert.deepEqual(foreign,[]);assert.deepEqual(errors,[]);
}));
