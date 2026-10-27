from pathlib import Path
from collections import defaultdict
import csv,hashlib,io,json,itertools,math,random,statistics,zipfile

OUT=Path('/workspace/work/rebenchmark-real-20261027')
assert (OUT/'completed.json').exists(),'Wait until all declared runs finish.'
allrows=[json.loads(x) for x in (OUT/'events.jsonl').read_text().splitlines()]
rows=[x for x in allrows if not x['warmup']]
assert len(rows)==432 and len(allrows)==464
assert all(x['status']==0 for x in allrows)
groups=defaultdict(list)
for x in rows:groups[(x['kind'],x['config'],x['project'],x['mode'])].append(x)
rng=random.Random(20261028);results={}
def mean(values):
 values=list(values)
 return math.fsum(values)/len(values)
def quantile(values,q):
 i=(len(values)-1)*q;lo=math.floor(i);hi=math.ceil(i)
 return values[lo]+(values[hi]-values[lo])*(i-lo)
for key,rs in sorted(groups.items()):
 blocks=defaultdict(list)
 for x in rs:blocks[(x['batch'],x['block'])].append(x)
 expected=6 if key[0]=='AB' else 3
 assert len(blocks)==expected
 metrics={}
 for metric in ['wall_s','cpu_s','rss_kib']:
  by_batch=defaultdict(list)
  for (batch,block),xs in sorted(blocks.items()):
   assert len(xs)==4 and sum(x['label']=='A' for x in xs)==2
   a=[math.log(x[metric]) for x in xs if x['label']=='A'];b=[math.log(x[metric]) for x in xs if x['label']=='B']
   by_batch[batch].append(mean(b)-mean(a))
  log_delta=mean(v for vs in by_batch.values() for v in vs)
  # Equal block counts per batch allow exhaustive hierarchical resampling:
  # 12^3=1728 outcomes for AB; 3^3=27 outcomes for AA.
  assert len({len(v) for v in by_batch.values()})==1
  choices=[]
  for vs in by_batch.values():
   choices.extend(mean(xs) for xs in itertools.product(vs,repeat=len(vs)))
  draws=[100*math.expm1(mean(xs)) for xs in itertools.product(choices,repeat=3)]
  draws.sort()
  metrics[metric]={'baseline_median':statistics.median(x[metric] for x in rs if x['label']=='A'),'candidate_median':statistics.median(x[metric] for x in rs if x['label']=='B'),'baseline_geomean':math.exp(mean(math.log(x[metric]) for x in rs if x['label']=='A')),'candidate_geomean':math.exp(mean(math.log(x[metric]) for x in rs if x['label']=='B')),'change_pct':100*math.expm1(log_delta),'ci95_pct':[quantile(draws,.025),quantile(draws,.975)],'batch_change_pct':{str(k):100*math.expm1(mean(v)) for k,v in by_batch.items()},'block_log_deltas':dict((str(k),v) for k,v in by_batch.items()),'bootstrap_outcomes':len(draws)}
 results['/'.join(key)]={'kind':key[0],'config':key[1],'project':key[2],'mode':key[3],'blocks':len(blocks),'runs_per_label':len(rs)//2,'metrics':metrics,'throttled_runs':{label:sum(x['cpu_delta']['nr_throttled']>0 for x in rs if x['label']==label) for label in ['A','B']},'throttle_usec':{label:sum(x['cpu_delta'].get('throttled_usec',0) for x in rs if x['label']==label) for label in ['A','B']},'memory_max_events':sum(x['memory_event_delta'].get('max',0) for x in rs)}

# Equal project weights, with a common resampled batch for all projects.
aggregates={}
for cfg in ['single','parallel4']:
 for mode in ['emit','noemit']:
  for metric in ['wall_s','cpu_s']:
   cells=[results[f'AB/{cfg}/{p}/{mode}']['metrics'][metric] for p in ['xstate','zod','self','compiler-fixture']]
   logs=[mean(v for vs in c['block_log_deltas'].values() for v in vs) for c in cells]
   draws=[]
   for _ in range(20000):
    bs=rng.choices(['0','1','2'],k=3);sample=[]
    for c in cells:
     sample.append(mean(v for b in bs for v in rng.choices(c['block_log_deltas'][b],k=2)))
    draws.append(100*math.expm1(mean(sample)))
   draws.sort();aggregates[f'{cfg}/{mode}/{metric}']={'change_pct':100*math.expm1(mean(logs)),'ci95_pct':[draws[499],draws[19499]],'weighting':'equal weight for each of four projects'}

summary={'method':'balanced four-run blocks; hierarchical bootstrap batches then blocks; unadjusted pointwise 95% intervals; no outlier exclusions','groups':results,'aggregates':aggregates,'runs':len(rows),'warmups':len(allrows)-len(rows)}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2))
buf=io.StringIO();w=csv.writer(buf);w.writerow(['comparison','config','project','mode','metric','baseline_median','candidate_median','baseline_geomean','candidate_geomean','change_pct','ci95_low','ci95_high','batch0_pct','batch1_pct','batch2_pct'])
for key,x in results.items():
 for metric,m in x['metrics'].items():w.writerow([x['kind'],x['config'],x['project'],x['mode'],metric,m['baseline_median'],m['candidate_median'],m['baseline_geomean'],m['candidate_geomean'],m['change_pct'],*m['ci95_pct'],*[m['batch_change_pct'][str(i)] for i in range(3)]])
(OUT/'summary.csv').write_text(buf.getvalue())
buf=io.StringIO();w=csv.writer(buf);w.writerow(['seq','comparison','config','project','mode','batch','block','pattern','label','actual_binary','warmup','wall_s','cpu_s','rss_kib','throttled_periods','throttled_usec','status'])
for x in allrows:w.writerow([x['seq'],x['kind'],x['config'],x['project'],x['mode'],x['batch'],x['block'],x['pattern'],x['label'],x['actual_binary'],x['warmup'],x['wall_s'],x['cpu_s'],x['rss_kib'],x['cpu_delta']['nr_throttled'],x['cpu_delta'].get('throttled_usec',0),x['status']])
(OUT/'runs.csv').write_text(buf.getvalue())
for key,x in results.items():
 m=x['metrics']['wall_s'];print(key,'wall',round(m['baseline_median'],4),'->',round(m['candidate_median'],4),'change',round(m['change_pct'],2),'CI',[round(v,2) for v in m['ci95_pct']],'batches',[round(v,2) for v in m['batch_change_pct'].values()])
print('AGGREGATES',json.dumps(aggregates))
