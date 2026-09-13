from collections import Counter, deque

from fluxmed.city.generator import build_santa_aurora
from fluxmed.city.naming import normalize_street_name
from fluxmed.domain.enums import FacilityType, LotStatus


def validate() -> list[str]:
    city = build_santa_aurora()
    errors: list[str] = []

    if len(city.districts) != 9:
        errors.append(f"expected 9 districts, got {len(city.districts)}")
    if not 140 <= len(city.streets) <= 170:
        errors.append(f"street count outside target: {len(city.streets)}")
    if not 20_000 <= len(city.addresses) <= 40_000:
        errors.append(f"address count outside target: {len(city.addresses)}")
    if not 40 <= len(city.facilities) <= 60:
        errors.append(f"facility count outside target: {len(city.facilities)}")

    normalized_names = [normalize_street_name(street.name) for street in city.streets]
    if len(normalized_names) != len(set(normalized_names)):
        errors.append("street names are not normalized-unique")

    adjacency: dict[object, list[object]] = {item.id: [] for item in city.intersections}
    segment_ids = {segment.id for segment in city.road_segments}
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
    if len(visited) != len(city.intersections):
        errors.append("road graph is not strongly reachable from the validation start node")

    building_ids = {building.id for building in city.buildings}
    occupied_lot_ids = {lot.id for lot in city.lots if lot.status == LotStatus.OCCUPIED}
    building_lot_ids = {building.lot_id for building in city.buildings}
    if not building_lot_ids <= occupied_lot_ids:
        errors.append("a building was generated on a vacant lot")
    if any(address.building_id not in building_ids for address in city.addresses):
        errors.append("an address references a missing building")
    if any(address.road_segment_id not in segment_ids for address in city.addresses):
        errors.append("an address references a missing road segment")

    address_ids = {address.id for address in city.addresses}
    if any(facility.address_id not in address_ids for facility in city.facilities):
        errors.append("a facility references a missing address")
    facility_types = Counter(facility.facility_type for facility in city.facilities)
    if facility_types[FacilityType.DEPOT] != 1:
        errors.append("city must contain exactly one FluxMed depot")

    bridge_names = {segment.bridge_name for segment in city.road_segments if segment.is_bridge}
    if bridge_names != {"Ponte Sul", "Ponte Central", "Ponte Norte"}:
        errors.append(f"unexpected bridge set: {sorted(str(item) for item in bridge_names)}")

    return errors


def main() -> None:
    errors = validate()
    if errors:
        print("Santa Aurora validation failed:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    city = build_santa_aurora()
    print(
        "Santa Aurora valid: "
        f"{len(city.districts)} districts, "
        f"{len(city.streets)} streets, "
        f"{len(city.intersections)} intersections, "
        f"{len(city.road_segments)} directed segments, "
        f"{len(city.addresses)} addresses, "
        f"{len(city.facilities)} facilities."
    )


if __name__ == "__main__":
    main()
