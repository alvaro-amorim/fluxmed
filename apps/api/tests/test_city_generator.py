from collections import deque

import pytest

from fluxmed.city.generator import GeneratedCity, build_santa_aurora
from fluxmed.city.naming import normalize_street_name
from fluxmed.domain.enums import FacilityType, LotStatus


@pytest.fixture(scope="module")
def city() -> GeneratedCity:
    return build_santa_aurora(seed=20260913, dataset_version="test")


def test_santa_aurora_generation_is_deterministic(city: GeneratedCity) -> None:
    second = build_santa_aurora(seed=20260913, dataset_version="test")

    assert city.id == second.id
    assert city.streets == second.streets
    assert city.facilities == second.facilities
    assert city.addresses[:100] == second.addresses[:100]
    assert city.addresses[-100:] == second.addresses[-100:]
    assert len(city.districts) == 9
    assert city.depot_name == "Centro de Distribuição FluxMed"


def test_city_reaches_phase_six_scale(city: GeneratedCity) -> None:
    assert 140 <= len(city.streets) <= 170
    assert 700 <= len(city.intersections) <= 900
    assert 2_000 <= len(city.road_segments) <= 3_200
    assert 20_000 <= len(city.addresses) <= 40_000
    assert 40 <= len(city.facilities) <= 60
    assert any(lot.status == LotStatus.VACANT for lot in city.lots)


def test_graph_is_connected_and_river_crossings_are_bridges(city: GeneratedCity) -> None:
    adjacency: dict[object, list[object]] = {item.id: [] for item in city.intersections}
    for segment in city.road_segments:
        adjacency[segment.from_intersection_id].append(segment.to_intersection_id)

    start = city.intersections[0].id
    visited = {start}
    queue = deque([start])
    while queue:
        current = queue.popleft()
        for neighbor in adjacency[current]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    assert len(visited) == len(city.intersections)

    bridge_segments = [segment for segment in city.road_segments if segment.is_bridge]
    assert len(bridge_segments) == 6
    assert {segment.bridge_name for segment in bridge_segments} == {
        "Ponte Norte",
        "Ponte Central",
        "Ponte Sul",
    }

    for segment in city.road_segments:
        start_lon = segment.coordinates[0][0]
        end_lon = segment.coordinates[1][0]
        crosses_center = (start_lon < -46.62 < end_lon) or (end_lon < -46.62 < start_lon)
        if crosses_center:
            assert segment.is_bridge


def test_addresses_map_to_buildings_and_road_segments(city: GeneratedCity) -> None:
    building_ids = {building.id for building in city.buildings}
    segment_ids = {segment.id for segment in city.road_segments}
    vacant_lot_ids = {lot.id for lot in city.lots if lot.status == LotStatus.VACANT}
    building_lot_ids = {building.lot_id for building in city.buildings}

    assert all(address.building_id in building_ids for address in city.addresses)
    assert all(address.road_segment_id in segment_ids for address in city.addresses)
    assert vacant_lot_ids.isdisjoint(building_lot_ids)
    assert all(0 < address.position_on_segment < 1 for address in city.addresses)


def test_street_names_are_normalized_unique(city: GeneratedCity) -> None:
    normalized = [normalize_street_name(street.name) for street in city.streets]
    assert len(normalized) == len(set(normalized))


def test_facilities_have_valid_addresses_and_depot(city: GeneratedCity) -> None:
    address_ids = {address.id for address in city.addresses}
    building_ids = {building.id for building in city.buildings}

    assert all(facility.address_id in address_ids for facility in city.facilities)
    assert all(facility.building_id in building_ids for facility in city.facilities)
    depots = [facility for facility in city.facilities if facility.facility_type == FacilityType.DEPOT]
    assert len(depots) == 1
    assert depots[0].name == "Centro de Distribuição FluxMed"
