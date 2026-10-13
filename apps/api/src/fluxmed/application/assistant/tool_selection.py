import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum

from fluxmed.llm import ToolDefinition

_MAX_SELECTED_TOOLS = 5
_MAX_SEMANTIC_CANDIDATES = 7


class AssistantIntent(StrEnum):
    COST = "cost"
    VEHICLE_EXPLANATION = "vehicle_explanation"
    DRIVER_INSTRUCTIONS = "driver_instructions"
    DAILY_REPORT = "daily_report"
    DISPATCH_REPORT = "dispatch_report"
    EXECUTIVE_SUMMARY = "executive_summary"
    HELPER_REMOVAL = "helper_removal"
    DRIVER_SWAP = "driver_swap"
    ALGORITHM = "algorithm"
    COMPARISON = "comparison"
    DELIVERY = "delivery"
    GENERAL = "general"


@dataclass(frozen=True, slots=True)
class AssistantGroundingPlan:
    """Deterministic plan for backend retrieval and provider-visible grounding.

    `retrieval_tools` may contain resolver-only calls needed by the backend to
    discover route/vehicle/delivery identifiers. `exposed_tools` is the smaller
    subset whose payload is actually sent to the LLM.
    """

    intent: AssistantIntent
    retrieval_tools: tuple[str, ...]
    exposed_tools: tuple[str, ...]
    semantic_tool_candidates: tuple[str, ...] = ()


