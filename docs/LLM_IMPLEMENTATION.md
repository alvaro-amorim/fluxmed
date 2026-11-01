# FluxMed — implementação do Assistente IA

## Objetivo e fluxo

O assistente interpreta dados operacionais calculados pelo backend e redige respostas sobre rotas, recursos, custos e atendimento. O fluxo parte da operação selecionada:

```text
mensagem + contexto + histórico recente
    → seleção das fontes autorizadas
    → consultas e grounding estruturado
    → provider de linguagem
    → resposta + fontes + provider/modelo
```

O endpoint é `POST /api/v1/assistant/messages`. O [contrato HTTP](API_SPEC.md) descreve entrada e saída; [`application/assistant/`](../apps/api/src/fluxmed/application/assistant/) implementa a coordenação.

## Grounding estruturado

`GroundingPlan` separa consultas necessárias à resolução de IDs (`retrieval_tools`) e o subconjunto de ferramentas exposto ao provider (`exposed_tools`). Os fatos operacionais vêm das fontes consultadas na requisição.

Perguntas com intenção reconhecida usam seleção determinística. Perguntas abertas ou ambíguas podem usar um planejador semântico com function calling para selecionar até três fontes permitidas. O backend valida a escolha e executa as consultas; o planejador recebe o catálogo de fontes e o contexto conversacional necessário.

Perguntas agregadas recebem o conjunto pertinente para a agregação. Para identificar a rota com mais entregas, por exemplo, o contexto deve abranger as rotas comparadas. Uma pergunta sobre custo usa os componentes do plano calculados pelo backend.

## Fontes e ferramentas

| Grupo | Ferramentas |
|---|---|
| Operação e busca | `get_operation_summary`, `get_algorithm_run_summary`, `get_comparison_results` |
| Rotas e recursos | `get_route_details`, `get_vehicle_details`, `get_delivery_details`, `get_team_assignment_details` |
| Custos | `get_cost_breakdown` |
| Contexto narrativo | `generate_driver_instructions`, `generate_dispatch_report`, `generate_daily_operation_report`, `generate_executive_summary` |
| Simulação | `simulate_driver_swap`, `simulate_helper_removal` |

As fontes respeitam a operação selecionada. As ferramentas narrativas preparam dados estruturados para a redação. As simulações devolvem impacto com `simulation_only=true` e `applied=false`; a aplicação de alterações pertence às ações autorizadas da interface/API.

## Histórico e orçamento de contexto

O serviço usa até oito mensagens recentes, com até quatro turnos para o planejamento semântico de follow-up. O histórico resolve referências conversacionais; os fatos são reconfirmados nas fontes atuais.

O contexto é reduzido conforme a pergunta e controlado por limite de tamanho. Se faltar informação para uma conclusão, a resposta deve explicitar essa condição. O modelo recebe instruções para preservar valores, IDs, fontes e ordem das paradas, separar fatos de recomendações e respeitar os limites do contexto.

## Providers

`LLMProvider` possui implementações mock, Cohere e Gemini. A configuração padrão local é mock. Os defaults de modelo e os parâmetros estão em [`llm/config.py`](../apps/api/src/fluxmed/llm/config.py); as chaves ficam no backend.

O Gemini usa REST `generateContent` com `httpx` para a resposta já fundamentada e o SDK para o caminho que exige function calling. A chamada final tem timeout explícito. Rate limit, timeout e falhas são classificados e apresentados de forma sanitizada; o provider respeita cooldown quando aplicável.

Os parâmetros de configuração incluem `LLM_PROVIDER`, `LLM_MODEL`, `LLM_TIMEOUT_SECONDS`, `LLM_MAX_TOOL_CALLS`, `LLM_MAX_OUTPUT_CHARS` e `LLM_MAX_CONTEXT_CHARS`. O [guia de avaliação](ASSISTANT_EVALUATION.md) descreve a configuração local e a conferência da resposta.

## Custos e horários na resposta

O custo apresentado usa os valores operacionais persistidos, compostos por veículo/contrato, combustível e equipe efetiva. Comparações devem identificar o cenário e a solução correspondente. O cálculo de rotas, da fitness e dos impactos de simulação permanece no backend.

Chegadas e janelas são apresentadas no fuso operacional. Instruções ao motorista usam sequência, endereço, prioridade, janela, temperatura, manuseio e serviço disponíveis na rota.

## Controles e observabilidade

- Allowlist de ferramentas e verificação de contexto antes das consultas.
- Limites de contexto, histórico, chamadas e saída.
- Credenciais mantidas na API e erros públicos sanitizados.
- Telemetria de metadados de execução, provider, duração e resultado, preservando informações sensíveis.
- Status de configuração separado do resultado de uma chamada externa.

## Avaliação qualitativa

| Caso | Conferência |
|---|---|
| Resumo factual | Entregas, veículos, custo, distância e makespan coincidem com o plano consultado. |
| Instruções ao motorista | Sequência e restrições correspondem à rota selecionada. |
| Premissa falsa | A resposta usa a informação das fontes para tratar a premissa. |
| Dados insuficientes | A resposta delimita a informação disponível. |
| Follow-up | A referência é resolvida e os fatos são reconfirmados. |
| Simulação | A resposta distingue impacto calculado de alteração aplicada. |

Os testes automatizados usam respostas controladas para verificar grounding, seleção, continuidade, factualidade e resiliência. Ensaios com provider externo devem identificar operação/run, modelo, pergunta, resposta e valores de referência, permitindo confrontar o texto com a fonte. O [guia de avaliação](ASSISTANT_EVALUATION.md) reúne o procedimento; [TESTING_STRATEGY.md](TESTING_STRATEGY.md) delimita a cobertura automatizada e a verificação manual.
