# Phase 17 — Academic benchmark plan

## Goal

Produce reproducible evidence for the Tech Challenge report and presentation without changing the production optimizer semantics.

## Comparison methods

- Nearest Neighbor
- Best Insertion
- GA basic
- GA + advanced pruning
- GA + advanced pruning + repair

The production default remains advanced pruning + repair. Benchmark flags exist only to make controlled ablation comparisons possible.

## Scenario matrix

Target profiles:

- NORMAL
- BUSY
- HIGH_PRESSURE
- EMERGENCY

Target sizes:

- 20
- 40
- 60
- 80 deliveries

The complete 4x4 matrix does not need to run on every development iteration. A representative subset is used during development; the final evidence run must record exactly which cells and seeds were executed.

## Repetitions

Baselines are deterministic and run once per scenario instance.

GA variants run with multiple explicit seeds. Final academic evidence should use at least five seeds per selected scenario cell unless measured runtime makes that impractical; any reduction must be documented.

## Metrics

Primary:

- feasibility rate
- hard violations
- cost
- makespan
- runtime

Secondary:

- distance
- vehicles used
- service penalty/on-time proxy
- critical risk
- pruning counts
- generations completed / stop reason

Later Phase 17 increments add evaluations, time-to-best, convergence series and charts.

## Fairness rules

- The same deliveries, vehicles, travel matrix and operation window are reused across methods within one scenario instance.
- Baselines do not receive GA repair.
- GA basic keeps basic payload/volume assignment constraints but disables advanced pruning and repair.
- GA + pruning enables refrigeration/range/hard-window/team pruning but disables repair.
- GA + pruning + repair matches the production optimizer behavior.
- When advanced pruning is disabled, invalid advanced assignments remain visible as hard violations instead of being silently treated as feasible.
- Cost metrics from optimizer fitness must not be mixed with persisted final operational cost unless their scopes are explicitly identified.

## First increment

Implemented:

- benchmark data model;
- baseline + three GA variants runner;
- summary statistics (best/mean/std/worst cost, feasibility, runtime, makespan);
- JSON/CSV export;
- deterministic smoke CLI;
- unit coverage for method matrix and pruning ablation semantics.

Second increment:

- read-only loader for an existing Santa Aurora operation;
- shared optimizer input transformations for deliveries, vehicles, timezone and operation window;
- routing matrix rebuilt from the selected operation without persisting benchmark changes;
- CLI support for `--operation-code` and a reduced `--quick` validation mode.

Third increment:

- validated the read-only loader against OP-20260915-001;
- added in-memory scenario-matrix generation using the production scenario generator;
- added deterministic scenario delivery IDs and the production service-time estimator;
- added matrix orchestration, progress output and a machine-readable manifest;
- added city-scoped scenario address pools so benchmark generation cannot mix cities.

Validation completed:

- NORMAL validated from 20 to 80 deliveries;
- BUSY, HIGH_PRESSURE and EMERGENCY validated at 20/40/60/80;
- infeasibility diagnostics distinguish unassigned deliveries from route hard violations;
- runtime remains practical for an evidence run.

Fourth increment:

- convergence series captured from the real GA progress callback;
- candidate-evaluation count recorded per GA run;
- best generation and time-to-best recorded;
- dedicated summary and convergence CSV artifacts added.

Validation completed:

- convergence artifacts validated on NORMAL x 20;
- lint, format, mypy and targeted benchmark tests are green.

Fifth increment:

- dependency-free SVG charts generated from benchmark evidence;
- report-ready Markdown summary table generated automatically;
- matrix manifest records the exact GA configuration;
- final evidence preset fixed at all four profiles x 20/40/60/80;
- final GA seeds fixed at 101/202/303/404/505 with scenario seed 20260917.

Final academic evidence — completed:

- The full 4 profiles × 4 scales preset was executed on the synthetic Santa Aurora benchmark; `quick=false`.
- The 16 scenarios have one scenario seed (`20260917`) and five GA seeds each (101/202/303/404/505), producing 272 method runs (32 deterministic baseline runs + 240 GA runs).
- The original result set was preserved at `benchmarks/results/final-evidence-20260917/`, including the manifest, CSV summaries, per-run CSV, convergence data, full JSON report, and five SVG charts.
- The GitHub evidence should be interpreted through `benchmarks/README.md` and the generated `academic-summary.md`.
- Measured feasibility: Nearest Neighbor 5/16, Best Insertion 3/16, GA Basic 14/80, GA + Pruning 60/80, GA + Pruning + Repair 80/80. Benchmarks establish observed viability and performance **within the sampled scenarios only**; they do not establish a global optimality guarantee.
- Mean optimizer runtime of GA + Pruning + Repair: 56.309 seconds; GA + Pruning: 37.046 seconds. Repair improves feasibility at a computational cost, not a guaranteed cost reduction.

Outstanding academic reproducibility qualification:

- The manifest identifies `template_operation_code=OP-20260915-001`, but this operation's persisted resource selections, planning window and road overrides are **not** recreated by a clean Docker seed. The archived measurements remain independently inspectable, but exact execution reproducibility requires a sanitized operation fixture or clear reconstruction instructions. Do not claim the benchmark can be regenerated from a fresh clone with the seed alone.
- Report the synthetic-data scope, single scenario seed per cell, and hardware dependence of runtime. Do not equate optimizer fitness cost and persisted operational total cost.
- Integrate real experimental tables/charts into the Tech Challenge report and presentation rather than using a smoke test as evidence.