def plan_assistant_grounding(
    message: str,
    definitions: tuple[ToolDefinition, ...],
    *,
    has_route_context: bool = False,
    has_delivery_context: bool = False,
) -> AssistantGroundingPlan:
    normalized = _normalize(message)
    available = {definition.name for definition in definitions}

    def supported(*names: str) -> tuple[str, ...]:
        return tuple(name for name in names if name in available)

    helper_simulation = _contains_any(normalized, "remover", "retirar", "sem") and (
        "ajudante" in normalized
    )
    driver_simulation = "motorista" in normalized and _contains_any(
        normalized,
        "trocar",
        "troca",
        "substituir",
        "simul",
    )

    if _contains_any(normalized, "instruc", "orientac") and _contains_any(
        normalized,
        "motorista",
        "rota",
    ):
        return AssistantGroundingPlan(
            intent=AssistantIntent.DRIVER_INSTRUCTIONS,
            retrieval_tools=supported("get_operation_summary", "generate_driver_instructions"),
            exposed_tools=supported("generate_driver_instructions"),
        )

    if "resumo executivo" in normalized:
        return AssistantGroundingPlan(
            intent=AssistantIntent.EXECUTIVE_SUMMARY,
            retrieval_tools=supported("get_operation_summary", "generate_executive_summary"),
            exposed_tools=supported("generate_executive_summary"),
        )

    if "relatorio" in normalized and "despacho" in normalized:
        return AssistantGroundingPlan(
            intent=AssistantIntent.DISPATCH_REPORT,
            retrieval_tools=supported("get_operation_summary", "generate_dispatch_report"),
            exposed_tools=supported("generate_dispatch_report"),
        )

    if "relatorio" in normalized:
        return AssistantGroundingPlan(
            intent=AssistantIntent.DAILY_REPORT,
            retrieval_tools=supported("get_operation_summary", "generate_daily_operation_report"),
            exposed_tools=supported("generate_daily_operation_report"),
        )

    if helper_simulation or ("simul" in normalized and "ajudante" in normalized):
        return AssistantGroundingPlan(
            intent=AssistantIntent.HELPER_REMOVAL,
            retrieval_tools=supported("get_operation_summary", "simulate_helper_removal"),
            exposed_tools=supported("simulate_helper_removal"),
        )

    if driver_simulation:
        return AssistantGroundingPlan(
            intent=AssistantIntent.DRIVER_SWAP,
            retrieval_tools=supported("get_operation_summary", "simulate_driver_swap"),
            exposed_tools=supported("simulate_driver_swap"),
        )

    if _contains_any(
        normalized,
        "custo",
        "custos",
        "custa",
        "custar",
        "preco",
        "gasto",
        "valor",
    ):
        return AssistantGroundingPlan(
            intent=AssistantIntent.COST,
            retrieval_tools=supported("get_operation_summary", "get_cost_breakdown"),
            exposed_tools=supported("get_cost_breakdown"),
        )

    if _contains_any(normalized, "por que", "porque") and _contains_any(
        normalized,
        "veiculo",
        "van",
        "caminhao",
        "moto",
        "rota",
    ):
        return AssistantGroundingPlan(
            intent=AssistantIntent.VEHICLE_EXPLANATION,
            retrieval_tools=supported(
                "get_operation_summary",
                "get_route_details",
                "get_vehicle_details",
            ),
            exposed_tools=supported("get_route_details", "get_vehicle_details"),
        )

    if _contains_any(
        normalized,
        "algoritmo",
        "genetico",
        "geracao",
        "geracoes",
        "poda",
        "pruning",
        "seed",
    ) or re.search(r"\bga\b", normalized):
        return AssistantGroundingPlan(
            intent=AssistantIntent.ALGORITHM,
            retrieval_tools=supported("get_operation_summary", "get_algorithm_run_summary"),
            exposed_tools=supported("get_algorithm_run_summary"),
        )

    if _contains_any(
        normalized,
        "compar",
        "baseline",
        "nearest",
        "insertion",
        "heuristica",
    ):
        return AssistantGroundingPlan(
            intent=AssistantIntent.COMPARISON,
            retrieval_tools=supported("get_operation_summary", "get_comparison_results"),
            exposed_tools=supported("get_comparison_results"),
        )

    if _contains_any(normalized, "entrega", "destinatario", "endereco", "risco"):
        delivery_retrieval = [
            "get_operation_summary",
            "get_route_details",
            "get_delivery_details",
        ]
        if has_delivery_context:
            delivery_retrieval = ["get_operation_summary", "get_delivery_details"]
        return AssistantGroundingPlan(
            intent=AssistantIntent.DELIVERY,
            retrieval_tools=supported(*delivery_retrieval),
            exposed_tools=supported("get_delivery_details"),
        )

    # Referential follow-ups such as "e ela usou quantos veículos?" must not be
    # hijacked by the generic vehicle keyword rule. Let the semantic planner use
    # recent conversation context to determine whether "ela" refers to a baseline,
    # route, vehicle or another entity, then re-ground the requested fact.
    if _contains_any(normalized, "veiculo", "frota") and not _is_referential_follow_up(normalized):
        return AssistantGroundingPlan(
            intent=AssistantIntent.VEHICLE_EXPLANATION,
            retrieval_tools=supported(
                "get_operation_summary",
                "get_route_details",
                "get_vehicle_details",
            ),
            exposed_tools=supported("get_route_details", "get_vehicle_details"),
        )

    retrieval: list[str] = ["get_operation_summary"]
    exposed: list[str] = ["get_operation_summary"]
    if has_route_context:
        retrieval.append("get_route_details")
        exposed.append("get_route_details")
    if has_delivery_context:
        retrieval.append("get_delivery_details")
        exposed.append("get_delivery_details")

    semantic_candidates = supported(
        "get_route_details",
        "get_vehicle_details",
        "get_delivery_details",
        "get_cost_breakdown",
        "get_algorithm_run_summary",
        "get_comparison_results",
        "get_team_assignment_details",
    )
    return AssistantGroundingPlan(
        intent=AssistantIntent.GENERAL,
        retrieval_tools=supported(*retrieval),
        exposed_tools=supported(*exposed),
        semantic_tool_candidates=semantic_candidates[:_MAX_SEMANTIC_CANDIDATES],
    )


def select_assistant_tools(
    message: str,
    definitions: tuple[ToolDefinition, ...],
    *,
    has_route_context: bool = False,
    has_delivery_context: bool = False,
) -> tuple[ToolDefinition, ...]:
    """Compatibility view of the deterministic retrieval plan."""

    plan = plan_assistant_grounding(
        message,
        definitions,
        has_route_context=has_route_context,
        has_delivery_context=has_delivery_context,
    )
    available = {definition.name: definition for definition in definitions}
    return tuple(
        available[name] for name in plan.retrieval_tools[:_MAX_SELECTED_TOOLS] if name in available
    )


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", without_marks).strip()


def _contains_any(value: str, *needles: str) -> bool:
    return any(needle in value for needle in needles)


def _is_referential_follow_up(value: str) -> bool:
    if value.startswith("e "):
        return True
    patterns = (
        r"\bele\b",
        r"\bela\b",
        r"\bdele\b",
        r"\bdela\b",
        r"\bessa alternativa\b",
        r"\besse baseline\b",
        r"\bessa baseline\b",
        r"\bessa solucao\b",
    )
    return any(re.search(pattern, value) for pattern in patterns)
