/** Real locally served public-only browser acceptance. Requires installed Edge/Chromium and repository Playwright. */
import test,{before,after} from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {promises as fs,existsSync} from 'node:fs';
import {dirname,resolve,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../../examples/proof_gallery');
const allow=new Map([['/','index.html'],['/index.html','index.html'],['/styles.css','styles.css'],['/app.mjs','app.mjs'],['/model.mjs','model.mjs']]);
let server,browser,origin;
before(async()=>{
 server=createServer(async(req,res)=>{
  const key=(req.url||'/').split('?')[0],name=allow.get(key);
  if(req.method!=='GET'||!name){res.writeHead(404,{'Content-Length':'0'});res.end();return;}
  try{const body=await fs.readFile(join(root,name));res.writeHead(200,{'Content-Type':name.endsWith('html')?'text/html;charset=utf-8':name.endsWith('css')?'text/css;charset=utf-8':'text/javascript;charset=utf-8','Content-Length':body.length,'X-Content-Type-Options':'nosniff','Cache-Control':'no-store','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'none'; img-src 'self' data:; object-src 'none'; base-uri 'none'; form-action 'none'"});res.end(body);}
  catch{res.writeHead(500,{'Content-Length':'0'});res.end();}
 });
 await new Promise((ok,no)=>{server.once('error',no);server.listen(0,'127.0.0.1',ok);});
 origin='http://127.0.0.1:'+server.address().port;
 const bin=process.env.BROWSER_PATH||(process.platform==='win32'?'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe':'/usr/bin/chromium');
 assert.ok(existsSync(bin),'An installed browser is required; tests do not download one.');
 browser=await chromium.launch({executablePath:bin,headless:true,args:process.platform==='linux'?['--no-sandbox']:[]});
 console.log(JSON.stringify({browser:await browser.version(),scope:'127.0.0.1 only'}));
});
after(async()=>{if(browser)await browser.close();if(server)await new Promise(resolve=>server.close(resolve));});
async function open(width=1280){
 const context=await browser.newContext({viewport:{width,height:800},acceptDownloads:true});
 const page=await context.newPage();page.setDefaultTimeout(8000);
 const errors=[],external=[];
 page.on('pageerror',e=>errors.push(e.message));
 page.on('request',req=>{if(!req.url().startsWith(origin))external.push(req.url());});
 await page.goto(origin+'/');await page.locator('.proof-card').first().waitFor();
 return {page,context,errors,external};
}
async function withPage(fn,width=1280){const x=await open(width);try{await fn(x);}finally{await x.context.close();}}
async function cards(page){return page.locator('.proof-card').count();}
async function overflow(page){return page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);}
test('one semantic main, labeled navigation, and all public cards',async()=>withPage(async({page,errors})=>{
 assert.equal(await page.getByRole('main').count(),1);
 assert.equal(await page.getByRole('navigation',{name:'Sections'}).count(),1);
 assert.equal(await cards(page),19);
 assert.deepEqual(errors,[]);
}));
test('all five viewport widths avoid document-level horizontal scrolling',async()=>{
 for(const width of [320,390,768,1024,1440])await withPage(async({page})=>assert.equal(await overflow(page),false,'width '+width),width);
});
test('mobile interactions and dialogs avoid horizontal overflow',async()=>withPage(async({page})=>{
 await page.getByRole('button',{name:'Inspect Interactive UI Atlas'}).click();
 assert.equal(await overflow(page),false);
 await page.keyboard.press('Escape');
 await page.getByRole('button',{name:'AI & Data',exact:false}).first().click();
 assert.equal(await overflow(page),false);
},320));
test('catalog search matches a specific original capability',async()=>withPage(async({page})=>{
 await page.locator('#search').fill('migration');
 assert.equal(await cards(page),1);
 assert.match(await page.locator('.proof-card h3').textContent(),/Migration/);
}));
test('search empty state is accessible and resettable',async()=>withPage(async({page})=>{
 await page.locator('#search').fill('missing-query-xyzzzz');
 assert.equal(await page.locator('#empty-state').isVisible(),true);
 await page.locator('#empty-reset').click();
 assert.equal(await cards(page),19);
}));
test('discipline filters work independently from search',async()=>withPage(async({page})=>{
 await page.locator('#category-tabs').getByRole('button',{name:/Security/}).click();
 assert.equal(await cards(page),2);
 assert.equal(await page.locator('#category-tabs').getByRole('button',{name:/Security/}).getAttribute('aria-pressed'),'true');
}));
test('qualification filter protects historical examples',async()=>withPage(async({page})=>{
 await page.locator('#level-filter').selectOption('Historical');
 assert.equal(await cards(page),2);
 assert.equal(await page.locator('.proof-card .level-label').first().textContent(),'Historical');
}));
test('sort is functional without losing all cards',async()=>withPage(async({page})=>{
 await page.locator('#sort').selectOption('title');
 assert.equal(await cards(page),19);
 const titles=await page.locator('.proof-card h3').allTextContents();
 assert.deepEqual(titles,[...titles].sort((a,b)=>a.localeCompare(b)));
}));
test('saving a reference persists after reload',async()=>withPage(async({page})=>{
 await page.getByRole('button',{name:'Save Interactive UI Atlas'}).click();
 await page.reload();
 await page.locator('.proof-card').first().waitFor();
 await page.locator('#saved-only').check();
 assert.equal(await cards(page),1);
 assert.match(await page.locator('.proof-card h3').first().textContent(),/Atlas/);
}));
test('light and dark theme persists after reload',async()=>withPage(async({page})=>{
 await page.locator('#theme-toggle').click();
 assert.equal(await page.locator('body').getAttribute('data-theme'),'light');
 await page.reload();await page.locator('.proof-card').first().waitFor();
 assert.equal(await page.locator('body').getAttribute('data-theme'),'light');
}));
test('case study dialog has real source and test links, Escape restores focus',async()=>withPage(async({page})=>{
 const trigger=page.getByRole('button',{name:'Inspect Interactive UI Atlas'});
 await trigger.focus();await trigger.press('Enter');
 const dialog=page.locator('#detail-dialog');
 assert.equal(await dialog.isVisible(),true);
 assert.match(await page.locator('#detail-source').getAttribute('href'),/^https:\/\/github\.com\/jemueldaniel\/danielworks\/blob\/main\//);
 assert.match(await page.locator('#detail-test').getAttribute('href'),/browser\.test\.mjs$/);
 await page.keyboard.press('Escape');
 assert.equal(await dialog.isVisible(),false);
 assert.equal(await trigger.evaluate(el=>el===document.activeElement),true);
}));
test('comparison collects a bounded public shortlist',async()=>withPage(async({page})=>{
 await page.getByRole('button',{name:'Add to comparison: Interactive UI Atlas'}).click();
 await page.getByRole('button',{name:'Add to comparison: Responsive Interface Lab'}).click();
 assert.equal(await page.locator('#compare-toolbar').isVisible(),true);
 await page.locator('#compare-open').click();
 assert.equal(await page.locator('#compare-dialog').isVisible(),true);
 assert.equal(await page.locator('.compare-item').count(),2);
 await page.keyboard.press('Escape');
 await page.locator('#compare-clear').click();
 assert.equal(await page.locator('#compare-toolbar').isVisible(),false);
}));
test('command palette opens by keyboard and navigates to a discipline',async()=>withPage(async({page})=>{
 await page.keyboard.press('Control+k');
 assert.equal(await page.locator('#command-dialog').isVisible(),true);
 await page.locator('#command-input').fill('Systems');
 await page.locator('#command-results').getByRole('button',{name:/Systems/}).click();
 assert.equal(await page.locator('#command-dialog').isVisible(),false);
 assert.equal(await page.locator('.proof-card .category-label').first().textContent(),'Systems');
}));
test('slash focuses search, outside text entry only',async()=>withPage(async({page})=>{
 await page.locator('body').click({position:{x:3,y:3}});
 await page.keyboard.press('/');
 assert.equal(await page.locator('#search').evaluate(el=>document.activeElement===el),true);
}));
test('JSON download contains only public URLs and statuses',async()=>withPage(async({page})=>{
 const wait=page.waitForEvent('download');await page.locator('#download-json').click();const dl=await wait;
 assert.equal(dl.suggestedFilename(),'danielworks-public-evidence.json');
 const chunks=await fs.readFile(await dl.path(),'utf8');const payload=JSON.parse(chunks);
 assert.equal(payload.capabilities.length,19);
 assert.ok(payload.capabilities.every(x=>x.source.startsWith('https://github.com/jemueldaniel/danielworks/')));
 assert.equal(chunks.includes('D:\\'),false);
}));
test('CSV download preserves quoted table and its count',async()=>withPage(async({page})=>{
 const wait=page.waitForEvent('download');await page.locator('#download-csv').click();const dl=await wait;
 assert.equal(dl.suggestedFilename(),'danielworks-public-evidence.csv');
 const contents=await fs.readFile(await dl.path(),'utf8');
 assert.equal(contents.split('\r\n').filter(Boolean).length,20);
 assert.match(contents,/"Capability","Discipline"/);
}));
test('recipe picker generates a fixed command requiring external pin',async()=>withPage(async({page})=>{
 await page.locator('#recipe-picker').selectOption('visual-analytics');
 const cmd=await page.locator('#recipe-command').textContent();
 assert.match(cmd,/--recipe visual-analytics/);
 assert.match(cmd,/YOUR_EXTERNALLY_VERIFIED_SOURCE_MANIFEST_SHA256/);
 assert.ok(!cmd.includes('powershell'));
}));
test('untrusted search markup remains literal and does not create HTML elements',async()=>withPage(async({page,errors})=>{
 await page.locator('#search').fill('<img src=x onerror=alert(1)>');
 assert.equal(await page.locator('#results img').count(),0);
 assert.deepEqual(errors,[]);
}));
test('no external network requests occur during public UI interactions',async()=>withPage(async({page,external})=>{
 await page.locator('#search').fill('graph');
 await page.locator('#theme-toggle').click();
 await page.locator('#level-filter').selectOption('Browser-tested');
 await page.locator('#download-json').click();
 assert.deepEqual(external,[]);
}));
