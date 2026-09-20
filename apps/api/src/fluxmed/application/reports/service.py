import csv
import io
import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from reportlab.lib import colors  # type: ignore[import-untyped]
from reportlab.lib.pagesizes import A4  # type: ignore[import-untyped]
from reportlab.lib.styles import getSampleStyleSheet  # type: ignore[import-untyped]
from reportlab.lib.units import mm  # type: ignore[import-untyped]
from reportlab.platypus import (  # type: ignore[import-untyped]
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from fluxmed.application.optimization.results import (
    OptimizationResultNotFoundError,
    OptimizationResultService,
    OptimizationResultView,
)
from fluxmed.domain.enums import OperationStatus
from fluxmed.infrastructure.models.operation import OperationModel
from fluxmed.infrastructure.models.report import ReportModel

REPORT_TYPE = "DAILY_OPERATION"
REPORT_FORMATS = {"PDF", "XLSX", "CSV"}
REPORT_TIMEZONE_NAME = "America/Sao_Paulo"
REPORT_TIMEZONE = ZoneInfo(REPORT_TIMEZONE_NAME)
REPORT_GENERATION_FAILED_MESSAGE = "Não foi possível gerar o arquivo do relatório."

logger = logging.getLogger(__name__)


class ReportNotFoundError(LookupError):
    pass


class ReportInputError(ValueError):
    pass


class ReportGenerationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ReportView:
    id: uuid.UUID
    operation_id: uuid.UUID
    optimization_run_id: uuid.UUID
    report_type: str
    format: str
    status: str
    filename: str | None
    content_type: str | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


class ReportService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        operation_id: uuid.UUID,
        *,
        report_type: str,
        report_format: str,
        actor_user_id: uuid.UUID,
    ) -> ReportView:
        normalized_type = report_type.upper()
        normalized_format = report_format.upper()
        if normalized_type != REPORT_TYPE:
            raise ReportInputError("Tipo de relatório não suportado.")
        if normalized_format not in REPORT_FORMATS:
            raise ReportInputError("Formato de relatório não suportado.")

        operation = self._session.get(OperationModel, operation_id)
        if operation is None:
            raise ReportNotFoundError(operation_id)
        if operation.status is OperationStatus.OUTDATED:
            raise ReportInputError(
                "O plano está desatualizado. Reotimize antes de gerar relatórios."
            )

        try:
            result = OptimizationResultService(self._session).latest_for_operation(operation_id)
        except OptimizationResultNotFoundError as exc:
            raise ReportInputError(
                "A operação ainda não possui um plano otimizado válido."
            ) from exc

        snapshot = self._build_snapshot(operation, result)
        report = ReportModel(
            operation_id=operation.id,
            optimization_run_id=result.run_id,
            created_by_user_id=actor_user_id,
            report_type=normalized_type,
            format=normalized_format,
            status="QUEUED",
            snapshot=snapshot,
        )
        self._session.add(report)
        self._session.flush()

        try:
            artifact, content_type, extension = self._generate(normalized_format, snapshot)
            report.artifact = artifact
            report.content_type = content_type
            report.filename = f"fluxmed_{operation.operation_code}_report.{extension}"
            report.status = "COMPLETED"
            report.completed_at = datetime.now(UTC)
        except Exception as exc:  # pragma: no cover - defensive persistence boundary
            logger.warning(
                "Report generation failed report_id=%s format=%s error=%s",
                report.id,
                normalized_format,
                type(exc).__name__,
            )
            report.status = "FAILED"
            report.error_message = REPORT_GENERATION_FAILED_MESSAGE
            report.completed_at = datetime.now(UTC)
        self._session.flush()
        return self._view(report)

    def list(self, operation_id: uuid.UUID | None = None) -> list[ReportView]:
        statement = select(ReportModel)
        if operation_id is not None:
            statement = statement.where(ReportModel.operation_id == operation_id)
        rows = self._session.scalars(statement.order_by(ReportModel.created_at.desc())).all()
        return [self._view(row) for row in rows]

    def get(self, report_id: uuid.UUID) -> ReportView:
        return self._view(self._require(report_id))

    def download(self, report_id: uuid.UUID) -> tuple[ReportView, bytes]:
        report = self._require(report_id)
        if report.status != "COMPLETED" or report.artifact is None:
            raise ReportInputError("O relatório ainda não possui um arquivo disponível.")
        return self._view(report), report.artifact

    def _require(self, report_id: uuid.UUID) -> ReportModel:
        report = self._session.get(ReportModel, report_id)
        if report is None:
            raise ReportNotFoundError(report_id)
        return report

    @staticmethod
    def _view(report: ReportModel) -> ReportView:
        return ReportView(
            id=report.id,
            operation_id=report.operation_id,
            optimization_run_id=report.optimization_run_id,
            report_type=report.report_type,
            format=report.format,
            status=report.status,
            filename=report.filename,
            content_type=report.content_type,
            error_message=report.error_message,
            created_at=report.created_at,
            completed_at=report.completed_at,
        )

    @staticmethod
    def _build_snapshot(
        operation: OperationModel,
        result: OptimizationResultView,
    ) -> dict[str, object]:
        routes: list[dict[str, object]] = []
        for route in result.routes:
            routes.append(
                {
                    "route_code": route.route_code,
                    "vehicle": {
                        "id": str(route.vehicle.id),
                        "plate": route.vehicle.plate,
                        "type": route.vehicle.type,
                        "ownership_type": route.vehicle.ownership_type,
                    },
                    "team": {
                        "primary_role": route.team.primary_role,
                        "primary_worker": (
                            {
                                "id": str(route.team.primary_worker.id),
                                "name": route.team.primary_worker.name,
                                "role": route.team.primary_worker.role,
                            }
                            if route.team.primary_worker is not None
                            else None
                        ),
                        "helper": (
                            {
                                "id": str(route.team.helper.id),
                                "name": route.team.helper.name,
                                "role": route.team.helper.role,
                            }
                            if route.team.helper is not None
                            else None
                        ),
                        "primary_included": route.team.primary_included,
                        "helper_included": route.team.helper_included,
                        "team_cost_brl": str(route.team.team_cost_brl),
                    },
                    "delivery_count": route.delivery_count,
                    "distance_km": str(route.distance_km),
                    "duration_minutes": str(route.duration_minutes),
                    "total_weight_kg": str(route.total_weight_kg),
                    "total_volume_m3": str(route.total_volume_m3),
                    "weight_utilization_pct": str(route.weight_utilization_pct),
                    "volume_utilization_pct": str(route.volume_utilization_pct),
                    "cost": {
                        "depreciation_brl": str(route.cost.depreciation_brl),
                        "maintenance_brl": str(route.cost.maintenance_brl),
                        "fixed_time_brl": str(route.cost.fixed_time_brl),
                        "fuel_brl": str(route.cost.fuel_brl),
                        "team_brl": str(route.cost.team_brl),
                        "contract_brl": str(route.cost.contract_brl),
                        "total_brl": str(route.cost.total_brl),
                    },
                    "stops": [
                        {
                            "sequence": stop.sequence,
                            "delivery_id": str(stop.delivery_id),
                            "delivery_code": stop.delivery_code,
                            "recipient_name": stop.recipient_name,
                            "address_label": stop.address_label,
                            "priority": stop.priority,
                            "planned_arrival_at": ReportService._iso(stop.planned_arrival_at),
                            "planned_departure_at": ReportService._iso(stop.planned_departure_at),
                            "time_window_start": ReportService._iso(stop.time_window_start),
                            "time_window_end": ReportService._iso(stop.time_window_end),
                            "time_window_policy": stop.time_window_policy,
                            "service_time_minutes": stop.service_time_minutes,
                            "lateness_minutes": str(stop.lateness_minutes),
                        }
                        for stop in route.stops
                    ],
                }
            )

        return {
            "snapshot_version": "report-v1",
            "captured_at": datetime.now(UTC).isoformat(),
            "operation": {
                "id": str(operation.id),
                "operation_code": operation.operation_code,
                "operation_date": operation.operation_date.isoformat(),
                "operation_start_time": operation.operation_start_time.isoformat(),
                "operation_end_time": operation.operation_end_time.isoformat(),
                "traffic_mode": operation.traffic_mode.value,
                "status": operation.status.value,
                "revision_number": result.revision_number,
                "city_name": "Santa Aurora",
                "timezone": REPORT_TIMEZONE_NAME,
            },
            "optimization": {
                "run_id": str(result.run_id),
                "random_seed": result.random_seed,
                "generations_completed": result.generations_completed,
                "stop_reason": result.stop_reason,
                "validated": result.validated,
            },
            "metrics": {
                "delivery_count": result.delivery_count,
                "vehicles_used": result.vehicles_used,
                "total_cost_brl": str(result.total_cost_brl),
                "distance_km": str(result.distance_km),
                "makespan_minutes": str(result.makespan_minutes),
                "critical_delays": result.critical_delays,
                "on_time_percentage": str(result.on_time_percentage),
                "average_weight_utilization_pct": str(result.average_weight_utilization_pct),
                "average_volume_utilization_pct": str(result.average_volume_utilization_pct),
            },
            "routes": routes,
        }

    @staticmethod
    def _iso(value: datetime | None) -> str | None:
        return value.isoformat() if value is not None else None

    @staticmethod
    def _generate(
        report_format: str,
        snapshot: dict[str, object],
    ) -> tuple[bytes, str, str]:
        if report_format == "CSV":
            return ReportService._generate_csv(snapshot), "text/csv; charset=utf-8", "csv"
        if report_format == "XLSX":
            return (
                ReportService._generate_xlsx(snapshot),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "xlsx",
            )
        if report_format == "PDF":
            return ReportService._generate_pdf(snapshot), "application/pdf", "pdf"
        raise ReportGenerationError("Formato de relatório não suportado.")

    @staticmethod
    def _generate_csv(snapshot: dict[str, object]) -> bytes:
        data = ReportService._snapshot_data(snapshot)
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(
            [
                "operacao",
                "rota",
                "veiculo",
                "sequencia",
                "entrega",
                "destinatario",
                "endereco",
                "prioridade",
                "chegada_planejada",
                "chegada_planejada_local",
                "atraso_minutos",
            ]
        )
        operation_code = str(data["operation"]["operation_code"])
        for route in data["routes"]:
            for stop in route["stops"]:
                arrival = stop["planned_arrival_at"] or ""
                writer.writerow(
                    [
                        operation_code,
                        route["route_code"],
                        route["vehicle"]["plate"],
                        stop["sequence"],
                        stop["delivery_code"],
                        stop["recipient_name"],
                        stop["address_label"],
                        stop["priority"],
                        arrival,
                        ReportService._local_iso(arrival),
                        stop["lateness_minutes"],
                    ]
                )
        return output.getvalue().encode("utf-8-sig")

    @staticmethod
    def _generate_xlsx(snapshot: dict[str, object]) -> bytes:
        data = ReportService._snapshot_data(snapshot)
        workbook = Workbook()
        summary = workbook.active
        if summary is None:
            raise ReportGenerationError("Não foi possível inicializar a planilha de resumo.")
        summary.title = "Resumo"
        operation = data["operation"]
        metrics = data["metrics"]
        summary_rows = [
            ("Operação", operation["operation_code"]),
            ("Data", operation["operation_date"]),
            ("Cidade", operation["city_name"]),
            ("Fuso operacional", operation.get("timezone", REPORT_TIMEZONE_NAME)),
            ("Revisão", operation["revision_number"]),
            ("Status", operation["status"]),
            ("Entregas", metrics["delivery_count"]),
            ("Veículos usados", metrics["vehicles_used"]),
            ("Custo total (R$)", ReportService._number(metrics["total_cost_brl"])),
            ("Distância (km)", ReportService._number(metrics["distance_km"])),
            ("Makespan (min)", ReportService._number(metrics["makespan_minutes"])),
            ("Atrasos críticos", metrics["critical_delays"]),
            ("No prazo (%)", ReportService._percent(metrics["on_time_percentage"])),
        ]
        for label, value in summary_rows:
            summary.append([label, value])
        summary["A1"].font = Font(bold=True)
        summary["B9"].number_format = "R$ #,##0.00"
        summary["B10"].number_format = '0.000 "km"'
        summary["B11"].number_format = '0.00 "min"'
        summary["B13"].number_format = "0.00%"

        routes_sheet = workbook.create_sheet("Rotas")
        ReportService._append_table(
            routes_sheet,
            [
                "Rota",
                "Veículo",
                "Tipo",
                "Entregas",
                "Distância (km)",
                "Duração (min)",
                "Peso (kg)",
                "Volume (m³)",
                "Uso peso (%)",
                "Uso volume (%)",
                "Custo total (R$)",
            ],
            [
                [
                    route["route_code"],
                    route["vehicle"]["plate"],
                    route["vehicle"]["type"],
                    route["delivery_count"],
                    ReportService._number(route["distance_km"]),
                    ReportService._number(route["duration_minutes"]),
                    ReportService._number(route["total_weight_kg"]),
                    ReportService._number(route["total_volume_m3"]),
                    ReportService._percent(route["weight_utilization_pct"]),
                    ReportService._percent(route["volume_utilization_pct"]),
                    ReportService._number(route["cost"]["total_brl"]),
                ]
                for route in data["routes"]
            ],
        )
        ReportService._format_column(routes_sheet, "E", '0.000 "km"')
        ReportService._format_column(routes_sheet, "F", '0.00 "min"')
        ReportService._format_column(routes_sheet, "G", '0.000 "kg"')
        ReportService._format_column(routes_sheet, "H", '0.0000 "m³"')
        ReportService._format_column(routes_sheet, "I", "0.00%")
        ReportService._format_column(routes_sheet, "J", "0.00%")
        ReportService._format_column(routes_sheet, "K", "R$ #,##0.00")

        deliveries_sheet = workbook.create_sheet("Entregas")
        delivery_rows: list[list[object]] = []
        for route in data["routes"]:
            for stop in route["stops"]:
                delivery_rows.append(
                    [
                        route["route_code"],
                        route["vehicle"]["plate"],
                        stop["sequence"],
                        stop["delivery_code"],
                        stop["recipient_name"],
                        stop["address_label"],
                        stop["priority"],
                        stop["time_window_policy"],
                        ReportService._xlsx_local_datetime(stop["planned_arrival_at"]),
                        ReportService._xlsx_local_datetime(stop["planned_departure_at"]),
                        ReportService._number(stop["service_time_minutes"]),
                        ReportService._number(stop["lateness_minutes"]),
                    ]
                )
        ReportService._append_table(
            deliveries_sheet,
            [
                "Rota",
                "Veículo",
                "Sequência",
                "Entrega",
                "Destinatário",
                "Endereço",
                "Prioridade",
                "Janela",
                "Chegada local",
                "Saída local",
                "Serviço (min)",
                "Atraso (min)",
            ],
            delivery_rows,
        )
        ReportService._format_column(deliveries_sheet, "I", "dd/mm/yyyy hh:mm")
        ReportService._format_column(deliveries_sheet, "J", "dd/mm/yyyy hh:mm")
        ReportService._format_column(deliveries_sheet, "K", '0.00 "min"')
        ReportService._format_column(deliveries_sheet, "L", '0.00 "min"')

        vehicles_sheet = workbook.create_sheet("Veículos")
        ReportService._append_table(
            vehicles_sheet,
            ["Rota", "Placa", "Tipo", "Propriedade", "Entregas", "Distância (km)"],
            [
                [
                    route["route_code"],
                    route["vehicle"]["plate"],
                    route["vehicle"]["type"],
                    route["vehicle"]["ownership_type"],
                    route["delivery_count"],
                    ReportService._number(route["distance_km"]),
                ]
                for route in data["routes"]
            ],
        )
        ReportService._format_column(vehicles_sheet, "F", '0.000 "km"')

        team_sheet = workbook.create_sheet("Equipe")
        ReportService._append_table(
            team_sheet,
            [
                "Rota",
                "Veículo",
                "Função principal",
                "Profissional",
                "Ajudante",
                "Custo (R$)",
            ],
            [
                [
                    route["route_code"],
                    route["vehicle"]["plate"],
                    route["team"]["primary_role"] or "Contrato",
                    ReportService._worker_name(route["team"]["primary_worker"]),
                    ReportService._worker_name(route["team"]["helper"]),
                    ReportService._number(route["team"]["team_cost_brl"]),
                ]
                for route in data["routes"]
            ],
        )
        ReportService._format_column(team_sheet, "F", "R$ #,##0.00")

        costs_sheet = workbook.create_sheet("Custos")
        ReportService._append_table(
            costs_sheet,
            [
                "Rota",
                "Combustível",
                "Depreciação",
                "Manutenção",
                "Fixo",
                "Equipe",
                "Contrato",
                "Total",
            ],
            [
                [
                    route["route_code"],
                    ReportService._number(route["cost"]["fuel_brl"]),
                    ReportService._number(route["cost"]["depreciation_brl"]),
                    ReportService._number(route["cost"]["maintenance_brl"]),
                    ReportService._number(route["cost"]["fixed_time_brl"]),
                    ReportService._number(route["cost"]["team_brl"]),
                    ReportService._number(route["cost"]["contract_brl"]),
                    ReportService._number(route["cost"]["total_brl"]),
                ]
                for route in data["routes"]
            ],
        )
        for column in "BCDEFGH":
            ReportService._format_column(costs_sheet, column, "R$ #,##0.00")

        for worksheet in workbook.worksheets:
            ReportService._autosize(worksheet)

        output = io.BytesIO()
        workbook.save(output)
        return output.getvalue()

    @staticmethod
    def _generate_pdf(snapshot: dict[str, object]) -> bytes:
        data = ReportService._snapshot_data(snapshot)
        output = io.BytesIO()
        document = SimpleDocTemplate(
            output,
            pagesize=A4,
            leftMargin=16 * mm,
            rightMargin=16 * mm,
            topMargin=14 * mm,
            bottomMargin=14 * mm,
            title=f"FluxMed {data['operation']['operation_code']}",
        )
        styles = getSampleStyleSheet()
        story: list[Any] = [
            Paragraph("FluxMed — Relatório Operacional", styles["Title"]),
            Spacer(1, 5 * mm),
        ]
        operation = data["operation"]
        metrics = data["metrics"]
        summary_rows = [
            ["Operação", operation["operation_code"], "Data", operation["operation_date"]],
            ["Cidade", operation["city_name"], "Revisão", operation["revision_number"]],
            ["Entregas", metrics["delivery_count"], "Veículos", metrics["vehicles_used"]],
            [
                "Custo total",
                f"R$ {metrics['total_cost_brl']}",
                "Distância",
                f"{metrics['distance_km']} km",
            ],
            [
                "Makespan",
                f"{metrics['makespan_minutes']} min",
                "No prazo",
                f"{metrics['on_time_percentage']}%",
            ],
            ["Atrasos críticos", metrics["critical_delays"], "Status", operation["status"]],
        ]
        summary_table = Table(
            summary_rows,
            colWidths=[30 * mm, 50 * mm, 30 * mm, 50 * mm],
        )
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.extend([summary_table, Spacer(1, 7 * mm)])

        story.append(Paragraph("Rotas", styles["Heading2"]))
        route_rows = [["Rota", "Veículo", "Entregas", "Distância", "Duração", "Custo"]]
        for route in data["routes"]:
            route_rows.append(
                [
                    route["route_code"],
                    route["vehicle"]["plate"],
                    route["delivery_count"],
                    f"{route['distance_km']} km",
                    f"{route['duration_minutes']} min",
                    f"R$ {route['cost']['total_brl']}",
                ]
            )
        route_table = Table(route_rows, repeatRows=1)
        route_table.setStyle(ReportService._pdf_table_style())
        story.extend([route_table, Spacer(1, 7 * mm)])

        for route in data["routes"]:
            story.append(
                Paragraph(
                    f"{route['route_code']} · {route['vehicle']['plate']}",
                    styles["Heading3"],
                )
            )
            team = route["team"]
            story.append(
                Paragraph(
                    "Equipe: "
                    f"{ReportService._worker_name(team['primary_worker'])} · "
                    f"Ajudante: {ReportService._worker_name(team['helper'])}",
                    styles["BodyText"],
                )
            )
            stops = [["#", "Entrega", "Destinatário", "Prioridade", "Chegada local"]]
            for stop in route["stops"]:
                stops.append(
                    [
                        stop["sequence"],
                        stop["delivery_code"],
                        stop["recipient_name"],
                        stop["priority"],
                        ReportService._display_time(stop["planned_arrival_at"]),
                    ]
                )
            stops_table = Table(
                stops,
                repeatRows=1,
                colWidths=[10 * mm, 36 * mm, 65 * mm, 25 * mm, 28 * mm],
            )
            stops_table.setStyle(ReportService._pdf_table_style())
            story.extend([stops_table, Spacer(1, 6 * mm)])

        conclusion = (
            f"Plano validado para {metrics['delivery_count']} entregas distribuídas em "
            f"{metrics['vehicles_used']} veículos, com {metrics['on_time_percentage']}% no prazo, "
            f"{metrics['critical_delays']} atrasos críticos, "
            f"{metrics['distance_km']} km de distância total e "
            f"custo de R$ {metrics['total_cost_brl']}."
        )
        story.extend(
            [
                Paragraph("Conclusões", styles["Heading2"]),
                Paragraph(conclusion, styles["BodyText"]),
                Spacer(1, 4 * mm),
                Paragraph(
                    f"Horários exibidos em {REPORT_TIMEZONE_NAME}. "
                    "Relatório gerado a partir de snapshot imutável do plano otimizado.",
                    styles["Italic"],
                ),
            ]
        )
        document.build(story)
        return output.getvalue()

    @staticmethod
    def _pdf_table_style() -> Any:
        return TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8F3F4")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]
        )

    @staticmethod
    def _append_table(
        worksheet: Any,
        headers: Sequence[str],
        rows: Sequence[Sequence[object]],
    ) -> None:
        worksheet.append(headers)
        for cell in worksheet[1]:
            cell.font = Font(bold=True)
        worksheet.freeze_panes = "A2"
        for row in rows:
            worksheet.append(row)

    @staticmethod
    def _autosize(worksheet: Any) -> None:
        for column_index, column in enumerate(worksheet.columns, start=1):
            width = max((len(str(cell.value or "")) for cell in column), default=8)
            worksheet.column_dimensions[get_column_letter(column_index)].width = min(width + 2, 44)

    @staticmethod
    def _format_column(worksheet: Any, column: str, number_format: str) -> None:
        for cell in worksheet[column][1:]:
            if cell.value is not None:
                cell.number_format = number_format

    @staticmethod
    def _worker_name(worker: object) -> str:
        if isinstance(worker, dict):
            name = worker.get("name")
            return str(name) if name else "Incluído no contrato"
        return "Não necessário"

    @staticmethod
    def _number(value: object) -> float:
        if value is None or value == "":
            return 0.0
        return float(str(value))

    @staticmethod
    def _percent(value: object) -> float:
        return ReportService._number(value) / 100.0

    @staticmethod
    def _aware_datetime(value: object) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=REPORT_TIMEZONE)
        return parsed

    @staticmethod
    def _local_datetime(value: object) -> datetime | None:
        parsed = ReportService._aware_datetime(value)
        return parsed.astimezone(REPORT_TIMEZONE) if parsed is not None else None

    @staticmethod
    def _xlsx_local_datetime(value: object) -> datetime | None:
        localized = ReportService._local_datetime(value)
        if localized is None:
            return None
        return localized.replace(tzinfo=None)

    @staticmethod
    def _local_iso(value: object) -> str:
        localized = ReportService._local_datetime(value)
        return localized.isoformat() if localized is not None else ""

    @staticmethod
    def _display_time(value: object) -> str:
        localized = ReportService._local_datetime(value)
        return localized.strftime("%H:%M") if localized is not None else "—"

    @staticmethod
    def _snapshot_data(snapshot: dict[str, object]) -> dict[str, Any]:
        return snapshot
