from pathlib import Path
import hashlib,json,os,random,subprocess,time,math

ROOT=Path('/workspace/work'); OUT=ROOT/'rebenchmark-real-20261027'
BIN={'A':ROOT/'bins/solution-cli-baseline','B':ROOT/'bins/solution-cli-bounded'}
CONFIGS={'single':{'procs':'1','cpus':[2],'flags':['--singleThreaded']},'parallel4':{'procs':'4','cpus':[0,1,2,3],'flags':[]}}
PROJECTS=['xstate','zod','self','compiler-fixture']
CELLS=[(c,p,m) for c in CONFIGS for p in PROJECTS for m in ['emit','noemit']]
os.sched_setaffinity(0,{4})
assert not (OUT/'events.jsonl').exists(),'Use a fresh directory; do not append duplicate runs.'
EXPECTED=json.loads((ROOT/'solution-followup/cli-build-info.json').read_text())
for label,name in [('A','baseline'),('B','bounded')]:
 assert hashlib.sha256(BIN[label].read_bytes()).hexdigest()==EXPECTED[name]['sha256']

def read(path):
 try:return Path(path).read_text()
 except FileNotFoundError:return None
def counters(path):
 t=read(path)
 if t is None:return {}
 return {x.split()[0]:int(x.split()[1]) for x in t.splitlines() if len(x.split())==2}
def state():
 return {'cpu':counters('/sys/fs/cgroup/cpu.stat'),'memory':counters('/sys/fs/cgroup/memory.events'),'memory_current':int(read('/sys/fs/cgroup/memory.current')),'load':read('/proc/loadavg'),'proc_stat':read('/proc/stat')}
def output_manifest(project):
 folder=ROOT/'workloads'/project/'out'
 return {str(p.relative_to(folder)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.rglob('*')) if p.is_file()}
def append(row):
 with (OUT/'events.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')

# Resolve and hash exactly the files that the compiler will read.
inputs={}
for project in PROJECTS:
 cmd=[str(BIN['A']),'--project','tsconfig.json','--listFilesOnly','--pretty','false','--singleThreaded']
 env=os.environ.copy();env['GOMAXPROCS']='1'
 p=subprocess.run(cmd,cwd=ROOT/'workloads'/project,env=env,capture_output=True,text=True,check=True)
 (OUT/(project+'-list-files.txt')).write_text(p.stdout)
 for line in p.stdout.splitlines():
  path=Path(line.strip())
  if path.is_file():inputs[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
 config=ROOT/'workloads'/project/'tsconfig.json';inputs[str(config)]=hashlib.sha256(config.read_bytes()).hexdigest()
(OUT/'inputs.json').write_text(json.dumps(inputs,indent=2))
settings={'seed':20261027,'batches':3,'blocks_per_batch':2,'runs_per_variant_cell':12,'block_patterns':['ABBA','BAAB'],'analysis':'within-block mean log(B)-mean log(A), hierarchical bootstrap by batch then block','binary_info':EXPECTED,'configs':CONFIGS,'cpu_max':read('/sys/fs/cgroup/cpu.max'),'memory_max':read('/sys/fs/cgroup/memory.max'),'cpus_effective':read('/sys/fs/cgroup/cpuset.cpus.effective'),'cpuinfo':read('/proc/cpuinfo'),'initial_state':state(),'started_utc':time.strftime('%Y-%m-%d %H:%M:%S UTC',time.gmtime())}
(OUT/'settings.json').write_text(json.dumps(settings,indent=2))
seq=0
def run(kind,cell,batch,block,pattern,label,index,warm=False):
 global seq
 seq+=1;config,project,mode=cell;cfg=CONFIGS[config]
 actual='A' if kind=='AA' else label
 cmd=[str(BIN[actual]),'--project','tsconfig.json','--pretty','false',*cfg['flags']]
 if mode=='noemit':cmd+=['--noEmit']
 env=os.environ.copy();env['GOMAXPROCS']=cfg['procs']
 logfile=f'{seq:04d}-{kind}-{config}-{project}-{mode}-{label}.txt'
 before=state();start=time.perf_counter()
 with (OUT/logfile).open('wb') as f:
  p=subprocess.Popen(cmd,cwd=ROOT/'workloads'/project,env=env,stdout=f,stderr=subprocess.STDOUT,preexec_fn=lambda:os.sched_setaffinity(0,cfg['cpus']))
  _,status,usage=os.wait4(p.pid,0);p.returncode=os.waitstatus_to_exitcode(status)
 elapsed=time.perf_counter()-start;after=state()
 row={'seq':seq,'kind':kind,'config':config,'project':project,'mode':mode,'batch':batch,'block':block,'pattern':pattern,'label':label,'actual_binary':actual,'index':index,'warmup':warm,'status':p.returncode,'wall_s':elapsed,'user_s':usage.ru_utime,'system_s':usage.ru_stime,'cpu_s':usage.ru_utime+usage.ru_stime,'rss_kib':usage.ru_maxrss,'log':logfile,'argv':cmd,'before':before,'after':after,'cpu_delta':{k:after['cpu'][k]-before['cpu'].get(k,0) for k in after['cpu']},'memory_event_delta':{k:after['memory'][k]-before['memory'].get(k,0) for k in after['memory']}}
 append(row)
 if p.returncode:raise RuntimeError(row)
 return row

rng=random.Random(20261027)
warm=CELLS.copy();rng.shuffle(warm);manifests={}
for cell in warm:
 labels=['A','B'];rng.shuffle(labels)
 for i,label in enumerate(labels):
  run('AB',cell,-1,-1,'warmup',label,i,True)
  if cell[2]=='emit':
   manifest=output_manifest(cell[1]);key=cell[0]+'/'+cell[1]
   if key in manifests:assert manifest==manifests[key],'Emitted files differ: '+key
   else:manifests[key]=manifest
 print('warmup',*cell,flush=True)
(OUT/'output-manifests.json').write_text(json.dumps(manifests,indent=2))

for batch in range(3):
 for round_no in range(2):
  jobs=[('AB',cell) for cell in CELLS]
  if round_no==0:jobs += [('AA',(config,'compiler-fixture',mode)) for config in CONFIGS for mode in ['emit','noemit']]
  rng.shuffle(jobs)
  for kind,cell in jobs:
   cell_no=CELLS.index(cell)
   pattern='ABBA' if (batch+round_no+cell_no)%2==0 else 'BAAB'
   block=batch*2+round_no
   for i,label in enumerate(pattern):run(kind,cell,batch,block,pattern,label,i)
   print('block',batch,round_no,kind,*cell,pattern,flush=True)
 print('BATCH_COMPLETE',batch,flush=True)

for filename,digest in inputs.items():assert hashlib.sha256(Path(filename).read_bytes()).hexdigest()==digest,'Input changed: '+filename
for label,name in [('A','baseline'),('B','bounded')]:assert hashlib.sha256(BIN[label].read_bytes()).hexdigest()==EXPECTED[name]['sha256']
(OUT/'completed.json').write_text(json.dumps({'runs':seq,'finished_utc':time.strftime('%Y-%m-%d %H:%M:%S UTC',time.gmtime()),'final_state':state(),'input_hashes_unchanged':True,'binary_hashes_unchanged':True},indent=2))
print('COMPLETE',seq,flush=True)
