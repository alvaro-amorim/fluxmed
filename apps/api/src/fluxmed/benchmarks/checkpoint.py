"""Scenario checkpoints bound to exact inputs, source bytes and experiment parameters."""

import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import zipfile
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import TYPE_CHECKING, Any, BinaryIO, Self

from fluxmed.application.optimization.evaluation import OperationalFitnessEvaluator
from fluxmed.benchmarks.export import read_benchmark_report, write_benchmark_report
from fluxmed.benchmarks.models import BenchmarkMethod, BenchmarkProblem, BenchmarkReport

if TYPE_CHECKING:
    from fluxmed.benchmarks.matrix import ScenarioMatrixCell


def _json(value: object) -> str:
    return json.dumps(
        value, default=str, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False
    )


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _atomic_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(_json(value))
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def source_identity(root: Path) -> dict[str, Any]:
    # Explicit allowlist: configuration/secrets, database files and generated outputs
    # are never candidates. Include untracked Python code and synthetic fixtures.
    candidates = [root / "apps/api/pyproject.toml"]
    for folder in ("apps/api/src", "apps/api/tests", "apps/api/alembic", "scripts"):
        candidates.extend(
            p for p in (root / folder).rglob("*") if p.is_file() and p.suffix in {".py", ".json"}
        )
    files = {
        p.relative_to(root).as_posix(): _digest(p.read_bytes())
        for p in sorted(candidates)
        if p.is_file()
    }
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False
    )
    status = subprocess.run(
        ["git", "status", "--porcelain=v1", "--", *files],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "git_head": head.stdout.strip() if head.returncode == 0 else None,
        "local_status": status.stdout.splitlines() if status.returncode == 0 else [],
        "files_sha256": files,
        "source_sha256": _digest(_json(files).encode("utf-8")),
    }


def environment_identity() -> dict[str, object]:
    packages = {
        name: importlib.metadata.version(name)
        for name in ("sqlalchemy", "psycopg", "pydantic", "tzdata")
    }
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "logical_cpu_count": os.cpu_count(),
        "packages": packages,
    }


def problem_snapshot(problem: BenchmarkProblem) -> dict[str, object]:
    locations = [None, *(d.id for d in sorted(problem.deliveries, key=lambda d: str(d.id)))]
    resources: object = None
    if problem.fitness_evaluator_factory:
        evaluator = problem.fitness_evaluator_factory()
        if isinstance(evaluator, OperationalFitnessEvaluator):
            resources = {
                "vehicles": [
                    {
                        k: value
                        for k, value in asdict(v).items()
                        if k not in {"created_at", "updated_at"}
                    }
                    for v in evaluator._vehicles
                ],
                "workers": [
                    {
                        k: value
                        for k, value in asdict(w).items()
                        if k not in {"created_at", "updated_at"}
                    }
                    for w in evaluator._workers
                ],
            }
    return {
        "scenario_name": problem.scenario_name,
        "deliveries": [asdict(d) for d in problem.deliveries],
        "vehicles": [asdict(v) for v in problem.vehicles],
        "operation_start_at": problem.operation_start_at,
        "operation_end_at": problem.operation_end_at,
        "operational_resources": resources,
        "travel_matrix": [
            {"origin": a, "destination": b, **asdict(problem.travel_matrix.metric(a, b))}
            for a in locations
            for b in locations
            if a != b
        ],
    }


