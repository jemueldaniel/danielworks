import test from 'node:test';
import assert from 'node:assert/strict';
import {
 FIXTURES,createState,readPreferences,savedPreferences,reduce,addRecord,
 derive,nextId,exportCsv,csvCell,STATUSES,CATEGORIES,SECTIONS,PAGE_SIZE
} from './model.mjs';

const fresh=()=>createState();

test('fixture is synthetic and bounded',()=>{
 assert.equal(FIXTURES.length,12);
 assert.equal(new Set(FIXTURES.map(x=>x.id)).size,12);
 assert.equal(PAGE_SIZE,5);
});
test('default view has coherent page and status counts',()=>{
 const view=derive(fresh());
 assert.deepEqual(view.counters,{total:12,active:5,review:3,complete:4});
 assert.equal(view.totalPages,3);
 assert.equal(view.records.length,5);
});
test('input state is independently copied',()=>{
 const rows=FIXTURES.map(r=>({...r}));
 const result=createState(rows);
 rows[0].title='untrusted changed value';
 assert.notEqual(result.records[0].title,rows[0].title);
});
test('source fixtures remain frozen',()=>assert.equal(Object.isFrozen(FIXTURES[0]),true));
test('query searches title without case sensitivity',()=>{
 const state=reduce(fresh(),{type:'QUERY',value:'KEYBOARD'});
 assert.deepEqual(derive(state).records.map(r=>r.id),['item-002']);
});
test('query searches owners and category',()=>{
 assert.equal(derive(reduce(fresh(),{type:'QUERY',value:'Jordan'})).filteredCount,1);
 assert.ok(derive(reduce(fresh(),{type:'QUERY',value:'Accessibility'})).filteredCount>=3);
});
test('query never mutates source records',()=>{
 const state=fresh(),copy=JSON.stringify(state.records);
 derive(reduce(state,{type:'QUERY',value:'ui'}));
 assert.equal(JSON.stringify(state.records),copy);
});
test('status filter returns only active rows',()=>{
 const view=derive(reduce(fresh(),{type:'STATUS',value:'active'}));
 assert.equal(view.filteredCount,5);
 assert.ok(view.records.every(r=>r.status==='active'));
});
test('status filter counts do not change global metrics',()=>{
 const view=derive(reduce(fresh(),{type:'STATUS',value:'review'}));
 assert.equal(view.counters.total,12);
 assert.equal(view.counters.active,5);
});
test('combined status and query is intersected',()=>{
 const state=reduce(reduce(fresh(),{type:'STATUS',value:'complete'}),{type:'QUERY',value:'contrast'});
 assert.deepEqual(derive(state).records.map(r=>r.id),['item-005']);
});
test('no results are distinguishable from an error',()=>{
 const view=derive(reduce(fresh(),{type:'QUERY',value:'an-unmatched-needle'}));
 assert.equal(view.filteredCount,0);
 assert.equal(view.showingFrom,0);
 assert.equal(view.showingTo,0);
 assert.equal(view.totalPages,1);
});
test('updated sorting uses deterministic latest first',()=>{
 assert.equal(derive(fresh()).records[0].id,'item-007');
});
test('title sorting ascending',()=>{
 const view=derive(reduce(fresh(),{type:'SORT',value:'title'}));
 assert.equal(view.records[0].title,'Color contrast study');
});
test('effort sorting highest first',()=>{
 const view=derive(reduce(fresh(),{type:'SORT',value:'effort'}));
 assert.equal(view.records[0].effort,9);
});
test('second page contains different entries and correct range',()=>{
 const state=reduce(fresh(),{type:'PAGE',value:2}),view=derive(state);
 assert.equal(view.page,2);
 assert.equal(view.showingFrom,6);
 assert.equal(view.showingTo,10);
});
test('last page clamps number of rows',()=>{
 const view=derive(reduce(fresh(),{type:'PAGE',value:3}));
 assert.equal(view.records.length,2);
 assert.equal(view.showingTo,12);
});
test('page is reset when query changes',()=>{
 const state=reduce(reduce(fresh(),{type:'PAGE',value:3}),{type:'QUERY',value:'audit'});
 assert.equal(state.page,1);
});
test('large requested page safely clamps view',()=>{
 assert.equal(derive(reduce(fresh(),{type:'PAGE',value:999})).page,3);
});
test('invalid action and filter values fail closed',()=>{
 for(const action of [{type:'UNKNOWN'},{type:'STATUS',value:'secret'},
                       {type:'SORT',value:'prototype'}, {type:'PAGE',value:0},
                       {type:'SECTION',value:'private'}, {type:'THEME',value:'auto'},
                       {type:'DENSITY',value:'none'}]){
   assert.throws(()=>reduce(fresh(),action),RangeError);
 }
});
test('button-like boolean cannot be used as page',()=>{
 assert.throws(()=>reduce(fresh(),{type:'PAGE',value:true}),RangeError);
});
test('preferences allow only supported theme and density',()=>{
 assert.deepEqual(readPreferences({theme:'dark',density:'compact'}),{theme:'dark',density:'compact'});
 assert.deepEqual(readPreferences({theme:'secrets',density:'invalid'}),
                  {theme:'light',density:'comfortable'});
});
test('malformed preferences retain safe defaults',()=>{
 for(const data of [null,42,'bad',[],{'__proto__':'oops'}]){
  assert.deepEqual(readPreferences(data),{theme:'light',density:'comfortable'});
 }
});
test('saved preferences contain no records or user input',()=>{
 const prefs=savedPreferences({...fresh(),theme:'dark'});
 assert.deepEqual(prefs,{theme:'dark',density:'comfortable'});
});
test('next record ID avoids existing records',()=>assert.equal(nextId(fresh().records),'item-013'));
test('new record enters library and increments counters',()=>{
 const state=addRecord(fresh(),{title:'Dialog accessibility',owner:'Alex Morgan',
                               category:'Accessibility',status:'active',effort:'5'});
 assert.equal(state.records.length,13);
 assert.equal(state.section,'library');
 assert.equal(derive(state).counters.active,6);
 assert.equal(state.records.at(-1).id,'item-013');
});
test('adding does not mutate original collection',()=>{
 const before=fresh(),after=addRecord(before,{title:'Focus test',owner:'Alex Morgan',
                                             category:'Interface',status:'review',effort:1});
 assert.equal(before.records.length,12);
 assert.equal(after.records.length,13);
});
test('new title and owner are trimmed',()=>{
 const state=addRecord(fresh(),{title:'  New interface  ',owner:'  Test Person ',
                               category:'Interface',status:'active',effort:2});
 assert.equal(state.records.at(-1).title,'New interface');
 assert.equal(state.records.at(-1).owner,'Test Person');
});
test('invalid record fields are rejected',()=>{
 for(const field of [
  {title:'',owner:'Alex',category:'Interface',status:'active',effort:3},
  {title:'Valid',owner:'',category:'Interface',status:'active',effort:3},
  {title:'Valid',owner:'Alex',category:'Unknown',status:'active',effort:3},
  {title:'Valid',owner:'Alex',category:'Interface',status:'unknown',effort:3},
  {title:'Valid',owner:'Alex',category:'Interface',status:'active',effort:0},
  {title:'Valid',owner:'Alex',category:'Interface',status:'active',effort:41},
  {title:'Valid',owner:'Alex',category:'Interface',status:'active',effort:'bad'}
 ])assert.throws(()=>addRecord(fresh(),field),RangeError);
});
test('untrusted title with markup remains literal model data',()=>{
 const state=addRecord(fresh(),{title:'<script>alert(1)</script>',
                    owner:'Alex',category:'Interface',status:'active',effort:2});
 assert.match(state.records.at(-1).title,/^<script>/);
});
test('duplicate IDs rejected at creation',()=>{
 const rows=FIXTURES.slice(0,2).map(r=>({...r}));
 rows[1].id=rows[0].id;
 assert.throws(()=>createState(rows),/invalid_records/);
});
test('unsafe fixture control characters rejected',()=>{
 const rows=FIXTURES.slice(0,2).map(r=>({...r}));
 rows[1].owner='Text\nInjection';
 assert.throws(()=>createState(rows),/invalid_records/);
});
test('invalid fixture date rejected',()=>{
 const rows=FIXTURES.slice(0,2).map(r=>({...r}));
 rows[1].updated='tomorrow';
 assert.throws(()=>createState(rows),/invalid_records/);
});
test('over-capacity fixtures rejected',()=>assert.throws(()=>
 createState(Array.from({length:101},(_,i)=>({...FIXTURES[0],id:'item-'+String(i).padStart(3,'0')}))),RangeError));
