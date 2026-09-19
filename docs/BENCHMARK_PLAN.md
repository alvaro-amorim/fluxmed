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

Next:

1. validate the loader against OP-20260915-001 locally;
2. add scenario-matrix orchestration for NORMAL/BUSY/HIGH_PRESSURE/EMERGENCY x 20/40/60/80;
3. persist convergence/evaluation/time-to-best series;
4. generate academic charts and report-ready tables.
