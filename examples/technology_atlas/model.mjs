import {CATEGORIES,LEVELS,RECIPES,TECHNOLOGIES,publicUrl,catalogProofCheck} from './data.mjs';
export {CATEGORIES,LEVELS,RECIPES,TECHNOLOGIES,publicUrl,catalogProofCheck};
export const SORTS=Object.freeze(['featured','name','category','evidence']);
const KNOWN=new Set(TECHNOLOGIES.map(x=>x.id));
const ORDER=new Map([['Public-tested',0],['Public-historical',1],['Source-observed',2]]);
export function initialState(){return {search:'',category:'All',level:'All',sort:'featured',saved:[],selected:[],theme:'dark',details:null,showSaved:false};}
function idValid(id){if(typeof id!=='string'||!KNOWN.has(id))throw new Error('invalid_technology_id');}
export function restoreSaved(value){return Array.isArray(value)?[...new Set(value.filter(x=>typeof x==='string'&&KNOWN.has(x)))].slice(0,50).sort():[];}
export function reduce(state,action){
 if(!state||!action||typeof action.type!=='string')throw new Error('invalid_action');
 const next={...state,saved:[...state.saved],selected:[...state.selected]};
 switch(action.type){
  case 'SEARCH':if(typeof action.value!=='string')throw new Error('invalid_search');next.search=action.value.slice(0,100);break;
  case 'CATEGORY':if(!CATEGORIES.includes(action.value))throw new Error('invalid_category');next.category=action.value;break;
  case 'LEVEL':if(!LEVELS.includes(action.value))throw new Error('invalid_level');next.level=action.value;break;
  case 'SORT':if(!SORTS.includes(action.value))throw new Error('invalid_sort');next.sort=action.value;break;
  case 'TOGGLE_SAVED':idValid(action.value);next.saved=next.saved.includes(action.value)?next.saved.filter(x=>x!==action.value):[...next.saved,action.value].sort();break;
  case 'TOGGLE_SELECT':idValid(action.value);next.selected=next.selected.includes(action.value)?next.selected.filter(x=>x!==action.value):next.selected.length<8?[...next.selected,action.value]:(()=>{throw new Error('selection_limit')})();break;
  case 'CLEAR_SELECTION':next.selected=[];break;
  case 'THEME':if(!['light','dark'].includes(action.value))throw new Error('invalid_theme');next.theme=action.value;break;
  case 'DETAIL':idValid(action.value);next.details=action.value;break;
  case 'CLOSE_DETAIL':next.details=null;break;
  case 'SAVED_ONLY':if(typeof action.value!=='boolean')throw new Error('invalid_boolean');next.showSaved=action.value;break;
  case 'RESTORE':
   if(!action.value||typeof action.value!=='object'||Array.isArray(action.value))throw new Error('invalid_restore');
   next.saved=restoreSaved(action.value.saved);next.theme=['dark','light'].includes(action.value.theme)?action.value.theme:'dark';break;
  case 'RESET_FILTERS':next.search='';next.category='All';next.level='All';next.sort='featured';next.showSaved=false;break;
  default:throw new Error('unknown_action');
 }
 return next;
}
export function byId(id){idValid(id);return TECHNOLOGIES.find(x=>x.id===id);}
export function visible(state){
 if(!CATEGORIES.includes(state.category)||!LEVELS.includes(state.level)||!SORTS.includes(state.sort))throw new Error('invalid_filter_state');
 const q=state.search.trim().toLowerCase();
 let a=TECHNOLOGIES.filter(t=>(!q||[t.name,t.category,t.summary].some(s=>s.toLowerCase().includes(q)))&&(state.category==='All'||t.category===state.category)&&(state.level==='All'||t.level===state.level)&&(!state.showSaved||state.saved.includes(t.id)));
 if(state.sort==='name')a=a.slice().sort((x,y)=>x.name.localeCompare(y.name));
 if(state.sort==='category')a=a.slice().sort((x,y)=>x.category.localeCompare(y.category)||x.name.localeCompare(y.name));
 if(state.sort==='evidence')a=a.slice().sort((x,y)=>ORDER.get(x.level)-ORDER.get(y.level)||x.name.localeCompare(y.name));
 return a;
}
export function categoryCounts(){return Object.fromEntries(CATEGORIES.map(c=>[c,c==='All'?TECHNOLOGIES.length:TECHNOLOGIES.filter(t=>t.category===c).length]));}
export function qualificationCounts(){return Object.fromEntries(LEVELS.map(c=>[c,c==='All'?TECHNOLOGIES.length:TECHNOLOGIES.filter(t=>t.level===c).length]));}
export function selection(state){return state.selected.map(byId);}
export function buildPlan(state){
 const picks=selection(state),runnable=picks.filter(x=>x.source!==null),unverified=picks.filter(x=>x.source===null);
 const recipes=[...new Set(runnable.map(t=>t.recipe))].sort();
 return {requested:picks.length,publicExamples:runnable.length,sourceObserved:unverified.length,recipes,unproven:unverified.map(t=>t.name),boundary:'A recipe demonstrates specific public reference modules, not necessarily every selected technology.'};
}
export function recipeCommand(recipe){
 if(!RECIPES.includes(recipe))throw new Error('unknown_recipe');
 return 'python -B tools/compose_public_solution.py --root . --expected-source-sha256 YOUR_EXTERNALLY_VERIFIED_MANIFEST_SHA256 --recipe '+recipe+' --destination ../public-'+recipe+'-reference --receipt ../public-'+recipe+'-proof.json';
}
export function csvCell(value){
 let s=String(value??'').replace(/\r\n?/g,'\n');
 if(/^\s*[=+\-@\t]/.test(s))s="'"+s;
 return '"'+s.replace(/"/g,'""')+'"';
}
export function exportCSV(state){
 const rows=[['Technology','Discipline','Qualification','Public source','Evidence meaning']];
 for(const t of visible(state))rows.push([t.name,t.category,t.level,t.source?publicUrl(t.source):'',t.summary]);
 return rows.map(line=>line.map(csvCell).join(',')).join('\r\n')+'\r\n';
}
export function exportJSON(state){
 const records=visible(state).map(t=>({name:t.name,category:t.category,qualification:t.level,public_source:t.source?publicUrl(t.source):null,notes:t.summary}));
 return JSON.stringify({schema:1,classification:'Educational public proofs vs inspected non-public-source technology presence',production_certification:false,private_source_exported:false,records},null,2)+'\n';
}
export function presentationCounts(){
 const x=catalogProofCheck(),q=qualificationCounts();
 return {total:x.count,runnable:q['Public-tested'],historical:q['Public-historical'],observed:q['Source-observed'],categories:CATEGORIES.length-1};
}
