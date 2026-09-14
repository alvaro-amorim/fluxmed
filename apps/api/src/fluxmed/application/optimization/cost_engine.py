from dataclasses import dataclass
from decimal import Decimal

from fluxmed.application.optimization.team_assignment import RouteTeamAssignment
from fluxmed.application.resources import VehicleView
from fluxmed.domain.enums import VehicleOwnershipType, VehicleType
from fluxmed.optimization import DecodedRoute

ZERO = Decimal("0")
REFERENCE_FUEL_PRICE_BRL_PER_L = Decimal("6.00")
DEFAULT_EFFICIENCY_KM_PER_L: dict[VehicleType, Decimal] = {
    VehicleType.MOTO: Decimal("30"),
    VehicleType.VAN_COMPACT: Decimal("10"),
    VehicleType.CARGO_VAN: Decimal("8"),
    VehicleType.LIGHT_TRUCK: Decimal("6"),
}


@dataclass(frozen=True, slots=True)
class RouteCostBreakdown:
    depreciation_brl: Decimal
    maintenance_brl: Decimal
    fixed_time_brl: Decimal
    fuel_brl: Decimal
    team_brl: Decimal
    contract_brl: Decimal
    total_brl: Decimal


class FinalCostEngine:
    def calculate(
        self,
        *,
        route: DecodedRoute,
        vehicle: VehicleView,
        team: RouteTeamAssignment,
    ) -> RouteCostBreakdown:
        duration_hours = route.total_duration_minutes / Decimal("60")
        depreciation = ZERO
        maintenance = ZERO
        fixed_time = ZERO
        contract = ZERO

        if vehicle.ownership_type is VehicleOwnershipType.OWNED:
            depreciation = route.distance_km * (vehicle.cost.depreciation_per_km or ZERO)
            maintenance = route.distance_km * (vehicle.cost.maintenance_per_km or ZERO)
            fixed_time = duration_hours * (vehicle.cost.fixed_cost_per_hour or ZERO)
        else:
            contract = vehicle.cost.contract_price_brl or ZERO

        fuel = ZERO
        if not vehicle.cost.fuel_included:
            efficiency = (
                vehicle.fuel_efficiency_km_per_l
                or DEFAULT_EFFICIENCY_KM_PER_L[vehicle.type]
            )
            if efficiency > ZERO:
                fuel = (route.distance_km / efficiency) * REFERENCE_FUEL_PRICE_BRL_PER_L

        total = depreciation + maintenance + fixed_time + fuel + team.team_cost_brl + contract
        return RouteCostBreakdown(
            depreciation_brl=depreciation,
            maintenance_brl=maintenance,
            fixed_time_brl=fixed_time,
            fuel_brl=fuel,
            team_brl=team.team_cost_brl,
            contract_brl=contract,
            total_brl=total,
        )
