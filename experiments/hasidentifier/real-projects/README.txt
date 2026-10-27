This run reuses the unchanged baseline and adaptive candidate CLI binaries.
No compiler source changes or rebuilds are part of this benchmark.

Protocol: three batches, two balanced ABBA/BAAB blocks per cell and batch.
Each block has two baseline and two candidate runs: twelve measurements per
variant/cell overall. Cell order is deterministically randomized per round.
All four project configurations run emit and noEmit in single-thread and
four-CPU configurations. Initial warm-ups are excluded and retained in logs.

Baseline-vs-baseline controls use exactly the same executable for both labels.
They cover the compiler fixture in both modes and CPU configurations, with one
four-run block per batch (six observations per label).

Primary comparison: mean within-block log time ratio. Confidence intervals use
hierarchical bootstrap over batches, then blocks. Medians and per-batch changes
are also reported. There is no outlier removal or early stopping based on results.
Every run records CPU time, wall time, peak RSS and cgroup throttle deltas.
