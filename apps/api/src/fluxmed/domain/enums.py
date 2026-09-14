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


class ServiceTimeSource(StrEnum):
    ESTIMATED = "ESTIMATED"
    MANUAL = "MANUAL"
    IMPORTED = "IMPORTED"


class TemperatureClass(StrEnum):
    AMBIENT = "AMBIENT"
    REFRIGERATED = "REFRIGERATED"


class HandlingRequirement(StrEnum):
    STANDARD = "STANDARD"
    TWO_PERSON = "TWO_PERSON"


class DeliveryStatus(StrEnum):
    PENDING = "PENDING"
    PLANNED = "PLANNED"
    LOADED = "LOADED"
    DISPATCHED = "DISPATCHED"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


class CargoProfile(StrEnum):
    MEDICATION_SMALL = "MEDICATION_SMALL"
    REFRIGERATED_MEDICATION = "REFRIGERATED_MEDICATION"
    LAB_MATERIAL = "LAB_MATERIAL"
    HOSPITAL_SUPPLIES = "HOSPITAL_SUPPLIES"
    BULK_CONSUMABLES = "BULK_CONSUMABLES"
    MEDICAL_EQUIPMENT = "MEDICAL_EQUIPMENT"


class VehicleType(StrEnum):
    MOTO = "MOTO"
    VAN_COMPACT = "VAN_COMPACT"
    CARGO_VAN = "CARGO_VAN"
    LIGHT_TRUCK = "LIGHT_TRUCK"


class VehicleOwnershipType(StrEnum):
    OWNED = "OWNED"
    AGGREGATED = "AGGREGATED"


class VehicleStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    MAINTENANCE = "MAINTENANCE"
    INACTIVE = "INACTIVE"


class HelperPolicy(StrEnum):
    FORBIDDEN = "FORBIDDEN"
    OPTIONAL = "OPTIONAL"
    REQUIRED = "REQUIRED"


class FuelType(StrEnum):
    GASOLINE = "GASOLINE"
    ETHANOL = "ETHANOL"
    DIESEL = "DIESEL"
    FLEX = "FLEX"
    OTHER = "OTHER"


class AggregatedPricingModel(StrEnum):
    PER_ROUTE = "PER_ROUTE"


class WorkerRole(StrEnum):
    DRIVER = "DRIVER"
    HELPER = "HELPER"
    MOTORCYCLE_COURIER = "MOTORCYCLE_COURIER"


class WorkerEngagementType(StrEnum):
    EMPLOYEE = "EMPLOYEE"
    DAY_WORKER = "DAY_WORKER"
    AGGREGATED = "AGGREGATED"


class CompensationModel(StrEnum):
    HOURLY = "HOURLY"
    DAILY = "DAILY"
    PER_ROUTE = "PER_ROUTE"
    INCLUDED_IN_VEHICLE_CONTRACT = "INCLUDED_IN_VEHICLE_CONTRACT"


class TrafficMode(StrEnum):
    AUTOMATIC = "AUTOMATIC"
    FREE = "FREE"
    CUSTOM = "CUSTOM"


class TrafficLevel(StrEnum):
    FREE = "FREE"
    LIGHT = "LIGHT"
    MODERATE = "MODERATE"
    HEAVY = "HEAVY"
    VERY_HEAVY = "VERY_HEAVY"


class RoadOverrideType(StrEnum):
    CLOSURE = "CLOSURE"
    TRAFFIC = "TRAFFIC"


class RoadOverrideDirectionScope(StrEnum):
    SEGMENT_DIRECTION = "SEGMENT_DIRECTION"


class RoutingAlgorithm(StrEnum):
    DIJKSTRA = "DIJKSTRA"
    ASTAR = "ASTAR"


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
