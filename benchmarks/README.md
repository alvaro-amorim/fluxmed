# FluxMed academic benchmarks

This directory stores reproducible Phase 17 benchmark inputs and outputs.

- `scenarios/`: scenario manifests or generated scenario descriptors.
- `algorithms/`: method/configuration manifests used in benchmark runs.
- `results/`: raw JSON/CSV evidence. Large local batches should not be committed blindly.
- `notebooks/`: optional analysis notebooks generated only when they add value.

The first increment adds a deterministic smoke benchmark and the core runner for:

1. Nearest Neighbor
2. Best Insertion
3. GA basic
4. GA + advanced pruning
5. GA + advanced pruning + repair

The smoke dataset validates the benchmark machinery only. It is not academic evidence for Santa Aurora.
