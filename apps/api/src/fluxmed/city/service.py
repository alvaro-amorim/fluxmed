import json
import re
import uuid
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, cast

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fluxmed.city.naming import normalize_street_name
from fluxmed.domain.enums import CitySourceType, FacilityType
from fluxmed.infrastructure.models.city import (
    AddressModel,
    CityModel,
    DistrictModel,
    FacilityModel,
    IntersectionModel,
    RoadSegmentModel,
    StreetModel,
)


class CityNotFoundError(LookupError):
    pass


@dataclass(frozen=True)
class CitySummary:
    id: uuid.UUID
    name: str
    country: str
    source_type: CitySourceType
    timezone: str
    dataset_version: str
    generation_seed: int
    generator_version: str
    depot_name: str
    district_count: int
    street_count: int
    intersection_count: int
    road_segment_count: int
    address_count: int
    facility_count: int
    bridge_count: int


@dataclass(frozen=True)
class AddressSearchMatch:
    id: uuid.UUID
    street_name: str
    house_number: str
    district_name: str
    complement: str | None
    formatted: str
    longitude: float
    latitude: float


@dataclass(frozen=True)
class AddressSearchResult:
    query: str
    matches: list[AddressSearchMatch]
    street_suggestion: str | None
    number_suggestions: list[str]


@dataclass(frozen=True)
class FacilitySummary:
    id: uuid.UUID
    name: str
    facility_type: FacilityType
    address_id: uuid.UUID
    street_name: str
    house_number: str
    district_name: str
    longitude: float
    latitude: float


