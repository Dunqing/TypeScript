# Interleaved real-project benchmark: base vs bounded3 vs shape, with an A/A control (base2 = byte-identical copy of base).
import hashlib, json, os, random, subprocess, sys, time
from pathlib import Path
B = Path('/home/user/bench'); OUT = B / 'results'; OUT.mkdir(exist_ok=True)
BINS = {k: B / 'bins' / f'tsc-{k}' for k in ['base', 'base2', 'bounded3', 'shape']}
PROJECTS = {'ts58': 8, 'datefns': 15, 'rxjs': 15, 'xstate': 15, 'zod': 15}  # rounds per cell
CONFIGS = {'single': {'procs': '1', 'cpus': {2}, 'flags': ['--singleThreaded']}, 'parallel': {'procs': '4', 'cpus': {0, 1, 2, 3}, 'flags': []}}
MODES = ['emit', 'noemit']
rng = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 20261027)

def manifest(project):
    out = B / 'work' / project / 'out'
    return {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file()}

def run(label, project, config, mode):
    cfg = CONFIGS[config]
    cmd = [str(BINS[label]), '-p', 'tsconfig.json', '--pretty', 'false', *cfg['flags']] + (['--noEmit'] if mode == 'noemit' else [])
    env = dict(os.environ, GOMAXPROCS=cfg['procs'])
    start = time.perf_counter()
    p = subprocess.Popen(cmd, cwd=B / 'work' / project, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=lambda: os.sched_setaffinity(0, cfg['cpus']))
    _, status, ru = os.wait4(p.pid, 0)
    wall = time.perf_counter() - start
    return {'label': label, 'project': project, 'config': config, 'mode': mode, 'status': os.waitstatus_to_exitcode(status),
            'wall_s': wall, 'cpu_s': ru.ru_utime + ru.ru_stime, 'rss_kib': ru.ru_maxrss}

# Correctness: every binary must emit byte-identical output to base.
diffs = {}
for project in PROJECTS:
    ref = None
    for label in BINS:
        run(label, project, 'parallel', 'emit')
        m = manifest(project)
        if ref is None: ref = m
        else:
            bad = sorted(k for k in set(ref) | set(m) if ref.get(k) != m.get(k))
            diffs[f'{project}/{label}'] = {'files': len(m), 'differing': bad}
        print('manifest', project, label, len(m), flush=True)
(OUT / 'output-diffs.json').write_text(json.dumps(diffs, indent=2))

cells = [(p, c, m) for p in PROJECTS for c in CONFIGS for m in MODES]
rows = []
with (OUT / 'runs.jsonl').open('w') as f:
    for cell in cells:  # warmup
        for label in BINS: run(label, *cell)
    max_rounds = max(PROJECTS.values())
    for rnd in range(max_rounds):
        order = cells[:]; rng.shuffle(order)
        for cell in order:
            if rnd >= PROJECTS[cell[0]]: continue
            labels = list(BINS); rng.shuffle(labels)
            for label in labels:
                r = run(label, *cell); r['round'] = rnd
                f.write(json.dumps(r) + '\n'); f.flush()
        print('round', rnd, 'done', flush=True)
print('COMPLETE', flush=True)
