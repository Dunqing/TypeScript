import json, math, random, statistics, sys
from collections import defaultdict
rows = [json.loads(l) for l in open('/home/user/bench/results/runs.jsonl')]
assert all(r['status'] in (0, 2) for r in rows)
by = defaultdict(dict)
for r in rows: by[(r['project'], r['config'], r['mode'], r['round'])][r['label']] = r
def ci(xs, n=4000, seed=1):
    rng = random.Random(seed); ms = sorted(statistics.fmean(rng.choices(xs, k=len(xs))) for _ in range(n))
    return ms[int(.025 * n)], ms[int(.975 * n)]
pct = lambda x: (math.exp(x) - 1) * 100
cells = sorted({k[:3] for k in by}, key=lambda c: (['ts58', 'datefns', 'rxjs', 'xstate', 'zod'].index(c[0]), c[1], c[2]))
metric = sys.argv[1] if len(sys.argv) > 1 else 'cpu_s'
print(f'metric={metric}: mean within-round change vs base, 95% bootstrap CI')
print(f"{'project':8} {'config':8} {'mode':6} {'n':>3} {'base med':>9} | {'base2 (A/A)':>22} | {'bounded3':>22} | {'shape':>22}")
for cell in cells:
    rounds = [v for k, v in by.items() if k[:3] == cell]
    base = statistics.median(r['base'][metric] for r in rounds)
    line = f'{cell[0]:8} {cell[1]:8} {cell[2]:6} {len(rounds):3} {base:9.3f}'
    for label in ['base2', 'bounded3', 'shape']:
        xs = [math.log(r[label][metric] / r['base'][metric]) for r in rounds]
        lo, hi = ci(xs)
        line += f' | {pct(statistics.fmean(xs)):+6.2f}% [{pct(lo):+5.1f},{pct(hi):+5.1f}]'
    print(line)
