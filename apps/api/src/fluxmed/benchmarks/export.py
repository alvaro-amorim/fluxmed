import csv
import json
from dataclasses import asdict
from pathlib import Path

from fluxmed.benchmarks.models import (\n    BenchmarkConvergencePoint,\n    BenchmarkMethod,\n    BenchmarkReport,\n    BenchmarkRun,\n    BenchmarkSummary,\n)


def write_benchmark_report(report: BenchmarkReport, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "benchmark-report.json"
    csv_path = output_dir / "benchmark-runs.csv"
    summaries_path = output_dir / "benchmark-summaries.csv"
    convergence_path = output_dir / "benchmark-convergence.csv"

    payload = {
        "runs": [{**asdict(run), "method": run.method.value} for run in report.runs],
        "summaries": [
            {**asdict(summary), "method": summary.method.value} for summary in report.summaries
        ],
        "convergence": [
            {**asdict(point), "method": point.method.value} for point in report.convergence
        ],
    }
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    fieldnames = [
        "scenario_name",
        "delivery_count",
        "method",
        "seed",
        "runtime_seconds",
        "feasible",
        "hard_violations",
        "unassigned_delivery_count",
        "route_hard_violation_counts",
        "candidate_evaluations",
        "best_generation",
        "time_to_best_seconds",
        "service_penalty",
        "critical_risk",
        "cost_brl",
        "makespan_minutes",
        "travel_minutes",
        "distance_km",
        "vehicles_used",
        "generations_completed",
        "stop_reason",
        "pruning_counts",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for run in report.runs:
            row = asdict(run)
            row["method"] = run.method.value
            row["route_hard_violation_counts"] = json.dumps(
                run.route_hard_violation_counts,
                sort_keys=True,
            )
            row["pruning_counts"] = json.dumps(run.pruning_counts, sort_keys=True)
            writer.writerow(row)

    summary_fieldnames = [
        "scenario_name",
        "delivery_count",
        "method",
        "runs",
        "feasible_runs",
        "feasible_rate",
        "best_cost_brl",
        "mean_cost_brl",
        "std_cost_brl",
        "worst_cost_brl",
        "mean_runtime_seconds",
        "mean_candidate_evaluations",
        "mean_time_to_best_seconds",
        "best_makespan_minutes",
        "mean_makespan_minutes",
    ]
    with summaries_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=summary_fieldnames)
        writer.writeheader()
        for summary in report.summaries:
            row = asdict(summary)
            row["method"] = summary.method.value
            writer.writerow(row)

    convergence_fieldnames = [
        "scenario_name",
        "delivery_count",
        "method",
        "seed",
        "generation",
        "elapsed_seconds",
        "improved",
        "feasible",
        "hard_violations",
        "service_penalty",
        "cost_brl",
        "makespan_minutes",
        "distance_km",
        "vehicles_used",
        "diversity_ratio",
        "effective_mutation_rate",
        "immigrants_added",
        "pruning_counts",
    ]
    with convergence_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=convergence_fieldnames)
        writer.writeheader()
        for point in report.convergence:
            row = asdict(point)
            row["method"] = point.method.value
            row["pruning_counts"] = json.dumps(point.pruning_counts, sort_keys=True)
            writer.writerow(row)

    return json_path, csv_path


def read_benchmark_report(path: Path) -> BenchmarkReport:
    payload = json.loads(path.read_text(encoding="utf-8"))
    runs = tuple(
        BenchmarkRun(**{**item, "method": BenchmarkMethod(item["method"])})
        for item in payload["runs"]
    )
    summaries = tuple(
        BenchmarkSummary(**{**item, "method": BenchmarkMethod(item["method"])})
        for item in payload["summaries"]
    )
    convergence = tuple(
        BenchmarkConvergencePoint(
            **{**item, "method": BenchmarkMethod(item["method"])}
        )
        for item in payload["convergence"]
    )
    return BenchmarkReport(
        runs=runs,
        summaries=summaries,
        convergence=convergence,
    )
