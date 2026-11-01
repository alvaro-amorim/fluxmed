# FluxMed benchmark academic summary

Baselines are deterministic and run once per scenario. GA variants use the explicit seed set recorded in the matrix manifest.
Costs are reported only for feasible runs and should be compared within the same scenario. The paired pruning/repair chart uses only matched feasible scenario+seed pairs.
Runtime includes optimizer execution only, excluding scenario generation and artifact export.

## Overall feasibility

| Method | Feasible | Rate | Mean runtime (s) |
|---|---:|---:|---:|
| Nearest Neighbor | 5/16 | 31.25% | 0.015 |
| Best Insertion | 3/16 | 18.75% | 0.111 |
| GA Basic | 13/80 | 16.25% | 51.325 |
| GA + Pruning | 62/80 | 77.50% | 49.810 |
| GA + Pruning + Repair | 80/80 | 100.00% | 82.846 |

## Scenario-level results

| Scenario | Method | Feasible | Mean cost | Std cost | Mean runtime (s) | Mean evals | Mean time-to-best (s) |
|---|---|---:|---:|---:|---:|---:|---:|
| NORMAL-20-S20260917 | Nearest Neighbor | 1/1 | 1960.23 | 0.00 | 0.010 |  |  |
| NORMAL-20-S20260917 | Best Insertion | 1/1 | 1928.97 | 0.00 | 0.017 |  |  |
| NORMAL-20-S20260917 | GA Basic | 5/5 | 1415.44 | 201.64 | 12.175 | 3794 | 8.378 |
| NORMAL-20-S20260917 | GA + Pruning | 5/5 | 1646.54 | 146.29 | 14.421 | 4370 | 10.666 |
| NORMAL-20-S20260917 | GA + Pruning + Repair | 5/5 | 1470.67 | 145.17 | 15.735 | 4687 | 12.025 |
| NORMAL-40-S20260917 | Nearest Neighbor | 1/1 | 2608.59 | 0.00 | 0.013 |  |  |
| NORMAL-40-S20260917 | Best Insertion | 0/1 |  |  | 0.052 |  |  |
| NORMAL-40-S20260917 | GA Basic | 5/5 | 2492.66 | 118.07 | 41.996 | 4946 | 35.669 |
| NORMAL-40-S20260917 | GA + Pruning | 5/5 | 2510.38 | 108.24 | 26.265 | 3036 | 15.824 |
| NORMAL-40-S20260917 | GA + Pruning + Repair | 5/5 | 2284.35 | 124.80 | 32.434 | 3448 | 22.254 |
| NORMAL-60-S20260917 | Nearest Neighbor | 0/1 |  |  | 0.018 |  |  |
| NORMAL-60-S20260917 | Best Insertion | 0/1 |  |  | 0.103 |  |  |
| NORMAL-60-S20260917 | GA Basic | 0/5 |  |  | 59.385 | 3554 | 39.428 |
| NORMAL-60-S20260917 | GA + Pruning | 5/5 | 2823.90 | 109.58 | 71.040 | 4428 | 54.708 |
| NORMAL-60-S20260917 | GA + Pruning + Repair | 5/5 | 2792.79 | 115.54 | 88.561 | 3324 | 56.774 |
| NORMAL-80-S20260917 | Nearest Neighbor | 0/1 |  |  | 0.024 |  |  |
| NORMAL-80-S20260917 | Best Insertion | 0/1 |  |  | 0.230 |  |  |
| NORMAL-80-S20260917 | GA Basic | 0/5 |  |  | 73.101 | 2776 | 42.153 |
| NORMAL-80-S20260917 | GA + Pruning | 5/5 | 3264.00 | 198.71 | 110.096 | 4552 | 86.649 |
| NORMAL-80-S20260917 | GA + Pruning + Repair | 5/5 | 3315.54 | 161.39 | 164.603 | 3631 | 117.804 |
| BUSY-20-S20260917 | Nearest Neighbor | 1/1 | 2076.45 | 0.00 | 0.003 |  |  |
| BUSY-20-S20260917 | Best Insertion | 1/1 | 1960.96 | 0.00 | 0.010 |  |  |
| BUSY-20-S20260917 | GA Basic | 0/5 |  |  | 15.148 | 3448 | 9.694 |
| BUSY-20-S20260917 | GA + Pruning | 5/5 | 1681.72 | 295.44 | 10.778 | 3285 | 6.821 |
| BUSY-20-S20260917 | GA + Pruning + Repair | 5/5 | 1979.71 | 91.65 | 8.493 | 2546 | 4.513 |
| BUSY-40-S20260917 | Nearest Neighbor | 0/1 |  |  | 0.006 |  |  |
| BUSY-40-S20260917 | Best Insertion | 0/1 |  |  | 0.037 |  |  |
| BUSY-40-S20260917 | GA Basic | 0/5 |  |  | 31.819 | 3832 | 25.430 |
| BUSY-40-S20260917 | GA + Pruning | 5/5 | 2634.21 | 156.54 | 20.324 | 2632 | 10.831 |
| BUSY-40-S20260917 | GA + Pruning + Repair | 5/5 | 2759.35 | 132.29 | 45.698 | 4015 | 32.254 |
| BUSY-60-S20260917 | Nearest Neighbor | 0/1 |  |  | 0.012 |  |  |
| BUSY-60-S20260917 | Best Insertion | 0/1 |  |  | 0.123 |  |  |
| BUSY-60-S20260917 | GA Basic | 0/5 |  |  | 56.172 | 3458 | 37.261 |
| BUSY-60-S20260917 | GA + Pruning | 5/5 | 3012.15 | 88.44 | 72.772 | 4504 | 58.853 |
| BUSY-60-S20260917 | GA + Pruning + Repair | 5/5 | 3008.92 | 141.54 | 79.251 | 2796 | 45.049 |
| BUSY-80-S20260917 | Nearest Neighbor | 0/1 |  |  | 0.043 |  |  |
| BUSY-80-S20260917 | Best Insertion | 0/1 |  |  | 0.301 |  |  |
| BUSY-80-S20260917 | GA Basic | 0/5 |  |  | 116.601 | 4226 | 86.818 |
| BUSY-80-S20260917 | GA + Pruning | 3/5 | 3656.03 | 232.41 | 88.419 | 3708 | 61.136 |
| BUSY-80-S20260917 | GA + Pruning + Repair | 5/5 | 3438.79 | 115.35 | 209.875 | 4639 | 152.987 |
| HIGH_PRESSURE-20-S20260917 | Nearest Neighbor | 1/1 | 2207.93 | 0.00 | 0.007 |  |  |
| HIGH_PRESSURE-20-S20260917 | Best Insertion | 0/1 |  |  | 0.017 |  |  |
| HIGH_PRESSURE-20-S20260917 | GA Basic | 3/5 | 1914.03 | 136.26 | 12.326 | 3410 | 7.998 |
| HIGH_PRESSURE-20-S20260917 | GA + Pruning | 5/5 | 1936.81 | 149.98 | 10.480 | 3208 | 6.368 |
| HIGH_PRESSURE-20-S20260917 | GA + Pruning + Repair | 5/5 | 1904.58 | 277.00 | 9.774 | 2901 | 5.533 |
| HIGH_PRESSURE-40-S20260917 | Nearest Neighbor | 0/1 |  |  | 0.017 |  |  |
| HIGH_PRESSURE-40-S20260917 | Best Insertion | 0/1 |  |  | 0.056 |  |  |
| HIGH_PRESSURE-40-S20260917 | GA Basic | 0/5 |  |  | 28.397 | 3352 | 18.427 |
| HIGH_PRESSURE-40-S20260917 | GA + Pruning | 5/5 | 2915.01 | 133.68 | 37.250 | 4600 | 29.445 |
| HIGH_PRESSURE-40-S20260917 | GA + Pruning + Repair | 5/5 | 2750.23 | 191.10 | 50.222 | 3487 | 35.129 |
| HIGH_PRESSURE-60-S20260917 | Nearest Neighbor | 0/1 |  |  | 0.025 |  |  |
| HIGH_PRESSURE-60-S20260917 | Best Insertion | 0/1 |  |  | 0.199 |  |  |
| HIGH_PRESSURE-60-S20260917 | GA Basic | 0/5 |  |  | 68.581 | 4159 | 50.810 |
| HIGH_PRESSURE-60-S20260917 | GA + Pruning | 4/5 | 3035.93 | 44.26 | 75.319 | 5138 | 59.720 |
| HIGH_PRESSURE-60-S20260917 | GA + Pruning + Repair | 5/5 | 3095.51 | 172.39 | 104.179 | 3823 | 76.275 |
| HIGH_PRESSURE-80-S20260917 | Nearest Neighbor | 0/1 |  |  | 0.018 |  |  |
| HIGH_PRESSURE-80-S20260917 | Best Insertion | 0/1 |  |  | 0.233 |  |  |
| HIGH_PRESSURE-80-S20260917 | GA Basic | 0/5 |  |  | 94.220 | 3765 | 66.202 |
| HIGH_PRESSURE-80-S20260917 | GA + Pruning | 0/5 |  |  | 88.387 | 4053 | 63.448 |
| HIGH_PRESSURE-80-S20260917 | GA + Pruning + Repair | 5/5 | 3526.05 | 152.66 | 229.744 | 5436 | 184.569 |
| EMERGENCY-20-S20260917 | Nearest Neighbor | 1/1 | 1845.12 | 0.00 | 0.007 |  |  |
| EMERGENCY-20-S20260917 | Best Insertion | 1/1 | 1965.19 | 0.00 | 0.017 |  |  |
| EMERGENCY-20-S20260917 | GA Basic | 0/5 |  |  | 16.517 | 4476 | 12.917 |
| EMERGENCY-20-S20260917 | GA + Pruning | 5/5 | 1695.08 | 140.74 | 11.094 | 3208 | 6.844 |
| EMERGENCY-20-S20260917 | GA + Pruning + Repair | 5/5 | 1977.24 | 72.39 | 16.887 | 4140 | 13.232 |
| EMERGENCY-40-S20260917 | Nearest Neighbor | 0/1 |  |  | 0.008 |  |  |
| EMERGENCY-40-S20260917 | Best Insertion | 0/1 |  |  | 0.039 |  |  |
| EMERGENCY-40-S20260917 | GA Basic | 0/5 |  |  | 41.906 | 4351 | 32.677 |
| EMERGENCY-40-S20260917 | GA + Pruning | 5/5 | 2712.61 | 220.87 | 31.539 | 4284 | 22.929 |
| EMERGENCY-40-S20260917 | GA + Pruning + Repair | 5/5 | 2789.35 | 170.86 | 55.559 | 4015 | 39.462 |
| EMERGENCY-60-S20260917 | Nearest Neighbor | 0/1 |  |  | 0.013 |  |  |
| EMERGENCY-60-S20260917 | Best Insertion | 0/1 |  |  | 0.101 |  |  |
| EMERGENCY-60-S20260917 | GA Basic | 0/5 |  |  | 59.302 | 3900 | 47.784 |
| EMERGENCY-60-S20260917 | GA + Pruning | 0/5 |  |  | 39.171 | 3074 | 23.921 |
| EMERGENCY-60-S20260917 | GA + Pruning + Repair | 5/5 | 3246.19 | 128.74 | 85.537 | 3410 | 60.804 |
| EMERGENCY-80-S20260917 | Nearest Neighbor | 0/1 |  |  | 0.018 |  |  |
| EMERGENCY-80-S20260917 | Best Insertion | 0/1 |  |  | 0.244 |  |  |
| EMERGENCY-80-S20260917 | GA Basic | 0/5 |  |  | 93.548 | 3996 | 66.419 |
| EMERGENCY-80-S20260917 | GA + Pruning | 0/5 |  |  | 89.612 | 4629 | 70.929 |
| EMERGENCY-80-S20260917 | GA + Pruning + Repair | 5/5 | 3780.55 | 139.62 | 128.979 | 3429 | 91.293 |
