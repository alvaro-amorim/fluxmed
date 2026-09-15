# FluxMed — Optimization Trace, SSE e Replay

**Status:** implementação da Fase 14  
**Escopo:** lifecycle da otimização, Decision Trace, streaming SSE, cancelamento, reconexão e replay.

## 1. Objetivo

A Fase 14 torna a execução do algoritmo genético observável sem inventar animações. Toda informação exibida durante a otimização vem de snapshots reais emitidos pelo `GeneticOptimizer` e persistidos no PostgreSQL.

O Decision Trace registra evidências estruturadas da execução. Ele não armazena raciocínio privado ou cadeia de pensamento: registra apenas métricas, mudanças de melhor solução, razões objetivas de seleção, mudanças de alocação, contagens de poda, geometria roteada e estado do run.

## 2. Lifecycle

`OptimizationRun` usa os estados:

```text
QUEUED
RUNNING
COMPLETED
FAILED
CANCELLED
INTERRUPTED
```

O POST de otimização persiste o run como `QUEUED` antes de entregá-lo ao executor em processo e muda a operação para `OPTIMIZING`. O worker usa outra sessão SQLAlchemy, marca `RUNNING` e só publica `COMPLETED` depois da validação independente e da persistência do resultado final.

A persistência do resultado validado, dos eventos finais do trace e do estado terminal é confirmada na mesma transação de conclusão. Isso evita uma janela em que o SSE pudesse observar `COMPLETED` antes de o evento terminal estar disponível.

Falha, cancelamento ou interrupção restauram o estado operacional anterior. Na inicialização da API, qualquer run deixado em `QUEUED` ou `RUNNING` por encerramento do processo é marcado como `INTERRUPTED`; a V1 não tenta restaurar população do GA.

## 3. Execução V1

A V1 usa um `ThreadPoolExecutor` interno com limite pequeno de workers. Essa escolha mantém a arquitetura simples e compatível com o escopo acadêmico atual. O banco continua sendo a fonte de verdade do lifecycle e do trace.

Não há Redis, Celery, RabbitMQ, Kafka, WebSocket ou checkpoint da população genética nesta fase.

## 4. Endpoints implementados

```text
POST /api/v1/operations/{operation_id}/optimize
GET  /api/v1/operations/{operation_id}/optimization-runs/latest-run
GET  /api/v1/optimization-runs/{run_id}
GET  /api/v1/optimization-runs/{run_id}/events
GET  /api/v1/optimization-runs/{run_id}/trace
POST /api/v1/optimization-runs/{run_id}/cancel
GET  /api/v1/optimization-runs/{run_id}/result
```

O POST retorna `202 Accepted`:

```json
{
  "optimization_run_id": "uuid",
  "status": "QUEUED",
  "result_url": "/api/v1/optimization-runs/{run_id}/result",
  "status_url": "/api/v1/optimization-runs/{run_id}",
  "events_url": "/api/v1/optimization-runs/{run_id}/events"
}
```

## 5. Eventos persistidos

O trace usa sequência monotônica por run. Eventos atuais:

```text
optimization_started
generation_snapshot
best_solution_updated
route_assignment_change
pruning_summary
final_comparison
optimization_completed
optimization_failed
optimization_cancelled
```

### `optimization_started`

Registra seed, quantidade de entregas, tamanho da população, máximo de gerações e pontos reais das entregas.

### `generation_snapshot`

Emitido pelo loop real do GA. Registra geração, melhor fitness global, custo, makespan, viagem, distância, quantidade de veículos, diversidade, taxa efetiva de mutação, imigrantes e contagens de poda.

### `best_solution_updated`

Emitido apenas quando existe melhora real. Além das métricas, registra:

- razões estruturadas da melhora lexicográfica;
- sequência de entregas por rota;
- veículo associado;
- geometria calculada no grafo dirigido de Santa Aurora;
- pontos das entregas com longitude, latitude e número da parada.

