"""Run the academic benchmark fixture seeder from the repository root."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    load_dotenv(repo_root / ".env", override=False)
    os.environ.setdefault("PGCONNECT_TIMEOUT", "5")
    sys.path.insert(0, str(repo_root / "apps" / "api" / "src"))
    from fluxmed.scripts.seed_benchmark_template import main as seed_main

    seed_main()


if __name__ == "__main__":
    main()
