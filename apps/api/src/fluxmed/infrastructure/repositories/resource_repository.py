import uuid
from datetime import date

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from fluxmed.domain.enums import VehicleStatus, WorkerRole
from fluxmed.infrastructure.models.resource import (
    AggregatedVehicleContractModel,
    OperationVehicleSelectionModel,
    OperationWorkerSelectionModel,
    OwnedVehicleCostProfileModel,
    VehicleMaintenanceItemModel,
    VehicleModel,
    WorkerAvailabilityModel,
    WorkerModel,
)


class ResourceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_vehicle(self, vehicle: VehicleModel) -> None:
        self._session.add(vehicle)

    def get_vehicle(self, vehicle_id: uuid.UUID) -> VehicleModel | None:
        return self._session.get(VehicleModel, vehicle_id)

    def get_vehicle_by_plate(self, plate: str) -> VehicleModel | None:
        return self._session.scalar(select(VehicleModel).where(VehicleModel.plate == plate))

    def list_vehicles(
        self,
        *,
        active: bool | None = None,
        status: VehicleStatus | None = None,
        refrigerated: bool | None = None,
        q: str | None = None,
    ) -> list[VehicleModel]:
        query = select(VehicleModel)
        if active is not None:
            query = query.where(VehicleModel.active.is_(active))
        if status is not None:
            query = query.where(VehicleModel.status == status)
        if refrigerated is not None:
            query = query.where(VehicleModel.refrigerated.is_(refrigerated))
        if q:
            query = query.where(func.lower(VehicleModel.plate).contains(q.lower().strip()))
        ordered = query.order_by(VehicleModel.active.desc(), VehicleModel.plate)
        return list(self._session.scalars(ordered))

    def get_owned_cost_profile(
        self, vehicle_id: uuid.UUID
    ) -> OwnedVehicleCostProfileModel | None:
        return self._session.scalar(
            select(OwnedVehicleCostProfileModel).where(
                OwnedVehicleCostProfileModel.vehicle_id == vehicle_id
            )
        )

    def get_aggregated_contract(
        self, vehicle_id: uuid.UUID
    ) -> AggregatedVehicleContractModel | None:
        return self._session.scalar(
            select(AggregatedVehicleContractModel).where(
                AggregatedVehicleContractModel.vehicle_id == vehicle_id
            )
        )

    def list_maintenance_items(self, vehicle_id: uuid.UUID) -> list[VehicleMaintenanceItemModel]:
        return list(
            self._session.scalars(
                select(VehicleMaintenanceItemModel)
                .where(VehicleMaintenanceItemModel.vehicle_id == vehicle_id)
                .order_by(VehicleMaintenanceItemModel.name)
            )
        )

    def replace_vehicle_cost_data(
        self,
        vehicle_id: uuid.UUID,
        *,
        owned_profile: OwnedVehicleCostProfileModel | None,
        maintenance_items: list[VehicleMaintenanceItemModel],
        aggregated_contract: AggregatedVehicleContractModel | None,
    ) -> None:
        self._session.execute(
            delete(VehicleMaintenanceItemModel).where(
                VehicleMaintenanceItemModel.vehicle_id == vehicle_id
            )
        )
        self._session.execute(
            delete(OwnedVehicleCostProfileModel).where(
                OwnedVehicleCostProfileModel.vehicle_id == vehicle_id
            )
        )
        self._session.execute(
            delete(AggregatedVehicleContractModel).where(
                AggregatedVehicleContractModel.vehicle_id == vehicle_id
            )
        )
        if owned_profile is not None:
            self._session.add(owned_profile)
        self._session.add_all(maintenance_items)
        if aggregated_contract is not None:
            self._session.add(aggregated_contract)

    def add_worker(self, worker: WorkerModel) -> None:
        self._session.add(worker)

    def get_worker(self, worker_id: uuid.UUID) -> WorkerModel | None:
        return self._session.get(WorkerModel, worker_id)

    def list_workers(
        self,
        *,
        active: bool | None = None,
        role: WorkerRole | None = None,
        q: str | None = None,
    ) -> list[WorkerModel]:
        query = select(WorkerModel)
        if active is not None:
            query = query.where(WorkerModel.active.is_(active))
        if role is not None:
            query = query.where(WorkerModel.role == role)
        if q:
            query = query.where(func.lower(WorkerModel.name).contains(q.lower().strip()))
        ordered = query.order_by(WorkerModel.active.desc(), WorkerModel.name)
        return list(self._session.scalars(ordered))

    def get_availability(
        self, worker_id: uuid.UUID, target_date: date
    ) -> WorkerAvailabilityModel | None:
        return self._session.scalar(
            select(WorkerAvailabilityModel).where(
                WorkerAvailabilityModel.worker_id == worker_id,
                WorkerAvailabilityModel.date == target_date,
            )
        )

    def set_availability(
        self,
        worker_id: uuid.UUID,
        target_date: date,
        *,
        available: bool,
        notes: str | None,
    ) -> WorkerAvailabilityModel:
        model = self.get_availability(worker_id, target_date)
        if model is None:
            model = WorkerAvailabilityModel(
                worker_id=worker_id,
                date=target_date,
                available=available,
                notes=notes,
            )
            self._session.add(model)
        else:
            model.available = available
            model.notes = notes
        return model

    def selected_vehicle_ids(self, operation_id: uuid.UUID) -> list[uuid.UUID]:
        return list(
            self._session.scalars(
                select(OperationVehicleSelectionModel.vehicle_id).where(
                    OperationVehicleSelectionModel.operation_id == operation_id
                )
            )
        )

    def selected_worker_ids(self, operation_id: uuid.UUID) -> list[uuid.UUID]:
        return list(
            self._session.scalars(
                select(OperationWorkerSelectionModel.worker_id).where(
                    OperationWorkerSelectionModel.operation_id == operation_id
                )
            )
        )

    def replace_operation_selection(
        self,
        operation_id: uuid.UUID,
        *,
        vehicle_ids: list[uuid.UUID],
        worker_ids: list[uuid.UUID],
    ) -> None:
        self._session.execute(
            delete(OperationVehicleSelectionModel).where(
                OperationVehicleSelectionModel.operation_id == operation_id
            )
        )
        self._session.execute(
            delete(OperationWorkerSelectionModel).where(
                OperationWorkerSelectionModel.operation_id == operation_id
            )
        )
        self._session.add_all(
            [
                OperationVehicleSelectionModel(operation_id=operation_id, vehicle_id=vehicle_id)
                for vehicle_id in vehicle_ids
            ]
        )
        self._session.add_all(
            [
                OperationWorkerSelectionModel(operation_id=operation_id, worker_id=worker_id)
                for worker_id in worker_ids
            ]
        )
