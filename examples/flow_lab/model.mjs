/** Flow Laboratory: original, offline-only, deterministic directed-graph editor model.
 * No private source, external APIs, accounts, authentication or network behavior. */
export const LIMITS = Object.freeze({nodes:24, edges:48, history:32, title:48, detail:110, file:20000, x:1060, y:610});
export const NODE_TYPES = Object.freeze(['source','process','output']);
export const TEMPLATES = Object.freeze([
  {id:'n1',type:'source',title:'Sample events',detail:'Fictional signals, no external data',x:65,y:90},
  {id:'n2',type:'source',title:'Survey notes',detail:'Synthetic responses, no accounts',x:65,y:350},
  {id:'n3',type:'process',title:'Normalize',detail:'Validate and align sample inputs',x:400,y:90},
  {id:'n4',type:'process',title:'Score',detail:'Apply transparent local rules',x:400,y:350},
  {id:'n5',type:'output',title:'Review panel',detail:'Visible results and traceability',x:770,y:210}
]);
export const TEMPLATE_EDGES = Object.freeze([
  {from:'n1',to:'n3'},{from:'n2',to:'n4'},{from:'n3',to:'n4'},{from:'n4',to:'n5'}
]);
const clone = x => structuredClone(x);
const fail = code => {throw new Error(code)};
const hasExactKeys = (value,keys) => value && typeof value==='object' && !Array.isArray(value) &&
  Object.keys(value).sort().join('|')===keys.slice().sort().join('|');
