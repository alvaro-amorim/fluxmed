# FluxMed — Implementação do Assistente IA (Fase 16)

## 1. Objetivo

A Fase 16 adiciona linguagem natural sobre dados operacionais já calculados e validados pelo FluxMed.

A LLM não substitui:

- Algoritmo Genético;
- roteamento A*/Dijkstra;
- Cost Engine;
- Team Assignment Solver;
- Solution Validator.

O modelo recebe somente contexto explícito e dados backend-side autorizados.

## 2. Arquitetura atual

```text
React /assistant
    |
    v
POST /api/v1/assistant/messages
    |
    v
AssistantService
    |
    +--> GroundingPlan
    |      +--> intenção conhecida
    |      +--> retrieval_tools
    |      +--> exposed_tools
    |      +--> candidatos semânticos para intenção ambígua
    |
    +--> AssistantToolbox
    |      +--> read tools
    |      +--> narrative context tools
    |      +--> safe simulation tools
    |
    +--> Context budget + compactação
    |
    +--> LLMProvider (uma chamada no caminho determinístico)
           +--> Mock
           +--> Cohere
           +--> Gemini
```

O frontend nunca recebe chaves dos providers e nunca chama Cohere/Gemini diretamente.

## 3. Structured RAG e GroundingPlan

O FluxMed usa Structured RAG: o backend recupera dados oficiais, monta contexto estruturado e somente depois chama a LLM para interpretar/redigir.

`GroundingPlan` separa duas responsabilidades que antes estavam misturadas:

- `retrieval_tools`: consultas que o backend precisa executar para resolver IDs, contexto e dependências;
- `exposed_tools`: subconjunto mínimo cujos payloads são realmente enviados à LLM.

Exemplo de custo:

```text
get_operation_summary   # resolver/contexto interno
get_cost_breakdown      # dado factual necessário
        |
        v
LLM recebe somente get_cost_breakdown
```

Exemplo de explicação de veículo:

```text
get_operation_summary
        |
resolve R-01
        |
get_route_details
        |
resolve vehicle_id
        |
get_vehicle_details
        |
LLM recebe route compacta + vehicle details
```

As paradas da rota são removidas do payload quando a intenção é apenas explicar o veículo, porque não são necessárias para essa resposta.

Exemplo de instruções ao motorista:

```text
get_operation_summary
        |
resolve primeira rota
        |
generate_driver_instructions
        |
LLM recebe somente o contexto final de instruções
```

Isso evita reenviar operation summary, route details, team details e delivery details duplicados no mesmo prompt.

## 4. Function calling e caminho híbrido

O caminho normal de intenções conhecidas é determinístico e executa uma única chamada externa à LLM. Isso reduz latência, custo e pressão de quota.

O plano também reserva `semantic_tool_candidates` para perguntas ambíguas. A arquitetura alvo é híbrida:

```text
intenção conhecida
    -> grounding determinístico
    -> uma chamada de geração

intenção ambígua
    -> catálogo read-only pequeno
    -> seleção semântica/function calling
    -> execução backend autorizada
    -> geração final
```

O function calling semântico não é necessário para as perguntas acadêmicas conhecidas da Fase 16 e não deve ser usado para operações de escrita. Antes de habilitar esse caminho em produção, ele deve ter testes próprios de quota, autorização, contexto e múltiplos turnos.

## 5. Context budget

O contexto estruturado tem limite explícito por requisição:

```env
LLM_MAX_CONTEXT_CHARS=30000
```

Se o grounding exceder o orçamento, o backend rejeita a chamada antes de enviar um payload excessivo ao provider. O sistema não deve truncar silenciosamente uma rota operacional e fingir que as instruções estão completas.

A estratégia primária é reduzir duplicação antes de atingir o limite.

## 6. Ambiente local

O arquivo versionado é `.env.example`.

Crie o arquivo local na raiz do repositório:

```powershell
Copy-Item .env.example .env
```

Por padrão o desenvolvimento usa mock:

```env
LLM_PROVIDER=mock
LLM_MODEL=fluxmed-mock-v1
```

Para Gemini real:

```env
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3.5-flash-lite
LLM_THINKING_LEVEL=minimal
GEMINI_API_KEY=...
```

O modelo padrão real da V1 é `gemini-3.5-flash-lite`, escolhido para o caminho grounded de baixa latência. O modelo não precisa resolver otimização; ele recebe dados já resolvidos pelo backend e interpreta/redige a resposta.

`LLM_THINKING_LEVEL` é configurável. O default depende do modelo. Para `gemini-3.5-flash-lite`, o padrão é `minimal`.

Outras opções podem ser testadas por benchmark sem alterar os módulos de negócio, por exemplo `gemini-3.6-flash` com `minimal` ou `gemini-3.8-flash` com `low`.

## 7. Cliente Gemini, retries e cooldown

O provider Gemini usa o SDK oficial `google-genai` e mantém o cliente reutilizável enquanto a configuração do processo não muda. A factory mantém providers configurados em cache por provider/model/timeout/thinking/key, permitindo reuso da conexão HTTP/TLS.

