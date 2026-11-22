import express from 'express';
import {randomUUID} from 'node:crypto';
import {installAuth} from './auth.js';
import {SQSClient,SendMessageCommand} from '@aws-sdk/client-sqs';
import {S3Client,GetObjectCommand} from '@aws-sdk/client-s3';
import {getSignedUrl} from '@aws-sdk/s3-request-presigner';
import {get,put,mutate,listJobs,jobHistory} from './store.js';
import {transition,nowSeconds,validateScan} from './domain.js';
import {status} from './gpu.js';
import {readTargets,saveTargets,requireAdmin} from './targets.js';
const app=express(); app.disable('x-powered-by'); app.use(express.json({limit:'16kb'}));
const sqs=new SQSClient({}); const s3=new S3Client({});
app.get('/health',(_req,res)=>res.json({ok:true}));
installAuth(app);
app.get('/api/config',async(req,res)=>res.json({...await readTargets(),canManageTargets:req.isAdmin,model:'GLM 5.3',graceSeconds:600}));
app.post('/api/admin/targets',requireAdmin,async(req,res)=>res.json(await saveTargets(req.body,req.identity.username)));
app.get('/api/gpu',async(req,res)=>{const s=await status();res.json({...s,sessions:undefined,jobs:undefined,mySession:Boolean(s.sessions[req.identity.sub]),mySessionExpiresAt:s.sessions[req.identity.sub]||null});});
app.post('/api/demo/start',async(req,res)=>{await mutate(s=>transition(s,{type:'begin',user:req.identity.sub},nowSeconds()));res.status(202).json({accepted:true});});
app.post('/api/demo/heartbeat',async(req,res)=>{if(req.body?.activity!==true)return res.json({ok:true,renewed:false});await mutate(s=>transition(s,{type:'heartbeat',user:req.identity.sub},nowSeconds()));res.json({ok:true});});
app.post('/api/demo/end',async(req,res)=>{const s=await mutate(s=>transition(s,{type:'end',user:req.identity.sub},nowSeconds()));res.json({stopAt:s.stopAt,activeJobs:Object.keys(s.jobs).length});});
app.get('/api/scan-history',async(req,res)=>res.json(await jobHistory(req.identity.sub,req.query.cursor)));
app.get('/api/scans',async(req,res)=>res.json(await listJobs(req.identity.sub)));
app.post('/api/scans',async(req,res)=>{
  const {repos,hosts}=await readTargets();
  let input;try{input=validateScan(req.body,repos,hosts);}catch(e){return res.status(400).json({error:e.message});}
  if(!(await status()).ready) return res.status(409).json({error:'模型仍在预热，请等待就绪后提交'});
  const id=randomUUID();const item={pk:`JOB#${id}`,id,owner:req.identity.sub,createdAt:nowSeconds(),status:'queued',...input};
  await mutate(s=>transition(s,{type:'job',id,user:req.identity.sub},nowSeconds()));
  try{await put(item);await sqs.send(new SendMessageCommand({QueueUrl:process.env.QUEUE_URL,MessageBody:JSON.stringify({id}),MessageGroupId:'gpu',MessageDeduplicationId:id}));}
  catch(e){await mutate(s=>transition(s,{type:'finish',id},nowSeconds()));await put({...item,status:'failed',error:'队列提交失败'});throw e;}
  res.status(202).json(item);
});
app.get('/api/scans/:id',async(req,res)=>{const j=await get(`JOB#${req.params.id}`);if(!j||j.owner!==req.identity.sub)return res.sendStatus(404);res.json(j);});
app.get('/api/scans/:id/artifact',async(req,res)=>{
  const j=await get(`JOB#${req.params.id}`);if(!j||j.owner!==req.identity.sub||!j.artifactKey)return res.sendStatus(404);
  const url=await getSignedUrl(s3,new GetObjectCommand({Bucket:process.env.ARTIFACT_BUCKET,Key:j.artifactKey,ResponseContentDisposition:`attachment; filename="strix-${j.id}.tar.gz"`}),{expiresIn:300});res.json({url});
});
app.use((err,_req,res,_next)=>{console.error(err.name,err.message);res.status(err.status||500).json({error:err.status?err.message:'请求失败，请稍后重试；后台任务状态会保留'});});
app.listen(process.env.PORT||3000,'0.0.0.0',()=>console.log('Security console API listening'));
