from dataclasses import dataclass
from datetime import datetime, time

from fluxmed.domain.enums import RoadClass, TrafficLevel, TrafficMode

TRAFFIC_LEVEL_FACTORS: dict[TrafficLevel, float] = {
    TrafficLevel.FREE: 1.00,
    TrafficLevel.LIGHT: 1.10,
    TrafficLevel.MODERATE: 1.25,
    TrafficLevel.HEAVY: 1.55,
    TrafficLevel.VERY_HEAVY: 1.90,
}

ROAD_CLASS_FACTORS: dict[RoadClass, float] = {
    RoadClass.EXPRESSWAY: 0.92,
    RoadClass.ARTERIAL: 1.00,
    RoadClass.COLLECTOR: 1.04,
    RoadClass.LOCAL: 1.07,
    RoadClass.SERVICE: 1.08,
}

DISTRICT_FACTORS: dict[str, float] = {
    "centro-historico": 1.14,
    "parque-universitario": 1.08,
    "santa-cecilia": 1.07,
    "vila-aurora": 1.04,
    "jardim-das-flores": 1.02,
    "nova-esperanca": 1.01,
    "distrito-industrial": 1.03,
    "distrito-logistico": 1.02,
    "vale-verde": 0.97,
}


@dataclass(frozen=True, slots=True)
class TimeBucket:
    start_minute: int
    end_minute: int
    label: str


def time_bucket(value: datetime | time, bucket_minutes: int = 15) -> TimeBucket:
    local_time = value.time() if isinstance(value, datetime) else value
    minute_of_day = local_time.hour * 60 + local_time.minute
    start = (minute_of_day // bucket_minutes) * bucket_minutes
    end = min(start + bucket_minutes, 24 * 60)
    return TimeBucket(
        start_minute=start,
        end_minute=end,
        label=f"{start // 60:02d}:{start % 60:02d}-{end // 60:02d}:{end % 60:02d}",
    )


class TrafficModel:
    @staticmethod
    def factor(
        *,
        mode: TrafficMode,
        entered_at: datetime,
        road_class: RoadClass,
        district_slug: str,
        override_level: TrafficLevel | None = None,
    ) -> float:
        if override_level is not None:
            return TRAFFIC_LEVEL_FACTORS[override_level]

        if mode in {TrafficMode.FREE, TrafficMode.CUSTOM}:
            return 1.0

        peak = TrafficModel._time_factor(entered_at.time())
        road = ROAD_CLASS_FACTORS[road_class]
        district = DISTRICT_FACTORS.get(district_slug, 1.0)
        return max(1.0, peak * road * district)

    @staticmethod
    def _time_factor(value: time) -> float:
        minute = value.hour * 60 + value.minute
        if 7 * 60 <= minute < 9 * 60:
            return 1.38
        if 16 * 60 <= minute < 19 * 60:
            return 1.48
        if 6 * 60 <= minute < 7 * 60:
            return 1.12
        if 9 * 60 <= minute < 11 * 60:
            return 1.18
        if 11 * 60 <= minute < 14 * 60:
            return 1.24
        if 14 * 60 <= minute < 16 * 60:
            return 1.16
        if 19 * 60 <= minute < 22 * 60:
            return 1.10
        return 1.0
