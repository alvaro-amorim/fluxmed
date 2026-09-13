from collections import deque

from fluxmed.city.generator import build_santa_aurora


def test_santa_aurora_generation_is_deterministic() -> None:
    first = build_santa_aurora(seed=20260913, dataset_version="test")
    second = build_santa_aurora(seed=20260913, dataset_version="test")

    assert first == second
    assert len(first.districts) == 9
    assert first.depot_name == "Centro de Distribuição FluxMed"


def test_graph_is_connected_and_river_crossings_are_bridges() -> None:
    city = build_santa_aurora(seed=20260913, dataset_version="test")
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