test('CSV export includes header and all records even when filtered',()=>{
 const csv=exportCsv(reduce(fresh(),{type:'STATUS',value:'complete'}));
 assert.ok(csv.startsWith('"ID","Title","Owner"'));
 assert.equal(csv.split('\r\n').filter(Boolean).length,13);
});
test('CSV escapes formula injection prefixes',()=>{
 for(const value of ['=1+1','+SUM(A1)','-8','@danger',' =evil'])
  assert.ok(csvCell(value).startsWith('"\''));
});
test('CSV escapes quoted fields',()=>assert.equal(csvCell('a"b'),'"a""b"'));
test('CSV export line endings are deterministic',()=>{
 const csv=exportCsv(fresh());
 assert.equal(csv.endsWith('\r\n'),true);
 assert.equal(csv.replaceAll('\r\n','').includes('\n'),false);
});
test('CSV full output changes if source changes',()=>{
 const base=fresh();
 const altered=addRecord(base,{title:'New test',owner:'Alex',category:'Systems',status:'review',effort:4});
 assert.notEqual(exportCsv(base),exportCsv(altered));
});
test('known sections are exactly the interactive views',()=>{
 assert.deepEqual(SECTIONS,['overview','library','activity','settings']);
});
test('categories and statuses are closed allowlists',()=>{
 assert.equal(CATEGORIES.length,4);
 assert.deepEqual(STATUSES,['active','review','complete']);
});
