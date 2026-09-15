import csv
import io
import unicodedata
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from openpyxl import load_workbook

from fluxmed.domain.enums import (
    DeliveryPriority,
    HandlingRequirement,
    TemperatureClass,
    TimeWindowPolicy,
)
from fluxmed.infrastructure.repositories.delivery_repository import AddressContext

REQUIRED_COLUMNS = {
    "numero_nf",
    "serie_nf",
    "emissor_documento",
    "destinatario",
    "rua",
    "numero",
    "peso_kg",
    "volume_m3",
    "quantidade_volumes",
}


class UnsupportedImportFormatError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ParsedImportRow:
    row_number: int
    status: str
    normalized: dict[str, object]
    errors: list[dict[str, str]]
    warnings: list[dict[str, str]]


def _header(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode()
    return text.strip().lower().replace(" ", "_").replace("-", "_")


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _decimal(value: object, field: str) -> Decimal:
    text = _text(value)
    raw = text.replace(".", "").replace(",", ".") if "," in text else text
    try:
        parsed = Decimal(raw)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} deve ser numérico.") from exc
    if parsed <= 0:
        raise ValueError(f"{field} deve ser maior que zero.")
    return parsed


def _integer(value: object, field: str) -> int:
    try:
        parsed = int(float(_text(value)))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} deve ser inteiro.") from exc
    if parsed <= 0:
        raise ValueError(f"{field} deve ser maior que zero.")
    return parsed


def _bool(value: object) -> bool:
    return _text(value).lower() in {"1", "true", "sim", "s", "yes", "y"}


def _enum_value(
    enum_type: type[Any],
    value: object,
    default: Any,
    field: str,
) -> Any:
    raw = _text(value).upper()
    if not raw:
        return default
    try:
        return enum_type(raw)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in enum_type)
        raise ValueError(f"{field} inválido. Use: {allowed}.") from exc


def _datetime_value(value: object, operation_date: date) -> datetime | None:
    raw = _text(value)
    if not raw:
        return None
    timezone = ZoneInfo("America/Sao_Paulo")
    try:
        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone)
        return parsed
    except ValueError:
        try:
            parsed_time = time.fromisoformat(raw)
        except ValueError as exc:
            raise ValueError("Janela deve usar ISO 8601 ou HH:MM.") from exc
        return datetime.combine(operation_date, parsed_time, timezone)


def _rows_from_csv(content: bytes) -> tuple[list[str], list[list[object]]]:
    text = content.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return [], []
    return [_header(item) for item in rows[0]], [list(row) for row in rows[1:]]


def _rows_from_xlsx(content: bytes) -> tuple[list[str], list[list[object]]]:
    workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    sheet = workbook.active
    if sheet is None:
        return [], []
    iterator = sheet.iter_rows(values_only=True)
    first = next(iterator, None)
    if first is None:
        return [], []
    headers = [_header(item) for item in first]
    return headers, [list(row) for row in iterator]


def _table(filename: str, content: bytes) -> tuple[list[str], list[list[object]]]:
    suffix = Path(filename).suffix.lower()
    if suffix == ".csv":
        return _rows_from_csv(content)
    if suffix == ".xlsx":
        return _rows_from_xlsx(content)
    raise UnsupportedImportFormatError("A importação aceita apenas arquivos .csv ou .xlsx.")


def _mapping(headers: list[str], row: Iterable[object]) -> dict[str, object]:
    values = list(row)
    return {
        header: values[index] if index < len(values) else None
        for index, header in enumerate(headers)
    }