const integer = (n,low,high) => Number.isInteger(n) && n>=low && n<=high;
const text = (str,max,{optional=false}={}) => {
  if(typeof str!=='string' || str.length>max || /[\u0000-\u001f\u007f]/u.test(str)) fail('invalid_text');
  const cleaned=str.trim();
  if(!optional && (cleaned.length<2 || cleaned.length>max)) fail('invalid_text');
  return cleaned;
};
export function validateGraph(graph) {
  if(!hasExactKeys(graph,['version','nodes','edges']) || graph.version!==1 ||
     !Array.isArray(graph.nodes) || !Array.isArray(graph.edges) ||
     graph.nodes.length>LIMITS.nodes || graph.edges.length>LIMITS.edges) fail('invalid_graph');
  const ids=new Set();
  const nodes=graph.nodes.map(node=>{
    if(!hasExactKeys(node,['id','type','title','detail','x','y']) ||
      typeof node.id!=='string' || !/^n[1-9][0-9]{0,5}$/.test(node.id) || ids.has(node.id) ||
      !NODE_TYPES.includes(node.type) || !integer(node.x,0,LIMITS.x) || !integer(node.y,0,LIMITS.y)) fail('invalid_node');
    ids.add(node.id);
    return {id:node.id,type:node.type,title:text(node.title,LIMITS.title),detail:text(node.detail,LIMITS.detail,{optional:true}),x:node.x,y:node.y};
  });
  const seen=new Set();
  const edges=graph.edges.map(edge=>{
    if(!hasExactKeys(edge,['from','to']) || !ids.has(edge.from) || !ids.has(edge.to) || edge.from===edge.to) fail('invalid_edge');
    const key=`${edge.from}->${edge.to}`;
    if(seen.has(key)) fail('duplicate_edge');
    seen.add(key);
    return {from:edge.from,to:edge.to};
  });
  const answer={version:1,nodes,edges};
  topology(answer); // explicitly reject cyclic edits and cyclic imported graphs
  return answer;
}
export function topology(graph){
  const indeg=new Map(graph.nodes.map(n=>[n.id,0]));
  const successors=new Map(graph.nodes.map(n=>[n.id,[]]));
  for(const edge of graph.edges){
    if(!indeg.has(edge.from)||!indeg.has(edge.to)) fail('invalid_edge');
    indeg.set(edge.to,indeg.get(edge.to)+1);
    successors.get(edge.from).push(edge.to);
  }
  const levels=[];let frontier=graph.nodes.filter(n=>!indeg.get(n.id)).map(n=>n.id);
  let processed=0;
  while(frontier.length){
    levels.push(frontier);
    const next=[];
    for(const id of frontier){processed++;for(const target of successors.get(id)){
      indeg.set(target,indeg.get(target)-1);
      if(indeg.get(target)===0) next.push(target);
    }}
    frontier=next;
  }
  if(processed!==graph.nodes.length) fail('graph_cycle');
  return levels;
}
export const graphFrom = state => ({version:1,nodes:clone(state.nodes),edges:clone(state.edges)});
export function createState(){
  const graph=validateGraph({version:1,nodes:clone(TEMPLATES),edges:clone(TEMPLATE_EDGES)});
  return {...graph,selected:'n3',zoom:1,theme:'light',grid:true,compact:false,past:[],future:[],notice:''};
}
function committed(state,next){
  const before=graphFrom(state);
  const validated=validateGraph(next);
  if(JSON.stringify(before)===JSON.stringify(validated)) return state;
  return {...state,nodes:validated.nodes,edges:validated.edges,
    selected:validated.nodes.some(n=>n.id===state.selected)?state.selected:null,
    past:[...state.past,before].slice(-LIMITS.history),future:[],notice:'Changes saved locally'};
}
const withSelected = (state,id) => (id!==null&&!state.nodes.some(n=>n.id===id))?fail('unknown_node'):{...state,selected:id};
export function reduce(state,action){
  if(!state || !action || typeof action.type!=='string') fail('invalid_action');
  const v=action.value;
  switch(action.type){
    case 'SELECT': return withSelected(state,v);
    case 'ADD_NODE': {
      if(!v || !NODE_TYPES.includes(v.type) || state.nodes.length>=LIMITS.nodes) fail('invalid_add');
      const serial=state.nodes.reduce((m,n)=>Math.max(m,Number(n.id.slice(1))),0)+1;
      const offset=(state.nodes.length%6)*65;
      const node={id:`n${serial}`,type:v.type,title:text(v.title,LIMITS.title),
        detail:text(v.detail??'',LIMITS.detail,{optional:true}),x:integer(v.x,0,LIMITS.x)?v.x:Math.min(1050,180+offset),
        y:integer(v.y,0,LIMITS.y)?v.y:Math.min(600,150+offset)};
      const next=committed(state,{version:1,nodes:[...state.nodes,node],edges:state.edges});
      return {...next,selected:node.id};
    }
    case 'MOVE_NODE': {
      if(!v || !integer(v.x,0,LIMITS.x) || !integer(v.y,0,LIMITS.y)) fail('invalid_move');
      if(!state.nodes.some(n=>n.id===v.id)) fail('unknown_node');
      return committed(state,{version:1,nodes:state.nodes.map(n=>n.id===v.id?{...n,x:v.x,y:v.y}:n),edges:state.edges});
    }
    case 'UPDATE_NODE': {
      if(!v || !state.nodes.some(n=>n.id===v.id)) fail('unknown_node');
      const title=text(v.title,LIMITS.title), detail=text(v.detail??'',LIMITS.detail,{optional:true});
      return committed(state,{version:1,nodes:state.nodes.map(n=>n.id===v.id?{...n,title,detail}:n),edges:state.edges});
    }
    case 'DELETE_NODE': {
      if(typeof v!=='string'||!state.nodes.some(n=>n.id===v)) fail('unknown_node');
      const next=committed(state,{version:1,nodes:state.nodes.filter(n=>n.id!==v),edges:state.edges.filter(e=>e.from!==v&&e.to!==v)});
      return {...next,selected:null};
    }
    case 'CONNECT': {
      if(!v || typeof v.from!=='string' || typeof v.to!=='string') fail('invalid_edge');
      return committed(state,{version:1,nodes:state.nodes,edges:[...state.edges,{from:v.from,to:v.to}]});
    }
    case 'DISCONNECT': {
      if(!v || !state.edges.some(e=>e.from===v.from&&e.to===v.to)) fail('unknown_edge');
      return committed(state,{version:1,nodes:state.nodes,edges:state.edges.filter(e=>!(e.from===v.from&&e.to===v.to))});
    }
    case 'UNDO': {
      if(!state.past.length)return state;
      const previous=state.past.at(-1);
      return {...state,...clone(previous),selected:previous.nodes.some(n=>n.id===state.selected)?state.selected:null,
        past:state.past.slice(0,-1),future:[graphFrom(state),...state.future].slice(0,LIMITS.history),notice:'Undid last edit'};
    }
    case 'REDO': {
      if(!state.future.length)return state;
      const next=state.future[0];
      return {...state,...clone(next),selected:next.nodes.some(n=>n.id===state.selected)?state.selected:null,
        past:[...state.past,graphFrom(state)].slice(-LIMITS.history),future:state.future.slice(1),notice:'Reapplied edit'};
    }
    case 'IMPORT': {
      if(typeof v!=='string'||v.length>LIMITS.file)fail('invalid_import');
      let parsed;try{parsed=JSON.parse(v)}catch{fail('invalid_import')}
      const graph=validateGraph(parsed);
      return {...committed(state,graph),selected:null,notice:'Validated graph imported'};
    }
    case 'RESET': return {...committed(state,{version:1,nodes:clone(TEMPLATES),edges:clone(TEMPLATE_EDGES)}),selected:'n3'};
    case 'ZOOM': if(typeof v!=='number'||!Number.isFinite(v)||v<0.6||v>1.5)fail('invalid_zoom');return {...state,zoom:Math.round(v*10)/10};
    case 'THEME': if(!['light','dark'].includes(v))fail('invalid_theme');return {...state,theme:v};
    case 'GRID': if(typeof v!=='boolean')fail('invalid_grid');return {...state,grid:v};
    case 'COMPACT': if(typeof v!=='boolean')fail('invalid_compact');return {...state,compact:v};
    case 'NOTICE': return {...state,notice:text(v,100,{optional:true})};
    default: fail('unknown_action');
  }
}
export function exportGraph(state){return JSON.stringify(graphFrom(state),null,2)+'\n'}
export function stats(state){
  const levels=topology(state);
  return {nodes:state.nodes.length,connections:state.edges.length,stages:levels.length,
    input:state.nodes.filter(n=>n.type==='source').length,output:state.nodes.filter(n=>n.type==='output').length};
}
export function nodeConnections(state,id){return {incoming:state.edges.filter(e=>e.to===id),outgoing:state.edges.filter(e=>e.from===id)}}
export function position(value){if(!Number.isFinite(value))fail('invalid_position');return Math.min(LIMITS.x,Math.max(0,Math.round(value/20)*20))}
export function positionY(value){if(!Number.isFinite(value))fail('invalid_position');return Math.min(LIMITS.y,Math.max(0,Math.round(value/20)*20))}
