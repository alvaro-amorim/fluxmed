import uuid

from fluxmed.application.assistant.grounding import AssistantGroundingBuilder
from fluxmed.application.assistant.toolbox import AssistantToolbox
from fluxmed.application.assistant.tool_selection import AssistantIntent
from fluxmed.llm import ToolCall, ToolDefinition, ToolResult


class _FakeToolbox(AssistantToolbox):
    def __init__(self, operation_id: uuid.UUID, route_id: uuid.UUID, vehicle_id: uuid.UUID) -> None:
        self.operation_id = operation_id
        self.route_id = route_id
        self.vehicle_id = vehicle_id
        self.calls: list[ToolCall] = []

    def definitions(self) -> tuple[ToolDefinition, ...]:
        names = (
            "get_operation_summary",
            "get_route_details",
            "get_vehicle_details",
            "get_delivery_details",
            "get_cost_breakdown",
            "get_comparison_results",
            "get_algorithm_run_summary",
            "get_team_assignment_details",
            "generate_driver_instructions",
            "generate_dispatch_report",
            "generate_daily_operation_report",
            "generate_executive_summary",
            "simulate_driver_swap",
            "simulate_helper_removal",
        )
        return tuple(
            ToolDefinition(
                name=name,
                description=name,
                input_schema={"type": "object", "properties": {}},
            )
            for name in names
        )

    def execute(self, call: ToolCall) -> ToolResult:
        self.calls.append(call)
        if call.name == "get_operation_summary":
            return ToolResult(
                call_id=call.id,
                name=call.name,
                content={
                    "operation": {
                        "id": str(self.operation_id),
                        "operation_code": "OP-1",
                    },
                    "optimization": {
                        "total_cost_brl": "400.38",
                        "routes": [{"route_id": str(self.route_id)}],
                    },
                },
            )
        if call.name == "get_cost_breakdown":
            return ToolResult(
                call_id=call.id,
                name=call.name,
                content={"total_cost_brl": "400.38"},
            )
        if call.name == "get_route_details":
            return ToolResult(
                call_id=call.id,
                name=call.name,
                content={
                    "route_id": str(self.route_id),
                    "route_code": "R-01",
                    "vehicle": {"id": str(self.vehicle_id), "plate": "FMD1A03"},
                    "stops": [{"delivery_id": str(uuid.uuid4())}],
                },
            )
        if call.name == "get_vehicle_details":
            return ToolResult(
                call_id=call.id,
                name=call.name,
                content={"id": str(self.vehicle_id), "plate": "FMD1A03"},
            )
        if call.name == "generate_driver_instructions":
            return ToolResult(
                call_id=call.id,
                name=call.name,
                content={
                    "generation_kind": "driver_instructions",
                    "route": {"route_code": "R-01", "stops": [{"sequence": 1}]},
                },
            )
        return ToolResult(call_id=call.id, name=call.name, content={})


def test_grounding_executes_resolver_but_exposes_only_cost_payload() -> None:
    operation_id = uuid.uuid4()
    route_id = uuid.uuid4()
    vehicle_id = uuid.uuid4()
    toolbox = _FakeToolbox(operation_id, route_id, vehicle_id)

    bundle = AssistantGroundingBuilder(
        toolbox,
        operation_id=operation_id,
        route_id=None,
        delivery_id=None,
    ).build("Qual o custo total da operação?")

    assert bundle.plan.intent == AssistantIntent.COST
    assert [result.name for result in bundle.results] == [
        "get_operation_summary",
        "get_cost_breakdown",
    ]
    grounding = bundle.context["grounding"]
    assert isinstance(grounding, list)
    assert len(grounding) == 1
    assert grounding[0]["tool"] == "get_cost_breakdown"
    assert grounding[0]["data"] == {"total_cost_brl": "400.38"}


def test_grounding_resolves_first_route_then_vehicle_without_exposing_stops() -> None:
    operation_id = uuid.uuid4()
    route_id = uuid.uuid4()
    vehicle_id = uuid.uuid4()
    toolbox = _FakeToolbox(operation_id, route_id, vehicle_id)

    bundle = AssistantGroundingBuilder(
        toolbox,
        operation_id=operation_id,
        route_id=None,
        delivery_id=None,
    ).build("Por que o veículo foi escolhido para a primeira rota?")

    assert bundle.plan.intent == AssistantIntent.VEHICLE_EXPLANATION
    assert [result.name for result in bundle.results] == [
        "get_operation_summary",
        "get_route_details",
        "get_vehicle_details",
    ]
    vehicle_call = toolbox.calls[-1]
    assert vehicle_call.arguments == {
        "operation_id": str(operation_id),
        "entity_id": str(vehicle_id),
    }
    grounding = bundle.context["grounding"]
    assert isinstance(grounding, list)
    route_entry = grounding[0]
    assert route_entry["tool"] == "get_route_details"
    assert "stops" not in route_entry["data"]


def test_driver_instructions_expose_only_final_narrative_context() -> None:
    operation_id = uuid.uuid4()
    route_id = uuid.uuid4()
    vehicle_id = uuid.uuid4()
    toolbox = _FakeToolbox(operation_id, route_id, vehicle_id)

    bundle = AssistantGroundingBuilder(
        toolbox,
        operation_id=operation_id,
        route_id=None,
        delivery_id=None,
    ).build("Gere instruções para o motorista da primeira rota.")

    assert bundle.plan.intent == AssistantIntent.DRIVER_INSTRUCTIONS
    assert [result.name for result in bundle.results] == [
        "get_operation_summary",
        "generate_driver_instructions",
    ]
    grounding = bundle.context["grounding"]
    assert isinstance(grounding, list)
    assert [entry["tool"] for entry in grounding] == ["generate_driver_instructions"]
