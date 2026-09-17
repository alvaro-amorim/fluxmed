from fluxmed.llm.prompts import ASSISTANT_SYSTEM_PROMPT, ASSISTANT_SYSTEM_PROMPT_VERSION


def test_assistant_prompt_versions_metric_scope_guardrails() -> None:
    assert ASSISTANT_SYSTEM_PROMPT_VERSION == "assistant-system-v4"
    assert "Preserve o escopo de cada métrica" in ASSISTANT_SYSTEM_PROMPT
    assert "custo total oficial do plano atual" in ASSISTANT_SYSTEM_PROMPT
    assert "fitness registrado na comparação" in ASSISTANT_SYSTEM_PROMPT


def test_assistant_prompt_does_not_infer_time_pressure_from_punctuality_alone() -> None:
    assert "Não conclua que o plano está temporalmente apertado ou folgado" in ASSISTANT_SYSTEM_PROMPT
    assert "evidência explícita de janelas, slack ou margens temporais" in ASSISTANT_SYSTEM_PROMPT
