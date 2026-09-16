import re
from decimal import Decimal, InvalidOperation

from fluxmed.llm import ProviderRequest, ProviderTurn


class GroundedMockLLMProvider:
    """Deterministic one-pass provider for the grounded assistant path."""

    def __init__(self, model: str = "fluxmed-mock-v2") -> None:
        self._model = model

    @property
    def name(self) -> str:
        return "mock"

    @property
    def model(self) -> str:
        return self._model

    def generate(self, request: ProviderRequest) -> ProviderTurn:
        grounding = request.context.get("grounding")
        if not isinstance(grounding, list):
            return ProviderTurn(content="Selecione uma operação para consultar dados validados.")

        entries = {
            str(entry.get("tool")): entry
            for entry in grounding
            if isinstance(entry, dict) and isinstance(entry.get("tool"), str)
        }
        message = self._normalize(request.user_message)

        if "custo" in message:
            cost = self._data(entries, "get_cost_breakdown")
            if cost:
                return ProviderTurn(
                    content=f"O custo total da operação é {self._currency(cost.get('total_cost_brl'))}."
                )

        if "por que" in message and ("veiculo" in message or "rota" in message):
            route = self._data(entries, "get_route_details")
            if route:
                vehicle = route.get("vehicle")
                vehicle_data = vehicle if isinstance(vehicle, dict) else {}
                return ProviderTurn(
                    content=(
                        f"No plano validado, a {route.get('route_code', 'rota')} foi atribuída ao "
                        f"veículo {vehicle_data.get('plate', 'não identificado')} "
                        f"({vehicle_data.get('type', 'tipo indisponível')}) para "
                        f"{route.get('delivery_count')} entregas, com "
                        f"{route.get('total_weight_kg')} kg e {route.get('total_volume_m3')} m³. "
                        "Os dados disponíveis confirmam a alocação, mas não registram uma causa "
                        "única ou comparação marginal suficiente para afirmar outro motivo."
                    )
                )

        instructions = self._data(entries, "generate_driver_instructions")
        if instructions and ("instruc" in message or "orientac" in message):
            return ProviderTurn(content=self._driver_instructions(instructions))

        for name, label in (
            ("generate_daily_operation_report", "Relatório diário"),
            ("generate_dispatch_report", "Relatório de despacho"),
            ("generate_executive_summary", "Resumo executivo"),
        ):
            report = self._data(entries, name)
            if report:
                return ProviderTurn(content=self._report(label, report))

        simulation = self._data(entries, "simulate_helper_removal")
        if simulation:
            valid = bool(simulation.get("valid"))
            if valid:
                return ProviderTurn(
                    content=(
                        "A simulação de remoção do ajudante é válida segundo o backend. "
                        f"Custo atual: {self._currency(simulation.get('current_route_cost_brl'))}; "
                        f"custo simulado: {self._currency(simulation.get('simulated_route_cost_brl'))}; "
                        f"delta: {self._currency(simulation.get('cost_delta_brl'))}. "
                        "Nenhuma alteração foi aplicada."
                    )
                )
            return ProviderTurn(
                content=(
                    "A simulação de remoção do ajudante é inválida e nenhuma alteração foi "
                    f"aplicada. Restrições: {simulation.get('issues')}."
                )
            )

        summary = self._data(entries, "get_operation_summary")
        if summary:
            operation = summary.get("operation")
            optimization = summary.get("optimization")
            operation_data = operation if isinstance(operation, dict) else {}
            optimization_data = optimization if isinstance(optimization, dict) else {}
            return ProviderTurn(
                content=(
                    f"A {operation_data.get('operation_code', 'operação selecionada')} possui "
                    f"{optimization_data.get('delivery_count')} entregas, "
                    f"{optimization_data.get('vehicles_used')} veículos e custo total de "
                    f"{self._currency(optimization_data.get('total_cost_brl'))}."
                )
            )

        return ProviderTurn(content="Essa informação não está disponível no contexto atual.")

    @staticmethod
    def _data(entries: dict[str, dict[str, object]], name: str) -> dict[str, object]:
        entry = entries.get(name)
        if not entry or entry.get("status") != "success":
            return {}
        data = entry.get("data")
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _driver_instructions(content: dict[str, object]) -> str:
        route = content.get("route")
        route_data = route if isinstance(route, dict) else {}
        vehicle = route_data.get("vehicle")
        vehicle_data = vehicle if isinstance(vehicle, dict) else {}
        team = route_data.get("team")
        team_data = team if isinstance(team, dict) else {}
        primary = team_data.get("primary_worker")
        primary_data = primary if isinstance(primary, dict) else {}
        lines = [
            f"Instruções para {route_data.get('route_code', 'rota')}",
            f"Veículo: {vehicle_data.get('plate', 'não informado')}",
            f"Motorista: {primary_data.get('name') or 'incluído no contrato'}",
            "Sequência de atendimento:",
        ]
        stops = route_data.get("stops")
        if isinstance(stops, list):
            for stop in stops:
                if not isinstance(stop, dict):
                    continue
                lines.append(
                    f"{stop.get('sequence')}. {stop.get('delivery_code')} — "
                    f"{stop.get('destination_address') or 'endereço não disponível'}"
                )
        return "\n".join(lines)

    @staticmethod
    def _report(label: str, content: dict[str, object]) -> str:
        summary = content.get("summary")
        summary_data = summary if isinstance(summary, dict) else {}
        operation = summary_data.get("operation")
        optimization = summary_data.get("optimization")
        operation_data = operation if isinstance(operation, dict) else {}
        optimization_data = optimization if isinstance(optimization, dict) else {}
        return (
            f"{label} — {operation_data.get('operation_code', 'operação selecionada')}: "
            f"{optimization_data.get('delivery_count')} entregas em "
            f"{optimization_data.get('vehicles_used')} veículos, "
            f"{optimization_data.get('distance_km')} km, custo de "
            f"{GroundedMockLLMProvider._currency(optimization_data.get('total_cost_brl'))} e "
            f"{optimization_data.get('on_time_percentage')}% no prazo."
        )

    @staticmethod
    def _currency(value: object) -> str:
        try:
            amount = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return "valor indisponível"
        return f"R$ {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @staticmethod
    def _normalize(value: str) -> str:
        lowered = value.casefold()
        for source, target in {
            "á": "a",
            "à": "a",
            "ã": "a",
            "â": "a",
            "é": "e",
            "ê": "e",
            "í": "i",
            "ó": "o",
            "ô": "o",
            "õ": "o",
            "ú": "u",
            "ç": "c",
        }.items():
            lowered = lowered.replace(source, target)
        return re.sub(r"\s+", " ", lowered).strip()
