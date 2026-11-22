import test from 'node:test';
import assert from 'node:assert/strict';
import {initial,transition,sweep,validateScan} from '../server/domain.js';
test('deployment never adopts an existing GPU',()=>assert.equal(transition(initial(),{type:'reserveStop'},999999).phase,'unmanaged'));
test('last session ending starts 600 second grace; restart cancels it',()=>{
 let s=transition(initial(),{type:'begin',user:'a'},0);s.phase='active';
 s=transition(s,{type:'end',user:'a'},30);assert.equal(s.stopAt,630);
 assert.equal(transition(s,{type:'reserveStop'},629).phase,'active');
 assert.equal(transition(s,{type:'reserveStop'},630).phase,'stopping');
 assert.equal(transition(s,{type:'begin',user:'b'},500).stopAt,null);
});
test('a running job prevents stop even with no browser',()=>{
 let s=transition(initial(),{type:'begin',user:'a'},0);s.phase='active';
 s=transition(s,{type:'job',user:'a',id:'job'},1);
 s=transition(s,{type:'end',user:'a'},2);assert.equal(s.stopAt,null);
 assert.equal(sweep(s,1000).stopAt,null);
 s=transition(s,{type:'finish',id:'job'},1001);assert.equal(s.stopAt,1601);
});
test('expired sessions and stopping intent reject heartbeat/start',()=>{
 let s=transition(initial(),{type:'begin',user:'a'},0);
 assert.throws(()=>transition(s,{type:'heartbeat',user:'a'},601));
 s.phase='stopping';assert.throws(()=>transition(s,{type:'begin',user:'a'},1));
});
test('scope validation rejects alternate hosts, credentials and unapproved repos',()=>{
 const input={kind:'code',target:'https://github.com/milan9527/AgentcoreShell',mode:'standard',authorized:true};
 const repos=['milan9527/agentcoreshell'];assert.equal(validateScan(input,repos,[]).kind,'code');
 for(const target of ['https://github.com.evil.test/milan9527/AgentcoreShell','https://user@github.com/milan9527/AgentcoreShell','https://github.com/other/repo','http://github.com/milan9527/AgentcoreShell'])assert.throws(()=>validateScan({...input,target},repos,[]));
 assert.throws(()=>validateScan({...input,authorized:false},repos,[]));
 assert.throws(()=>validateScan({...input,kind:'web',target:'https://example.com'},repos,[]));
});

test('inactivity stops at ten minutes without an additional grace period',()=>{
 const s=transition(initial(),{type:'begin',user:'a'},0);
 assert.equal(transition(s,{type:'reserveStop'},599).phase,'starting');
 assert.equal(transition(s,{type:'reserveStop'},600).phase,'stopping');
 assert.equal(sweep(s,650).stopAt,600);
});
test('activity and other users extend protection, reads do not',()=>{
 let s=transition(initial(),{type:'begin',user:'a'},0);
 s=transition(s,{type:'heartbeat',user:'a'},300);
 assert.equal(sweep(s,500).sessions.a,900);
 s=transition(s,{type:'begin',user:'b'},400);
 assert.equal(transition(s,{type:'reserveStop'},999).phase,'starting');
 assert.equal(transition(s,{type:'reserveStop'},1000).phase,'stopping');
});
