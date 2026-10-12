import {REFERENCES,filterReferences,publicUrl} from './data.mjs';
const $=id=>document.getElementById(id);
const categories=[...new Set(REFERENCES.map(x=>x.discipline))].sort();
for(const name of categories){const option=document.createElement('option');option.value=name;option.textContent=name;$('discipline').append(option);}
$('total').textContent=REFERENCES.length;
$('groups').textContent=categories.length;
$('links').textContent=REFERENCES.length;
function render(){
 const items=filterReferences(REFERENCES,{search:$('search').value,discipline:$('discipline').value,sort:$('sort').value});
 const host=$('cards');host.replaceChildren();
 for(const item of items){
  const node=$('card-template').content.cloneNode(true);
  node.querySelector('.category').textContent=item.discipline;
  node.querySelector('h3').textContent=item.title;
  node.querySelector('p').textContent=item.description;
  const tags=node.querySelector('.tags');
  for(const tag of item.tags){const span=document.createElement('span');span.textContent=tag;tags.append(span);}
  node.querySelector('a.source').href=publicUrl(item.path);
  host.append(node);
 }
 $('empty').hidden=items.length!==0;
 $('count').textContent=items.length+' of '+REFERENCES.length+' public references';
}
for(const id of ['search','discipline','sort'])$(id).addEventListener('input',render);
$('theme').addEventListener('click',()=>{
 const next=document.documentElement.dataset.theme==='dark'?'light':'dark';
 document.documentElement.dataset.theme=next;
 try{localStorage.setItem('proof-dashboard-theme',next);}catch{}
});
try{const theme=localStorage.getItem('proof-dashboard-theme');if(theme==='dark')document.documentElement.dataset.theme='dark';}catch{}
render();
