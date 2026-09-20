import argparse
from pathlib import Path

from fluxmed.benchmarks.charts import write_academic_artifacts
from fluxmed.benchmarks.export import read_benchmark_report
from fluxmed.benchmarks.matrix import enrich_matrix_manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Regenerate academic artifacts from an existing benchmark report."
    )
    parser.add_argument(
        "--report",
        type=Path,
        required=True,
        help="Path to benchmark-report.json.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Artifact directory. Defaults to the report directory.",
    )
    args = parser.parse_args()

    report_path = args.report.resolve()
    output_dir = (args.output or report_path.parent).resolve()
    report = read_benchmark_report(report_path)
    artifacts = write_academic_artifacts(report, output_dir)
    manifest_path = output_dir / "matrix-manifest.json"
    if manifest_path.exists():
        enrich_matrix_manifest(manifest_path)
        print(f"Matrix manifest enriched: {manifest_path}")

    print(f"Academic artifacts regenerated: {len(artifacts)} files")
    for artifact in artifacts:
        print(artifact)


if __name__ == "__main__":
    main()
