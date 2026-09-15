import io

from openpyxl import load_workbook

from fluxmed.application.reports.service import ReportService


def _snapshot() -> dict[str, object]:
    return {
        "snapshot_version": "report-v1",
        "captured_at": "2026-09-15T14:00:00+00:00",
        "operation": {
            "id": "operation-id",
            "operation_code": "OP-20260915-001",
            "operation_date": "2026-09-15",
            "operation_start_time": "07:30:00",
            "operation_end_time": "18:00:00",
            "traffic_mode": "AUTOMATIC",
            "status": "OPTIMIZED",
            "revision_number": 2,
            "city_name": "Santa Aurora",
        },
        "optimization": {
            "run_id": "run-id",
            "random_seed": 42,
            "generations_completed": 66,
            "stop_reason": "EARLY_STOPPING",
            "validated": True,
        },
        "metrics": {
            "delivery_count": 1,
            "vehicles_used": 1,
            "total_cost_brl": "123.45",
            "distance_km": "25.200",
            "makespan_minutes": "95.00",
            "critical_delays": 0,
            "on_time_percentage": "100.00",
            "average_weight_utilization_pct": "35.00",
            "average_volume_utilization_pct": "42.00",
        },
        "routes": [
            {
                "route_code": "R-01",
                "vehicle": {
                    "id": "vehicle-id",
                    "plate": "FMD1A03",
                    "type": "VAN_COMPACT",
                    "ownership_type": "OWNED",
                },
                "team": {
                    "primary_role": "DRIVER",
                    "primary_worker": {
                        "id": "worker-id",
                        "name": "Motorista Demo 1",
                        "role": "DRIVER",
                    },
                    "helper": None,
                    "primary_included": False,
                    "helper_included": False,
                    "team_cost_brl": "50.00",
                },
                "delivery_count": 1,
                "distance_km": "25.200",
                "duration_minutes": "95.00",
                "total_weight_kg": "20.000",
                "total_volume_m3": "0.2000",
                "weight_utilization_pct": "35.00",
                "volume_utilization_pct": "42.00",
                "cost": {
                    "depreciation_brl": "10.00",
                    "maintenance_brl": "8.00",
                    "fixed_time_brl": "5.00",
                    "fuel_brl": "20.00",
                    "team_brl": "50.00",
                    "contract_brl": "0.00",
                    "total_brl": "93.00",
                },
                "stops": [
                    {
                        "sequence": 1,
                        "delivery_id": "delivery-id",
                        "delivery_code": "DLV-NF001-001",
                        "recipient_name": "Hospital Central",
                        "address_label": "Avenida Central, 100",
                        "priority": "HIGH",
                        "planned_arrival_at": "2026-09-15T09:30:00-03:00",
                        "planned_departure_at": "2026-09-15T09:45:00-03:00",
                        "time_window_start": "2026-09-15T09:00:00-03:00",
                        "time_window_end": "2026-09-15T10:00:00-03:00",
                        "time_window_policy": "HARD",
                        "service_time_minutes": 15,
                        "lateness_minutes": "0.00",
                    }
                ],
            }
        ],
    }


def test_csv_report_contains_delivery_rows() -> None:
    content = ReportService._generate_csv(_snapshot()).decode("utf-8-sig")

    assert "OP-20260915-001" in content
    assert "DLV-NF001-001" in content
    assert "Hospital Central" in content


def test_xlsx_report_contains_required_sheets() -> None:
    content = ReportService._generate_xlsx(_snapshot())
    workbook = load_workbook(io.BytesIO(content), read_only=True)

    assert workbook.sheetnames == ["Resumo", "Rotas", "Entregas", "Veículos", "Equipe", "Custos"]
    assert workbook["Resumo"]["B1"].value == "OP-20260915-001"
    assert workbook["Entregas"]["D2"].value == "DLV-NF001-001"


def test_pdf_report_is_valid_document() -> None:
    content = ReportService._generate_pdf(_snapshot())

    assert content.startswith(b"%PDF-")
    assert len(content) > 1000
