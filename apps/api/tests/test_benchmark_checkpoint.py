import json
import zipfile
from dataclasses import asdict

import pytest

from fluxmed.application.deliveries.scenario import ScenarioProfile
from fluxmed.benchmarks import OptimizerBenchmarkRunner, ScenarioMatrixBenchmarkRunner
from fluxmed.benchmarks.checkpoint import MatrixCheckpoint, source_identity
from fluxmed.optimization import GeneticOptimizerConfig
from test_benchmark_matrix import _problem


def setup_experiment(tmp_path):
    root = tmp_path / "source"
    module = root / "apps/api/src/fluxmed/optimization/engine.py"
    module.parent.mkdir(parents=True)
    module.write_text("# local uncommitted version\n", encoding="utf-8")
    (root / ".env").write_text("PRIVATE_VALUE=excluded", encoding="utf-8")
    config = GeneticOptimizerConfig(population_size=8, max_generations=2, stagnation_generations=1)
    recipe = {"ga_seeds": [101], "ga_config": asdict(config)}
    args = dict(
        template_operation_code="TEMPLATE",
        profiles=(ScenarioProfile.NORMAL,),
        sizes=(2, 3),
        scenario_seeds=(9001,),
        ga_seeds=(101,),
    )
    return root, config, recipe, args


def test_resume_after_interruption_preserves_completed_scenario_without_duplicates(tmp_path):
    root, config, recipe, args = setup_experiment(tmp_path)
    calls = []
    benchmark = OptimizerBenchmarkRunner(config)
    original = benchmark.run

    def interrupted(problem, *, seeds):
        calls.append(problem.delivery_count)
        if problem.delivery_count == 3:
            raise RuntimeError("simulated interruption")
        return original(problem, seeds=seeds)

    benchmark.run = interrupted
    runner = ScenarioMatrixBenchmarkRunner(problem_factory=_problem, benchmark_runner=benchmark)
    output = tmp_path / "results"
    with (
        pytest.raises(RuntimeError, match="simulated interruption"),
        MatrixCheckpoint(output, root=root, recipe=recipe) as checkpoint,
    ):
        runner.run(**args, checkpoint=checkpoint)
    completed = output / "scenarios/NORMAL-2-S9001/complete.json"
    original_bytes = completed.read_bytes()

    def resumed(problem, *, seeds):
        calls.append(problem.delivery_count)
        return original(problem, seeds=seeds)

    benchmark.run = resumed
    with MatrixCheckpoint(output, root=root, recipe=recipe, resume=True) as checkpoint:
        result = runner.run(**args, checkpoint=checkpoint)
    assert calls == [2, 3, 3]
    assert completed.read_bytes() == original_bytes
    assert len(result.report.runs) == 10
    assert len({(r.scenario_name, r.method, r.seed) for r in result.report.runs}) == 10
    assert all(r.solution_evidence for r in result.report.runs)


@pytest.mark.parametrize("change", ["code", "parameters", "corruption", "inputs"])
def test_resume_rejects_incompatible_or_corrupted_results(tmp_path, change):
    root, config, recipe, args = setup_experiment(tmp_path)
    output = tmp_path / "results"
    runner = ScenarioMatrixBenchmarkRunner(
        problem_factory=_problem, benchmark_runner=OptimizerBenchmarkRunner(config)
    )
    args["sizes"] = (2,)
    with MatrixCheckpoint(output, root=root, recipe=recipe) as checkpoint:
        runner.run(**args, checkpoint=checkpoint)
    if change == "code":
        (root / "apps/api/src/fluxmed/optimization/engine.py").write_text(
            "# changed", encoding="utf-8"
        )
    if change == "parameters":
        recipe = {**recipe, "ga_seeds": [202]}
    if change == "corruption":
        (output / "scenarios/NORMAL-2-S9001/benchmark-report.json").write_text(
            "{}", encoding="utf-8"
        )
    if change == "inputs":

        def changed_problem(**kwargs):
            from dataclasses import replace
            from decimal import Decimal

            problem = _problem(**kwargs)
            return replace(
                problem,
                deliveries=[replace(d, weight_kg=Decimal("11")) for d in problem.deliveries],
            )

        runner = ScenarioMatrixBenchmarkRunner(
            problem_factory=changed_problem, benchmark_runner=OptimizerBenchmarkRunner(config)
        )
    with (
        pytest.raises(ValueError),
        MatrixCheckpoint(output, root=root, recipe=recipe, resume=True) as checkpoint,
    ):
        runner.run(**args, checkpoint=checkpoint)


def test_source_snapshot_excludes_secrets_and_identifies_local_code(tmp_path):
    root, _, recipe, _ = setup_experiment(tmp_path)
    initial = source_identity(root)
    (root / ".env").write_text("PRIVATE_VALUE=changed", encoding="utf-8")
    assert source_identity(root)["source_sha256"] == initial["source_sha256"]
    output = tmp_path / "results"
    with (
        MatrixCheckpoint(output, root=root, recipe=recipe),
        zipfile.ZipFile(output / "source-snapshot.zip") as archive,
    ):
        assert archive.namelist() == ["apps/api/src/fluxmed/optimization/engine.py"]
        assert "local uncommitted" in archive.read(archive.namelist()[0]).decode()
    manifest = json.loads((output / "experiment.json").read_text(encoding="utf-8"))
    assert manifest["code"]["files_sha256"] == initial["files_sha256"]
    assert "PRIVATE_VALUE" not in json.dumps(manifest)


def test_existing_results_are_preserved_and_concurrent_writer_is_rejected(tmp_path):
    root, _, recipe, _ = setup_experiment(tmp_path)
    old = tmp_path / "old"
    old.mkdir()
    (old / "benchmark-report.json").write_text("old", encoding="utf-8")
    with pytest.raises(ValueError), MatrixCheckpoint(old, root=root, recipe=recipe):
        pass
    assert sorted(p.name for p in old.iterdir()) == ["benchmark-report.json"]
    output = tmp_path / "new"
    with (
        MatrixCheckpoint(output, root=root, recipe=recipe),
        pytest.raises(OSError),
        MatrixCheckpoint(output, root=root, recipe=recipe, resume=True),
    ):
        pass
