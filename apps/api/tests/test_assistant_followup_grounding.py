from fluxmed.application.assistant.tool_selection import (
    AssistantIntent,
    plan_assistant_grounding,
)
from fluxmed.llm import ToolDefinition
from fluxmed.llm.prompts import ASSISTANT_SYSTEM_PROMPT, ASSISTANT_SYSTEM_PROMPT_VERSION


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


def test_referential_vehicle_word_does_not_hijack_follow_up() -> None:
    plan = plan_assistant_grounding(
        "e ela usou quantos veículos?",
        _definitions(),
    )

    assert plan.intent is AssistantIntent.GENERAL
    assert plan.retrieval_tools == ("get_operation_summary",)
    assert "get_comparison_results" in plan.semantic_tool_candidates
    assert "get_vehicle_details" in plan.semantic_tool_candidates


def test_standalone_vehicle_question_keeps_fast_deterministic_path() -> None:
    plan = plan_assistant_grounding(
        "qual veículo está na primeira rota?",
        _definitions(),
    )

    assert plan.intent is AssistantIntent.VEHICLE_EXPLANATION
    assert plan.retrieval_tools == (
        "get_operation_summary",
        "get_route_details",
        "get_vehicle_details",
    )


def test_prompt_blocks_global_extremes_from_partial_grounding() -> None:
    assert ASSISTANT_SYSTEM_PROMPT_VERSION == "assistant-system-v5"
    assert "não provam um extremo global" in ASSISTANT_SYSTEM_PROMPT
    assert "Nunca use apenas o histórico conversacional" in ASSISTANT_SYSTEM_PROMPT
