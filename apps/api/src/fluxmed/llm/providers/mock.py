import re
import uuid
from decimal import Decimal, InvalidOperation

from fluxmed.llm import ProviderRequest, ProviderTurn, ToolCall


class MockLLMProvider:
    def __init__(self, model: str = "fluxmed-mock-v1") -> None:
        self._model = model

    @property
    def name(self) -> str:
        return "mock"

    @property
    def model(self) -> str:
        return self._model

    def generate(self, request: ProviderRequest) -> ProviderTurn:
        if not request.history:
            operation_id = request.context.get("operation_id")
            if operation_id is None:
                return ProviderTurn(
                    content=(
                        "Selecione uma operação para que eu possa responder com dados "
                        "operacionais validados."
                    )
                )
            return ProviderTurn(
                content="",
                tool_calls=(
                    ToolCall(
                        id=f"mock_{uuid.uuid4().hex[:12]}",
                        name="get_operation_summary",
                        arguments={"operation_id": str(operation_id)},
                    ),
                ),
            )

        latest = request.history[-1].result
        if not latest.success:
            return ProviderTurn(
                content="Não consegui consultar os dados necessários para responder com segurança."
            )
        if latest.name != "get_operation_summary":
            return ProviderTurn(content="Essa informação não está disponível no contexto atual.")

        operation = self._mapping(latest.content.get("operation"))
        optimization = self._mapping(latest.content.get("optimization"))
        operation_code = str(operation.get("operation_code", "operação selecionada"))
        message = self._normalize(request.user_message)

        if not optimization:
            status = str(operation.get("status", "desconhecido"))
            return ProviderTurn(
                content=(
                    f"A {operation_code} está no status {status} e ainda não possui um plano "
                    "otimizado disponível para consulta."
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
            content = f"A {operation_code} possui {deliveries} entregas no plano."
            return ProviderTurn(content=content)

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
        try:
            amount = Decimal(str(value))
        except (InvalidOperation, ValueError):
            return "valor indisponível"
        rendered = (
            f"{amount:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
        )
        return f"R$ {rendered}"
