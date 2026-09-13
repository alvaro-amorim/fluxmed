import json
import uuid
from dataclasses import dataclass
from typing import Any, cast

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fluxmed.domain.enums import CitySourceType
from fluxmed.infrastructure.models.city import (
    CityModel,
    DistrictModel,
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
    intersection_count: int
    road_segment_count: int
    bridge_count: int


class CityService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _summary(self, city: CityModel) -> CitySummary:
        district_count = self._session.scalar(
            select(func.count()).select_from(DistrictModel).where(DistrictModel.city_id == city.id)
        )
        intersection_count = self._session.scalar(
            select(func.count())
            .select_from(IntersectionModel)
            .where(IntersectionModel.city_id == city.id)
        )
        road_segment_count = self._session.scalar(
            select(func.count())
            .select_from(RoadSegmentModel)
            .where(RoadSegmentModel.city_id == city.id)
        )
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
            district_count=int(district_count or 0),
            intersection_count=int(intersection_count or 0),
            road_segment_count=int(road_segment_count or 0),
            bridge_count=int(bridge_count or 0),
        )

    def list(self) -> list[CitySummary]:
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
                        "street_name": street_name,
                        "road_class": segment.road_class.value,
                        "speed_limit_kmh": segment.speed_limit_kmh,
                        "lanes": segment.lanes,
                        "is_bridge": segment.is_bridge,
                        "bridge_name": segment.bridge_name,
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
