import json, pathlib, subprocess, time, urllib.request, traceback
root=pathlib.Path('/opt/glm-ablation-20261120'); out=root/'results'; out.mkdir(exist_ok=True)
def shell(args):
    return subprocess.check_output(args,stderr=subprocess.STDOUT,text=True)
def record(name,args):
    (out/name).write_text(shell(args))
def ready():
    deadline=time.time()+4200
    while time.time()<deadline:
        try:
            with urllib.request.urlopen('http://localhost:8000/health',timeout=5) as r:
                if r.status==200:return
        except Exception:pass
        time.sleep(15)
    raise RuntimeError('Model readiness timeout')
def run(variant):
    # Flush before identical four-case warmup; no active requests at this point.
    req=urllib.request.Request('http://localhost:8000/flush_cache',data=b'',method='POST')
    with urllib.request.urlopen(req,timeout=30) as r:
        (out/(variant+'-cache-flush.txt')).write_bytes(r.read())
    with open(out/(variant+'-progress.log'),'w') as f:
        subprocess.run(['python3',str(root/'stream-benchmark.py'),'--cases-json',str(root/'source-cases.json'),'--out',str(out/(variant+'.jsonl')),'--variant',variant,'--warm-all','--max-tokens','32768','--repeats','5','--reasoning-effort','low'],stdout=f,stderr=subprocess.STDOUT,check=True)
    rows=[json.loads(x) for x in (out/(variant+'.jsonl')).read_text().splitlines()]
    if any(r.get('error') for r in rows):raise RuntimeError(variant+' has request errors')
    record(variant+'-gpu.csv',['nvidia-smi','--query-gpu=index,name,memory.used,memory.total,utilization.gpu','--format=csv'])
    with urllib.request.urlopen('http://localhost:8000/get_server_info',timeout=30) as r:
        (out/(variant+'-server-info.json')).write_bytes(r.read())
def status(text):
    (out/'status.json').write_text(json.dumps({'state':text,'time':time.time()}));print(text,flush=True)
try:
    status('waiting_baseline');ready()
    record('baseline-command.json',['docker','inspect','--format','{{json .Config.Cmd}}','glm53'])
    status('baseline');run('baseline')
    status('concise');run('concise')
    status('preparing_mtp')
    record('baseline-server.log',['docker','logs','glm53'])
    subprocess.run(['docker','stop','--time','120','glm53'],check=True)
    image='glm53-ablation-patched:20261120'
    subprocess.run(['docker','commit','glm53',image],check=True)
    cmd=json.loads((out/'baseline-command.json').read_text())
    cmd+=['--speculative-algorithm','EAGLE','--speculative-num-steps','3','--speculative-eagle-topk','1','--speculative-num-draft-tokens','4']
    (out/'mtp-command.json').write_text(json.dumps(cmd,indent=2))
    subprocess.run(['docker','run','-d','--name','glm53-mtp-ablation','--gpus','all','--ipc=host','--network=host','--ulimit','memlock=-1','--ulimit','stack=67108864','-v','/model-cache:/root/.cache/huggingface',image]+cmd,check=True)
    status('waiting_mtp');ready();status('mtp');run('mtp')
    record('mtp-server.log',['docker','logs','glm53-mtp-ablation'])
    status('complete')
except Exception:
    (out/'error.txt').write_text(traceback.format_exc());status('failed')
finally:
    for name in ['glm53','glm53-mtp-ablation']:
        with open(out/(name+'-final.log'),'w') as f:subprocess.run(['docker','logs','--tail','1000',name],stdout=f,stderr=subprocess.STDOUT)
    subprocess.run(['docker','stop','--time','120','glm53-mtp-ablation'])
