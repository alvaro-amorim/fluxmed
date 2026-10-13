import re
import uuid
from decimal import Decimal, InvalidOperation

from fluxmed.llm import ProviderRequest, ProviderTurn, ToolCall


class MockLLMProvider:
    """Deterministic provider used by development and CI without external token spend."""

    def __init__(self, model: str = "fluxmed-mock-v1") -> None:
        self._model = model

    @property
    def name(self) -> str:
        return "mock"

    @property
    def model(self) -> str:
        return self._model

    def generate(self, request: ProviderRequest) -> ProviderTurn:
        operation_id = request.context.get("operation_id")
        if operation_id is None:
            return ProviderTurn(
                content=(
                    "Selecione uma operação para que eu possa responder com dados "
                    "operacionais validados."
                )
            )

        if not request.history:
            return self._tool_turn(
                "get_operation_summary",
                {"operation_id": str(operation_id)},
            )

        latest = request.history[-1].result
        if not latest.success:
            return ProviderTurn(
                content="Não consegui consultar os dados necessários para responder com segurança."
            )

        message = self._normalize(request.user_message)
        if latest.name == "get_operation_summary":
            return self._after_summary(request, latest.content, message)
        if latest.name == "get_route_details":
            return self._route_explanation(latest.content)
        if latest.name == "get_team_assignment_details":
            return self._team_explanation(latest.content)
        if latest.name == "generate_driver_instructions":
            return self._driver_instructions(latest.content)
        if latest.name in {
            "generate_dispatch_report",
            "generate_daily_operation_report",
            "generate_executive_summary",
        }:
            return self._narrative(latest.name, latest.content)
        if latest.name == "simulate_helper_removal":
            return self._helper_simulation(latest.content)
        if latest.name == "simulate_driver_swap":
            return self._driver_simulation(latest.content)

        return ProviderTurn(content="Essa informação não está disponível no contexto atual.")

    def _after_summary(
        self,
        request: ProviderRequest,
        content: dict[str, object],
        message: str,
    ) -> ProviderTurn:
        operation = self._mapping(content.get("operation"))
        optimization = self._mapping(content.get("optimization"))
        operation_id = str(operation.get("id") or request.context.get("operation_id"))
        operation_code = str(operation.get("operation_code", "operação selecionada"))

        if not optimization:
            status = str(operation.get("status", "desconhecido"))
            return ProviderTurn(
                content=(
                    f"A {operation_code} está no status {status} e ainda não possui um plano "
                    "otimizado disponível para consulta."
                )
            )

        route_id = self._selected_route_id(request, optimization)
        if self._asks_driver_instructions(message):
            if route_id is None:
                return ProviderTurn(
                    content="Nenhuma rota do plano está disponível para instruções."
                )
            return self._tool_turn(
                "generate_driver_instructions",
                {"operation_id": operation_id, "route_id": route_id},
            )

        if "resumo executivo" in message:
            return self._tool_turn(
                "generate_executive_summary",
                {"operation_id": operation_id},
            )
        if "despacho" in message and "relatorio" in message:
            return self._tool_turn(
                "generate_dispatch_report",
                {"operation_id": operation_id},
            )
        if "relatorio" in message or "relatório" in request.user_message.casefold():
            return self._tool_turn(
                "generate_daily_operation_report",
                {"operation_id": operation_id},
            )

        if self._asks_vehicle_reason(message):
            if route_id is None:
                return ProviderTurn(content="Nenhuma rota do plano está disponível para explicar.")
            return self._tool_turn(
                "get_route_details",
                {"operation_id": operation_id, "entity_id": route_id},
            )

        if "ajudante" in message:
            if ("remover" in message or "retirar" in message or "simul" in message) and route_id:
                return self._tool_turn(
                    "simulate_helper_removal",
                    {"operation_id": operation_id, "route_id": route_id},
                )
            return self._tool_turn(
                "get_team_assignment_details",
                {"operation_id": operation_id},
            )

        if "risco" in message or "critico" in message:
            critical_delays = optimization.get("critical_delays")
            on_time = optimization.get("on_time_percentage")
            if critical_delays == 0 or str(critical_delays) == "0":
                return ProviderTurn(
                    content=(
                        f"A {operation_code} não possui atrasos críticos registrados no plano "
                        f"validado e apresenta {on_time}% das entregas no prazo."
                    )
                )
            return ProviderTurn(
                content=(
                    f"A {operation_code} possui {critical_delays} atrasos críticos registrados "
                    f"e {on_time}% das entregas no prazo."
                )
            )

        if "custo" in message:
            total = self._currency(optimization.get("total_cost_brl"))
            return ProviderTurn(content=f"O custo total da {operation_code} é {total}.")
        if "distancia" in message:
            distance = optimization.get("distance_km")
            return ProviderTurn(content=f"A distância total da {operation_code} é {distance} km.")
        if "entrega" in message:
            deliveries = optimization.get("delivery_count")
            return ProviderTurn(
                content=f"A {operation_code} possui {deliveries} entregas no plano."
            )

        cost = self._currency(optimization.get("total_cost_brl"))
        distance = optimization.get("distance_km")
        deliveries = optimization.get("delivery_count")
        vehicles = optimization.get("vehicles_used")
        return ProviderTurn(
            content=(
                f"A {operation_code} possui {deliveries} entregas distribuídas em {vehicles} "
                f"veículos, com custo total de {cost} e distância de {distance} km."
            )
        )

    def _route_explanation(self, content: dict[str, object]) -> ProviderTurn:
        route_code = content.get("route_code", "rota")
        vehicle = self._mapping(content.get("vehicle"))
        plate = vehicle.get("plate", "veículo não identificado")
        vehicle_type = vehicle.get("type", "tipo indisponível")
        deliveries = content.get("delivery_count")
        weight = content.get("total_weight_kg")
        volume = content.get("total_volume_m3")
        weight_utilization = content.get("weight_utilization_pct")
        volume_utilization = content.get("volume_utilization_pct")
        return ProviderTurn(
            content=(
                f"No plano validado, a {route_code} foi atribuída ao veículo {plate} "
                f"({vehicle_type}) para atender {deliveries} entregas, com {weight} kg e "
                f"{volume} m³. A utilização registrada é de {weight_utilization}% em peso e "
                f"{volume_utilization}% em volume. Estes dados confirmam a alocação atual; "
                "o contexto disponível não registra uma causa única ou uma comparação marginal "
                "que permita atribuir outro motivo sem especulação."
            )
        )

    def _team_explanation(self, content: dict[str, object]) -> ProviderTurn:
        routes = content.get("routes")
        if not isinstance(routes, list) or not routes:
            return ProviderTurn(content="Não há atribuição de equipe disponível no contexto atual.")
        descriptions: list[str] = []
        for item in routes:
            if not isinstance(item, dict):
                continue
            team = self._mapping(item.get("team"))
            helper = self._mapping(team.get("helper"))
            primary = self._mapping(team.get("primary_worker"))
            primary_name = primary.get("name") or "motorista incluído no contrato"
            helper_name = helper.get("name") or "sem ajudante"
            descriptions.append(f"{item.get('route_code')}: {primary_name}; {helper_name}")
        if not descriptions:
            return ProviderTurn(content="Não há atribuição de equipe disponível no contexto atual.")
        return ProviderTurn(content="Equipe do plano validado: " + "; ".join(descriptions) + ".")

    def _driver_instructions(self, content: dict[str, object]) -> ProviderTurn:
        route = self._mapping(content.get("route"))
        vehicle = self._mapping(route.get("vehicle"))
        team = self._mapping(route.get("team"))
        primary = self._mapping(team.get("primary_worker"))
        helper = self._mapping(team.get("helper"))
        lines = [
            f"Instruções para {route.get('route_code', 'rota')}",
            f"Veículo: {vehicle.get('plate', 'não informado')}",
            f"Motorista: {primary.get('name') or 'incluído no contrato'}",
            f"Ajudante: {helper.get('name') or 'não necessário/não atribuído'}",
            "Sequência de atendimento:",
        ]
        stops = route.get("stops")
        if isinstance(stops, list):
            for stop in stops:
                if not isinstance(stop, dict):
                    continue
                line = (
                    f"{stop.get('sequence')}. {stop.get('delivery_code')} — "
                    f"{stop.get('destination_address') or 'endereço não disponível'}"
                )
                priority = stop.get("priority")
                window_start = stop.get("time_window_start")
                window_end = stop.get("time_window_end")
                temperature = stop.get("temperature_class")
                handling = stop.get("handling_requirement")
                details = [f"prioridade {priority}"]
                if window_start or window_end:
                    details.append(f"janela {window_start or '?'} a {window_end or '?'}")
                if temperature and temperature != "AMBIENT":
                    details.append(f"temperatura {temperature}")
                if handling and handling != "STANDARD":
                    details.append(f"manuseio {handling}")
                lines.append(line + " (" + ", ".join(details) + ")")
        return ProviderTurn(content="\n".join(lines))

    def _narrative(self, tool_name: str, content: dict[str, object]) -> ProviderTurn:
        summary = self._mapping(content.get("summary"))
        operation = self._mapping(summary.get("operation"))
        optimization = self._mapping(summary.get("optimization"))
        code = operation.get("operation_code", "operação selecionada")
        cost = self._currency(optimization.get("total_cost_brl"))
        distance = optimization.get("distance_km")
        deliveries = optimization.get("delivery_count")
        vehicles = optimization.get("vehicles_used")
        on_time = optimization.get("on_time_percentage")
        prefix = {
            "generate_dispatch_report": "Relatório de despacho",
            "generate_daily_operation_report": "Relatório diário",
            "generate_executive_summary": "Resumo executivo",
        }[tool_name]
        return ProviderTurn(
            content=(
                f"{prefix} — {code}: {deliveries} entregas em {vehicles} veículos, "
                f"{distance} km de distância total, custo de {cost} e {on_time}% no prazo. "
                "Os valores foram obtidos do plano validado do FluxMed."
            )
        )

    def _helper_simulation(self, content: dict[str, object]) -> ProviderTurn:
        valid = bool(content.get("valid"))
        current = self._currency(content.get("current_route_cost_brl"))
        simulated = self._currency(content.get("simulated_route_cost_brl"))
        delta = self._currency(content.get("cost_delta_brl"))
        if valid:
            return ProviderTurn(
                content=(
                    "A simulação de remoção do ajudante é válida segundo o backend. "
                    f"Custo atual da rota: {current}; custo simulado: {simulated}; "
                    f"delta: {delta}. Nenhuma alteração foi aplicada."
                )
            )
        issues = content.get("issues")
        return ProviderTurn(
            content=(
                "A simulação de remoção do ajudante é inválida e nenhuma alteração foi aplicada. "
                f"Restrições encontradas: {issues}."
            )
        )

    def _driver_simulation(self, content: dict[str, object]) -> ProviderTurn:
        valid = bool(content.get("valid"))
        issues = content.get("issues")
        if not valid:
            return ProviderTurn(
                content=(
                    "A troca simulada de motorista é inválida e não foi aplicada. "
                    f"Restrições encontradas: {issues}."
                )
            )
        current = self._currency(content.get("current_route_cost_brl"))
        simulated = self._currency(content.get("simulated_route_cost_brl"))
        delta = self._currency(content.get("cost_delta_brl"))
        return ProviderTurn(
            content=(
                "A troca simulada de motorista é válida segundo o backend. "
                f"Custo atual: {current}; custo simulado: {simulated}; delta: {delta}. "
                "Nenhuma alteração foi aplicada."
            )
        )

    @staticmethod
    def _tool_turn(name: str, arguments: dict[str, object]) -> ProviderTurn:
        return ProviderTurn(
            content="",
            tool_calls=(
                ToolCall(
                    id=f"mock_{uuid.uuid4().hex[:12]}",
                    name=name,
                    arguments=arguments,
                ),
            ),
        )

    @staticmethod
    def _selected_route_id(request: ProviderRequest, optimization: dict[str, object]) -> str | None:
        explicit = request.context.get("route_id")
        if explicit is not None:
            return str(explicit)
        routes = optimization.get("routes")
        if not isinstance(routes, list) or not routes:
            return None
        first = routes[0]
        if not isinstance(first, dict):
            return None
        route_id = first.get("route_id")
        return str(route_id) if route_id is not None else None

    @staticmethod
    def _asks_driver_instructions(message: str) -> bool:
        return "instruc" in message and ("motorista" in message or "rota" in message)

    @staticmethod
    def _asks_vehicle_reason(message: str) -> bool:
        return "por que" in message and (
            "veiculo" in message or "van" in message or "rota" in message
        )

    @staticmethod
    def _mapping(value: object) -> dict[str, object]:
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _normalize(value: str) -> str:
        lowered = value.casefold()
        replacements = {
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
        }
        for source, target in replacements.items():
            lowered = lowered.replace(source, target)
        return re.sub(r"\s+", " ", lowered).strip()

    @staticmethod
    def _currency(value: object) -> str:
        if value is None:
            return "valor indisponível"
        try:
            amount = Decimal(str(value))
        except (InvalidOperation, ValueError):
            return "valor indisponível"
        rendered = f"{amount:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
        return f"R$ {rendered}"
