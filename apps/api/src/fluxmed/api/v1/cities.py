import uuid
from typing import Any

from fastapi import APIRouter, Query, status
from pydantic import BaseModel

from fluxmed.api.dependencies import CurrentUser, DbSession
from fluxmed.api.errors import ApiError
from fluxmed.city.service import (
    AddressSearchResult,
    CityNotFoundError,
    CityService,
    CitySummary,
    FacilitySummary,
)
from fluxmed.domain.enums import CitySourceType, FacilityType

router = APIRouter(prefix="/cities", tags=["cities"])


class CityResponse(BaseModel):
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


class DistrictResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str


class AddressMatchResponse(BaseModel):
    id: uuid.UUID
    street_name: str
    house_number: str
    district_name: str
    complement: str | None
    formatted: str
    longitude: float
    latitude: float


class AddressSearchResponse(BaseModel):
    query: str
    matches: list[AddressMatchResponse]
    street_suggestion: str | None
    number_suggestions: list[str]


class FacilityResponse(BaseModel):
    id: uuid.UUID
    name: str
    facility_type: FacilityType
    address_id: uuid.UUID
    street_name: str
    house_number: str
    district_name: str
    longitude: float
    latitude: float


def _city_response(summary: CitySummary) -> CityResponse:
    return CityResponse(**summary.__dict__)


def _address_search_response(result: AddressSearchResult) -> AddressSearchResponse:
    return AddressSearchResponse(
        query=result.query,
        matches=[AddressMatchResponse(**item.__dict__) for item in result.matches],
        street_suggestion=result.street_suggestion,
        number_suggestions=result.number_suggestions,
    )


def _facility_response(item: FacilitySummary) -> FacilityResponse:
    return FacilityResponse(**item.__dict__)


def _not_found(exc: CityNotFoundError) -> ApiError:
    return ApiError(status.HTTP_404_NOT_FOUND, "CITY_NOT_FOUND", "Cidade não encontrada.")


@router.get("", response_model=list[CityResponse])
def list_cities(session: DbSession, current_user: CurrentUser) -> list[CityResponse]:
    del current_user
    return [_city_response(city) for city in CityService(session).list_cities()]


@router.get("/{city_id}", response_model=CityResponse)
def get_city(city_id: uuid.UUID, session: DbSession, current_user: CurrentUser) -> CityResponse:
    del current_user
    try:
        return _city_response(CityService(session).get(city_id))
    except CityNotFoundError as exc:
        raise _not_found(exc) from exc


@router.get("/{city_id}/districts", response_model=list[DistrictResponse])
def list_districts(
    city_id: uuid.UUID, session: DbSession, current_user: CurrentUser
) -> list[DistrictResponse]:
    del current_user
    try:
        districts = CityService(session).districts(city_id)
    except CityNotFoundError as exc:
        raise _not_found(exc) from exc
    return [DistrictResponse(id=item.id, name=item.name, slug=item.slug) for item in districts]


@router.get("/{city_id}/addresses/search", response_model=AddressSearchResponse)
def search_addresses(
    city_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
    q: str = Query(min_length=1, max_length=180),
    limit: int = Query(default=8, ge=1, le=20),
) -> AddressSearchResponse:
    del current_user
    try:
        result = CityService(session).search_addresses(city_id, q, limit)
    except CityNotFoundError as exc:
        raise _not_found(exc) from exc
    return _address_search_response(result)


@router.get("/{city_id}/facilities", response_model=list[FacilityResponse])
def list_facilities(
    city_id: uuid.UUID, session: DbSession, current_user: CurrentUser
) -> list[FacilityResponse]:
    del current_user
    try:
        return [_facility_response(item) for item in CityService(session).facilities(city_id)]
    except CityNotFoundError as exc:
        raise _not_found(exc) from exc


@router.get("/{city_id}/map", response_model=dict[str, Any])
def get_city_map(
    city_id: uuid.UUID, session: DbSession, current_user: CurrentUser
) -> dict[str, Any]:
    del current_user
    try:
        return CityService(session).map_geojson(city_id)
    except CityNotFoundError as exc:
        raise _not_found(exc) from exc
