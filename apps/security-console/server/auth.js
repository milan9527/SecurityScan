import {randomBytes, scrypt as scryptCallback, timingSafeEqual, createHash} from 'node:crypto';
import {promisify} from 'node:util';
import {PutCommand} from '@aws-sdk/lib-dynamodb';
import {db,get,put} from './store.js';
const scrypt=promisify(scryptCallback), cookieName='__Host-strix_session', lifetime=8*3600;
export const digest=value=>createHash('sha256').update(value).digest('hex');
export async function passwordHash(password,salt=randomBytes(16).toString('hex')) {
 return `${salt}:${(await scrypt(password,salt,64)).toString('hex')}`;
}
export async function verifyPassword(password,stored) {
 const [salt,hash]=stored.split(':');
 const computed=Buffer.from((await passwordHash(password,salt)).split(':')[1],'hex');
 const expected=Buffer.from(hash,'hex');
 return computed.length===expected.length&&timingSafeEqual(computed,expected);
}
const dummy=await passwordHash(randomBytes(32).toString('hex'));
const token=req=>(req.headers.cookie||'').split(';').map(v=>v.trim()).find(v=>v.startsWith(cookieName+'='))?.slice(cookieName.length+1);
const cookie=(res,value,age)=>res.setHeader('Set-Cookie',`${cookieName}=${value}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=${age}`);
async function allowance(key,limit) {
 const window=Math.floor(Date.now()/600000),pk=`AUTHRATE#${window}#${digest(key)}`;
 for(let i=0;i<8;i++) {
  const old=await get(pk);if((old?.count||0)>=limit)return false;
  try {await db.send(new PutCommand({TableName:process.env.TABLE_NAME,Item:{pk,count:(old?.count||0)+1,expiresAt:(window+2)*600},ConditionExpression:old?'#n = :n':'attribute_not_exists(pk)',...(old?{ExpressionAttributeNames:{'#n':'count'},ExpressionAttributeValues:{':n':old.count}}:{})}));return true;}
  catch(e){if(e.name!=='ConditionalCheckFailedException')throw e;}
 }
 return false;
}
export function installAuth(app) {
 app.use('/api',(req,res,next)=>{
  res.setHeader('Cache-Control','no-store');
  if(!['GET','HEAD','OPTIONS'].includes(req.method)&&req.headers.origin!==process.env.APP_ORIGIN)return res.status(403).json({error:'请求来源不匹配'});
  next();
 });
 app.post('/api/auth/login',async(req,res)=>{
  const {username,password}=req.body||{};
  if(typeof username!=='string'||!/^[a-zA-Z0-9_.-]{3,64}$/.test(username)||typeof password!=='string'||password.length>256)return res.status(400).json({error:'请输入有效的用户名和密码'});
  // Global budget also bounds requests using many fabricated usernames.
  if(!await allowance('global',100)||!await allowance(username.toLowerCase(),10))return res.status(429).json({error:'登录尝试过多，请在 10 分钟后重试'});
  const user=await get(`USER#${username.toLowerCase()}`);
  const valid=await verifyPassword(password,user?.passwordHash||dummy);
  if(!valid||!user||user.disabled)return res.status(401).json({error:'用户名或密码错误'});
  const value=randomBytes(32).toString('hex');
  await put({pk:`SESSION#${digest(value)}`,sub:user.sub,username:user.username,expiresAt:Math.floor(Date.now()/1000)+lifetime});
  cookie(res,value,lifetime);res.json({username:user.username});
 });
 app.use('/api',async(req,res,next)=>{
  const value=token(req);
  const session=value&&/^[a-f0-9]{64}$/.test(value)?await get(`SESSION#${digest(value)}`):null;
  if(!session||session.expiresAt<=Date.now()/1000)return res.status(401).json({error:'请登录后操作'});
  const user=await get(`USER#${session.username}`);
  if(!user||user.disabled||user.sub!==session.sub)return res.status(401).json({error:'账号不可用'});
  req.identity=session;req.isAdmin=user.role==='admin';next();
 });
 app.get('/api/auth/me',(req,res)=>res.json({username:req.identity.username}));
 app.post('/api/auth/logout',async(req,res)=>{await put({...req.identity,expiresAt:0});cookie(res,'',0);res.json({ok:true});});
}
