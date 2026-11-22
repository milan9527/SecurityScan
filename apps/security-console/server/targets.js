import {PutCommand} from '@aws-sdk/lib-dynamodb';
import {db,get} from './store.js';
const pk='CONFIG#TARGETS';
const bad=message=>Object.assign(new Error(message),{status:400});
export function normalizeTargets(input){
 if(!input||!Array.isArray(input.repos)||!Array.isArray(input.hosts))throw bad('请提供仓库和域名列表');
 const clean=(items,kind)=>{
  if(items.length>100)throw bad('每类最多配置 100 个目标');
  return [...new Set(items.map(value=>{
   if(typeof value!=='string'||value.length>300)throw bad('目标格式无效');
   const v=value.trim().toLowerCase();
   if(kind==='repo'){
    if(!/^[a-z0-9_-][a-z0-9_.-]*\/[a-z0-9_-][a-z0-9_.-]*$/.test(v))throw bad('仓库请填写 owner/repository，不包含 URL');
    return v.replace(/\.git$/,'');
   }
   let url;try{url=new URL('https://'+v);}catch{throw bad('域名格式无效');}
   if(!v||/[\s/@?#\\*]/.test(v)||url.username||url.password||url.pathname!=='/'||!/^([a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?::[0-9]+)?$/.test(v))throw bad('请填写完整域名，可含端口，不含协议、路径或通配符');
   return url.host;
  }))];
 };
 return {repos:clean(input.repos,'repo'),hosts:clean(input.hosts,'host')};
}
export async function readTargets(){
 return await get(pk)||{repos:(process.env.ALLOWED_REPOS||'').toLowerCase().split(',').map(v=>v.trim()).filter(Boolean),hosts:(process.env.ALLOWED_HOSTS||'').toLowerCase().split(',').map(v=>v.trim()).filter(Boolean),version:0};
}
export async function saveTargets(input,username){
 const targets=normalizeTargets(input);
 if(!Number.isSafeInteger(input.version)||input.version<0)throw bad('配置版本无效，请刷新后重试');
 const item={pk,...targets,version:input.version+1,updatedBy:username,updatedAt:Math.floor(Date.now()/1000)};
 try{await db.send(new PutCommand({TableName:process.env.TABLE_NAME,Item:item,ConditionExpression:input.version?'#v = :v':'attribute_not_exists(pk)',...(input.version?{ExpressionAttributeNames:{'#v':'version'},ExpressionAttributeValues:{':v':input.version}}:{})}));}
 catch(e){if(e.name==='ConditionalCheckFailedException')throw Object.assign(new Error('配置已被其他管理员修改，请重新加载后再保存'),{status:409});throw e;}
 return item;
}
export function requireAdmin(req,res,next){if(!req.isAdmin)return res.status(403).json({error:'仅管理员可以修改授权目标'});next();}
