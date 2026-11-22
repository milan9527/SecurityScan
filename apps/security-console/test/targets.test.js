import test from 'node:test';
import assert from 'node:assert/strict';
import {normalizeTargets,readTargets,saveTargets,requireAdmin} from '../server/targets.js';
import {db} from '../server/store.js';
test('target formats and normalization',()=>{
 assert.deepEqual(normalizeTargets({repos:['Owner/Repo.git','owner/repo'],hosts:['APP.EXAMPLE.COM','api.example.com:8443']}),{repos:['owner/repo'],hosts:['app.example.com','api.example.com:8443']});
 for(const host of ['https://example.com','example.com/path','*.example.com','user@example.com','example.com?x=1','example.com:99999',''])assert.throws(()=>normalizeTargets({repos:[],hosts:[host]}));
 assert.throws(()=>normalizeTargets({repos:['https://github.com/a/b'],hosts:[]}));
 assert.throws(()=>normalizeTargets({repos:[],hosts:Array(101).fill('example.com')}));
});
test('persistent targets replace environment defaults, including empty lists; stale writes conflict',async()=>{
 const original=db.send;let stored;
 process.env.ALLOWED_REPOS='owner/repo';process.env.ALLOWED_HOSTS='example.com';
 db.send=async c=>{if(c.constructor.name==='GetCommand')return {Item:stored};const p=c.input;if(stored&&p.ExpressionAttributeValues?.[':v']!==stored.version)throw Object.assign(new Error(),{name:'ConditionalCheckFailedException'});stored=p.Item;return {};};
 try{
  assert.deepEqual((await readTargets()).hosts,['example.com']);
  await saveTargets({repos:[],hosts:[],version:0},'admin');
  assert.deepEqual((await readTargets()).hosts,[]);
  await assert.rejects(saveTargets({repos:[],hosts:['example.com'],version:0},'admin'),{status:409});
  await saveTargets({repos:[],hosts:['api.example.com'],version:1},'admin');
  assert.equal((await readTargets()).version,2);
 }finally{db.send=original;}
});
test('only explicit administrators may mutate targets',()=>{
 let code,next=false;const res={status:s=>{code=s;return res;},json:()=>{}};
 requireAdmin({},res,()=>{next=true;});assert.equal(code,403);assert.equal(next,false);
 requireAdmin({isAdmin:true},res,()=>{next=true;});assert.equal(next,true);
});
