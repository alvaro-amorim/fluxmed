import uuid
from unittest.mock import Mock

from fluxmed.application.assistant.service import (
    AssistantConversationTurn,
    AssistantService,
)
from fluxmed.application.assistant.tool_selection import select_assistant_tools
from fluxmed.application.assistant.toolbox import AssistantToolbox


def _selected_tools(message: str, history: tuple[AssistantConversationTurn, ...]) -> list[str]:
    planning_message = AssistantService._planning_message(message, history)
    definitions = AssistantToolbox(Mock(), context_operation_id=uuid.uuid4()).definitions()
    return [tool.name for tool in select_assistant_tools(planning_message, definitions)]


def test_vehicle_capacity_follow_up_reuses_recent_exchange_subject() -> None:
    history = (
        AssistantConversationTurn(role="user", content="Qual veículo está na primeira rota?"),
        AssistantConversationTurn(
            role="assistant",
            content="O veículo da primeira rota é a VAN_COMPACT FMD1A03.",
        ),
    )

    assert _selected_tools("E qual é a capacidade dele?", history) == [
        "get_operation_summary",
        "get_route_details",
        "get_vehicle_details",
    ]


def test_vehicle_autonomy_follow_up_keeps_subject_after_two_turns() -> None:
    history = (
        AssistantConversationTurn(role="user", content="Qual veículo está na primeira rota?"),
        AssistantConversationTurn(
            role="assistant",
            content="O veículo da primeira rota é a VAN_COMPACT FMD1A03.",
        ),
        AssistantConversationTurn(role="user", content="E qual é a capacidade dele?"),
        AssistantConversationTurn(
            role="assistant",
            content=(
                "O veículo da rota R-01, placa FMD1A03, suporta 900 kg, 5 m³ e possui "
                "autonomia máxima de 430 km."
            ),
        ),
    )

    assert _selected_tools("E qual é a autonomia?", history) == [
        "get_operation_summary",
        "get_route_details",
        "get_vehicle_details",
    ]


def test_vehicle_fuel_follow_up_keeps_subject_across_chain() -> None:
    history = (
        AssistantConversationTurn(role="user", content="E qual é a capacidade dele?"),
        AssistantConversationTurn(
            role="assistant",
            content="O veículo da rota R-01, placa FMD1A03, suporta 900 kg e 5 m³.",
        ),
        AssistantConversationTurn(role="user", content="E qual é a autonomia?"),
        AssistantConversationTurn(
            role="assistant",
            content="O veículo da rota R-01 possui autonomia máxima de 430 km.",
        ),
    )

    assert _selected_tools("E qual combustível ele usa?", history) == [
        "get_operation_summary",
        "get_route_details",
        "get_vehicle_details",
    ]


def test_route_cost_follow_up_reuses_recent_exchange_subject() -> None:
    history = (
        AssistantConversationTurn(role="user", content="Qual rota custa mais?"),
        AssistantConversationTurn(role="assistant", content="A rota R-01 custa mais."),
    )

    assert _selected_tools("Por quê?", history) == [
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
