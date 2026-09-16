import uuid

from fluxmed.application.assistant.grounding import AssistantGroundingBuilder
from fluxmed.application.assistant.toolbox import AssistantToolbox
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
                    "stops": [],
                },
            )
        if call.name == "get_vehicle_details":
            return ToolResult(
                call_id=call.id,
                name=call.name,
                content={"id": str(self.vehicle_id), "plate": "FMD1A03"},
            )
        return ToolResult(call_id=call.id, name=call.name, content={})


def test_grounding_executes_cost_tools_before_provider_call() -> None:
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

    assert [result.name for result in bundle.results] == [
        "get_operation_summary",
        "get_cost_breakdown",
    ]
    grounding = bundle.context["grounding"]
    assert isinstance(grounding, list)
    assert grounding[1]["data"] == {"total_cost_brl": "400.38"}


def test_grounding_resolves_first_route_then_vehicle_deterministically() -> None:
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
