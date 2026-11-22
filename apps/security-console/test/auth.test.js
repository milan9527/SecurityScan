import test from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import {db} from '../server/store.js';
import {installAuth,passwordHash,digest} from '../server/auth.js';
test('password login, origin validation, session expiry, logout revocation and rate limit',async()=>{
 process.env.APP_ORIGIN='https://console.example';
 const rows=new Map();const original=db.send;
 db.send=async command=>{const p=command.input;if(command.constructor.name==='GetCommand')return {Item:rows.get(p.Key.pk)};rows.set(p.Item.pk,structuredClone(p.Item));return {};};
 rows.set('USER#admin',{pk:'USER#admin',username:'admin',sub:'user-1',passwordHash:await passwordHash('test-only-password')});
 const app=express();app.use(express.json());installAuth(app);
 const server=app.listen(0,'127.0.0.1');await new Promise(resolve=>server.once('listening',resolve));
 const url=`http://127.0.0.1:${server.address().port}/api/auth`;
 const request=(path,body,cookie,origin=process.env.APP_ORIGIN)=>fetch(url+path,{method:body?'POST':'GET',headers:{origin,'Content-Type':'application/json',...(cookie?{cookie}:{})},...(body?{body:JSON.stringify(body)}:{})});
 try {
  assert.equal((await request('/me')).status,401);
  assert.equal((await request('/login',{username:'admin',password:'test-only-password'},null,'https://evil.example')).status,403);
  assert.equal((await request('/login',{username:'admin',password:'wrong'})).status,401);
  const login=await request('/login',{username:'admin',password:'test-only-password'});assert.equal(login.status,200);
  const raw=login.headers.get('set-cookie');for(const attribute of ['Secure','HttpOnly','SameSite=Strict'])assert.ok(raw.includes(attribute));
  const cookie=raw.split(';')[0];assert.equal((await request('/me',null,cookie)).status,200);
  assert.equal((await request('/logout',{},cookie)).status,200);assert.equal((await request('/me',null,cookie)).status,401);
  const again=await request('/login',{username:'admin',password:'test-only-password'});const second=again.headers.get('set-cookie').split(';')[0];
  rows.get('SESSION#'+digest(second.split('=')[1])).expiresAt=1;assert.equal((await request('/me',null,second)).status,401);
  for(let i=0;i<7;i++)assert.equal((await request('/login',{username:'admin',password:'wrong'})).status,401);
  assert.equal((await request('/login',{username:'admin',password:'test-only-password'})).status,429);
 }finally{db.send=original;await new Promise(resolve=>server.close(resolve));}
});