Erros transitórios `408` e `5xx` usam retries limitados do SDK. `429` não é retentado automaticamente.

Ao receber `429`, o provider extrai o tempo de retry quando disponível e abre um cooldown local. Durante esse intervalo, novas requisições são rejeitadas localmente em vez de continuar pressionando a quota externa.

Isso não é fallback: o provider continua sendo Gemini e nenhuma resposta alternativa é gerada silenciosamente.

## 8. Timeout e classificação de erros

Defaults atuais:

```env
LLM_TIMEOUT_SECONDS=45
LLM_MAX_OUTPUT_CHARS=6000
LLM_MAX_TOOL_CALLS=5
LLM_MAX_CONTEXT_CHARS=30000
```

O backend diferencia:

- timeout do provider;
- rate limit;
- provider indisponível;
- resposta inválida;
- limite de tools;
- limite de contexto.

`APITimeoutError` do SDK Gemini é tratado como timeout, não como indisponibilidade genérica.

## 9. Tools de leitura

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

## 10. Tools narrativas

Estas tools montam contexto estruturado; a redação final continua sendo responsabilidade da LLM:

- `generate_driver_instructions`;
- `generate_dispatch_report`;
- `generate_daily_operation_report`;
- `generate_executive_summary`.

As instruções de motorista enriquecem cada parada com endereço, janela, temperatura, manuseio e tempo de serviço quando esses dados existem. As janelas são convertidas para `America/Sao_Paulo` antes de serem apresentadas ao modelo.

## 11. Simulações seguras

A Fase 16 expõe inicialmente:

- `simulate_driver_swap`;
- `simulate_helper_removal`.

Ambas usam `apply=False`.

Invariantes:

- `simulation_only = true`;
- `applied = false`;
- nenhuma tool da LLM altera rota, equipe ou operação;
- validade e impacto vêm do backend.

## 12. Guardrails

O prompt e o backend exigem:

- factualidade;
- ausência de valores inventados;
- dados operacionais vindos de grounding autorizado;
- nenhuma aplicação autônoma de mudanças;
- nenhum SQL livre;
- nenhum secret no frontend;
- conteúdo operacional tratado como dado, não como instrução;
- operação selecionada como contexto confiável.

## 13. Telemetria

A migration `20260916_0012` cria `assistant_telemetry`.

São armazenados metadados operacionais:

- request/user/operation;
- provider/model;
- latência;
- tokens;
- nomes/status das tools;
- quantidade de falhas de tool;
- status e código de erro.

Não são persistidos nessa tabela:

- prompt do usuário;
- resposta da LLM;
- payload integral das tools;
- chaves de API.

## 14. Estado de conversa

O frontend atualmente mantém mensagens para exibição, mas o backend ainda trata cada requisição como independente e envia `history=()` com `store=False`.

Portanto, continuidade real entre turnos ainda não está concluída. O desenho previsto é manter estado de diálogo próprio no FluxMed (operação/rota/veículo/entrega em foco e histórico resumido), em vez de depender do armazenamento do provider como fonte principal de memória.

Esse item deve ser implementado e testado antes de declarar suporte a perguntas anafóricas como “e qual a capacidade dele?”.

## 15. Status do provider

`GET /api/v1/assistant/status` indica se o provider está configurado, não executa uma chamada paga de health-check a cada carregamento da tela.

A interface deve comunicar “Configurado”, não prometer disponibilidade instantânea. Evolução prevista: expor estado recente como cooldown/rate limit e última chamada bem-sucedida sem fazer polling caro no provider.

## 16. Demonstração acadêmica

A validação manual cobre:

1. `Qual o custo total da operação?`;
2. `Por que o veículo foi escolhido para a primeira rota?`;
3. `Gere instruções para o motorista da primeira rota.`;
4. `Gere um relatório diário da operação.`;
5. `Simule remover o ajudante da primeira rota.`;
6. tentativa adversarial de inventar uma métrica.

Além dos testes unitários, a validação real deve incluir perguntas consecutivas para detectar rate limit, timeout e regressões de contexto.

## 17. Critério de segurança para explicações

Quando a evidência comprova somente a alocação final, mas não uma causalidade única, a resposta deve distinguir isso explicitamente.

A van pode estar comprovadamente alocada à rota e ter capacidade compatível, mas a LLM não deve afirmar que ela foi escolhida “porque era a mais barata” se essa comparação causal não estiver persistida.

Decision Trace e métricas estruturadas podem sustentar explicações, mas nunca devem ser convertidos em chain-of-thought privada.

## 18. Próximos incrementos desta fase

Antes do merge final da Fase 16:

- validar o grounding compacto com provider real;
- medir latência/tokens nas cinco perguntas de demonstração;
- adicionar teste de duas ou mais mensagens consecutivas;
- implementar estado de conversa próprio;
- habilitar function calling semântico apenas para intenção ambígua, com catálogo read-only pequeno;
- melhorar UX de falha e, posteriormente, oferecer fallback explícito somente com consentimento do usuário;
- manter a documentação sincronizada com cada mudança arquitetural.
