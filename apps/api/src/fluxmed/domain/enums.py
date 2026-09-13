from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "ADMIN"
    PLANNER = "PLANNER"


class OperationStatus(StrEnum):
    DRAFT = "DRAFT"
    READY = "READY"
    OPTIMIZING = "OPTIMIZING"
    OPTIMIZED = "OPTIMIZED"
    OUTDATED = "OUTDATED"
    APPROVED = "APPROVED"
    DISPATCHED = "DISPATCHED"


class RevisionStatus(StrEnum):
    DRAFT = "DRAFT"
    OPTIMIZED = "OPTIMIZED"
    OUTDATED = "OUTDATED"
    APPROVED = "APPROVED"
    DISPATCHED = "DISPATCHED"


class DeliveryPriority(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"


class TimeWindowPolicy(StrEnum):
    HARD = "HARD"
    SOFT = "SOFT"


class TemperatureClass(StrEnum):
    AMBIENT = "AMBIENT"
    REFRIGERATED = "REFRIGERATED"


class HandlingRequirement(StrEnum):
    STANDARD = "STANDARD"
    TWO_PERSON = "TWO_PERSON"


class VehicleType(StrEnum):
    MOTO = "MOTO"
    VAN_COMPACT = "VAN_COMPACT"
    CARGO_VAN = "CARGO_VAN"
    LIGHT_TRUCK = "LIGHT_TRUCK"


class VehicleOwnershipType(StrEnum):
    OWNED = "OWNED"
    AGGREGATED = "AGGREGATED"


class WorkerRole(StrEnum):
    DRIVER = "DRIVER"
    HELPER = "HELPER"
    MOTORCYCLE_COURIER = "MOTORCYCLE_COURIER"


class TrafficMode(StrEnum):
    AUTOMATIC = "AUTOMATIC"
    FREE = "FREE"
    CUSTOM = "CUSTOM"


class CitySourceType(StrEnum):
    SYNTHETIC = "SYNTHETIC"


class RoadClass(StrEnum):
    EXPRESSWAY = "EXPRESSWAY"
    ARTERIAL = "ARTERIAL"
    COLLECTOR = "COLLECTOR"
    LOCAL = "LOCAL"
    SERVICE = "SERVICE"


class LotStatus(StrEnum):
    OCCUPIED = "OCCUPIED"
    VACANT = "VACANT"


class BuildingType(StrEnum):
    HOUSE = "HOUSE"
    APARTMENT_BUILDING = "APARTMENT_BUILDING"
    COMMERCIAL = "COMMERCIAL"
    CLINIC = "CLINIC"
    HOSPITAL = "HOSPITAL"
    PHARMACY = "PHARMACY"
    LABORATORY = "LABORATORY"
    WAREHOUSE = "WAREHOUSE"
    SCHOOL = "SCHOOL"
    PUBLIC_BUILDING = "PUBLIC_BUILDING"
    OTHER = "OTHER"


class FacilityType(StrEnum):
    DEPOT = "DEPOT"
    HOSPITAL = "HOSPITAL"
    CLINIC = "CLINIC"
    LABORATORY = "LABORATORY"
    PHARMACY = "PHARMACY"
    WAREHOUSE = "WAREHOUSE"
    PUBLIC_FACILITY = "PUBLIC_FACILITY"
