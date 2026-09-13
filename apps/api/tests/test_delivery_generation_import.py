import uuid
from datetime import date, time

from fluxmed.application.deliveries.importer import parse_delivery_file
from fluxmed.application.deliveries.scenario import ScenarioProfile, generate_scenario
from fluxmed.domain.enums import BuildingType, FacilityType
from fluxmed.infrastructure.models.city import AddressModel, BuildingModel, FacilityModel
from fluxmed.infrastructure.repositories.delivery_repository import AddressContext


def _context(index: int, facility_type: FacilityType | None = None) -> AddressContext:
    building_id = uuid.uuid5(uuid.NAMESPACE_URL, f"building-{index}")
    address = AddressModel(
        id=uuid.uuid5(uuid.NAMESPACE_URL, f"address-{index}"),
        city_id=uuid.uuid5(uuid.NAMESPACE_URL, "city"),
        street_id=uuid.uuid5(uuid.NAMESPACE_URL, "street"),
        district_id=uuid.uuid5(uuid.NAMESPACE_URL, "district"),
        building_id=building_id,
        road_segment_id=uuid.uuid5(uuid.NAMESPACE_URL, "segment"),
        house_number=str(100 + index),
        house_number_numeric=100 + index,
        suffix=None,
        complement=None,
        position_on_segment=0.5,
        location=None,
        active=True,
    )
    building_type = (
        BuildingType.HOSPITAL
        if facility_type is FacilityType.HOSPITAL
        else BuildingType.HOUSE
    )
    building = BuildingModel(
        id=building_id,
        city_id=address.city_id,
        district_id=address.district_id,
        lot_id=uuid.uuid5(uuid.NAMESPACE_URL, f"lot-{index}"),
        building_type=building_type,
        entrance_location=None,
    )
    facility = None
    if facility_type is not None:
        facility = FacilityModel(
            id=uuid.uuid5(uuid.NAMESPACE_URL, f"facility-{index}"),
            city_id=address.city_id,
            address_id=address.id,
            building_id=building_id,
            name=f"Facility {index}",
            facility_type=facility_type,
            active=True,
        )
    return AddressContext(
        address=address,
        street_name="Rua Teste",
        district_name="Centro",
        building=building,
        facility=facility,
    )


def test_scenario_generation_is_deterministic_for_same_seed() -> None:
    pool = [
        _context(index, FacilityType.HOSPITAL if index < 2 else None)
        for index in range(12)
    ]

    first = generate_scenario(
        address_pool=pool,
        operation_date=date(2026, 9, 14),
        operation_start_time=time(7, 30),
        operation_end_time=time(18, 0),
        profile=ScenarioProfile.HIGH_PRESSURE,
        delivery_count=8,
        seed=424242,
    )
    second = generate_scenario(
        address_pool=pool,
        operation_date=date(2026, 9, 14),
        operation_start_time=time(7, 30),
        operation_end_time=time(18, 0),
        profile=ScenarioProfile.HIGH_PRESSURE,
        delivery_count=8,
        seed=424242,
    )

    assert first == second
    assert len(first.deliveries) == 8
    assert len({item.destination_address_id for item in first.deliveries}) == 8


def test_import_does_not_approximate_missing_address() -> None:
    valid_context = _context(1)

    def resolver(street: str, number: str) -> AddressContext | None:
        if street == "Rua Teste" and number == valid_context.address.house_number:
            return valid_context
        return None

    csv_content = (
        b"numero_nf,serie_nf,emissor_documento,destinatario,rua,numero,peso_kg,"
        b"volume_m3,quantidade_volumes\n"
        b"123,1,12345678000190,Destino Teste,Rua Teste,999,10,0.1,2\n"
    )

    rows = parse_delivery_file(
        filename="entregas.csv",
        content=csv_content,
        operation_date=date(2026, 9, 14),
        resolve_address=resolver,
    )

    assert len(rows) == 1
    assert rows[0].status == "ERROR"
    assert rows[0].errors[0]["code"] == "ADDRESS_NOT_FOUND"
    assert rows[0].normalized == {}
