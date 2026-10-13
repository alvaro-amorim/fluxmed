import uuid

from fluxmed.application.assistant.narrative_tools import AssistantNarrativeToolset


def test_driver_instruction_localizes_planned_arrival_with_delivery_windows() -> None:
    toolset = object.__new__(AssistantNarrativeToolset)
    toolset._read_result = lambda _call: {  # type: ignore[method-assign]
        "time_window_start": "2026-09-15T12:38:00+00:00",
        "time_window_end": "2026-09-15T15:03:00+00:00",
        "time_window_policy": "HARD",
    }
    route = {
        "stops": [
            {
                "delivery_id": str(uuid.uuid4()),
                "planned_arrival_at": "2026-09-15T14:14:02+00:00",
            }
        ]
    }

    enriched = toolset._enrich_route_stops(uuid.uuid4(), route, "call-1")

    stops = enriched["stops"]
    assert isinstance(stops, list)
    stop = stops[0]
    assert isinstance(stop, dict)
    assert stop["planned_arrival_at"] == "2026-09-15T11:14:02-03:00"
    assert stop["time_window_start"] == "2026-09-15T09:38:00-03:00"
    assert stop["time_window_end"] == "2026-09-15T12:03:00-03:00"


def test_driver_instruction_localizes_arrival_even_when_delivery_lookup_fails() -> None:
    toolset = object.__new__(AssistantNarrativeToolset)
    toolset._read_result = lambda _call: None  # type: ignore[method-assign]
    route = {
        "stops": [
            {
                "delivery_id": str(uuid.uuid4()),
                "planned_arrival_at": "2026-09-15T18:54:57+00:00",
            }
        ]
    }

    enriched = toolset._enrich_route_stops(uuid.uuid4(), route, "call-2")

    stops = enriched["stops"]
    assert isinstance(stops, list)
    stop = stops[0]
    assert isinstance(stop, dict)
    assert stop["planned_arrival_at"] == "2026-09-15T15:54:57-03:00"
