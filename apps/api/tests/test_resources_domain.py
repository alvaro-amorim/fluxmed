from decimal import Decimal

import pytest

from fluxmed.domain.enums import CompensationModel
from fluxmed.domain.resources import (
    MaintenanceItemInput,
    OwnedVehicleCostInput,
    ResourceValidationError,
    VehicleCostCalculator,
    WorkerCompensationCalculator,
)


def test_owned_vehicle_cost_rates_and_route_estimate() -> None:
    profile = OwnedVehicleCostInput(
        acquisition_value_brl=Decimal("120000"),
        residual_value_brl=Decimal("20000"),
        useful_life_km=Decimal("200000"),
        annual_ipva_brl=Decimal("2400"),
        annual_insurance_brl=Decimal("3600"),
        annual_fixed_costs_brl=Decimal("6000"),
        expected_productive_hours_per_year=Decimal("2000"),
    )
    maintenance = [
        MaintenanceItemInput(cost_brl=Decimal("1200"), interval_km=Decimal("10000")),
        MaintenanceItemInput(cost_brl=Decimal("2000"), interval_km=Decimal("40000")),
    ]

    rates = VehicleCostCalculator.owned_rates(profile, maintenance)
    assert rates.depreciation_per_km == Decimal("0.5")
    assert rates.maintenance_per_km == Decimal("0.17")
    assert rates.fixed_cost_per_hour == Decimal("6")

    route = VehicleCostCalculator.estimate_owned_route(
        rates=rates,
        distance_km=Decimal("100"),
        duration_hours=Decimal("2"),
        fuel_efficiency_km_per_l=Decimal("10"),
        fuel_price_brl_per_l=Decimal("6"),
    )
    assert route.depreciation_brl == Decimal("50.0")
    assert route.maintenance_brl == Decimal("17.00")
    assert route.fixed_brl == Decimal("12")
    assert route.fuel_brl == Decimal("60")
    assert route.total_brl == Decimal("139.00")


def test_aggregated_vehicle_cost_has_only_contract_component() -> None:
    route = VehicleCostCalculator.aggregated_route(Decimal("450"))
    assert route.contract_brl == Decimal("450")
    assert route.total_brl == Decimal("450")
    assert route.fuel_brl == Decimal("0")


def test_worker_compensation_models() -> None:
    assert WorkerCompensationCalculator.estimate(
        model=CompensationModel.HOURLY,
        value_brl=Decimal("30"),
        duration_hours=Decimal("8.5"),
    ) == Decimal("255.0")
    assert WorkerCompensationCalculator.estimate(
        model=CompensationModel.DAILY,
        value_brl=Decimal("180"),
        day_count=1,
    ) == Decimal("180")
    assert WorkerCompensationCalculator.estimate(
        model=CompensationModel.PER_ROUTE,
        value_brl=Decimal("80"),
        route_count=3,
    ) == Decimal("240")
    assert WorkerCompensationCalculator.estimate(
        model=CompensationModel.INCLUDED_IN_VEHICLE_CONTRACT,
        value_brl=Decimal("999"),
    ) == Decimal("0")


def test_invalid_owned_cost_profile_is_rejected() -> None:
    profile = OwnedVehicleCostInput(
        acquisition_value_brl=Decimal("10000"),
        residual_value_brl=Decimal("12000"),
        useful_life_km=Decimal("100000"),
        annual_ipva_brl=Decimal("0"),
        annual_insurance_brl=Decimal("0"),
        annual_fixed_costs_brl=Decimal("0"),
        expected_productive_hours_per_year=Decimal("1000"),
    )
    with pytest.raises(ResourceValidationError):
        profile.validate()
