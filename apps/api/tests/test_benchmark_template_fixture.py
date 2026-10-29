import hashlib
import json
import os
import uuid
from dataclasses import asdict

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from fluxmed.application.deliveries.scenario import ScenarioProfile
from fluxmed.benchmarks.matrix import SantaAuroraScenarioProblemFactory
from fluxmed.city.persistence import seed_santa_aurora
from fluxmed.domain.enums import UserRole
from fluxmed.infrastructure.database import engine
from fluxmed.infrastructure.models.user import UserModel
from fluxmed.scripts.seed_benchmark_template import (
    load_fixture,
    seed_template,
    verify_template,
)

pytestmark = pytest.mark.integration


def test_fixture_recreates_archived_normal_20_input_without_persisting() -> None:
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL is not configured")

    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            if connection.scalar(text("SELECT current_database()")) != "fluxmed_test":
                raise RuntimeError("Academic fixture test requires fluxmed_test.")
            with Session(bind=connection) as session:
                seed_santa_aurora(session)
                session.add(
                    UserModel(
                        id=uuid.uuid4(),
                        email=os.getenv("DEMO_PLANNER_EMAIL", "planner@fluxmed.demo").lower(),
                        display_name="Academic fixture test",
                        password_hash="test-only",
                        role=UserRole.PLANNER,
                        active=True,
                    )
                )
                session.flush()
                fixture = load_fixture()
                assert seed_template(session, fixture) is True
                assert seed_template(session, fixture) is False
                verify_template(session, fixture)

                problem = SantaAuroraScenarioProblemFactory(
                    session, template_operation_code="OP-20260915-001"
                ).build(profile=ScenarioProfile.NORMAL, delivery_count=20, scenario_seed=20260917)
                payload = {
                    "deliveries": [asdict(delivery) for delivery in problem.deliveries],
                    "vehicles": [asdict(vehicle) for vehicle in problem.vehicles],
                    "start": problem.operation_start_at,
                    "end": problem.operation_end_at,
                    "travel": [
                        (
                            str(origin),
                            str(destination),
                            str(metric.distance_km),
                            str(metric.travel_minutes),
                        )
                        for (origin, destination), metric in sorted(
                            problem.travel_matrix._metrics.items(),
                            key=lambda item: (str(item[0][0]), str(item[0][1])),
                        )
                    ],
                }
                data = json.dumps(payload, default=str, sort_keys=True, separators=(",", ":"))
                assert hashlib.sha256(data.encode("utf-8")).hexdigest() == (
                    "5a2bdacd2a529e7310d5871e83885f6cc16046ebb9f631ce9df22478f2cc88ee"
                )
        finally:
            transaction.rollback()
