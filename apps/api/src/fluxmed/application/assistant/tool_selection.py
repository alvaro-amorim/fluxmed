import re
import unicodedata

from fluxmed.llm import ToolDefinition

_MAX_SELECTED_TOOLS = 5


def select_assistant_tools(
    message: str,
    definitions: tuple[ToolDefinition, ...],
    *,
    has_route_context: bool = False,
    has_delivery_context: bool = False,
) -> tuple[ToolDefinition, ...]:
    """Select a small deterministic tool set for the current assistant request.

    The selector never answers the question. It only reduces the provider-facing
    tool catalogue so the LLM chooses among relevant backend tools instead of
    receiving every available schema on every request.
    """

    normalized = _normalize(message)
    selected: list[str] = ["get_operation_summary"]

    def add(*names: str) -> None:
        for name in names:
            if name not in selected:
                selected.append(name)

    if has_route_context:
        add("get_route_details")
    if has_delivery_context:
        add("get_delivery_details")

    if _contains_any(normalized, "custo", "custos", "preco", "gasto", "valor"):
        add("get_cost_breakdown")

    if _contains_any(normalized, "por que", "porque") and _contains_any(
        normalized,
        "veiculo",
        "van",
        "caminhao",
        "moto",
        "rota",
    ):
        add("get_route_details", "get_vehicle_details")

    if _contains_any(normalized, "veiculo", "frota"):
        add("get_route_details", "get_vehicle_details")

    if _contains_any(normalized, "instruc", "orientac") and _contains_any(
        normalized,
        "motorista",
        "rota",
    ):
        add("generate_driver_instructions")

    if "resumo executivo" in normalized:
        add("generate_executive_summary")
    elif "relatorio" in normalized and "despacho" in normalized:
        add("generate_dispatch_report")
    elif "relatorio" in normalized:
        add("generate_daily_operation_report")

    helper_simulation = _contains_any(normalized, "remover", "retirar", "sem") and (
        "ajudante" in normalized
    )
    if helper_simulation or ("simul" in normalized and "ajudante" in normalized):
        add("simulate_helper_removal", "get_team_assignment_details")
    elif _contains_any(normalized, "equipe", "ajudante", "motorista"):
        add("get_team_assignment_details")

    driver_simulation = "motorista" in normalized and _contains_any(
        normalized,
        "trocar",
        "troca",
        "substituir",
        "simul",
    )
    if driver_simulation:
        add("simulate_driver_swap", "get_team_assignment_details")

    if _contains_any(normalized, "entrega", "destinatario", "endereco", "risco"):
        add("get_route_details", "get_delivery_details")

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
        add("get_algorithm_run_summary")

    if _contains_any(
        normalized,
        "compar",
        "baseline",
        "nearest",
        "insertion",
        "heuristica",
    ):
        add("get_comparison_results")

    if len(selected) == 1:
        add("get_route_details", "get_cost_breakdown", "get_team_assignment_details")

    available = {definition.name: definition for definition in definitions}
    return tuple(available[name] for name in selected[:_MAX_SELECTED_TOOLS] if name in available)


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", without_marks).strip()


def _contains_any(value: str, *needles: str) -> bool:
    return any(needle in value for needle in needles)
