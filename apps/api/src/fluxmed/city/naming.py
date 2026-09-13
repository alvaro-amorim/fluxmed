import json
import re
import unicodedata
from dataclasses import dataclass
from importlib.resources import files

from fluxmed.domain.enums import RoadClass

CATALOG_VERSION = "1.0.0"


def normalize_street_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", ascii_value.strip().lower())


@dataclass(frozen=True)
class StreetNameRequest:
    key: str
    district_slug: str
    road_class: RoadClass
    ordinal: int


class StreetNamingService:
    """Deterministic naming backed by the versioned Santa Aurora catalog."""

    def __init__(self) -> None:
        catalog_file = files("fluxmed.city.catalogs").joinpath("street_names.json")
        payload = json.loads(catalog_file.read_text(encoding="utf-8"))
        if payload.get("version") != CATALOG_VERSION:
            raise RuntimeError("Unsupported Santa Aurora street catalog version")
        self._themes: dict[str, list[str]] = payload["themes"]
        self._global: dict[str, str] = payload["global_corridors"]
        self._used: set[str] = set()

    def reserve_global(self, key: str) -> str:
        try:
            name = self._global[key]
        except KeyError as exc:
            raise RuntimeError(f"Unknown global corridor: {key}") from exc
        self._reserve(name)
        return name

    def name(self, request: StreetNameRequest) -> str:
        terms = self._themes.get(request.district_slug)
        if not terms:
            raise RuntimeError(f"No street catalog for district {request.district_slug}")

        street_type = self._street_type(request.road_class)
        start = request.ordinal % len(terms)
        for offset in range(len(terms)):
            term = terms[(start + offset) % len(terms)]
            normalized_term = normalize_street_name(term)
            if normalized_term.startswith(("rua ", "avenida ", "via ", "anel ")):
                candidate = term
            else:
                candidate = f"{street_type} {term}"
            normalized = normalize_street_name(candidate)
            if normalized not in self._used:
                self._used.add(normalized)
                return candidate
        raise RuntimeError(
            f"Street name catalog exhausted for district {request.district_slug}; "
            "extend the versioned catalog instead of reusing names."
        )

    def _reserve(self, name: str) -> None:
        normalized = normalize_street_name(name)
        if normalized in self._used:
            raise RuntimeError(f"Duplicate street name: {name}")
        self._used.add(normalized)

    @staticmethod
    def _street_type(road_class: RoadClass) -> str:
        if road_class == RoadClass.EXPRESSWAY:
            return "Via"
        if road_class == RoadClass.ARTERIAL:
            return "Avenida"
        if road_class == RoadClass.SERVICE:
            return "Via de Serviço"
        return "Rua"
