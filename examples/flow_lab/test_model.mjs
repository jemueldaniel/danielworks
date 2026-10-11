import test from 'node:test';
import assert from 'node:assert/strict';
import {LIMITS,NODE_TYPES,TEMPLATES,TEMPLATE_EDGES,createState,reduce,stats,topology,validateGraph,graphFrom,exportGraph,nodeConnections,position,positionY} from './model.mjs';
const fresh=()=>createState();
const go=(s,type,value)=>reduce(s,{type,value});
const add=(s,title='Review component',type='process')=>go(s,'ADD_NODE',{title,type,detail:''});
const invalid=(fn,code)=>assert.throws(fn,new RegExp(code));
const isolated=()=>({version:1,nodes:[{id:'n1',type:'source',title:'An input',detail:'',x:0,y:0}],edges:[]});
test('original source contains fixed synthetic fixture without identities',()=>{
 assert.equal(TEMPLATES.length,5);assert.equal(TEMPLATE_EDGES.length,4);
 assert.deepEqual(NODE_TYPES,['source','process','output']);
 assert.ok(TEMPLATES.every(n=>!n.title.includes('@')));
});
test('source fixture produces stable levels and health stats',()=>{
 assert.deepEqual(topology(fresh()),[['n1','n2'],['n3'],['n4'],['n5']]);
 assert.deepEqual(stats(fresh()),{nodes:5,connections:4,stages:4,input:2,output:1});
});
test('initial UI state is offline-friendly and non-authenticated',()=>{
 const s=fresh();assert.equal(s.theme,'light');assert.equal(s.zoom,1);assert.equal(s.grid,true);assert.equal(s.compact,false);
 assert.deepEqual(s.past,[]);assert.deepEqual(s.future,[]);assert.equal(s.user,undefined);
});
test('new states never share mutable fixture object references',()=>{
 const a=fresh(),b=fresh();a.nodes[0].title='changed';assert.notEqual(a.nodes[0].title,b.nodes[0].title);
});
test('select changes current node, not graph history',()=>{
 const s=go(fresh(),'SELECT','n5');assert.equal(s.selected,'n5');assert.equal(s.past.length,0);
});
test('selecting unknown node fails closed',()=>invalid(()=>go(fresh(),'SELECT','missing'),'unknown_node'));
test('null selection supported',()=>assert.equal(go(fresh(),'SELECT',null).selected,null));
test('add source component makes stable id',()=>{
 const s=go(fresh(),'ADD_NODE',{type:'source',title:'Sample collection',detail:'Public-only'});
 assert.equal(s.nodes.at(-1).id,'n6');assert.equal(s.nodes.at(-1).type,'source');assert.equal(s.selected,'n6');
});
test('all types are valid, arbitrary type is not',()=>{
 for(const type of NODE_TYPES)assert.equal(go(fresh(),'ADD_NODE',{type,title:'Example'}).nodes.at(-1).type,type);
 invalid(()=>go(fresh(),'ADD_NODE',{type:'private',title:'Bad'}),'invalid_add');
});
test('add accepts x and y within drawable surface',()=>{
 const s=go(fresh(),'ADD_NODE',{type:'process',title:'On canvas',x:1000,y:600});
 assert.deepEqual([s.nodes.at(-1).x,s.nodes.at(-1).y],[1000,600]);
});
test('adding does not mutate previous graph',()=>{
 const a=fresh(),b=add(a);assert.equal(a.nodes.length,5);assert.equal(b.nodes.length,6);
});
test('invalid empty and too-long titles rejected',()=>{
 for(const title of ['', ' ', 'a', 'x'.repeat(49), '\u0000bad', 'ok\nnewline'])invalid(()=>add(fresh(),title),'invalid_text');
});
test('trimmed title is saved without whitespace',()=>{
 assert.equal(add(fresh(),'  Prepared item  ').nodes.at(-1).title,'Prepared item');
});
test('dangerous markup retained as literal text only',()=>{
 const str='<img src=x onerror=alert(1)>';
 assert.equal(add(fresh(),str).nodes.at(-1).title,str);
});
test('oversized detail rejected',()=>invalid(()=>go(fresh(),'ADD_NODE',{type:'process',title:'Valid',detail:'x'.repeat(111)}),'invalid_text'));
test('node count bound enforced without mutation',()=>{
 let s=fresh();for(let i=s.nodes.length;i<LIMITS.nodes;i++)s=add(s,'New entry');
 assert.equal(s.nodes.length,LIMITS.nodes);invalid(()=>add(s),'invalid_add');
});
test('move changes only one graph coordinate',()=>{
 const a=fresh(),b=go(a,'MOVE_NODE',{id:'n3',x:420,y:170});
 assert.equal(a.nodes.find(n=>n.id==='n3').x,400);
 assert.deepEqual([b.nodes.find(n=>n.id==='n3').x,b.nodes.find(n=>n.id==='n3').y],[420,170]);
});
test('no-op move does not consume undo history',()=>{
 const s=fresh();assert.equal(go(s,'MOVE_NODE',{id:'n3',x:400,y:90}).past.length,0);
});
test('invalid moves rejected',()=>{
 for(const x of [-1,1061,NaN,Infinity,1.2,'1',null])invalid(()=>go(fresh(),'MOVE_NODE',{id:'n3',x,y:20}),'invalid_move');
 invalid(()=>go(fresh(),'MOVE_NODE',{id:'missing',x:20,y:20}),'unknown_node');
});
test('editing title and description updates inspector data',()=>{
 const s=go(fresh(),'UPDATE_NODE',{id:'n2',title:' New label ',detail:' New explanation '});
 assert.equal(s.nodes[1].title,'New label');assert.equal(s.nodes[1].detail,'New explanation');
});
test('editing unknown id is rejected',()=>invalid(()=>go(fresh(),'UPDATE_NODE',{id:'unknown',title:'Valid'}),'unknown_node'));
test('editing node with same data preserves old state',()=>{
 const s=fresh(),n=s.nodes[0];assert.equal(go(s,'UPDATE_NODE',{id:n.id,title:n.title,detail:n.detail}),s);
});
test('delete node removes its incoming and outgoing edges',()=>{
 const s=go(fresh(),'DELETE_NODE','n4');assert.equal(s.nodes.length,4);assert.equal(s.edges.length,1);assert.equal(s.selected,null);
});
test('delete refuses nonexisting id',()=>invalid(()=>go(fresh(),'DELETE_NODE','n19'),'unknown_node'));
test('new connection increments count',()=>{
 const s=go(fresh(),'CONNECT',{from:'n1',to:'n4'});assert.equal(s.edges.length,5);
});
test('duplicate connection rejected',()=>invalid(()=>go(fresh(),'CONNECT',{from:'n1',to:'n3'}),'duplicate_edge'));
test('self connection rejected',()=>invalid(()=>go(fresh(),'CONNECT',{from:'n3',to:'n3'}),'invalid_edge'));
test('unknown connection endpoint rejected',()=>invalid(()=>go(fresh(),'CONNECT',{from:'n3',to:'n123'}),'invalid_edge'));
test('direct cycle is blocked',()=>invalid(()=>go(fresh(),'CONNECT',{from:'n4',to:'n3'}),'graph_cycle'));
test('longer feedback cycle is blocked',()=>invalid(()=>go(fresh(),'CONNECT',{from:'n5',to:'n1'}),'graph_cycle'));
test('valid independent cross-link does not create cycle',()=>{
 assert.equal(go(fresh(),'CONNECT',{from:'n1',to:'n5'}).edges.length,5);
});
test('disconnect removes only one edge',()=>{
 const s=go(fresh(),'DISCONNECT',{from:'n1',to:'n3'});assert.equal(s.edges.length,3);
 assert.ok(!s.edges.some(e=>e.from==='n1'&&e.to==='n3'));
});
test('disconnect unknown edge fails',()=>invalid(()=>go(fresh(),'DISCONNECT',{from:'n1',to:'n5'}),'unknown_edge'));
test('node connection lists are separated correctly',()=>{
 const c=nodeConnections(fresh(),'n4');assert.deepEqual(c.incoming,[{from:'n2',to:'n4'},{from:'n3',to:'n4'}]);
 assert.deepEqual(c.outgoing,[{from:'n4',to:'n5'}]);
});
test('undo reverts a committed edit',()=>{
 const a=fresh(),b=add(a),c=go(b,'UNDO');assert.deepEqual(graphFrom(c),graphFrom(a));
});
test('redo reapplies a committed edit',()=>{
 const b=add(fresh()),c=go(go(b,'UNDO'),'REDO');assert.deepEqual(graphFrom(c),graphFrom(b));
});
test('new edit clears redo chain',()=>{
 let s=add(fresh());s=go(s,'UNDO');s=go(s,'MOVE_NODE',{id:'n1',x:40,y:40});assert.equal(s.future.length,0);
});
test('empty undo and redo are stable no-ops',()=>{
 const s=fresh();assert.equal(go(s,'UNDO'),s);assert.equal(go(s,'REDO'),s);
});
test('bounded history prevents unbounded memory growth',()=>{
 let s=fresh();for(let i=0;i<90;i++)s=go(s,'MOVE_NODE',{id:'n1',x:(i+1)%40*20,y:90});
 assert.equal(s.past.length,LIMITS.history);
});
test('undo across a deletion restores its edges',()=>{
 const s=go(fresh(),'DELETE_NODE','n3'),again=go(s,'UNDO');assert.equal(again.nodes.length,5);assert.equal(again.edges.length,4);
});
test('import roundtrip restores exact graph',()=>{
 let s=add(fresh(),'Another step');s=go(s,'CONNECT',{from:'n5',to:'n6'});
 const t=go(fresh(),'IMPORT',exportGraph(s));assert.deepEqual(graphFrom(t),graphFrom(s));
});
test('import deliberately discards untrusted UI config',()=>{
 const v=JSON.parse(exportGraph(fresh()));v.theme='dark';invalid(()=>go(fresh(),'IMPORT',JSON.stringify(v)),'invalid_graph');
});
test('malformed JSON refused',()=>invalid(()=>go(fresh(),'IMPORT','{not JSON'),'invalid_import'));
test('oversized import is rejected before parsing',()=>invalid(()=>go(fresh(),'IMPORT',' '.repeat(LIMITS.file+1)),'invalid_import'));
test('missing or unknown top-level graph fields rejected',()=>{
 for(const graph of [{nodes:[],edges:[]},{version:1,nodes:[],edges:[],credential:'not-allowed'}])invalid(()=>validateGraph(graph),'invalid_graph');
});
test('invalid numeric position rejected on import',()=>{
 const g=isolated();g.nodes[0].x=Infinity;invalid(()=>validateGraph(g),'invalid_node');
});
test('prototype-like extra node field is rejected',()=>{
 const g=isolated();g.nodes[0].__proto__;g.nodes[0].extra={};invalid(()=>validateGraph(g),'invalid_node');
});
test('duplicate node id blocked on import',()=>{
 const g=isolated();g.nodes.push({...g.nodes[0]});invalid(()=>validateGraph(g),'invalid_node');
});
test('import rejects duplicate edges',()=>{
 const g=JSON.parse(exportGraph(fresh()));g.edges.push({...g.edges[0]});invalid(()=>validateGraph(g),'duplicate_edge');
});
test('import rejects disconnected referential endpoint',()=>{
 const g=JSON.parse(exportGraph(fresh()));g.edges.push({from:'n3',to:'n19'});invalid(()=>validateGraph(g),'invalid_edge');
});
test('import rejects a cycle',()=>{
 const g=JSON.parse(exportGraph(fresh()));g.edges.push({from:'n5',to:'n2'});invalid(()=>validateGraph(g),'graph_cycle');
});
test('import accepts empty graph as a valid blank canvas',()=>{
 const s=go(fresh(),'IMPORT',JSON.stringify({version:1,nodes:[],edges:[]}));assert.deepEqual(stats(s),{nodes:0,connections:0,stages:0,input:0,output:0});
});
test('deleted node does not stay in selection after undo and redo',()=>{
 const s=go(go(fresh(),'DELETE_NODE','n3'),'REDO');assert.equal(s.selected,null);
});
test('reset recreates sample graph and can be undone',()=>{
 const b=add(fresh());const r=go(b,'RESET');assert.equal(r.nodes.length,5);
 assert.equal(go(r,'UNDO').nodes.length,6);
});
test('reset on unchanged sample does not erase history',()=>{
 const s=fresh();assert.equal(go(s,'RESET').past.length,0);
});
test('theme accepts only explicitly supported values',()=>{
 assert.equal(go(fresh(),'THEME','dark').theme,'dark');invalid(()=>go(fresh(),'THEME','private'),'invalid_theme');
});
test('grid and compact accept booleans only',()=>{
 assert.equal(go(fresh(),'GRID',false).grid,false);assert.equal(go(fresh(),'COMPACT',true).compact,true);
 invalid(()=>go(fresh(),'GRID','false'),'invalid_grid');invalid(()=>go(fresh(),'COMPACT',0),'invalid_compact');
});
test('zoom enforces valid scale',()=>{
 assert.equal(go(fresh(),'ZOOM',.8).zoom,.8);for(const z of [-1,0.2,1.6,'1',NaN,Infinity])invalid(()=>go(fresh(),'ZOOM',z),'invalid_zoom');
});
test('display preferences do not pollute graph export',()=>{
 let s=go(fresh(),'ZOOM',1.2);s=go(s,'THEME','dark');s=go(s,'GRID',false);
 const exported=JSON.parse(exportGraph(s));assert.deepEqual(Object.keys(exported).sort(),['edges','nodes','version']);
});
test('graph exporter outputs only versioned arrays',()=>{
 const raw=exportGraph(fresh());assert.ok(raw.endsWith('\n'));
 const parsed=JSON.parse(raw);assert.equal(parsed.version,1);assert.equal(parsed.nodes.length,5);
});
test('position snapping bounds coordinates',()=>{
 assert.deepEqual([-5,7,25,1067].map(position),[0,0,20,1060]);
 assert.deepEqual([-10,36,612].map(positionY),[0,40,610]);
});
test('invalid position input is rejected',()=>{
 for(const v of ['7',Infinity,NaN,undefined])invalid(()=>position(v),'invalid_position');
});
test('unknown action is refused, never evaluated',()=>invalid(()=>go(fresh(),'EVAL','alert(1)'),'unknown_action'));
test('missing action fields rejected',()=>invalid(()=>reduce(fresh(),{}),'invalid_action'));
test('notice only allows safe length and characters',()=>{
 assert.equal(go(fresh(),'NOTICE','  Ready  ').notice,'Ready');
 invalid(()=>go(fresh(),'NOTICE','x'.repeat(101)),'invalid_text');
});
test('large edge fan-out limit is strict',()=>{
 const g={version:1,nodes:Array.from({length:12},(_,i)=>({id:`n${i+1}`,type:'process',title:'Generic step',detail:'',x:0,y:0})),edges:[]};
 for(let i=1;i<=8;i++)for(let j=i+1;j<=12;j++)g.edges.push({from:`n${i}`,to:`n${j}`});
 invalid(()=>validateGraph(g),'invalid_graph');
});
