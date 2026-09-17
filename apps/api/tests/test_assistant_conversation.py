import uuid
from unittest.mock import Mock

from fluxmed.application.assistant.service import (
    AssistantConversationTurn,
    AssistantService,
)
from fluxmed.application.assistant.tool_selection import (
    AssistantIntent,
    plan_assistant_grounding,
)
from fluxmed.application.assistant.toolbox import AssistantToolbox


def _definitions():
    return AssistantToolbox(Mock(), context_operation_id=uuid.uuid4()).definitions()


def _assert_semantic_follow_up(
    message: str,
    history: tuple[AssistantConversationTurn, ...],
    *,
    expected_history_fragment: str,
    expected_candidate: str,
) -> None:
    planning_message = AssistantService._planning_message(message, history)
    assert expected_history_fragment in planning_message
    assert f"Pergunta atual: {message}" in planning_message

    plan = plan_assistant_grounding(message, _definitions())
    assert plan.intent is AssistantIntent.GENERAL
    assert plan.retrieval_tools == ("get_operation_summary",)
    assert expected_candidate in plan.semantic_tool_candidates


def test_vehicle_capacity_follow_up_reuses_recent_exchange_subject() -> None:
    history = (
        AssistantConversationTurn(role="user", content="Qual veículo está na primeira rota?"),
        AssistantConversationTurn(
            role="assistant",
            content="O veículo da primeira rota é a VAN_COMPACT FMD1A03.",
        ),
    )

    _assert_semantic_follow_up(
        "E qual é a capacidade dele?",
        history,
        expected_history_fragment="VAN_COMPACT FMD1A03",
        expected_candidate="get_vehicle_details",
    )


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

    _assert_semantic_follow_up(
        "E qual é a autonomia?",
        history,
        expected_history_fragment="autonomia máxima de 430 km",
        expected_candidate="get_vehicle_details",
    )


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

    _assert_semantic_follow_up(
        "E qual combustível ele usa?",
        history,
        expected_history_fragment="rota R-01",
        expected_candidate="get_vehicle_details",
    )


def test_route_cost_follow_up_reuses_recent_exchange_subject() -> None:
    history = (
        AssistantConversationTurn(role="user", content="Qual rota custa mais?"),
        AssistantConversationTurn(role="assistant", content="A rota R-01 custa mais."),
    )

    _assert_semantic_follow_up(
        "Por quê?",
        history,
        expected_history_fragment="A rota R-01 custa mais.",
        expected_candidate="get_cost_breakdown",
    )


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


def test_generic_solution_reference_does_not_import_previous_cost_or_team_terms() -> None:
    history = (
        AssistantConversationTurn(
            role="assistant",
            content="O maior custo está na equipe e nenhum ajudante foi alocado.",
        ),
        AssistantConversationTurn(
            role="assistant",
            content="Não há simulações anteriores disponíveis.",
        ),
    )
    message = "essa solução ficou melhor que as alternativas simples que tentaram antes?"

    assert AssistantService._planning_message(message, history) == message


def test_solution_search_question_does_not_inherit_simulation_terms_from_history() -> None:
    history = (
        AssistantConversationTurn(
            role="assistant",
            content="Nenhum ajudante está alocado e a simulação não foi aplicada.",
        ),
    )
    message = "como foi a busca até chegar nessa solução?"

    assert AssistantService._planning_message(message, history) == message


def test_history_is_bounded_and_long_turns_are_compacted() -> None:
    history = tuple(
        AssistantConversationTurn(role="user", content=f"mensagem-{index}-" + "x" * 2500)
        for index in range(10)
    )

    compacted = AssistantService._compact_history(history)

    assert len(compacted) == 8
    assert compacted[0].content.startswith("mensagem-2-")
    assert all(len(turn.content) <= 2003 for turn in compacted)
