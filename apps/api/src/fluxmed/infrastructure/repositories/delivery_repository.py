import re
import uuid
from dataclasses import dataclass

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.orm import Session

from fluxmed.city.naming import normalize_street_name
from fluxmed.domain.enums import DeliveryPriority, DeliveryStatus, TemperatureClass
from fluxmed.infrastructure.models.city import (
    AddressModel,
    BuildingModel,
    DistrictModel,
    FacilityModel,
    StreetModel,
)
from fluxmed.infrastructure.models.delivery import DeliveryModel


@dataclass(frozen=True, slots=True)
class AddressContext:
    address: AddressModel
    street_name: str
    district_name: str
    building: BuildingModel
    facility: FacilityModel | None

    @property
    def formatted(self) -> str:
        return f"{self.street_name}, {self.address.house_number} — {self.district_name}"


class DeliveryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, delivery: DeliveryModel) -> None:
        self._session.add(delivery)

    def get_by_id(self, delivery_id: uuid.UUID) -> DeliveryModel | None:
        return self._session.get(DeliveryModel, delivery_id)

    def delete(self, delivery: DeliveryModel) -> None:
        self._session.delete(delivery)

    def next_delivery_code(self, invoice_number: str) -> str:
        token = re.sub(r"[^A-Z0-9]", "", invoice_number.upper())[:24] or "SEMNUMERO"
        prefix = f"DLV-NF{token}-"
        latest = self._session.scalar(
            select(DeliveryModel.delivery_code)
            .where(DeliveryModel.delivery_code.like(f"{prefix}%"))
            .order_by(DeliveryModel.delivery_code.desc())
            .limit(1)
        )
        sequence = int(latest.rsplit("-", 1)[1]) + 1 if latest else 1
        return f"{prefix}{sequence:03d}"

    def list_page(
        self,
        *,
        page: int,
        page_size: int,
        operation_id: uuid.UUID | None = None,
        priority: DeliveryPriority | None = None,
        temperature_class: TemperatureClass | None = None,
        status: DeliveryStatus | None = None,
        district_id: uuid.UUID | None = None,
        q: str | None = None,
    ) -> tuple[list[tuple[DeliveryModel, str, str]], int]:
        filters: list[ColumnElement[bool]] = []
        if operation_id is not None:
            filters.append(DeliveryModel.operation_id == operation_id)
        if priority is not None:
            filters.append(DeliveryModel.priority == priority)
        if temperature_class is not None:
            filters.append(DeliveryModel.temperature_class == temperature_class)
        if status is not None:
            filters.append(DeliveryModel.status == status)
        if district_id is not None:
            filters.append(AddressModel.district_id == district_id)
        if q:
            pattern = f"%{q.strip()}%"
            filters.append(
                or_(
                    DeliveryModel.delivery_code.ilike(pattern),
                    DeliveryModel.invoice_number.ilike(pattern),
                    DeliveryModel.recipient_name.ilike(pattern),
                    StreetModel.name.ilike(pattern),
                )
            )

        base = (
            select(DeliveryModel, StreetModel.name, DistrictModel.name)
            .join(AddressModel, AddressModel.id == DeliveryModel.destination_address_id)
            .join(StreetModel, StreetModel.id == AddressModel.street_id)
            .join(DistrictModel, DistrictModel.id == AddressModel.district_id)
            .where(*filters)
        )
        total = int(
            self._session.scalar(
                select(func.count())
                .select_from(DeliveryModel)
                .join(AddressModel, AddressModel.id == DeliveryModel.destination_address_id)
                .join(StreetModel, StreetModel.id == AddressModel.street_id)
                .where(*filters)
            )
            or 0
        )
        statement = (
            base.order_by(DeliveryModel.created_at.desc(), DeliveryModel.delivery_code.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self._session.execute(statement).tuples().all()), total

    def address_context(self, address_id: uuid.UUID) -> AddressContext | None:
        row = self._session.execute(
            select(
                AddressModel,
                StreetModel.name,
                DistrictModel.name,
                BuildingModel,
                FacilityModel,
            )
            .join(StreetModel, StreetModel.id == AddressModel.street_id)
            .join(DistrictModel, DistrictModel.id == AddressModel.district_id)
            .join(BuildingModel, BuildingModel.id == AddressModel.building_id)
            .outerjoin(FacilityModel, FacilityModel.address_id == AddressModel.id)
            .where(AddressModel.id == address_id, AddressModel.active.is_(True))
        ).one_or_none()
        if row is None:
            return None
        address, street_name, district_name, building, facility = row
        return AddressContext(address, street_name, district_name, building, facility)

    def find_exact_address(self, street_name: str, house_number: str) -> AddressContext | None:
        normalized = normalize_street_name(street_name)
        streets = self._session.scalars(select(StreetModel).order_by(StreetModel.name)).all()
        street = next(
            (item for item in streets if normalize_street_name(item.name) == normalized),
            None,
        )
        if street is None:
            return None
        address_id = self._session.scalar(
            select(AddressModel.id).where(
                AddressModel.street_id == street.id,
                AddressModel.active.is_(True),
                func.upper(AddressModel.house_number) == house_number.strip().upper(),
            )
        )
        return self.address_context(address_id) if address_id is not None else None

    def scenario_address_pool(self) -> list[AddressContext]:
        rows = self._session.execute(
            select(
                AddressModel,
                StreetModel.name,
                DistrictModel.name,
                BuildingModel,
                FacilityModel,
            )
            .join(StreetModel, StreetModel.id == AddressModel.street_id)
            .join(DistrictModel, DistrictModel.id == AddressModel.district_id)
            .join(BuildingModel, BuildingModel.id == AddressModel.building_id)
            .outerjoin(FacilityModel, FacilityModel.address_id == AddressModel.id)
            .where(AddressModel.active.is_(True))
            .order_by(AddressModel.id)
        ).all()
        return [AddressContext(*row) for row in rows]
