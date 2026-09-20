from __future__ import annotations

import html
from collections import defaultdict
from pathlib import Path
from statistics import fmean

from fluxmed.benchmarks.models import BenchmarkMethod, BenchmarkReport, BenchmarkRun

_METHOD_LABELS = {
    BenchmarkMethod.NEAREST_NEIGHBOR: "Nearest Neighbor",
    BenchmarkMethod.BEST_INSERTION: "Best Insertion",
    BenchmarkMethod.GA_BASIC: "GA Basic",
    BenchmarkMethod.GA_PRUNING: "GA + Pruning",
    BenchmarkMethod.GA_PRUNING_REPAIR: "GA + Pruning + Repair",
}
_METHOD_COLORS = {
    BenchmarkMethod.NEAREST_NEIGHBOR: "#355070",
    BenchmarkMethod.BEST_INSERTION: "#6d597a",
    BenchmarkMethod.GA_BASIC: "#b56576",
    BenchmarkMethod.GA_PRUNING: "#e56b6f",
    BenchmarkMethod.GA_PRUNING_REPAIR: "#2a9d8f",
}
_PROFILE_ORDER = {
    "NORMAL": 0,
    "BUSY": 1,
    "HIGH_PRESSURE": 2,
    "EMERGENCY": 3,
}


def write_academic_artifacts(report: BenchmarkReport, output_dir: Path) -> tuple[Path, ...]:
    charts_dir = output_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)

    artifacts: list[Path] = []
    feasibility = _aggregate_by_scale(report, metric="feasibility")
    paired_cost = _paired_pruning_repair_cost_by_scale(report)
    runtime = _aggregate_by_scale(report, metric="runtime")
    hard_violations = _aggregate_by_scale(
        report,
        metric="hard_violations",
        methods=(
            BenchmarkMethod.GA_BASIC,
            BenchmarkMethod.GA_PRUNING,
            BenchmarkMethod.GA_PRUNING_REPAIR,
        ),
    )

    artifacts.append(
        _write_line_chart(
            charts_dir / "feasibility-by-scale.svg",
            title="Feasibility rate by scale",
            y_label="Feasibility rate",
            series=feasibility,
            y_min=0.0,
            y_max=1.0,
        )
    )
    obsolete_cost_chart = charts_dir / "mean-feasible-cost-by-scale.svg"
    if obsolete_cost_chart.exists():
        obsolete_cost_chart.unlink()
    if paired_cost:
        artifacts.append(
            _write_line_chart(
                charts_dir / "paired-pruning-repair-cost-by-scale.svg",
                title="Paired cost by scale: pruning variants",
                y_label="Optimizer cost (BRL)",
                series=paired_cost,
            )
        )
    artifacts.append(
        _write_line_chart(
            charts_dir / "runtime-by-scale.svg",
            title="Mean runtime by scale",
            y_label="Runtime (seconds)",
            series=runtime,
        )
    )
    artifacts.append(
        _write_line_chart(
            charts_dir / "ga-hard-violations-by-scale.svg",
            title="GA ablation: mean hard violations by scale",
            y_label="Hard violations",
            series=hard_violations,
            y_min=0.0,
        )
    )

    convergence = _convergence_for_hardest_scenario(report)
    if convergence:
        artifacts.append(
            _write_line_chart(
                charts_dir / "convergence-hard-violations.svg",
                title="Convergence on hardest available scenario",
                y_label="Mean hard violations",
                series=convergence,
                y_min=0.0,
                x_label="Generation",
            )
        )

    artifacts.append(_write_academic_table(report, output_dir / "academic-summary.md"))
    return tuple(artifacts)


def _aggregate_by_scale(
    report: BenchmarkReport,
    *,
    metric: str,
    methods: tuple[BenchmarkMethod, ...] | None = None,
) -> dict[BenchmarkMethod, list[tuple[int, float]]]:
    allowed = set(methods or tuple(BenchmarkMethod))
    grouped: dict[tuple[BenchmarkMethod, int], list[float]] = defaultdict(list)
    for run in report.runs:
        if run.method not in allowed:
            continue
        if metric == "feasibility":
            value = 1.0 if run.feasible else 0.0
        elif metric == "runtime":
            value = run.runtime_seconds
        elif metric == "hard_violations":
            value = float(run.hard_violations)
        else:
            raise ValueError(f"Unsupported benchmark chart metric: {metric}.")
        grouped[(run.method, run.delivery_count)].append(value)

    result: dict[BenchmarkMethod, list[tuple[int, float]]] = {}
    for method in BenchmarkMethod:
        if method not in allowed:
            continue
        points = [
            (size, fmean(values))
            for (group_method, size), values in grouped.items()
            if group_method is method and values
        ]
        if points:
            result[method] = sorted(points)
    return result


