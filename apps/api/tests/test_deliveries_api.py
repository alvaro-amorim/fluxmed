import os
import uuid
from datetime import date, time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from fluxmed.city.persistence import seed_santa_aurora
from fluxmed.domain.enums import OperationStatus, TrafficMode, UserRole
from fluxmed.infrastructure.database import session_scope
from fluxmed.infrastructure.models.auth_session import AuthSessionModel
from fluxmed.infrastructure.models.city import AddressModel, CityModel, StreetModel
from fluxmed.infrastructure.models.operation import OperationModel
from fluxmed.infrastructure.models.user import UserModel
from fluxmed.main import app
from fluxmed.security.passwords import hash_password

pytestmark = pytest.mark.integration


def test_delivery_endpoints_use_real_addresses_and_confirm_import_atomically() -> None:
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL is not configured")

    email = f"deliveries-api-{uuid.uuid4().hex}@example.test"
    password = "TestPassword2026!"
    with session_scope() as session:
        user = UserModel(
            email=email,
            display_name="Deliveries API Test",
            password_hash=hash_password(password),
            role=UserRole.PLANNER,
            active=True,
        )
        session.add(user)
        session.flush()
        user_id = user.id
        city = seed_santa_aurora(
            session,
            seed=int(uuid.uuid4().int % 1_000_000_000),
            dataset_version=f"deliveries-api-{uuid.uuid4().hex[:8]}",
            replace=True,
        )
        city_id = city.id
        operation = OperationModel(
            operation_code=f"OP-TEST-{uuid.uuid4().hex[:8]}",
            operation_date=date(2026, 9, 14),
            operation_start_time=time(7, 30),
            operation_end_time=time(18, 0),
            traffic_mode=TrafficMode.AUTOMATIC,
            status=OperationStatus.DRAFT,
            current_revision_number=0,
            created_by_user_id=user_id,
        )
        session.add(operation)
        session.flush()
        operation_id = operation.id
        address, street_name = session.execute(
            select(AddressModel, StreetModel.name)
            .join(StreetModel, StreetModel.id == AddressModel.street_id)
            .where(AddressModel.city_id == city_id, AddressModel.active.is_(True))
            .order_by(AddressModel.id)
            .limit(1)
        ).one()
        address_id = address.id
        house_number = address.house_number

    try:
        with TestClient(app) as client:
            login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
            assert login.status_code == 200

            created = client.post(
                f"/api/v1/operations/{operation_id}/deliveries",
                json={
                    "invoice_number": "45872",
                    "invoice_series": "1",
                    "issuer_document": "12.345.678/0001-90",
                    "recipient_name": "Hospital de Teste",
                    "destination_address_id": str(address_id),
                    "package_count": 4,
                    "total_weight_kg": "32.5",
                    "total_volume_m3": "0.42",
                    "priority": "CRITICAL",
                    "time_window_policy": "HARD",
                    "temperature_class": "REFRIGERATED",
                    "handling_requirement": "STANDARD",
                },
            )
            assert created.status_code == 201
            created_body = created.json()
            assert created_body["delivery_code"].startswith("DLV-NF45872-")
            assert created_body["destination_address_id"] == str(address_id)
            assert created_body["service_time_source"] == "ESTIMATED"

            invalid_address = client.post(
                f"/api/v1/operations/{operation_id}/deliveries",
                json={
                    "invoice_number": "999",
                    "invoice_series": "1",
                    "issuer_document": "12.345.678/0001-90",
                    "recipient_name": "Destino inválido",
                    "destination_address_id": str(uuid.uuid4()),
                    "package_count": 1,
                    "total_weight_kg": "1",
                    "total_volume_m3": "0.01",
                },
            )
            assert invalid_address.status_code == 422
            assert invalid_address.json()["error"]["code"] == "ADDRESS_NOT_FOUND"

            scenario = client.post(
                f"/api/v1/operations/{operation_id}/generate-scenario",
                json={"profile": "NORMAL", "delivery_count": 3, "random_seed": 424242},
            )
            assert scenario.status_code == 200
            assert scenario.json()["seed"] == 424242
            assert scenario.json()["summary"]["generated_count"] == 3
            assert scenario.json()["validation"]["status"] == "PENDING_RESOURCES"

            csv_content = (
                "numero_nf,serie_nf,emissor_documento,destinatario,rua,numero,peso_kg,"
                "volume_m3,quantidade_volumes,prioridade\n"
                f"700,1,12345678000190,Clínica Importada,{street_name},{house_number},12,0.08,2,HIGH\n"
            )
            preview = client.post(
                f"/api/v1/operations/{operation_id}/delivery-imports",
                files={"file": ("entregas.csv", csv_content.encode(), "text/csv")},
            )
            assert preview.status_code == 201
            preview_body = preview.json()
            assert preview_body["summary"]["error_rows"] == 0
            assert preview_body["summary"]["valid_rows"] == 1

            confirmed = client.post(
                f"/api/v1/delivery-imports/{preview_body['id']}/confirm"
            )
            assert confirmed.status_code == 200
            assert confirmed.json()["status"] == "CONFIRMED"

            deliveries = client.get(
                "/api/v1/deliveries",
                params={"operation_id": str(operation_id)},
            )
            assert deliveries.status_code == 200
            assert deliveries.json()["total"] == 5
    finally:
        with session_scope() as session:
            session.execute(delete(OperationModel).where(OperationModel.id == operation_id))
            session.execute(delete(AuthSessionModel).where(AuthSessionModel.user_id == user_id))
            session.execute(delete(UserModel).where(UserModel.id == user_id))
            session.execute(delete(CityModel).where(CityModel.id == city_id))
