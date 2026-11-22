import {EC2Client, DescribeInstancesCommand, StartInstancesCommand, StopInstancesCommand} from '@aws-sdk/client-ec2';
import {get, mutate} from './store.js';
import {initial, nowSeconds, sweep, transition} from './domain.js';
const ec2 = new EC2Client({});
const InstanceIds = [process.env.GPU_INSTANCE_ID];
export async function instance() {
  const r = await ec2.send(new DescribeInstancesCommand({InstanceIds}));
  return r.Reservations?.[0]?.Instances?.[0];
}
export async function status() {
  const [s,i] = await Promise.all([get('GPU'),instance()]);
  let ready = false;
  if(i?.State.Name === 'running') {
    try { const r = await fetch(`http://${i.PrivateIpAddress}:8000/v1/models`,{signal:AbortSignal.timeout(2500)}); const b=await r.json(); ready=r.ok && b.data?.some(m=>m.id==='glm-5.3'); } catch {}
  }
  const state = sweep(s || initial(),nowSeconds());
  return {...state,instanceId:i.InstanceId,instanceType:i.InstanceType,ec2State:i.State.Name,ready,region:process.env.AWS_REGION,model:'GLM 5.3',gpu:'8 × NVIDIA B200',sessionCount:Object.keys(state.sessions).length,jobCount:Object.keys(state.jobs).length};
}
export async function reconcile() {
  let s = await mutate(old=>sweep(old,nowSeconds()));
  if(s.phase==='unmanaged' || s.phase==='idle') return s;
  // A persisted stopping intent excludes concurrent new sessions before the EC2 mutation.
  s = await mutate(old=>transition(old,{type:'reserveStop'},nowSeconds()));
  const i = await instance();
  if(s.phase==='stopping') {
    if(i.State.Name === 'stopped') return mutate(old=>old.phase==='stopping'?{...old,phase:'idle',stopAt:null,lastError:null}:old);
    if(i.State.Name === 'running' || i.State.Name === 'pending') await ec2.send(new StopInstancesCommand({InstanceIds}));
  } else if(s.phase==='starting' || s.phase==='active') {
    // Start is only issued for a persisted managed intent. Stop/start are retried by the reaper.
    if(i.State.Name==='stopped') await ec2.send(new StartInstancesCommand({InstanceIds}));
    if(i.State.Name==='running' && s.phase==='starting') await mutate(old=>old.phase==='starting'?{...old,phase:'active',lastError:null}:old);
  }
  return s;
}
