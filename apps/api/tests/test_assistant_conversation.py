import uuid
from unittest.mock import Mock

from fluxmed.application.assistant.service import (
    AssistantConversationTurn,
    AssistantService,
)
from fluxmed.application.assistant.tool_selection import select_assistant_tools
from fluxmed.application.assistant.toolbox import AssistantToolbox


def test_vehicle_capacity_follow_up_reuses_previous_user_subject() -> None:
    history = (
        AssistantConversationTurn(role="user", content="Qual veículo está na primeira rota?"),
        AssistantConversationTurn(
            role="assistant",
            content="O veículo da primeira rota é a VAN_COMPACT FMD1A03.",
        ),
    )

    planning_message = AssistantService._planning_message(
        "E qual é a capacidade dele?",
        history,
    )

    definitions = AssistantToolbox(Mock(), context_operation_id=uuid.uuid4()).definitions()
    selected = select_assistant_tools(planning_message, definitions)

    assert [tool.name for tool in selected] == [
        "get_operation_summary",
        "get_route_details",
        "get_vehicle_details",
    ]


def test_route_cost_follow_up_reuses_previous_user_subject() -> None:
    history = (
        AssistantConversationTurn(role="user", content="Qual rota custa mais?"),
        AssistantConversationTurn(role="assistant", content="A rota R-01 custa mais."),
    )

    planning_message = AssistantService._planning_message("Por quê?", history)

    definitions = AssistantToolbox(Mock(), context_operation_id=uuid.uuid4()).definitions()
    selected = select_assistant_tools(planning_message, definitions)

    assert [tool.name for tool in selected] == [
        "get_operation_summary",
        "get_cost_breakdown",
    ]


def test_unrelated_message_does_not_inherit_previous_subject() -> None:
    history = (
        AssistantConversationTurn(role="user", content="Qual veículo está na primeira rota?"),
        AssistantConversationTurn(role="assistant", content="A placa é FMD1A03."),
    )

    planning_message = AssistantService._planning_message(
        "Me dê um resumo geral da operação e dos prazos.",
        history,
    )

    assert planning_message == "Me dê um resumo geral da operação e dos prazos."


def test_history_is_bounded_and_long_turns_are_compacted() -> None:
    history = tuple(
        AssistantConversationTurn(role="user", content=f"mensagem-{index}-" + "x" * 2500)
        for index in range(10)
    )

    compacted = AssistantService._compact_history(history)

    assert len(compacted) == 8
    assert compacted[0].content.startswith("mensagem-2-")
    assert all(len(turn.content) <= 2003 for turn in compacted)
