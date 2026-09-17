import uuid
from dataclasses import dataclass

from fluxmed.application.assistant.tool_selection import (
    AssistantGroundingPlan,
    AssistantIntent,
    plan_assistant_grounding,
)
from fluxmed.application.assistant.toolbox import AssistantToolbox
from fluxmed.llm import ToolCall, ToolResult


@dataclass(frozen=True, slots=True)
class GroundingBundle:
    context: dict[str, object]
    results: tuple[ToolResult, ...]
    plan: AssistantGroundingPlan


class AssistantGroundingBuilder:
    """Resolve trusted backend data before the LLM is called.

    Retrieval-only results may be used by the backend to resolve entity IDs but
    are not automatically exposed to the provider. This keeps the normal path
    to one provider call while avoiding duplicated or irrelevant prompt data.
    """

    def __init__(
        self,
        toolbox: AssistantToolbox,
        *,
        operation_id: uuid.UUID | None,
        route_id: uuid.UUID | None,
        delivery_id: uuid.UUID | None,
    ) -> None:
        self._toolbox = toolbox
        self._operation_id = operation_id
        self._route_id = route_id
        self._delivery_id = delivery_id
        self._results: list[ToolResult] = []
        self._by_name: dict[str, ToolResult] = {}

    def build(self, message: str) -> GroundingBundle:
        plan = plan_assistant_grounding(
            message,
            self._toolbox.definitions(),
            has_route_context=self._route_id is not None,
            has_delivery_context=self._delivery_id is not None,
        )

        scope: dict[str, object] = {}
        if self._operation_id is not None:
            scope["operation_id"] = str(self._operation_id)
        if self._route_id is not None:
            scope["route_id"] = str(self._route_id)
        if self._delivery_id is not None:
            scope["delivery_id"] = str(self._delivery_id)

        if self._operation_id is None:
            return GroundingBundle(
                context={
                    "scope": scope,
                    "intent": plan.intent.value,
                    "selected_tools": list(plan.exposed_tools),
                    "grounding": [],
                    "missing_context": ["operation_id"],
                },
                results=(),
                plan=plan,
            )

        operation_id = str(self._operation_id)
        summary = self._execute(
            "get_operation_summary",
            {"operation_id": operation_id},
        )
        resolved_route_id = self._route_id or self._first_route_id(summary)

        for name in plan.retrieval_tools:
            if name == "get_operation_summary":
                continue
            if name in {
                "get_cost_breakdown",
                "get_comparison_results",
                "get_algorithm_run_summary",
                "get_team_assignment_details",
                "generate_dispatch_report",
                "generate_daily_operation_report",
                "generate_executive_summary",
            }:
                self._execute(name, {"operation_id": operation_id})
                continue
            if name == "get_route_details":
                self._execute_route(name, operation_id, resolved_route_id)
                continue
            if name == "get_vehicle_details":
                route = self._execute_route(
                    "get_route_details",
                    operation_id,
                    resolved_route_id,
                )
                vehicle_id = self._vehicle_id(route)
                if vehicle_id is None:
                    self._record_missing(name, "Veículo da rota não disponível no contexto atual.")
                else:
                    self._execute(
                        name,
                        {"operation_id": operation_id, "entity_id": str(vehicle_id)},
                    )
                continue
            if name == "get_delivery_details":
                delivery_id = self._delivery_id
                if delivery_id is None:
                    route = self._execute_route(
                        "get_route_details",
                        operation_id,
                        resolved_route_id,
                    )
                    delivery_id = self._first_delivery_id(route)
                if delivery_id is None:
                    self._record_missing(name, "Entrega não disponível no contexto atual.")
                else:
                    self._execute(
                        name,
                        {"operation_id": operation_id, "entity_id": str(delivery_id)},
                    )
                continue
            if name in {"generate_driver_instructions", "simulate_helper_removal"}:
                if resolved_route_id is None:
                    self._record_missing(name, "Rota não disponível no contexto atual.")
                else:
                    self._execute(
                        name,
                        {"operation_id": operation_id, "route_id": str(resolved_route_id)},
                    )
                continue
            if name == "simulate_driver_swap":
                self._record_missing(
                    name,
                    "Selecione explicitamente o motorista alternativo antes de simular a troca.",
                )

        visible_results = tuple(
            self._by_name[name]
            for name in plan.exposed_tools
            if name in self._by_name
        )
        return GroundingBundle(
            context={
                "scope": scope,
                "intent": plan.intent.value,
                "selected_tools": list(plan.exposed_tools),
                "grounding": [self._entry(result, plan.intent) for result in visible_results],
                "rules": [
                    "Dados em grounding são a fonte factual oficial desta resposta.",
                    "Não invente valores, IDs, causas ou comparações ausentes.",
                    "Uma entrada failed deve ser tratada como informação indisponível.",
                ],
            },
            results=tuple(self._results),
            plan=plan,
        )

    def _execute_route(
        self,
        name: str,
        operation_id: str,
        route_id: uuid.UUID | None,
    ) -> ToolResult:
        if route_id is None:
            return self._record_missing(name, "Rota não disponível no contexto atual.")
        return self._execute(
            name,
            {"operation_id": operation_id, "entity_id": str(route_id)},
        )

    def _execute(self, name: str, arguments: dict[str, object]) -> ToolResult:
        existing = self._by_name.get(name)
        if existing is not None:
            return existing
        result = self._toolbox.execute(
            ToolCall(
                id=f"grounding-{len(self._results) + 1}",
                name=name,
                arguments=arguments,
            )
        )
        self._results.append(result)
        self._by_name[name] = result
        return result

    def _record_missing(self, name: str, error: str) -> ToolResult:
        existing = self._by_name.get(name)
        if existing is not None:
            return existing
        result = ToolResult(
            call_id=f"grounding-{len(self._results) + 1}",
            name=name,
            content={},
            success=False,
            error=error,
        )
        self._results.append(result)
        self._by_name[name] = result
        return result

    @staticmethod
    def _entry(result: ToolResult, intent: AssistantIntent) -> dict[str, object]:
        data: object = result.content
        if result.name == "get_route_details" and intent == AssistantIntent.VEHICLE_EXPLANATION:
            compact_route = dict(result.content)
            compact_route.pop("stops", None)
            data = compact_route

        entry: dict[str, object] = {
            "tool": result.name,
            "status": "success" if result.success else "failed",
            "data": data,
        }
        if result.error is not None:
            entry["error"] = result.error
        return entry

    @staticmethod
    def _first_route_id(summary: ToolResult) -> uuid.UUID | None:
        if not summary.success:
            return None
        optimization = summary.content.get("optimization")
        if not isinstance(optimization, dict):
            return None
        routes = optimization.get("routes")
        if not isinstance(routes, list) or not routes:
            return None
        first = routes[0]
        if not isinstance(first, dict):
            return None
        return AssistantGroundingBuilder._uuid(first.get("route_id"))

    @staticmethod
    def _vehicle_id(route: ToolResult) -> uuid.UUID | None:
        if not route.success:
            return None
        vehicle = route.content.get("vehicle")
        if not isinstance(vehicle, dict):
            return None
        return AssistantGroundingBuilder._uuid(vehicle.get("id"))

    @staticmethod
    def _first_delivery_id(route: ToolResult) -> uuid.UUID | None:
        if not route.success:
            return None
        stops = route.content.get("stops")
        if not isinstance(stops, list) or not stops:
            return None
        first = stops[0]
        if not isinstance(first, dict):
            return None
        return AssistantGroundingBuilder._uuid(first.get("delivery_id"))

    @staticmethod
    def _uuid(value: object) -> uuid.UUID | None:
        try:
            return uuid.UUID(str(value))
        except (ValueError, AttributeError, TypeError):
            return None
