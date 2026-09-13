import argparse

from fluxmed.city.generator import DATASET_VERSION, DEFAULT_SEED
from fluxmed.city.persistence import seed_santa_aurora
from fluxmed.infrastructure.database import session_scope


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and persist the Santa Aurora base city.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--dataset-version", default=DATASET_VERSION)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()

    with session_scope() as session:
        city = seed_santa_aurora(
            session,
            seed=args.seed,
            dataset_version=args.dataset_version,
            replace=args.replace,
        )
        session.flush()
        city_id = city.id
        city_name = city.name
        dataset_version = city.dataset_version
        generation_seed = city.generation_seed

    print(f"{city_name} ready: id={city_id} dataset={dataset_version} seed={generation_seed}")


if __name__ == "__main__":
    main()