def _paired_pruning_repair_cost_by_scale(
    report: BenchmarkReport,
) -> dict[BenchmarkMethod, list[tuple[int, float]]]:
    paired_methods = (
        BenchmarkMethod.GA_PRUNING,
        BenchmarkMethod.GA_PRUNING_REPAIR,
    )
    runs_by_key = {
        (run.scenario_name, run.seed, run.method): run
        for run in report.runs
        if run.seed is not None and run.method in paired_methods
    }
    grouped: dict[tuple[BenchmarkMethod, int], list[float]] = defaultdict(list)
    scenario_seed_keys = {(scenario_name, seed) for scenario_name, seed, _method in runs_by_key}
    for scenario_name, seed in scenario_seed_keys:
        pruning = runs_by_key.get((scenario_name, seed, BenchmarkMethod.GA_PRUNING))
        repair = runs_by_key.get((scenario_name, seed, BenchmarkMethod.GA_PRUNING_REPAIR))
        if pruning is None or repair is None:
            continue
        if not pruning.feasible or not repair.feasible:
            continue
        grouped[(BenchmarkMethod.GA_PRUNING, pruning.delivery_count)].append(pruning.cost_brl)
        grouped[(BenchmarkMethod.GA_PRUNING_REPAIR, repair.delivery_count)].append(repair.cost_brl)

    result: dict[BenchmarkMethod, list[tuple[int, float]]] = {}
    for method in (
        BenchmarkMethod.GA_PRUNING,
        BenchmarkMethod.GA_PRUNING_REPAIR,
    ):
        points = [
            (size, fmean(values))
            for (group_method, size), values in grouped.items()
            if group_method is method and values
        ]
        if points:
            result[method] = sorted(points)
    return result


def _convergence_for_hardest_scenario(
    report: BenchmarkReport,
) -> dict[BenchmarkMethod, list[tuple[int, float]]]:
    if not report.convergence:
        return {}

    scenario_names = {point.scenario_name for point in report.convergence}
    scenario_name = max(scenario_names, key=_scenario_difficulty_key)
    grouped: dict[tuple[BenchmarkMethod, int], list[float]] = defaultdict(list)
    for point in report.convergence:
        if point.scenario_name != scenario_name:
            continue
        grouped[(point.method, point.generation)].append(float(point.hard_violations))

    series: dict[BenchmarkMethod, list[tuple[int, float]]] = {}
    for method in (
        BenchmarkMethod.GA_BASIC,
        BenchmarkMethod.GA_PRUNING,
        BenchmarkMethod.GA_PRUNING_REPAIR,
    ):
        points = [
            (generation, fmean(values))
            for (group_method, generation), values in grouped.items()
            if group_method is method and values
        ]
        if points:
            series[method] = sorted(points)
    return series


def _scenario_difficulty_key(name: str) -> tuple[int, int, str]:
    profile = next((profile for profile in _PROFILE_ORDER if name.startswith(profile)), "")
    profile_rank = _PROFILE_ORDER.get(profile, -1)
    parts = name.split("-")
    size = next((int(part) for part in parts if part.isdigit()), 0)
    return profile_rank, size, name


def _x_tick_values(values: list[int], *, max_ticks: int = 8) -> list[int]:
    if len(values) <= max_ticks:
        return values
    indexes = {round(index * (len(values) - 1) / (max_ticks - 1)) for index in range(max_ticks)}
    return [values[index] for index in sorted(indexes)]


