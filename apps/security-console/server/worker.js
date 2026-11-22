import {spawn} from 'node:child_process';
import {mkdir,writeFile,readFile,readdir,stat,rm} from 'node:fs/promises';
import {createWriteStream,createReadStream} from 'node:fs';
import {SQSClient,ReceiveMessageCommand,DeleteMessageCommand,ChangeMessageVisibilityCommand} from '@aws-sdk/client-sqs';
import {S3Client,PutObjectCommand} from '@aws-sdk/client-s3';
import {get,put,mutate} from './store.js';
import {instance} from './gpu.js';
import {nowSeconds,transition} from './domain.js';
const sqs=new SQSClient({}),s3=new S3Client({});
const QueueUrl=process.env.QUEUE_URL;
const root=process.env.WORK_ROOT||'/opt/strix-work';
function run(command,args,cwd,env,log,timeout,signal) {
  return new Promise((resolve,reject)=>{
    const child=spawn(command,args,{cwd,env,detached:true,stdio:['ignore','pipe','pipe']});
    child.stdout.pipe(log,{end:false});child.stderr.pipe(log,{end:false});
    let timedOut=false;
    const kill=()=>{try{process.kill(-child.pid,'SIGKILL');}catch{}};
    const timer=setTimeout(()=>{timedOut=true;kill();},timeout);
    signal?.addEventListener('abort',kill,{once:true});if(signal?.aborted)kill();
    const cleanup=()=>{clearTimeout(timer);signal?.removeEventListener('abort',kill);};
    child.on('error',e=>{cleanup();reject(e);});
    child.on('close',code=>{cleanup();resolve({code,timedOut});});
  });
}
async function execute(message) {
  const {id}=JSON.parse(message.Body);
  let job=await get(`JOB#${id}`);
  if(!job || ['completed','failed'].includes(job.status)) {
    await sqs.send(new DeleteMessageCommand({QueueUrl,ReceiptHandle:message.ReceiptHandle}));return;
  }
  // A redelivery after an interrupted worker is recorded, never silently repeated.
  if(job.status==='running') {
    await put({...job,status:'failed',error:'执行器中断；请检查报告后重新提交',endedAt:nowSeconds()});
    await mutate(s=>transition(s,{type:'finish',id},nowSeconds()));
    await sqs.send(new DeleteMessageCommand({QueueUrl,ReceiptHandle:message.ReceiptHandle}));return;
  }
  const work=`${root}/${id}`;await mkdir(work,{recursive:true});
  const log=createWriteStream(`${work}/worker.log`);
  let leaseLost=false,beating=false;
  const controller=new AbortController();
  const heartbeat=setInterval(async()=>{
    if(beating)return;beating=true;
    try {
      await sqs.send(new ChangeMessageVisibilityCommand({QueueUrl,ReceiptHandle:message.ReceiptHandle,VisibilityTimeout:120}));
      await mutate(s=>{
        if(!s.jobs[id] || s.jobs[id]<=nowSeconds() || s.phase!=='active')throw new Error('Lease lost');
        return {...s,jobs:{...s.jobs,[id]:nowSeconds()+7200}};
      });
    }catch(e){leaseLost=true;controller.abort();console.error('Worker heartbeat failed',e.name);}
    finally{beating=false;}
  },30000);
  try {
    const gpu=await get('GPU');
    if(!gpu?.jobs?.[id] || gpu.jobs[id]<=nowSeconds() || gpu.phase!=='active') throw new Error('扫描租约已过期，请重新启动演示');
    job={...job,status:'running',startedAt:nowSeconds()};await put(job);
    const i=await instance();
    const env={...process.env,STRIX_RUN_ID:id,STRIX_RUN_TYPE:'console',STRIX_LLM:'openai/glm-5.3',STRIX_API_TYPE:'chat_completions',LLM_API_BASE:`http://${i.PrivateIpAddress}:8000/v1`,LLM_API_KEY:'EMPTY',LLM_EXTRA_BODY:JSON.stringify({max_tokens:32768,chat_template_kwargs:{reasoning_effort:'low'}}),STRIX_CONTEXT_TOKENS:'262144',STRIX_OUTPUT_TOKENS:'32768',STRIX_PROMPT_CACHE:'false',LLM_DISABLE_STREAMING:'true',LLM_TIMEOUT:'600',LLM_PREFLIGHT_TIMEOUT:'180',STRIX_TELEMETRY:'false',STRIX_RUN_RECORD_TIMINGS:'true',STRIX_LLM_INPUT_COST_PER_MTOK:'0',STRIX_LLM_OUTPUT_COST_PER_MTOK:'0'};
    let target=job.target;
    if(job.kind==='code') {
      target=`${work}/repository`;
      const clone=await run('git',['clone','--depth','1','--',job.target,target],work,{...env,GIT_TERMINAL_PROMPT:'0'},log,300000,controller.signal);
      if(clone.code!==0)throw new Error('仓库克隆失败');
    }
    await writeFile(`${work}/instructions.txt`,`Only test the authorized target ${job.target}. Do not test third-party services, cloud metadata, or unrelated infrastructure. Findings require evidence. ${job.instructions}`);
    const result=await run('strix',['-n','-t',target,'--scan-mode',job.mode,'--scope-mode','full','--max-turns','150','--instruction-file',`${work}/instructions.txt`],work,env,log,3600000,controller.signal);
    if(leaseLost)throw new Error('任务租约丢失，扫描已停止');
    const findings=[];
    for(const name of await readdir(`${work}/strix_runs`).catch(()=>[])) {
      try {
        const rows=JSON.parse(await readFile(`${work}/strix_runs/${name}/vulnerabilities.json`,'utf8'));
        if(Array.isArray(rows))for(const f of rows)findings.push({title:String(f.title||'发现').slice(0,300),severity:String(f.severity||'unknown'),id:String(f.id||'')});
      }catch{}
    }
    job={...job,status:!result.timedOut&&[0,2].includes(result.code)?'completed':'failed',exitCode:result.code,findings:findings.slice(0,150),findingCount:findings.length,error:result.timedOut?'扫描达到 60 分钟时限':result.code!==0&&result.code!==2?'Strix 执行失败，请下载日志':undefined,leaseWarning:leaseLost};
  }catch(e){job={...job,status:'failed',error:e.message};}
  finally {
    const cleanupLog=createWriteStream('/dev/null');
    await run('sh',['-c','docker ps -aq --filter "label=strix-run-id=$1" | xargs -r docker rm -f','cleanup',id],root,process.env,cleanupLog,60000).catch(()=>{});
    cleanupLog.end();log.end();
    try {
      const archive=`${root}/${id}.tar.gz`;
      const tarlog=createWriteStream('/dev/null');
      const r=await run('tar',['-czf',archive,'--exclude=repository','-C',work,'.'],root,process.env,tarlog,120000);tarlog.end();
      if(r.code!==0)throw new Error('打包失败');
      const key=`reports/${job.owner}/${id}.tar.gz`;
      await s3.send(new PutObjectCommand({Bucket:process.env.ARTIFACT_BUCKET,Key:key,Body:createReadStream(archive),ContentLength:(await stat(archive)).size,ContentType:'application/gzip'}));
      job.artifactKey=key;
    }catch(e){job.artifactError=e.message;}
    clearInterval(heartbeat);
    while(beating)await new Promise(r=>setTimeout(r,50));
    job.endedAt=nowSeconds();job.durationSeconds=job.startedAt?job.endedAt-job.startedAt:0;
    await put(job);
    await mutate(s=>transition(s,{type:'finish',id},nowSeconds()));
    await sqs.send(new DeleteMessageCommand({QueueUrl,ReceiptHandle:message.ReceiptHandle}));
    if(job.artifactKey){await rm(work,{recursive:true,force:true});await rm(`${root}/${id}.tar.gz`,{force:true});}
  }
}
await mkdir(root,{recursive:true});
for(;;) {
  try {
    const r=await sqs.send(new ReceiveMessageCommand({QueueUrl,MaxNumberOfMessages:1,WaitTimeSeconds:20,VisibilityTimeout:120}));
    for(const message of r.Messages||[])await execute(message);
  }catch(e){console.error('Worker error',e.name,e.message);await new Promise(r=>setTimeout(r,5000));}
}