### `route_assignment_change`

Quando uma nova melhor solução altera a alocação ou a posição de uma entrega, registra de forma agregada:

- entrega alterada;
- veículo anterior e novo;
- posição anterior e nova.

A primeira melhor solução não gera mudança artificial: ela estabelece o baseline para comparações seguintes.

### `pruning_summary`

Registra contagens de poda durante e ao final da execução.

### `final_comparison`

Persiste a comparação entre a melhor solução do GA e os baselines heurísticos utilizados pela execução. O objetivo é manter evidência acadêmica reproduzível sem recalcular a otimização durante o replay.

### Eventos terminais

`optimization_completed`, `optimization_failed` e `optimization_cancelled` encerram o stream quando todos os eventos persistidos já foram entregues.

## 6. SSE e reconexão

Endpoint:

```text
GET /api/v1/optimization-runs/{run_id}/events
Content-Type: text/event-stream
```

Cada frame usa `id`, `event` e `data`:

```text
id: 37
event: generation_snapshot
data: {"sequence":37,"event_type":"generation_snapshot",...}
```

O cliente pode retomar por:

```text
Last-Event-ID: 37
```

ou:

```text
?after=37
```

O backend lê eventos já commitados no banco e continua a partir da sequência seguinte. Heartbeats são comentários SSE e não alteram o Decision Trace.

## 7. Cancelamento

`POST /optimization-runs/{run_id}/cancel` grava `cancel_requested_at` e sinaliza o executor local quando ele está no mesmo processo. O GA consulta o cancelamento cooperativamente entre gerações. Nenhuma solução parcial cancelada é aprovada como resultado válido.

No frontend, o cancelamento pede confirmação curta antes de interromper a execução.

## 8. Replay

`GET /optimization-runs/{run_id}/trace` devolve os eventos ordenados e persistidos. O frontend reproduz esses eventos em ordem e atualiza métricas, curva e mapa a partir deles.

O replay **não executa o algoritmo genético novamente** e, portanto, representa a execução histórica real daquele run.

A experiência é aberta em overlay e oferece:

- reproduzir/pausar;
- evento anterior/próximo;
- velocidades `1x`, `2x` e `4x`;
- timeline navegável;
- reinício;
- fechamento por botão ou `Esc`.

## 9. UI ao vivo

Durante o run o frontend mostra:

- fase operacional atual derivada do trace/lifecycle;
- geração atual;
- tempo decorrido;
- melhor custo;
- violações HARD da melhor candidata atual;
- makespan;
- distância total da melhor candidata atual;
- diversidade;
- taxa de mutação;
- total e razões de poda;
- curva de convergência;
- mudanças da melhor solução no mapa;
- entregas como pontos vermelhos numerados;
- estado de conexão/reconexão;
- ação de cancelamento.

A exibição explícita de violações HARD evita que uma solução intermediária ainda inviável seja confundida com o plano final validado.

O resultado persistido também exibe as entregas numeradas sobre as rotas finais.

## 10. Segurança e validade

O frontend nunca converte snapshot intermediário em plano aprovado. A solução final continua passando por `SolutionValidator`, Team Assignment e Cost Engine antes de ser persistida como `COMPLETED` e `validated=true`.

Falha de geração de geometria apenas para um snapshot visual do trace não fabrica uma linha: o evento mantém `geometry=null`. O resultado final continua exigindo roteamento e validação normais.

## 11. Testes da fase

A suíte cobre:

- emissão real de progresso pelo GA;
- cancelamento cooperativo;
- ordenação monotônica do trace;
- recuperação de run interrompido;
- replay do trace persistido;
- retomada SSE a partir de `Last-Event-ID`;
- replay frontend sem criar nova execução;
- navegação do replay por controles e timeline.

A validação de CI executa lint, formatação, type-check, migrations, testes de backend, testes de frontend, build e jornada E2E de login demo.
