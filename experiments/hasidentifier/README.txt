WIP: SourceFile.HasIdentifier literal reservation investigation

Base: 49e69830214c55a8cc361aa3c4e7412d0afd02fe
Candidate: bounded3, the exact production source used for the latest benchmarks.
This is an experimental checkpoint, not a merge-ready optimization.

Known limitations
- Whole-project speedups have not been established. Default parallel runs show
  a possible regression; A/A controls also show substantial variation.
- A padded direct-eval example still fails under literal filtering. See eval/.
- Small/low-diversity inputs deliberately keep the original reservations.
- The map-representation optimization relies on Go 1.27 clear retaining capacity.

Validation
The exact production and black-box test bytes passed npx hereby validate using
Go 1.27.3 and an overlay, with GOTMPDIR=/tmp and -gcflags=all=-dwarf=false.
See validation.txt. No implementation or test changes were made when saving
this checkpoint; benchmark records were collected separately afterward.

Contents
- tsc/internal/ast/ast.go: latest adaptive collector, physically saved in this branch.
- tsc/internal/ast/identifier_reservation_heuristic_test.go: standalone tests.
- investigation.txt: detailed investigation and prior measurements.
- real-projects/: latest 432 measured runs plus 32 warmups, summaries, settings,
  input/output hashes, and the exact randomized ABBA/BAAB driver and analysis.
- microbenchmarks/: measured summaries and Linux-only benchmark source snapshots.
- eval/: original and padded known semantic counterexample with emitted JS.

Reproduction
The recorded Python drivers use the original /workspace/work directory layout.
Adjust ROOT/OUT if relocating. Source projects are XState core 5.19.2, Zod 3.24.2,
TypeScript API source at the base revision, and the historical compiler fixture.
Use the saved project configurations and input hashes; timings use full fresh
process compilations, not incremental builds. Shared libraries and the two CLI
binaries were in /workspace/work/bins. Build flags and SHA-256 are in settings.

For the Linux-only local microbenchmarks, copy the .go.txt snapshots from
microbenchmarks/sources to tsc/internal/ast, removing only the final .txt suffix,
then run go test -run='^$' -bench=BenchmarkBoundedSameBinary -benchmem ./internal/ast
from the tsc module. The helper contains the original collector for comparison
within the same test binary. These experimental helpers are not enabled in CI.

JSON/source evidence uses .txt suffixes to preserve the exact recorded bytes
without repository-wide formatters rewriting benchmark inputs or evidence.
Large compiled binaries, node_modules, Go caches and scratch variants are not
part of this checkpoint. AI assistance was used for implementation and analysis.

CSV line endings are normalized to LF for Git; recorded numerical values are unchanged.
