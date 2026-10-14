# FluxMed benchmark academic summary

Baselines are deterministic and run once per scenario. GA variants use the explicit seed set recorded in the matrix manifest.
Costs are reported only for feasible runs and should be compared within the same scenario. The paired pruning/repair chart uses only matched feasible scenario+seed pairs.
Runtime includes optimizer execution only, excluding scenario generation and artifact export.

## Overall feasibility

| Method | Feasible | Rate | Mean runtime (s) |
|---|---:|---:|---:|
| Nearest Neighbor | 5/16 | 31.25% | 0.012 |
| Best Insertion | 3/16 | 18.75% | 0.115 |
| GA Basic | 14/80 | 17.50% | 41.893 |
| GA + Pruning | 60/80 | 75.00% | 37.046 |
| GA + Pruning + Repair | 80/80 | 100.00% | 56.309 |

## Scenario-level results

| Scenario | Method | Feasible | Mean cost | Std cost | Mean runtime (s) | Mean evals | Mean time-to-best (s) |
|---|---|---:|---:|---:|---:|---:|---:|
| NORMAL-20-S20260917 | Nearest Neighbor | 1/1 | 535.67 | 0.00 | 0.002 |  |  |
| NORMAL-20-S20260917 | Best Insertion | 1/1 | 534.92 | 0.00 | 0.005 |  |  |
| NORMAL-20-S20260917 | GA Basic | 5/5 | 110.53 | 4.26 | 8.681 | 3372 | 5.656 |
| NORMAL-20-S20260917 | GA + Pruning | 5/5 | 107.66 | 3.55 | 6.747 | 2738 | 3.946 |
| NORMAL-20-S20260917 | GA + Pruning + Repair | 5/5 | 107.66 | 3.55 | 6.625 | 2738 | 3.675 |
| NORMAL-40-S20260917 | Nearest Neighbor | 1/1 | 603.61 | 0.00 | 0.012 |  |  |
| NORMAL-40-S20260917 | Best Insertion | 0/1 |  |  | 0.065 |  |  |
| NORMAL-40-S20260917 | GA Basic | 5/5 | 598.37 | 8.04 | 26.882 | 3986 | 19.176 |
| NORMAL-40-S20260917 | GA + Pruning | 5/5 | 218.75 | 9.02 | 23.523 | 3679 | 16.363 |
| NORMAL-40-S20260917 | GA + Pruning + Repair | 5/5 | 223.63 | 5.01 | 30.966 | 4572 | 24.102 |
| NORMAL-60-S20260917 | Nearest Neighbor | 0/1 |  |  | 0.024 |  |  |
| NORMAL-60-S20260917 | Best Insertion | 0/1 |  |  | 0.146 |  |  |
| NORMAL-60-S20260917 | GA Basic | 3/5 | 741.42 | 24.53 | 53.488 | 4274 | 40.857 |
| NORMAL-60-S20260917 | GA + Pruning | 5/5 | 695.17 | 14.15 | 37.959 | 3208 | 23.790 |
| NORMAL-60-S20260917 | GA + Pruning + Repair | 5/5 | 675.06 | 8.88 | 64.824 | 3256 | 41.384 |
| NORMAL-80-S20260917 | Nearest Neighbor | 0/1 |  |  | 0.017 |  |  |
| NORMAL-80-S20260917 | Best Insertion | 0/1 |  |  | 0.220 |  |  |
| NORMAL-80-S20260917 | GA Basic | 0/5 |  |  | 54.106 | 2719 | 30.315 |
| NORMAL-80-S20260917 | GA + Pruning | 5/5 | 846.36 | 18.23 | 70.353 | 3794 | 47.879 |
| NORMAL-80-S20260917 | GA + Pruning + Repair | 5/5 | 832.96 | 37.25 | 126.528 | 3765 | 100.258 |
| BUSY-20-S20260917 | Nearest Neighbor | 1/1 | 545.64 | 0.00 | 0.002 |  |  |
| BUSY-20-S20260917 | Best Insertion | 1/1 | 555.15 | 0.00 | 0.005 |  |  |
| BUSY-20-S20260917 | GA Basic | 1/5 | 137.60 | 0.00 | 9.148 | 3506 | 6.214 |
| BUSY-20-S20260917 | GA + Pruning | 5/5 | 111.97 | 3.18 | 9.538 | 3976 | 6.990 |
| BUSY-20-S20260917 | GA + Pruning + Repair | 5/5 | 115.03 | 4.46 | 9.310 | 3909 | 6.378 |
| BUSY-40-S20260917 | Nearest Neighbor | 0/1 |  |  | 0.006 |  |  |
| BUSY-40-S20260917 | Best Insertion | 0/1 |  |  | 0.038 |  |  |
| BUSY-40-S20260917 | GA Basic | 0/5 |  |  | 23.419 | 3583 | 15.623 |
| BUSY-40-S20260917 | GA + Pruning | 5/5 | 370.14 | 167.87 | 25.045 | 4149 | 18.248 |
| BUSY-40-S20260917 | GA + Pruning + Repair | 5/5 | 373.46 | 166.92 | 33.383 | 4101 | 24.209 |
| BUSY-60-S20260917 | Nearest Neighbor | 0/1 |  |  | 0.010 |  |  |
| BUSY-60-S20260917 | Best Insertion | 0/1 |  |  | 0.108 |  |  |
| BUSY-60-S20260917 | GA Basic | 0/5 |  |  | 41.760 | 3448 | 27.599 |
| BUSY-60-S20260917 | GA + Pruning | 5/5 | 730.54 | 27.38 | 37.100 | 3314 | 23.929 |
| BUSY-60-S20260917 | GA + Pruning + Repair | 5/5 | 703.58 | 24.67 | 66.252 | 3304 | 42.241 |
| BUSY-80-S20260917 | Nearest Neighbor | 0/1 |  |  | 0.017 |  |  |
| BUSY-80-S20260917 | Best Insertion | 0/1 |  |  | 0.242 |  |  |
| BUSY-80-S20260917 | GA Basic | 0/5 |  |  | 78.256 | 3909 | 59.622 |
| BUSY-80-S20260917 | GA + Pruning | 2/5 | 843.71 | 5.20 | 72.163 | 4063 | 52.675 |
| BUSY-80-S20260917 | GA + Pruning + Repair | 5/5 | 841.06 | 18.73 | 109.668 | 3266 | 69.855 |
| HIGH_PRESSURE-20-S20260917 | Nearest Neighbor | 1/1 | 542.34 | 0.00 | 0.004 |  |  |
| HIGH_PRESSURE-20-S20260917 | Best Insertion | 0/1 |  |  | 0.012 |  |  |
| HIGH_PRESSURE-20-S20260917 | GA Basic | 0/5 |  |  | 12.236 | 4716 | 9.703 |
| HIGH_PRESSURE-20-S20260917 | GA + Pruning | 5/5 | 114.02 | 3.10 | 7.418 | 3074 | 4.543 |
| HIGH_PRESSURE-20-S20260917 | GA + Pruning + Repair | 5/5 | 120.13 | 4.35 | 6.780 | 2680 | 3.884 |
| HIGH_PRESSURE-40-S20260917 | Nearest Neighbor | 0/1 |  |  | 0.011 |  |  |
| HIGH_PRESSURE-40-S20260917 | Best Insertion | 0/1 |  |  | 0.065 |  |  |
| HIGH_PRESSURE-40-S20260917 | GA Basic | 0/5 |  |  | 32.577 | 4764 | 27.580 |
| HIGH_PRESSURE-40-S20260917 | GA + Pruning | 5/5 | 610.18 | 28.31 | 18.108 | 2949 | 10.686 |
| HIGH_PRESSURE-40-S20260917 | GA + Pruning + Repair | 5/5 | 588.89 | 8.84 | 33.193 | 3084 | 20.182 |
| HIGH_PRESSURE-60-S20260917 | Nearest Neighbor | 0/1 |  |  | 0.010 |  |  |
| HIGH_PRESSURE-60-S20260917 | Best Insertion | 0/1 |  |  | 0.166 |  |  |
| HIGH_PRESSURE-60-S20260917 | GA Basic | 0/5 |  |  | 50.449 | 3823 | 34.421 |
| HIGH_PRESSURE-60-S20260917 | GA + Pruning | 3/5 | 769.41 | 38.80 | 50.927 | 4533 | 41.529 |
| HIGH_PRESSURE-60-S20260917 | GA + Pruning + Repair | 5/5 | 734.22 | 35.10 | 77.943 | 3660 | 54.593 |
| HIGH_PRESSURE-80-S20260917 | Nearest Neighbor | 0/1 |  |  | 0.016 |  |  |
| HIGH_PRESSURE-80-S20260917 | Best Insertion | 0/1 |  |  | 0.289 |  |  |
| HIGH_PRESSURE-80-S20260917 | GA Basic | 0/5 |  |  | 102.554 | 5061 | 85.881 |
| HIGH_PRESSURE-80-S20260917 | GA + Pruning | 0/5 |  |  | 62.372 | 3660 | 44.668 |
| HIGH_PRESSURE-80-S20260917 | GA + Pruning + Repair | 5/5 | 868.76 | 15.44 | 128.728 | 3880 | 89.228 |
| EMERGENCY-20-S20260917 | Nearest Neighbor | 1/1 | 119.31 | 0.00 | 0.002 |  |  |
| EMERGENCY-20-S20260917 | Best Insertion | 1/1 | 509.13 | 0.00 | 0.005 |  |  |
| EMERGENCY-20-S20260917 | GA Basic | 0/5 |  |  | 10.797 | 3871 | 7.900 |
| EMERGENCY-20-S20260917 | GA + Pruning | 5/5 | 93.00 | 3.02 | 7.678 | 3055 | 4.836 |
| EMERGENCY-20-S20260917 | GA + Pruning + Repair | 5/5 | 97.41 | 3.34 | 8.147 | 3084 | 4.999 |
| EMERGENCY-40-S20260917 | Nearest Neighbor | 0/1 |  |  | 0.016 |  |  |
| EMERGENCY-40-S20260917 | Best Insertion | 0/1 |  |  | 0.091 |  |  |
| EMERGENCY-40-S20260917 | GA Basic | 0/5 |  |  | 26.277 | 3487 | 18.601 |
| EMERGENCY-40-S20260917 | GA + Pruning | 5/5 | 619.80 | 30.84 | 29.543 | 4648 | 23.980 |
| EMERGENCY-40-S20260917 | GA + Pruning + Repair | 5/5 | 609.26 | 14.99 | 34.305 | 3016 | 20.638 |
| EMERGENCY-60-S20260917 | Nearest Neighbor | 0/1 |  |  | 0.017 |  |  |
| EMERGENCY-60-S20260917 | Best Insertion | 0/1 |  |  | 0.105 |  |  |
| EMERGENCY-60-S20260917 | GA Basic | 0/5 |  |  | 56.318 | 4053 | 44.880 |
| EMERGENCY-60-S20260917 | GA + Pruning | 0/5 |  |  | 54.962 | 4850 | 48.113 |
| EMERGENCY-60-S20260917 | GA + Pruning + Repair | 5/5 | 761.36 | 22.36 | 68.228 | 3189 | 42.863 |
| EMERGENCY-80-S20260917 | Nearest Neighbor | 0/1 |  |  | 0.021 |  |  |
| EMERGENCY-80-S20260917 | Best Insertion | 0/1 |  |  | 0.274 |  |  |
| EMERGENCY-80-S20260917 | GA Basic | 0/5 |  |  | 83.335 | 3900 | 59.813 |
| EMERGENCY-80-S20260917 | GA + Pruning | 0/5 |  |  | 79.294 | 4696 | 67.016 |
| EMERGENCY-80-S20260917 | GA + Pruning + Repair | 5/5 | 890.86 | 28.99 | 96.063 | 2940 | 56.823 |
