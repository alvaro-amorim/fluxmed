from importlib import import_module
from pathlib import Path
import sys


def main() -> None:
    api_src = Path(__file__).resolve().parents[1] / "apps" / "api" / "src"
    sys.path.insert(0, str(api_src))
    module = import_module("fluxmed.scripts.benchmark_optimizer")
    module.main()


if __name__ == "__main__":
    main()
