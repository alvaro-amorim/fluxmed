from importlib import import_module
import os
from pathlib import Path
import sys

from dotenv import load_dotenv


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    load_dotenv(repo_root / ".env", override=False)
    os.environ.setdefault("PGCONNECT_TIMEOUT", "5")
    api_src = repo_root / "apps" / "api" / "src"
    sys.path.insert(0, str(api_src))
    module = import_module("fluxmed.scripts.benchmark_optimizer")
    module.main()


if __name__ == "__main__":
    main()
