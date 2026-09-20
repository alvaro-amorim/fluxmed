import sys
from importlib import import_module
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    api_src = repo_root / "apps" / "api" / "src"
    sys.path.insert(0, str(api_src))
    module = import_module("fluxmed.scripts.render_benchmark_artifacts")
    module.main()


if __name__ == "__main__":
    main()