class MatrixCheckpoint:
    def __init__(
        self, output_dir: Path, *, root: Path, recipe: dict[str, object], resume: bool = False
    ) -> None:
        self.output_dir = output_dir
        self._root = root
        self._recipe = recipe
        self._resume = resume
        self._lock: BinaryIO | None = None
        self.experiment_id = ""
        self._source_sha256 = ""

    def __enter__(self) -> Self:
        if (
            self.output_dir.exists()
            and not (self.output_dir / "experiment.json").exists()
            and any(self.output_dir.iterdir())
        ):
            raise ValueError(
                "Output is not an empty experiment folder; existing files were preserved."
            )
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._lock = (self.output_dir / ".run.lock").open("a+b")
        self._lock.seek(0, os.SEEK_END)
        if self._lock.tell() == 0:
            self._lock.write(b"0")
            self._lock.flush()
        self._lock.seek(0)
        try:
            if os.name == "nt":
                msvcrt = importlib.import_module("msvcrt")

                msvcrt.locking(self._lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl = importlib.import_module("fcntl")

                fcntl.flock(self._lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._prepare()
        except BaseException:
            self._lock.close()
            self._lock = None
            raise
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._lock is not None:
            self._lock.close()  # OS releases the lock even after an interrupted process.
            self._lock = None

    def _prepare(self) -> None:
        code = source_identity(self._root)
        self._source_sha256 = code["source_sha256"]
        environment = environment_identity()
        identity = {
            "recipe": self._recipe,
            "source_sha256": code["source_sha256"],
            "environment": environment,
        }
        self.experiment_id = _digest(_json(identity).encode("utf-8"))
        manifest_path = self.output_dir / "experiment.json"
        archive = self.output_dir / "source-snapshot.zip"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if not self._resume:
                raise ValueError(
                    "Output already contains an experiment; use --resume or a new folder."
                )
            if manifest["experiment_id"] != self.experiment_id:
                raise ValueError(
                    "Cannot resume: code, parameters or execution environment changed."
                )
            if _digest(archive.read_bytes()) != manifest["source_archive_sha256"]:
                raise ValueError("Cannot resume: source archive checksum mismatch.")
            return
        if any(p.name != ".run.lock" for p in self.output_dir.iterdir()):
            raise ValueError(
                "Output is not an empty experiment folder; existing files were preserved."
            )
        if self._resume:
            raise ValueError("Cannot resume: experiment manifest is absent.")
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as snapshot:
            for name, expected in code["files_sha256"].items():
                data = (self._root / name).read_bytes()
                if _digest(data) != expected:
                    raise ValueError("Source changed while taking the snapshot.")
                entry = zipfile.ZipInfo(name)
                entry.compress_type = zipfile.ZIP_DEFLATED
                snapshot.writestr(entry, data)
        _atomic_json(
            manifest_path,
            {
                "schema_version": 1,
                "experiment_id": self.experiment_id,
                "created_at_utc": datetime.now(UTC).isoformat(),
                "recipe": self._recipe,
                "code": code,
                "environment": environment,
                "source_archive_sha256": _digest(archive.read_bytes()),
            },
        )

    def load(self, cell: "ScenarioMatrixCell", problem: BenchmarkProblem) -> BenchmarkReport | None:
        folder = self.output_dir / "scenarios" / cell.scenario_name
        marker = folder / "complete.json"
        if not marker.exists():
            return None  # A partial scenario is rerun; it is never included in totals.
        payload = json.loads(marker.read_text(encoding="utf-8"))
        fingerprint = _digest(_json(problem_snapshot(problem)).encode("utf-8"))
        if (
            payload["experiment_id"] != self.experiment_id
            or payload["input_sha256"] != fingerprint
            or payload["cell"] != json.loads(_json(asdict(cell)))
        ):
            raise ValueError(f"Cannot reuse {cell.scenario_name}: experiment or input mismatch.")
        expected_names = {
            "benchmark-report.json",
            "benchmark-runs.csv",
            "benchmark-summaries.csv",
            "benchmark-convergence.csv",
            "input.json",
        }
        if set(payload["files_sha256"]) != expected_names:
            raise ValueError("Scenario completion marker has an invalid file list.")
        for name, expected in payload["files_sha256"].items():
            if _digest((folder / name).read_bytes()) != expected:
                raise ValueError(f"Scenario checksum mismatch: {cell.scenario_name}/{name}.")
        report = read_benchmark_report(folder / "benchmark-report.json")
        self._validate_report(cell, report)
        return report

    def save(
        self, cell: "ScenarioMatrixCell", problem: BenchmarkProblem, report: BenchmarkReport
    ) -> None:
        if source_identity(self._root)["source_sha256"] != self._source_sha256:
            raise ValueError("Source changed during the experiment; scenario was not certified.")
        self._validate_report(cell, report)
        folder = self.output_dir / "scenarios" / cell.scenario_name
        folder.mkdir(parents=True, exist_ok=True)
        inputs = problem_snapshot(problem)
        _atomic_json(folder / "input.json", inputs)
        write_benchmark_report(report, folder)
        files = {
            name: _digest((folder / name).read_bytes())
            for name in (
                "benchmark-report.json",
                "benchmark-runs.csv",
                "benchmark-summaries.csv",
                "benchmark-convergence.csv",
                "input.json",
            )
        }
        _atomic_json(
            folder / "complete.json",
            {
                "experiment_id": self.experiment_id,
                "cell": asdict(cell),
                "input_sha256": _digest(_json(inputs).encode("utf-8")),
                "files_sha256": files,
                "completed_at_utc": datetime.now(UTC).isoformat(),
            },
        )

    def _validate_report(self, cell: "ScenarioMatrixCell", report: BenchmarkReport) -> None:
        seeds = self._recipe["ga_seeds"]
        if not isinstance(seeds, list):
            raise ValueError("Experiment GA seeds must be a list.")
        expected = {
            (method, seed)
            for method in BenchmarkMethod
            for seed in (seeds if method.value.startswith("GA_") else [None])
        }
        actual = [(run.method, run.seed) for run in report.runs]
        if (
            len(actual) != len(expected)
            or set(actual) != expected
            or any(
                run.scenario_name != cell.scenario_name or run.delivery_count != cell.delivery_count
                for run in report.runs
            )
        ):
            raise ValueError(f"Invalid or duplicate run set for {cell.scenario_name}.")
        if len(report.summaries) != len(BenchmarkMethod) or any(
            point.scenario_name != cell.scenario_name for point in report.convergence
        ):
            raise ValueError(f"Invalid summaries or convergence for {cell.scenario_name}.")
