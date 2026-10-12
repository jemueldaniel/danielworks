import test from 'node:test';import assert from 'node:assert/strict';import {REFERENCES,filterReferences,publicUrl} from './data.mjs';
test('all public entries have distinct names',()=>assert.equal(new Set(REFERENCES.map(x=>x.title)).size,REFERENCES.length));
test('all references have categories, descriptions and tags',()=>assert.ok(REFERENCES.every(x=>x.title&&x.description&&x.discipline&&x.tags.length)));
test('all references use approved public paths',()=>assert.ok(REFERENCES.every(x=>publicUrl(x.path).startsWith('https://github.com/jemueldaniel/danielworks/blob/main/'))));
test('search matches original implementation',()=>assert.equal(filterReferences(REFERENCES,{search:'Layout Foundry'}).length,1));
test('search is case insensitive',()=>assert.ok(filterReferences(REFERENCES,{search:'RUST'}).length>=1));
test('discipline filter narrows',()=>assert.ok(filterReferences(REFERENCES,{discipline:'Backend systems'}).every(x=>x.discipline==='Backend systems')));
test('unknown category yields empty result',()=>assert.equal(filterReferences(REFERENCES,{discipline:'Unknown'}).length,0));
test('empty query returns every reference',()=>assert.equal(filterReferences(REFERENCES).length,REFERENCES.length));
test('alphabetical ordering is stable',()=>assert.deepEqual(filterReferences(REFERENCES).map(x=>x.title),[...REFERENCES].map(x=>x.title).sort()));
test('category sorting groups disciplines',()=>{const x=filterReferences(REFERENCES,{sort:'discipline'}).map(x=>x.discipline);assert.deepEqual(x,[...x].sort());});
test('does not mutate original entries',()=>{const original=JSON.stringify(REFERENCES);filterReferences(REFERENCES,{sort:'discipline'});assert.equal(JSON.stringify(REFERENCES),original);});
for(const path of ['../secrets','.env','examples/../private','https://private.example','D:/user/private','examples/a b']){
 test('rejects unsafe path '+path,()=>assert.throws(()=>publicUrl(path)));
}
