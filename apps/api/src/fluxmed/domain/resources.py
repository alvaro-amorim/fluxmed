from dataclasses import dataclass
from decimal import Decimal

from fluxmed.domain.enums import CompensationModel

ZERO = Decimal("0")


class ResourceValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class OwnedVehicleCostInput:
    acquisition_value_brl: Decimal
    residual_value_brl: Decimal
    useful_life_km: Decimal
    annual_ipva_brl: Decimal
    annual_insurance_brl: Decimal
    annual_fixed_costs_brl: Decimal
    expected_productive_hours_per_year: Decimal

    def validate(self) -> None:
        non_negative = {
            "acquisition_value_brl": self.acquisition_value_brl,
            "residual_value_brl": self.residual_value_brl,
            "annual_ipva_brl": self.annual_ipva_brl,
            "annual_insurance_brl": self.annual_insurance_brl,
            "annual_fixed_costs_brl": self.annual_fixed_costs_brl,
        }
        for field, value in non_negative.items():
            if value < ZERO:
                raise ResourceValidationError(f"{field} não pode ser negativo.")
        if self.residual_value_brl > self.acquisition_value_brl:
            raise ResourceValidationError("O valor residual não pode superar o valor de aquisição.")
        if self.useful_life_km <= ZERO:
            raise ResourceValidationError("A vida útil em km deve ser maior que zero.")
        if self.expected_productive_hours_per_year <= ZERO:
            raise ResourceValidationError("As horas produtivas anuais devem ser maiores que zero.")

    @property
    def depreciation_per_km(self) -> Decimal:
        self.validate()
        return (self.acquisition_value_brl - self.residual_value_brl) / self.useful_life_km

    @property
    def fixed_cost_per_hour(self) -> Decimal:
        self.validate()
        annual_total = (
            self.annual_ipva_brl + self.annual_insurance_brl + self.annual_fixed_costs_brl
        )
        return annual_total / self.expected_productive_hours_per_year


@dataclass(frozen=True, slots=True)
class MaintenanceItemInput:
    cost_brl: Decimal
    interval_km: Decimal

    def validate(self) -> None:
        if self.cost_brl < ZERO:
            raise ResourceValidationError("O custo de manutenção não pode ser negativo.")
        if self.interval_km <= ZERO:
            raise ResourceValidationError("O intervalo de manutenção deve ser maior que zero.")

    @property
    def cost_per_km(self) -> Decimal:
        self.validate()
        return self.cost_brl / self.interval_km


@dataclass(frozen=True, slots=True)
class VehicleCostRates:
    depreciation_per_km: Decimal
    maintenance_per_km: Decimal
    fixed_cost_per_hour: Decimal

    @property
    def non_fuel_variable_per_km(self) -> Decimal:
        return self.depreciation_per_km + self.maintenance_per_km


@dataclass(frozen=True, slots=True)
class VehicleRouteCost:
    depreciation_brl: Decimal
    maintenance_brl: Decimal
    fixed_brl: Decimal
    fuel_brl: Decimal
    contract_brl: Decimal

    @property
    def total_brl(self) -> Decimal:
        return (
            self.depreciation_brl
            + self.maintenance_brl
            + self.fixed_brl
            + self.fuel_brl
            + self.contract_brl
        )


class VehicleCostCalculator:
    @staticmethod
    def owned_rates(
        profile: OwnedVehicleCostInput,
        maintenance_items: list[MaintenanceItemInput],
    ) -> VehicleCostRates:
        profile.validate()
        maintenance_per_km = sum(
            (item.cost_per_km for item in maintenance_items),
            ZERO,
        )
        return VehicleCostRates(
            depreciation_per_km=profile.depreciation_per_km,
            maintenance_per_km=maintenance_per_km,
            fixed_cost_per_hour=profile.fixed_cost_per_hour,
        )

    @staticmethod
    def estimate_owned_route(
        *,
        rates: VehicleCostRates,
        distance_km: Decimal,
        duration_hours: Decimal,
        fuel_efficiency_km_per_l: Decimal | None = None,
        fuel_price_brl_per_l: Decimal | None = None,
    ) -> VehicleRouteCost:
        if distance_km < ZERO or duration_hours < ZERO:
            raise ResourceValidationError("Distância e duração não podem ser negativas.")
        fuel = ZERO
        if fuel_price_brl_per_l is not None:
            if fuel_price_brl_per_l < ZERO:
                raise ResourceValidationError("O preço do combustível não pode ser negativo.")
            if fuel_efficiency_km_per_l is None or fuel_efficiency_km_per_l <= ZERO:
                raise ResourceValidationError(
                    "Eficiência de combustível válida é obrigatória para calcular combustível."
                )
            fuel = (distance_km / fuel_efficiency_km_per_l) * fuel_price_brl_per_l
        return VehicleRouteCost(
            depreciation_brl=distance_km * rates.depreciation_per_km,
            maintenance_brl=distance_km * rates.maintenance_per_km,
            fixed_brl=duration_hours * rates.fixed_cost_per_hour,
            fuel_brl=fuel,
            contract_brl=ZERO,
        )

    @staticmethod
    def aggregated_route(price_brl: Decimal) -> VehicleRouteCost:
        if price_brl < ZERO:
            raise ResourceValidationError("O preço do contrato não pode ser negativo.")
        return VehicleRouteCost(
            depreciation_brl=ZERO,
            maintenance_brl=ZERO,
            fixed_brl=ZERO,
            fuel_brl=ZERO,
            contract_brl=price_brl,
        )


class WorkerCompensationCalculator:
    @staticmethod
    def estimate(
        *,
        model: CompensationModel,
        value_brl: Decimal,
        duration_hours: Decimal = ZERO,
        route_count: int = 1,
        day_count: int = 1,
    ) -> Decimal:
        if value_brl < ZERO or duration_hours < ZERO:
            raise ResourceValidationError("Valores de custo e duração não podem ser negativos.")
        if route_count < 0 or day_count < 0:
            raise ResourceValidationError("Quantidades não podem ser negativas.")
        if model is CompensationModel.HOURLY:
            return value_brl * duration_hours
        if model is CompensationModel.DAILY:
            return value_brl * Decimal(day_count)
        if model is CompensationModel.PER_ROUTE:
            return value_brl * Decimal(route_count)
        if model is CompensationModel.INCLUDED_IN_VEHICLE_CONTRACT:
            return ZERO
        raise ResourceValidationError(f"Modelo de compensação não suportado: {model}.")
