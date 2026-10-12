import test from 'node:test';
import assert from 'node:assert/strict';
import {FIXTURES,TOKENS,TEAMS,STATUSES,PRIORITIES,queryText,safeDate,safeRow,safeRows,
 visibleRows,totals,validateDraft,advance,deleteTicket,safeTokens,tokenJson,tokenCss,
 rowsCsv,saveWorkspace,restoreWorkspace} from './model.mjs';

const copy=()=>FIXTURES.map(x=>({...x}));
const draft={title:'Inspect keyboard focus',team:'North',priority:'Medium',due:'2026-11-20',notes:''};
test('fixture rows are synthetic and valid',()=>{
 assert.equal(FIXTURES.length,8);assert.ok(FIXTURES.every(safeRow));
 assert.equal(new Set(FIXTURES.map(x=>x.id)).size,FIXTURES.length);
});
test('normalization limits query length and handles unicode',()=>{
 assert.equal(queryText('  KeyBOARD '),'keyboard');
 assert.equal(queryText('ＡＢＣ'),'abc');assert.equal(queryText('a'.repeat(100)).length,80);
});
for(const value of ['2026-02-29','2026-13-01','2026-11-31','today',null,123,'2026-2-1']){
 test('invalid dates fail: '+String(value),()=>assert.equal(safeDate(value),false));
}
for(const date of ['2024-02-29','2026-11-30','2000-01-01']){
 test('valid calendar date '+date,()=>assert.equal(safeDate(date),true));
}
test('sanitizer rejects duplicate and malformed rows',()=>{
 const r=safeRows([...copy(),copy()[0],{...copy()[0],id:'x'}]);
 assert.equal(r.length,FIXTURES.length);
});
test('no caller mutation from filtering',()=>{
 const rows=copy(),before=JSON.stringify(rows);
 visibleRows(rows,{sort:'priority',desc:true});assert.equal(JSON.stringify(rows),before);
});
test('filter respects title and team',()=>{
 const x=visibleRows(copy(),{search:'keyboard',team:'East'});
 assert.equal(x.length,1);assert.equal(x[0].id,'T-102');
});
test('invalid team fails closed to no result',()=>assert.deepEqual(visibleRows(copy(),{team:'unknown'}),[]));
for(const sort of ['id','title','team','status','priority','due']){
 test('sorting field: '+sort,()=>{
  const x=visibleRows(copy(),{sort}),y=visibleRows(copy(),{sort,desc:true});
  assert.equal(x.length,8);assert.equal(y.length,8);
  assert.deepEqual(x.map(i=>i.id),y.map(i=>i.id).reverse());
 });
}
test('empty summary has no division by zero',()=>assert.deepEqual(totals([]),
 {total:0,done:0,active:0,review:0,urgent:0,percent:0}));
test('summary counts are calculated',()=>{
 const stats=totals(copy());assert.equal(stats.total,8);assert.equal(stats.done,2);
 assert.equal(stats.active,2);assert.equal(stats.review,2);
});
test('valid draft receives unique identifier',()=>{
 const x=validateDraft(draft,copy());
 assert.equal(x.ok,true);assert.equal(x.ticket.id,'T-109');assert.equal(x.ticket.status,'Planned');
});
for(const change of [
 {title:'x'},{team:'Mystery'},{priority:'Urgent'},
 {due:'2026-02-29'},{notes:'a'.repeat(241)}
]){
 test('invalid draft rejects unsafe input: '+Object.keys(change)[0],()=>{
  const x=validateDraft({...draft,...change},copy());assert.equal(x.ok,false);
 });
}
test('malformed draft fails without throwing',()=>{
 assert.equal(validateDraft(null,copy()).ok,false);
});
test('workspace has bounded capacity',()=>{
 const rows=Array.from({length:120},(_,i)=>({...FIXTURES[0],id:'T-'+(101+i)}));
 assert.equal(validateDraft(draft,rows).ok,false);
});
test('advance follows bounded forward transition',()=>{
 let rows=copy();let first=advance(rows,'T-105');
 assert.equal(first.ok,true);assert.equal(first.rows.find(x=>x.id==='T-105').status,'In progress');
 assert.equal(rows.find(x=>x.id==='T-105').status,'Planned');
 first=advance(first.rows,'T-105');assert.equal(first.rows.find(x=>x.id==='T-105').status,'Review');
 first=advance(first.rows,'T-105');assert.equal(first.rows.find(x=>x.id==='T-105').status,'Done');
 assert.equal(advance(first.rows,'T-105').ok,false);
});
test('transition rejects unknown identifiers',()=>assert.equal(advance(copy(),'T-999').reason,'missing'));
test('deletion is scoped to selected id',()=>{
 const rows=copy();assert.equal(deleteTicket(rows,'T-101').length,7);assert.equal(rows.length,8);
});
test('tokens reject CSS injection and preserve valid values',()=>{
 assert.deepEqual(safeTokens({hue:'0; background:url(evil)',radius:100,density:'invalid'}),
 {...TOKENS});assert.equal(safeTokens({hue:0,radius:2,density:'compact',theme:'dark'}).hue,0);
});
test('exported JSON and CSS are parseable and bounded',()=>{
 const json=JSON.parse(tokenJson({hue:327,radius:24}));
 assert.equal(json.tokens.hue,327);assert.match(tokenCss(json.tokens),/--corner: 24px/);
 assert.doesNotMatch(tokenCss({hue:';url(evil)'}),/evil/);
});
test('CSV escapes quotes and prevents spreadsheet formulas',()=>{
 const rows=[{...FIXTURES[0],title:'=SUM(1,2) "unsafe"',notes:'+cmd'}];
 const csv=rowsCsv(rows);assert.match(csv,/\x27=SUM/);
 assert.match(csv,/\x27\+cmd/);assert.match(csv,/""unsafe""/);
});
test('safe workspace round trip preserves canonical state',()=>{
 const rows=copy(),tokens={hue:120,radius:9,density:'compact',theme:'dark'};
 const result=restoreWorkspace(saveWorkspace(rows,tokens));
 assert.equal(result.ok,true);assert.deepEqual(result.rows,rows);assert.deepEqual(result.tokens,tokens);
});
for(const invalid of ['{', '{}','null', '{"schema":9,"rows":[]}', 'x'.repeat(80001)]){
 test('corrupt storage fails safely',()=>{
  const result=restoreWorkspace(invalid);assert.equal(result.ok,false);
  assert.equal(result.rows.length,8);
 });
}
test('recovery drops malformed or duplicate data',()=>{
 const rows=[FIXTURES[0],FIXTURES[0],{...FIXTURES[0],id:'bad'}];
 const result=restoreWorkspace(JSON.stringify({schema:1,rows,tokens:TOKENS}));
 assert.equal(result.ok,true);assert.equal(result.rows.length,1);
});
