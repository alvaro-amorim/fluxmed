from typing import Protocol

from fluxmed.city.generator import DATASET_VERSION, DEFAULT_SEED, GeneratedCity, build_santa_aurora


class CityProvider(Protocol):
    def generate(self) -> GeneratedCity: ...


class SantaAuroraProvider:
    def __init__(self, *, seed: int = DEFAULT_SEED, dataset_version: str = DATASET_VERSION) -> None:
        self._seed = seed
        self._dataset_version = dataset_version

    def generate(self) -> GeneratedCity:
        return build_santa_aurora(seed=self._seed, dataset_version=self._dataset_version)
