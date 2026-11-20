#!/usr/bin/env python3
"""Unofficial application-workload benchmark against the supplied endpoint.
Client-observed timings include the transport path (including an SSM tunnel).
TTOT = request start to last generated SSE delta (not SSE usage/[DONE]).
TPOT is approximate because SSE delivery can batch tokens.
"""
import argparse
import concurrent.futures
import datetime
import json
import pathlib
import statistics
import time
import urllib.request

p=argparse.ArgumentParser()
p.add_argument('--base',default='http://127.0.0.1:8000/v1')
p.add_argument('--out',default='metrics.jsonl')
p.add_argument('--fixtures',default=str(pathlib.Path(__file__).parent/'fixtures'))
p.add_argument('--cases-json', help='JSON mapping scenario names to source bundles')
p.add_argument('--repeats',type=int,default=5)
p.add_argument('--max-tokens',type=int,default=8192)
p.add_argument('--reasoning-effort',choices=['low','high'],default='low')
p.add_argument('--variant',choices=['baseline','concise','mtp'],default='baseline')
p.add_argument('--warm-all',action='store_true')
a=p.parse_args()
cases=json.loads(pathlib.Path(a.cases_json).read_text()) if a.cases_json else {d.name:(d/'app.py').read_text() for d in sorted(pathlib.Path(a.fixtures).iterdir()) if d.is_dir()}
def request(case, concurrency, iteration, warmup=False):
    prompt='Authorized offline source-code security audit. Identify exploitable defects and safe controls. Cite source locations and propose a minimal local proof and remediation. Do not claim any proof was executed. Be concise.\n'+cases[case]
    if a.variant == 'concise':
        prompt += '\nOutput format: compact findings table only, followed by a single sentence for safe controls. Each finding must retain severity, exact source location, exploit preconditions, a minimal local proof proposal, and remediation. Avoid introductions, repeated code, and repeated explanations. Merge duplicate root causes. Do not omit distinct supported findings to meet a length target.'
    body={'model':'glm-5.3','messages':[{'role':'user','content':prompt}], 'stream':True,'stream_options':{'include_usage':True},'max_tokens':a.max_tokens,'temperature':0,'chat_template_kwargs':{'reasoning_effort':a.reasoning_effort}}
    started_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
    start=time.perf_counter(); first=visible=last=None; usage={}; reasons=[]; text=''; reasoning=''; error=None; done=False
    try:
        req=urllib.request.Request(a.base+'/chat/completions',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=600) as response:
            for raw in response:
                if not raw.startswith(b'data:'): continue
                data=raw[5:].strip()
                if data==b'[DONE]':
                    done=True
                    break
                chunk=json.loads(data)
                if chunk.get('error'): raise RuntimeError(str(chunk['error']))
                if chunk.get('usage'): usage=chunk['usage']
                for choice in chunk.get('choices',[]):
                    delta=choice.get('delta',{}); now=time.perf_counter()-start
                    if any(delta.get(k) for k in ('content','reasoning_content','reasoning','tool_calls')):
                        first=now if first is None else first; last=now
                    if delta.get('content'):
                        visible=now if visible is None else visible; text+=delta['content']
                    reasoning+=delta.get('reasoning_content') or delta.get('reasoning') or ''
                    if choice.get('finish_reason'): reasons.append(choice['finish_reason'])
        if not done or not reasons or not usage:
            raise RuntimeError('Incomplete SSE response: missing DONE, finish reason, or usage')
    except Exception as e: error=repr(e)
    elapsed=time.perf_counter()-start; tokens=usage.get('completion_tokens',0)
    return {'started_at':started_at,'case':case,'concurrency':concurrency,'iteration':iteration,'warmup':warmup,'ttft_s':first,'first_visible_s':visible,'ttot_s':last,'e2e_s':elapsed,'approx_tpot_s':(last-first)/(tokens-1) if first is not None and last is not None and tokens>1 else None,'usage':usage,'finish_reasons':reasons,'answer':text,'reasoning_chars':len(reasoning),'error':error,'max_tokens':a.max_tokens}

rows=[]
with open(a.out,'w') as f:
    def save(row):
        row['reasoning_effort']=a.reasoning_effort
        row['variant']=a.variant
        row['useful_completion']=not row['error'] and bool(row['answer'].strip()) and 'stop' in row['finish_reasons']
        rows.append(row); f.write(json.dumps(row)+'\n'); f.flush()
        print(json.dumps({k:v for k,v in row.items() if k not in ('answer',)}),flush=True)
    for case in (cases if a.warm_all else [next(iter(cases))]):
        save(request(case,1,-1,True))
    for c in (1,2):
        jobs=[(case,c,i) for i in range(a.repeats) for case in cases]
        start=time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=c) as pool:
            for row in pool.map(lambda args:request(*args),jobs): save(row)
        duration=time.perf_counter()-start
        selected=[r for r in rows if r['concurrency']==c and not r['warmup']]
        def quantile(xs,q):
            xs=sorted(xs); pos=(len(xs)-1)*q; low=int(pos); return xs[low]+(xs[min(low+1,len(xs)-1)]-xs[low])*(pos-low)
        summary={'type':'summary','concurrency':c,'requests':len(selected),'batch_s':duration,'output_tokens_per_s':sum(r['usage'].get('completion_tokens',0) for r in selected)/duration,'errors':sum(r['error'] is not None for r in selected),'truncated':sum('length' in r['finish_reasons'] for r in selected)}
        for metric in ('ttft_s','first_visible_s','ttot_s','e2e_s','approx_tpot_s'):
            xs=[r[metric] for r in selected if r[metric] is not None]
            summary[metric]={'n':len(xs),'mean':statistics.mean(xs),'p50':quantile(xs,.5),'p95':quantile(xs,.95)} if xs else None
        summary['useful_completions']=sum(r['useful_completion'] for r in selected)
        summary['reasoning_only']=sum(not r['answer'].strip() and r['reasoning_chars']>0 for r in selected)
        f.write(json.dumps(summary)+'\n'); f.flush(); print(json.dumps(summary),flush=True)
