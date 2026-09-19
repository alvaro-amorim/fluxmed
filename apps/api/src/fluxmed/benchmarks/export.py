import csv
import json
from dataclasses import asdict
from pathlib import Path

from fluxmed.benchmarks.models import BenchmarkReport


def write_benchmark_report(report: BenchmarkReport, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "benchmark-report.json"
    csv_path = output_dir / "benchmark-runs.csv"

    payload = {
        "runs": [
            {**asdict(run), "method": run.method.value}
            for run in report.runs
        ],
        "summaries": [
            {**asdict(summary), "method": summary.method.value}
            for summary in report.summaries
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
            row["pruning_counts"] = json.dumps(run.pruning_counts, sort_keys=True)
            writer.writerow(row)

    return json_path, csv_path
