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

## Smoke validation

From the repository root, with the API virtual environment activated:

```powershell
cd "$HOME\Desktop\fluxmed"
.\apps\api\.venv\Scripts\Activate.ps1
python scripts\benchmark_optimizer.py --smoke --seeds 101 202 303
```

The repository-level launcher adds `apps/api/src` to the Python module path, so the smoke benchmark does not depend on an editable package install merely to resolve the local `fluxmed` package.

Expected artifacts:

```text
benchmarks/results/smoke/benchmark-report.json
benchmarks/results/smoke/benchmark-runs.csv
```


## Existing Santa Aurora operation

The benchmark runner can load an existing operation read-only. It reuses the same delivery,
vehicle-cost, helper-availability, timezone and routing-matrix transformations used by the
production optimizer, then closes the SQLAlchemy session with a rollback.

For a fast development validation:

```powershell
cd "$HOME\Desktop\fluxmed"
.\apps\api\.venv\Scripts\Activate.ps1
python scripts\benchmark_optimizer.py --operation-code OP-20260915-001 --quick --seeds 101
```

For an evidence-oriented run, omit `--quick` and provide the chosen seed set explicitly.


## Scenario matrix development mode

Matrix mode generates deliveries in memory from the same Santa Aurora scenario generator used by
the application. The existing operation contributes the selected fleet/workforce, operation
window, traffic mode and road overrides; benchmark deliveries are never persisted.

Validate one small cell before running a larger matrix:

```powershell
python scripts\benchmark_optimizer.py \
  --matrix-template-code OP-20260915-001 \
  --profiles NORMAL \
  --sizes 20 \
  --scenario-seeds 20260917 \
  --quick \
  --seeds 101
```

The final academic matrix targets all four profiles and 20/40/60/80 deliveries with an explicitly
recorded GA seed set. Do not use `--quick` for final evidence.


## Convergence evidence

Each GA benchmark now records the optimizer's real progress callback. In addition to the raw run
CSV and JSON report, the runner emits:

- `benchmark-summaries.csv`: report-ready summary statistics;
- `benchmark-convergence.csv`: generation-by-generation best fitness, feasibility, diversity,
  adaptive mutation and elapsed time.

`candidate_evaluations` counts individuals passed through the optimizer evaluation step:
two internal baseline evaluations plus the configured population for generation zero and every
completed generation. `time_to_best_seconds` is measured from optimizer start to the progress
event that last improved the final best solution.


## Reproducible academic artifacts

Every benchmark export now creates `charts/` with dependency-free SVG charts and an
`academic-summary.md` table. The charts aggregate only compatible optimizer metrics:

- feasibility rate by delivery count;
- mean optimizer cost for feasible runs;
- runtime by scale;
- GA hard-violation ablation by scale;
- convergence of hard violations on the hardest scenario present in the report.

The final evidence preset is intentionally explicit and reproducible:

```powershell
python scripts\benchmark_optimizer.py \
  --matrix-template-code OP-20260915-001 \
  --preset final
```

It runs NORMAL/BUSY/HIGH_PRESSURE/EMERGENCY at 20/40/60/80 deliveries, one deterministic
scenario seed (`20260917`) and five GA seeds (`101 202 303 404 505`). It uses the production
GA configuration, never `--quick`, and writes to
`benchmarks/results/final-evidence-20260917` unless `--output` is supplied.