def parse_delivery_file(
    *,
    filename: str,
    content: bytes,
    operation_date: date,
    resolve_address: Callable[
        [str, str],
        AddressContext | None,
    ],
) -> list[ParsedImportRow]:
    headers, rows = _table(filename, content)
    missing = sorted(REQUIRED_COLUMNS - set(headers))
    if missing:
        raise ValueError(f"Colunas obrigatórias ausentes: {', '.join(missing)}.")

    parsed_rows: list[ParsedImportRow] = []
    document_keys: set[tuple[str, str, str]] = set()
    for row_number, raw_row in enumerate(rows, start=2):
        data = _mapping(headers, raw_row)
        if not any(_text(value) for value in data.values()):
            continue
        errors: list[dict[str, str]] = []
        warnings: list[dict[str, str]] = []
        normalized: dict[str, object] = {}
        try:
            invoice_number = _text(data.get("numero_nf"))
            invoice_series = _text(data.get("serie_nf"))
            issuer_document = _text(data.get("emissor_documento"))
            recipient = _text(data.get("destinatario"))
            street = _text(data.get("rua"))
            number = _text(data.get("numero"))
            required_text = {
                "numero_nf": invoice_number,
                "serie_nf": invoice_series,
                "emissor_documento": issuer_document,
                "destinatario": recipient,
                "rua": street,
                "numero": number,
            }
            empty_fields = [field for field, value in required_text.items() if not value]
            if empty_fields:
                raise ValueError(f"Campos obrigatórios vazios: {', '.join(empty_fields)}.")

            context = resolve_address(street, number)
            if context is None:
                errors.append(
                    {
                        "code": "ADDRESS_NOT_FOUND",
                        "message": (f"{street}, {number} não existe no dataset de Santa Aurora."),
                    }
                )
                raise LookupError("address")

            package_count = _integer(
                data.get("quantidade_volumes"),
                "quantidade_volumes",
            )
            weight = _decimal(data.get("peso_kg"), "peso_kg")
            volume = _decimal(data.get("volume_m3"), "volume_m3")
            priority = _enum_value(
                DeliveryPriority,
                data.get("prioridade"),
                DeliveryPriority.NORMAL,
                "prioridade",
            )
            window_policy = _enum_value(
                TimeWindowPolicy,
                data.get("janela_tipo"),
                TimeWindowPolicy.SOFT,
                "janela_tipo",
            )
            temperature = _enum_value(
                TemperatureClass,
                data.get("temperatura"),
                TemperatureClass.AMBIENT,
                "temperatura",
            )
            handling = (
                HandlingRequirement.TWO_PERSON
                if _bool(data.get("duas_pessoas"))
                else HandlingRequirement.STANDARD
            )
            window_start = _datetime_value(data.get("janela_inicio"), operation_date)
            window_end = _datetime_value(data.get("janela_fim"), operation_date)
            if (window_start is None) != (window_end is None):
                raise ValueError("janela_inicio e janela_fim devem ser informadas em conjunto.")
            if window_start is not None and window_end is not None and window_end <= window_start:
                raise ValueError("janela_fim deve ser posterior a janela_inicio.")

            service_raw = _text(data.get("tempo_servico_min"))
            service_minutes = _integer(service_raw, "tempo_servico_min") if service_raw else None
            key = (issuer_document, invoice_series, invoice_number)
            if key in document_keys:
                warnings.append(
                    {
                        "code": "DUPLICATE_INVOICE_IN_FILE",
                        "message": (
                            "A mesma NF aparece em mais de uma linha; "
                            "serão geradas entregas separadas."
                        ),
                    }
                )
            document_keys.add(key)

            normalized = {
                "invoice_number": invoice_number,
                "invoice_series": invoice_series,
                "issuer_document": issuer_document,
                "issuer_name": _text(data.get("emissor_nome")) or None,
                "external_reference": _text(data.get("referencia_externa")) or None,
                "recipient_name": recipient,
                "destination_address_id": str(context.address.id),
                "destination_address": context.formatted,
                "package_count": package_count,
                "total_weight_kg": str(weight),
                "total_volume_m3": str(volume),
                "priority": priority.value,
                "time_window_start": (window_start.isoformat() if window_start else None),
                "time_window_end": window_end.isoformat() if window_end else None,
                "time_window_policy": window_policy.value,
                "temperature_class": temperature.value,
                "handling_requirement": handling.value,
                "service_time_minutes": service_minutes,
                "notes": _text(data.get("observacoes")) or None,
            }
        except LookupError:
            pass
        except ValueError as exc:
            errors.append({"code": "INVALID_ROW", "message": str(exc)})

        status = "ERROR" if errors else "WARNING" if warnings else "VALID"
        parsed_rows.append(
            ParsedImportRow(
                row_number=row_number,
                status=status,
                normalized=normalized,
                errors=errors,
                warnings=warnings,
            )
        )
    return parsed_rows