def _write_line_chart(
    path: Path,
    *,
    title: str,
    y_label: str,
    series: dict[BenchmarkMethod, list[tuple[int, float]]],
    y_min: float | None = None,
    y_max: float | None = None,
    x_label: str = "Deliveries",
) -> Path:
    width = 960
    height = 560
    left = 90
    right = 40
    top = 80
    bottom = 95
    plot_width = width - left - right
    plot_height = height - top - bottom

    all_points = [point for points in series.values() for point in points]
    x_values = sorted({x for x, _ in all_points}) or [0, 1]
    y_values = [y for _, y in all_points] or [0.0, 1.0]
    min_x = min(x_values)
    max_x = max(x_values)
    min_y = y_min if y_min is not None else min(y_values)
    max_y = y_max if y_max is not None else max(y_values)
    if max_x == min_x:
        max_x = min_x + 1
    if max_y == min_y:
        max_y = min_y + 1.0
    padding = (max_y - min_y) * 0.08
    if y_max is None:
        max_y += padding
    if y_min is None:
        min_y = max(0.0, min_y - padding)

    def px(x: int) -> float:
        return left + ((x - min_x) / (max_x - min_x)) * plot_width

    def py(y: float) -> float:
        return top + ((max_y - y) / (max_y - min_y)) * plot_height

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width / 2}" y="36" text-anchor="middle" '
        'font-family="Arial, sans-serif" font-size="22" font-weight="700">'
        f"{html.escape(title)}</text>",
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}" '
        'stroke="#222" stroke-width="1.5"/>',
        f'<line x1="{left}" y1="{top + plot_height}" x2="{left + plot_width}" '
        f'y2="{top + plot_height}" stroke="#222" stroke-width="1.5"/>',
    ]

    for tick in range(6):
        value = min_y + (max_y - min_y) * tick / 5
        y = py(value)
        svg.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{left + plot_width}" y2="{y:.2f}" '
            'stroke="#e5e7eb" stroke-width="1"/>'
        )
        svg.append(
            f'<text x="{left - 12}" y="{y + 4:.2f}" text-anchor="end" '
            'font-family="Arial, sans-serif" font-size="12">'
            f"{value:.2f}</text>"
        )

    for x in _x_tick_values(x_values):
        x_pos = px(x)
        svg.append(
            f'<text x="{x_pos:.2f}" y="{top + plot_height + 24}" text-anchor="middle" '
            'font-family="Arial, sans-serif" font-size="12">'
            f"{x}</text>"
        )

    svg.append(
        f'<text x="{left + plot_width / 2}" y="{height - 25}" text-anchor="middle" '
        'font-family="Arial, sans-serif" font-size="13">'
        f"{html.escape(x_label)}</text>"
    )
    svg.append(
        f'<text transform="translate(24 {top + plot_height / 2}) rotate(-90)" '
        'text-anchor="middle" font-family="Arial, sans-serif" font-size="13">'
        f"{html.escape(y_label)}</text>"
    )

    legend_y = 57
    legend_x = left
    for method, points in series.items():
        color = _METHOD_COLORS[method]
        polyline = " ".join(f"{px(x):.2f},{py(y):.2f}" for x, y in points)
        polyline_element = "".join(
            [
                f'<polyline points="{polyline}"',
                ' fill="none"',
                f' stroke="{color}"',
                ' stroke-width="2.5"/>',
            ]
        )
        svg.append(polyline_element)
        for x, y in points:
            circle_element = "".join(
                [
                    f'<circle cx="{px(x):.2f}"',
                    f' cy="{py(y):.2f}"',
                    ' r="4"',
                    f' fill="{color}"/>',
                ]
            )
            svg.append(circle_element)
        svg.append(
            f'<line x1="{legend_x}" y1="{legend_y}" x2="{legend_x + 24}" '
            f'y2="{legend_y}" stroke="{color}" stroke-width="3"/>'
        )
        svg.append(
            f'<text x="{legend_x + 30}" y="{legend_y + 4}" '
            'font-family="Arial, sans-serif" font-size="12">'
            f"{html.escape(_METHOD_LABELS[method])}</text>"
        )
        legend_x += 165

    svg.append("</svg>")
    path.write_text("\n".join(svg), encoding="utf-8")
    return path


def _write_academic_table(report: BenchmarkReport, path: Path) -> Path:
    rows = sorted(
        report.summaries,
        key=lambda summary: (
            _scenario_difficulty_key(summary.scenario_name),
            list(BenchmarkMethod).index(summary.method),
        ),
    )
    overall: dict[BenchmarkMethod, list[BenchmarkRun]] = defaultdict(list)
    for run in report.runs:
        overall[run.method].append(run)

    lines = [
        "# FluxMed benchmark academic summary",
        "",
        (
            "Baselines are deterministic and run once per scenario. GA variants use the "
            "explicit seed set recorded in the matrix manifest."
        ),
        (
            "Costs are reported only for feasible runs and should be compared within the "
            "same scenario. The paired pruning/repair chart uses only matched feasible "
            "scenario+seed pairs."
        ),
        (
            "Runtime includes optimizer execution only, excluding scenario generation and "
            "artifact export."
        ),
        "",
        "## Overall feasibility",
        "",
        "| Method | Feasible | Rate | Mean runtime (s) |",
        "|---|---:|---:|---:|",
    ]
    for method in BenchmarkMethod:
        method_runs = overall.get(method, [])
        if not method_runs:
            continue
        feasible_runs = sum(1 for run in method_runs if run.feasible)
        rate = feasible_runs / len(method_runs)
        mean_runtime = fmean(run.runtime_seconds for run in method_runs)
        lines.append(
            f"| {_METHOD_LABELS[method]} | {feasible_runs}/{len(method_runs)} | "
            f"{rate:.2%} | {mean_runtime:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Scenario-level results",
            "",
            "| Scenario | Method | Feasible | Mean cost | Std cost | Mean runtime (s) | "
            "Mean evals | Mean time-to-best (s) |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for summary in rows:
        cost = "" if summary.mean_cost_brl is None else f"{summary.mean_cost_brl:.2f}"
        std = "" if summary.std_cost_brl is None else f"{summary.std_cost_brl:.2f}"
        evals = (
            ""
            if summary.mean_candidate_evaluations is None
            else f"{summary.mean_candidate_evaluations:.0f}"
        )
        time_to_best = (
            ""
            if summary.mean_time_to_best_seconds is None
            else f"{summary.mean_time_to_best_seconds:.3f}"
        )
        lines.append(
            f"| {summary.scenario_name} | {_METHOD_LABELS[summary.method]} | "
            f"{summary.feasible_runs}/{summary.runs} | {cost} | {std} | "
            f"{summary.mean_runtime_seconds:.3f} | {evals} | {time_to_best} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