class CityService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _summary(self, city: CityModel) -> CitySummary:
        district_count = self._count(DistrictModel, DistrictModel.city_id, city.id)
        street_count = self._count(StreetModel, StreetModel.city_id, city.id)
        intersection_count = self._count(IntersectionModel, IntersectionModel.city_id, city.id)
        road_segment_count = self._count(RoadSegmentModel, RoadSegmentModel.city_id, city.id)
        address_count = self._count(AddressModel, AddressModel.city_id, city.id)
        facility_count = self._count(FacilityModel, FacilityModel.city_id, city.id)
        bridge_count = self._session.scalar(
            select(func.count(func.distinct(RoadSegmentModel.bridge_name)))
            .select_from(RoadSegmentModel)
            .where(RoadSegmentModel.city_id == city.id, RoadSegmentModel.is_bridge.is_(True))
        )
        return CitySummary(
            id=city.id,
            name=city.name,
            country=city.country,
            source_type=city.source_type,
            timezone=city.timezone,
            dataset_version=city.dataset_version,
            generation_seed=city.generation_seed,
            generator_version=city.generator_version,
            depot_name=city.depot_name,
            district_count=district_count,
            street_count=street_count,
            intersection_count=intersection_count,
            road_segment_count=road_segment_count,
            address_count=address_count,
            facility_count=facility_count,
            bridge_count=int(bridge_count or 0),
        )

    def _count(self, model: Any, city_column: Any, city_id: uuid.UUID) -> int:
        value = self._session.scalar(
            select(func.count()).select_from(model).where(city_column == city_id)
        )
        return int(value or 0)

    def list_cities(self) -> list[CitySummary]:
        cities = self._session.scalars(select(CityModel).order_by(CityModel.name)).all()
        return [self._summary(city) for city in cities]

    def get(self, city_id: uuid.UUID) -> CitySummary:
        city = self._session.get(CityModel, city_id)
        if city is None:
            raise CityNotFoundError(str(city_id))
        return self._summary(city)

    def districts(self, city_id: uuid.UUID) -> list[DistrictModel]:
        self.get(city_id)
        return list(
            self._session.scalars(
                select(DistrictModel)
                .where(DistrictModel.city_id == city_id)
                .order_by(DistrictModel.name)
            )
        )

    def search_addresses(
        self, city_id: uuid.UUID, query: str, limit: int = 8
    ) -> AddressSearchResult:
        self.get(city_id)
        cleaned_query = query.strip()
        if not cleaned_query:
            return AddressSearchResult(cleaned_query, [], None, [])

        street_query, number_query = self._split_address_query(cleaned_query)
        streets = list(
            self._session.scalars(
                select(StreetModel).where(StreetModel.city_id == city_id).order_by(StreetModel.name)
            )
        )
        ranked_streets = self._rank_streets(streets, street_query)
        if not ranked_streets:
            return AddressSearchResult(cleaned_query, [], None, [])

        selected_streets = [street for street, _score in ranked_streets[:3]]
        street_suggestion = None
        if normalize_street_name(selected_streets[0].name) != normalize_street_name(street_query):
            street_suggestion = selected_streets[0].name

        statement = (
            select(
                AddressModel,
                StreetModel.name,
                DistrictModel.name,
                func.ST_X(AddressModel.location),
                func.ST_Y(AddressModel.location),
            )
            .join(StreetModel, StreetModel.id == AddressModel.street_id)
            .join(DistrictModel, DistrictModel.id == AddressModel.district_id)
            .where(
                AddressModel.city_id == city_id,
                AddressModel.active.is_(True),
                AddressModel.street_id.in_([street.id for street in selected_streets]),
            )
        )
        if number_query is not None:
            statement = statement.where(
                func.upper(AddressModel.house_number) == number_query.upper()
            )
        statement = statement.order_by(StreetModel.name, AddressModel.house_number_numeric).limit(
            limit
        )
        rows = self._session.execute(statement).all()
        matches = [self._address_match(*row) for row in rows]

        number_suggestions: list[str] = []
        if number_query is not None and not matches:
            numeric_match = re.match(r"^(\d+)", number_query)
            if numeric_match:
                requested_number = int(numeric_match.group(1))
                nearest_rows = self._session.execute(
                    select(AddressModel.house_number, AddressModel.house_number_numeric)
                    .where(
                        AddressModel.city_id == city_id,
                        AddressModel.active.is_(True),
                        AddressModel.street_id == selected_streets[0].id,
                    )
                    .order_by(
                        func.abs(AddressModel.house_number_numeric - requested_number),
                        AddressModel.house_number_numeric,
                    )
                    .limit(4)
                ).all()
                number_suggestions = [house_number for house_number, _numeric in nearest_rows]

        return AddressSearchResult(
            query=cleaned_query,
            matches=matches,
            street_suggestion=street_suggestion,
            number_suggestions=number_suggestions,
        )

    def facilities(self, city_id: uuid.UUID) -> list[FacilitySummary]:
        self.get(city_id)
        rows = self._session.execute(
            select(
                FacilityModel,
                AddressModel,
                StreetModel.name,
                DistrictModel.name,
                func.ST_X(AddressModel.location),
                func.ST_Y(AddressModel.location),
            )
            .join(AddressModel, AddressModel.id == FacilityModel.address_id)
            .join(StreetModel, StreetModel.id == AddressModel.street_id)
            .join(DistrictModel, DistrictModel.id == AddressModel.district_id)
            .where(FacilityModel.city_id == city_id, FacilityModel.active.is_(True))
            .order_by(FacilityModel.facility_type, FacilityModel.name)
        ).all()
        return [
            FacilitySummary(
                id=facility.id,
                name=facility.name,
                facility_type=facility.facility_type,
                address_id=address.id,
                street_name=street_name,
                house_number=address.house_number,
                district_name=district_name,
                longitude=float(longitude),
                latitude=float(latitude),
            )
            for facility, address, street_name, district_name, longitude, latitude in rows
        ]

    def map_geojson(self, city_id: uuid.UUID) -> dict[str, Any]:
        city = self._session.get(CityModel, city_id)
        if city is None:
            raise CityNotFoundError(str(city_id))

        features: list[dict[str, Any]] = []
        city_geometries = self._session.execute(
            select(
                func.ST_AsGeoJSON(CityModel.boundary),
                func.ST_AsGeoJSON(CityModel.river_geometry),
                func.ST_AsGeoJSON(CityModel.depot_geometry),
            ).where(CityModel.id == city_id)
        ).one()
        boundary_geojson, river_geojson, depot_geojson = city_geometries
        features.append(
            self._feature(
                feature_id=f"city:{city.id}",
                geometry_json=boundary_geojson,
                properties={"feature_type": "city_boundary", "name": city.name},
            )
        )

        district_rows = self._session.execute(
            select(DistrictModel, func.ST_AsGeoJSON(DistrictModel.geometry))
            .where(DistrictModel.city_id == city_id)
            .order_by(DistrictModel.name)
        )
        for district, geometry_json in district_rows:
            features.append(
                self._feature(
                    feature_id=f"district:{district.id}",
                    geometry_json=geometry_json,
                    properties={
                        "feature_type": "district",
                        "name": district.name,
                        "slug": district.slug,
                    },
                )
            )

        segment_rows = self._session.execute(
            select(
                RoadSegmentModel,
                StreetModel.name,
                func.ST_AsGeoJSON(RoadSegmentModel.geometry),
            )
            .join(StreetModel, StreetModel.id == RoadSegmentModel.street_id)
            .where(RoadSegmentModel.city_id == city_id, RoadSegmentModel.active.is_(True))
        )
        for segment, street_name, geometry_json in segment_rows:
            features.append(
                self._feature(
                    feature_id=f"road-segment:{segment.id}",
                    geometry_json=geometry_json,
                    properties={
                        "feature_type": "road",
                        "road_segment_id": str(segment.id),
                        "street_id": str(segment.street_id),
                        "from_intersection_id": str(segment.from_intersection_id),
                        "to_intersection_id": str(segment.to_intersection_id),
                        "street_name": street_name,
                        "road_class": segment.road_class.value,
                        "speed_limit_kmh": segment.speed_limit_kmh,
                        "lanes": segment.lanes,
                        "is_bridge": segment.is_bridge,
                        "bridge_name": segment.bridge_name,
                    },
                )
            )

        facility_rows = self._session.execute(
            select(FacilityModel, func.ST_AsGeoJSON(AddressModel.location))
            .join(AddressModel, AddressModel.id == FacilityModel.address_id)
            .where(FacilityModel.city_id == city_id, FacilityModel.active.is_(True))
        )
        for facility, geometry_json in facility_rows:
            features.append(
                self._feature(
                    feature_id=f"facility:{facility.id}",
                    geometry_json=geometry_json,
                    properties={
                        "feature_type": "facility",
                        "name": facility.name,
                        "facility_type": facility.facility_type.value,
                    },
                )
            )

        features.append(
            self._feature(
                feature_id=f"river:{city.id}",
                geometry_json=river_geojson,
                properties={"feature_type": "river", "name": "Rio Santa Aurora"},
            )
        )
        features.append(
            self._feature(
                feature_id=f"depot:{city.id}",
                geometry_json=depot_geojson,
                properties={"feature_type": "depot", "name": city.depot_name},
            )
        )
        return {"type": "FeatureCollection", "features": features}

    @staticmethod
    def _split_address_query(query: str) -> tuple[str, str | None]:
        comma_match = re.match(r"^(.*?),\s*(\d+[A-Za-z]?)\s*$", query)
        if comma_match:
            return comma_match.group(1).strip(), comma_match.group(2).strip()
        trailing_match = re.match(r"^(.*?)\s+(\d+[A-Za-z]?)\s*$", query)
        if trailing_match:
            return trailing_match.group(1).strip(), trailing_match.group(2).strip()
        return query, None

    @staticmethod
    def _rank_streets(streets: list[StreetModel], query: str) -> list[tuple[StreetModel, float]]:
        normalized_query = normalize_street_name(query)
        if not normalized_query:
            return []
        ranked: list[tuple[StreetModel, float]] = []
        for street in streets:
            normalized_name = normalize_street_name(street.name)
            if normalized_query == normalized_name:
                score = 1.0
            elif normalized_query in normalized_name:
                score = 0.96
            else:
                score = SequenceMatcher(None, normalized_query, normalized_name).ratio()
            if score >= 0.48:
                ranked.append((street, score))
        ranked.sort(key=lambda item: (-item[1], item[0].name))
        return ranked

    @staticmethod
    def _address_match(
        address: AddressModel,
        street_name: str,
        district_name: str,
        longitude: float,
        latitude: float,
    ) -> AddressSearchMatch:
        formatted = f"{street_name}, {address.house_number} — {district_name}"
        return AddressSearchMatch(
            id=address.id,
            street_name=street_name,
            house_number=address.house_number,
            district_name=district_name,
            complement=address.complement,
            formatted=formatted,
            longitude=float(longitude),
            latitude=float(latitude),
        )

    @staticmethod
    def _feature(
        *, feature_id: str, geometry_json: str, properties: dict[str, Any]
    ) -> dict[str, Any]:
        geometry = cast(dict[str, Any], json.loads(geometry_json))
        return {
            "type": "Feature",
            "id": feature_id,
            "geometry": geometry,
            "properties": properties,
        }
