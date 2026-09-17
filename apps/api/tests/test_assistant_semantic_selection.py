import uuid
from unittest.mock import Mock

from fluxmed.application.assistant.service import AssistantContext, AssistantService
from fluxmed.application.assistant.tool_selection import AssistantGroundingPlan, AssistantIntent
from fluxmed.llm import ProviderRequest, ProviderTurn, ToolCall, ToolDefinition
from fluxmed.llm.config import LLMSettings


class _SemanticProvider:
    def __init__(self, selected: list[str]) -> None:
        self._selected = selected
        self.requests: list[ProviderRequest] = []

    @property
    def name(self) -> str:
        return "semantic-test"

    @property
    def model(self) -> str:
        return "semantic-test-v1"

    def generate(self, request: ProviderRequest) -> ProviderTurn:
        self.requests.append(request)
        return ProviderTurn(
            content="",
            tool_calls=(
                ToolCall(
                    id="selector-call",
                    name="select_assistant_context",
                    arguments={"tools": list(self._selected)},
                ),
            ),
            input_tokens=11,
            output_tokens=3,
        )


def _settings() -> LLMSettings:
    return LLMSettings(
        provider="mock",
        model="semantic-test-v1",
        timeout_seconds=20,
        max_tool_calls_per_request=5,
        max_output_chars=6000,
        thinking_level="minimal",
        max_context_chars=30000,
    )


def _definitions() -> tuple[ToolDefinition, ...]:
    schema = {"type": "object", "properties": {}}
    return tuple(
        ToolDefinition(name=name, description=name, input_schema=schema)
        for name in (
            "get_operation_summary",
            "get_route_details",
            "get_vehicle_details",
            "get_delivery_details",
            "get_cost_breakdown",
            "get_algorithm_run_summary",
            "get_comparison_results",
            "get_team_assignment_details",
        )
    )


def _base_plan() -> AssistantGroundingPlan:
    return AssistantGroundingPlan(
        intent=AssistantIntent.GENERAL,
        retrieval_tools=("get_operation_summary",),
        exposed_tools=("get_operation_summary",),
        semantic_tool_candidates=(
            "get_route_details",
            "get_vehicle_details",
            "get_delivery_details",
            "get_cost_breakdown",
            "get_algorithm_run_summary",
            "get_comparison_results",
            "get_team_assignment_details",
        ),
    )


def test_semantic_selection_uses_model_choice_without_trusting_arguments() -> None:
    provider = _SemanticProvider(
        ["get_team_assignment_details", "get_cost_breakdown", "unauthorized_write_tool"]
    )
    service = AssistantService(Mock(), provider, _settings())
    operation_id = uuid.uuid4()

    plan, input_tokens, output_tokens = service._semantic_grounding_plan(
        "Tem alguma coisa nessa operação consumindo recurso demais pelo que entrega?",
        context=AssistantContext(operation_id=operation_id),
        base_plan=_base_plan(),
        definitions=_definitions(),
    )

    assert plan.retrieval_tools == (
        "get_operation_summary",
        "get_team_assignment_details",
        "get_cost_breakdown",
    )
    assert plan.exposed_tools == plan.retrieval_tools
    assert "unauthorized_write_tool" not in plan.retrieval_tools
    assert input_tokens == 11
    assert output_tokens == 3

    request = provider.requests[0]
    assert request.context["scope"] == {"operation_id": str(operation_id)}
    assert len(request.tools) == 1
    selector = request.tools[0]
    assert selector.name == "select_assistant_context"
    tools_schema = selector.input_schema["properties"]
    assert isinstance(tools_schema, dict)
    tools_property = tools_schema["tools"]
    assert isinstance(tools_property, dict)
    assert tools_property["maxItems"] == 3


def test_semantic_selection_accepts_empty_selection_for_out_of_scope_question() -> None:
    provider = _SemanticProvider([])
    service = AssistantService(Mock(), provider, _settings())

    plan, _, _ = service._semantic_grounding_plan(
        "Escreve uma calculadora em Python para mim.",
        context=AssistantContext(operation_id=uuid.uuid4()),
        base_plan=_base_plan(),
        definitions=_definitions(),
    )

    assert plan.retrieval_tools == ("get_operation_summary",)
    assert plan.exposed_tools == ("get_operation_summary",)
