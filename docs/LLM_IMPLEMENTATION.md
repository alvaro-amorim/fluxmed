# FluxMed — Implementação do Assistente IA (Fase 16)

## 1. Objetivo

A Fase 16 adiciona linguagem natural sobre dados operacionais já calculados e validados pelo FluxMed.

A LLM não substitui:

- Algoritmo Genético;
- roteamento A*/Dijkstra;
- Cost Engine;
- Team Assignment Solver;
- Solution Validator.

O modelo recebe apenas contexto explícito e dados retornados por tools backend-side autorizadas.

## 2. Arquitetura

```text
React /assistant
    |
    v
POST /api/v1/assistant/messages
    |
    v
AssistantService
    |
    +--> AssistantToolbox
    |      +--> read tools
    |      +--> narrative context tools
    |      +--> safe simulation tools
    |
    +--> LLMProvider
           +--> MockLLMProvider
           +--> CohereProvider
           +--> GeminiProvider
```

O frontend nunca recebe chaves dos providers e nunca chama Cohere/Gemini diretamente.

## 3. Ambiente local

O arquivo versionado é `.env.example`.

Crie o arquivo local na raiz do repositório:

```powershell
Copy-Item .env.example .env
```

O backend carrega `fluxmed/.env` sem sobrescrever variáveis reais já definidas no ambiente. O Vite também usa a raiz do repositório como `envDir` e expõe ao navegador apenas variáveis `VITE_*`.

Por padrão:

```env
LLM_PROVIDER=mock
LLM_MODEL=fluxmed-mock-v1
```

Isso permite desenvolver e executar CI sem consumo externo de tokens.

Para teste real, configure localmente apenas uma opção, sem versionar a chave.

Gemini:

```env
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3.8-flash
GEMINI_API_KEY=...
```

Cohere:

```env
LLM_PROVIDER=cohere
LLM_MODEL=command-a-plus-05-2026
COHERE_API_KEY=...
```

## 4. Tools de leitura

O catálogo atual oferece:

- `get_operation_summary`;
- `get_route_details`;
- `get_vehicle_details`;
- `get_delivery_details`;
- `get_cost_breakdown`;
- `get_comparison_results`;
- `get_algorithm_run_summary`;
- `get_team_assignment_details`.

Todas respeitam a operação selecionada. Uma tentativa de acessar outra operação é rejeitada antes da consulta operacional.

## 5. Tools de geração

Estas tools não pedem que a LLM invente dados. Elas montam contexto estruturado para redação:

- `generate_driver_instructions`;
- `generate_dispatch_report`;
- `generate_daily_operation_report`;
- `generate_executive_summary`.

As instruções de motorista enriquecem cada parada com endereço, janela, temperatura, manuseio e tempo de serviço quando esses dados existem. As janelas persistidas com timezone são convertidas para o fuso operacional `America/Sao_Paulo` antes de serem apresentadas ao modelo para redação das instruções, evitando expor horários UTC como se fossem horários locais.

## 6. Simulações seguras

A Fase 16 expõe inicialmente duas simulações apoiadas pelo validador oficial de equipe:

- `simulate_driver_swap`;
- `simulate_helper_removal`.

Ambas chamam `OptimizationResultService.simulate_team(..., apply=False)`.

Invariantes:

- `simulation_only = true`;
- `applied = false`;
- nenhuma tool da LLM altera rota, equipe ou operação;
- a resposta inclui validade, issues e impacto de custo quando calculável.

Simulações adicionais descritas no `LLM_SPEC.md` continuam sendo extensões possíveis, mas não devem ser expostas até existir um validador backend completo para cada tipo de alteração.

## 7. Guardrails

O prompt de sistema versionado exige:

- factualidade;
- ausência de valores inventados;
- uso de tools para dados operacionais;
- tratamento de conteúdo de entregas/observações como dados, nunca como instrução;
- nenhuma aplicação autônoma de mudanças;
- nenhuma exposição ou solicitação de secrets.

O backend também impõe:

- whitelist de tools;
- limite de tool calls por solicitação;
- limite de tamanho da saída;
- escopo por operação;
- códigos explícitos para timeout, rate limit, provider indisponível e resposta inválida.

## 8. Telemetria

A migration `20260916_0012` cria `assistant_telemetry`.

São armazenados somente metadados operacionais:

- `request_id`;
- `user_id`;
- `operation_id`;
- provider/model;
- latência;
- tokens de entrada/saída;
- nomes/status das tools;
- quantidade de falhas de tool;
- status da requisição;
- indicação de fallback;
- código de erro.

Não são persistidos nessa tabela:

- prompt do usuário;
- resposta da LLM;
- payload completo das tools;
- chaves de API.

## 9. Degraded mode

`GET /api/v1/assistant/status` informa `HEALTHY` ou `DEGRADED`.

Se um provider real estiver configurado sem a respectiva chave, o restante do FluxMed continua funcionando e a interface do assistente comunica indisponibilidade em vez de quebrar a aplicação principal.

## 10. Demonstração acadêmica

A tela `/assistant` oferece perguntas que cobrem o critério de aceite da Fase 16:

1. factual — `Qual o custo total da operação?`;
2. explicação — `Por que o veículo foi escolhido para a primeira rota?`;
3. instrução — `Gere instruções para o motorista da primeira rota.`;
4. relatório — `Gere um relatório diário da operação.`;
5. sugestão/simulação — `Simule remover o ajudante da primeira rota.`.

O `MockLLMProvider` executa esses fluxos de maneira determinística para CI e demonstração sem rede. A validação final da fase também deve executar ao menos o mesmo conjunto com um provider real antes do merge.

## 11. Critério de segurança para explicações

Quando a evidência disponível comprova somente a alocação final, mas não uma causalidade única, a resposta deve distinguir isso explicitamente.

Exemplo: os dados podem comprovar que uma van atende uma rota com determinada carga e utilização, mas não devem afirmar que ela foi escolhida *porque era a mais barata* se uma comparação marginal entre todos os veículos não foi persistida.

Decision Trace e métricas estruturadas podem sustentar explicações, mas nunca devem ser convertidos em chain-of-thought privada.
