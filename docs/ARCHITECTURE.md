# FluxMed — Architecture

**Documento:** `docs/ARCHITECTURE.md`  
**Status:** Arquitetura oficial da V1  
**Projeto:** FluxMed — Planejamento Inteligente de Rotas Médicas  
**Contexto:** Tech Challenge — Fase 2 — Projeto 2

---

# 1. Objetivo deste documento

Este documento define a arquitetura técnica oficial do FluxMed V1.

Ele estabelece:

- organização do monorepo;
- responsabilidades de frontend e backend;
- fronteiras entre módulos;
- dependências permitidas;
- fluxo de dados;
- persistência;
- integração com mapa;
- contratos de API;
- progresso de otimização;
- integração com LLM;
- observabilidade;
- segurança;
- deploy;
- regras para evitar overengineering.

Este documento deve ser considerado fonte de verdade arquitetural para o Codex.

---

# 2. Princípio arquitetural central

O FluxMed deve ser tecnicamente profissional sem carregar infraestrutura desnecessária.

A arquitetura da V1 seguirá estes princípios:

1. **monorepo**;
2. **frontend e backend separados por contrato HTTP**;
3. **backend como monólito modular**;
4. **domínio isolado de frameworks**;
5. **otimização isolada da API**;
6. **routing separado de optimization**;
7. **PostgreSQL/PostGIS como fonte de verdade**;
8. **OpenAPI como contrato frontend/backend**;
9. **SSE para progresso de otimização**;
10. **LLM como camada auxiliar, nunca como núcleo de decisão**;
11. **baixo acoplamento com provedores externos**;
12. **sem microserviços na V1**.

---

# 3. Visão de alto nível

```text
┌─────────────────────────────────────────────┐
│                 Navegador                   │
│                                             │
│ React + Vite + TypeScript + MapLibre        │
└──────────────────────┬──────────────────────┘
                       │
                       │ HTTPS / JSON / SSE
                       ▼
┌─────────────────────────────────────────────┐
│                  FastAPI                    │
│                                             │
│ API                                         │
│ Application                                 │
│ Domain                                      │
│ Operations                                  │
│ Deliveries                                  │
│ Fleet                                       │
│ Workforce                                   │
│ City                                        │
│ Routing                                     │
│ Optimization                                │
│ Reports                                     │
│ LLM                                         │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│          PostgreSQL + PostGIS               │
└─────────────────────────────────────────────┘
```

Dependências externas opcionais:

```text
FastAPI
├── Cohere / Gemini
├── Sentry
└── Vercel runtime
```

---

# 4. Estilo arquitetural

O backend será um **monólito modular inspirado em DDD e Clean Architecture**, sem aplicar essas abordagens de forma dogmática.

Objetivo:

- regras de negócio testáveis;
- módulos bem definidos;
- pouca dependência entre áreas;
- possibilidade futura de extrair componentes;
- simplicidade operacional.

Não será implementada arquitetura de microserviços na V1.

---

# 5. Monorepo

Estrutura planejada:

```text
fluxmed/
├── apps/
│   ├── web/
│   └── api/
├── data/
├── benchmarks/
├── docs/
├── infra/
├── scripts/
├── tests/
├── .github/
├── docker-compose.yml
├── .env.example
├── README.md
├── CONTRIBUTING.md
└── LICENSE
```

A estrutura deve ser criada gradualmente.

O Codex não deve criar dezenas de diretórios vazios antecipadamente.

---

# 6. Frontend

Local:

```text
apps/web/
```

Stack:

- React;
- Vite;
- TypeScript;
- MapLibre GL;
- Vitest;
- React Testing Library;
- Playwright.

Estrutura sugerida:

```text
apps/web/src/
├── app/
├── components/
├── features/
├── pages/
├── services/
├── hooks/
├── types/
├── lib/
└── assets/
```

---

# 7. Responsabilidades do frontend

O frontend é responsável por:

- renderização;
- navegação;
- formulários;
- interação com mapa;
- tabelas;
- filtros;
- gráficos;
- estados de loading;
- estados de erro;
- autenticação visual;
- consumo da API;
- consumo de SSE;
- replay visual do Decision Trace.

O frontend **não é responsável por**:

- cálculo de custo;
- validação final de domínio;
- algoritmo genético;
- roteamento;
- pruning;
- alocação de equipe;
- geração de cidade;
- decisão de viabilidade;
- regras de negócio críticas.

---

# 8. Regra de lógica no frontend

É permitido no frontend:

```text
formatar moeda
formatar data
ordenar lista local
filtrar tabela
controlar estado de formulário
desenhar rotas
animar eventos
```

Não é permitido:

```text
decidir se uma rota é válida
calcular fitness
calcular custo oficial
atribuir veículo
executar GA
simular routing
validar autonomia oficial
```

Essas decisões pertencem ao backend.

---

# 9. Backend

Local:

```text
apps/api/
```

Stack:

- Python;
- FastAPI;
- Pydantic;
- SQLAlchemy;
- Alembic;
- PostgreSQL;
- PostGIS.

Estrutura sugerida:

```text
apps/api/src/fluxmed/
├── api/
├── application/
├── domain/
├── infrastructure/
├── operations/
├── deliveries/
├── fleet/
├── workforce/
├── city/
├── routing/
├── optimization/
├── reports/
├── llm/
├── security/
└── observability/
```

Essa estrutura pode ser ajustada durante a implementação se uma organização mais simples se mostrar melhor.

---

# 10. Camadas principais

## 10.1 Domain

Contém regras centrais.

Exemplos:

```text
Delivery
Vehicle
Worker
Operation
Route
TimeWindow
Cost
Capacity
Priority
Fitness
```

O domínio não deve depender de:

- FastAPI;
- SQLAlchemy;
- Cohere;
- Gemini;
- Vercel;
- React;
- requests HTTP.

---

## 10.2 Application

Coordena casos de uso.

Exemplos:

```text
CreateOperation
ImportDeliveries
GenerateScenario
OptimizeOperation
ApproveOperation
DispatchOperation
GenerateReport
AskAssistant
```

A camada Application orquestra módulos sem implementar detalhes externos.

---

## 10.3 Infrastructure

Implementa integrações concretas:

- PostgreSQL;
- SQLAlchemy;
- filesystem;
- LLM providers;
- logging;
- exports;
- serviços externos.

---

## 10.4 API

Expõe:

- HTTP;
- JSON;
- autenticação;
- SSE;
- OpenAPI.

A API não deve conter regras de negócio relevantes diretamente.

---

# 11. Regra de dependência

Direção preferida:

```text
API
 ↓
Application
 ↓
Domain
```

Infrastructure implementa interfaces usadas pelas camadas internas.

Nunca:

```text
Domain → FastAPI
Domain → SQLAlchemy
Domain → Gemini
Optimization → FastAPI
Frontend → banco
LLM → SQLAlchemy diretamente
```

---

# 12. Módulo Operations

Responsável por:

- criação de operação;
- revisão;
- status;
- recursos selecionados;
- horários;
- trânsito;
- interdições;
- aprovação;
- dispatch;
- snapshots.

Não deve implementar internamente o algoritmo genético.

---

# 13. Módulo Deliveries

Responsável por:

- cadastro;
- importação;
- validação;
- priorização;
- janelas;
- temperatura;
- manuseio;
- geração sintética de entregas.

---

# 14. Módulo Fleet

Responsável por:

- veículos;
- capacidades;
- autonomia;
- refrigeração;
- tipos;
- ownership;
- custos de frota.

---

# 15. Módulo Workforce

Responsável por:

- motoristas;
- ajudantes;
- motoboys;
- disponibilidade;
- vínculos;
- custos;
- compatibilidade.

---

# 16. Módulo City

Responsável por:

- cidades;
- bairros;
- ruas;
- segmentos;
- interseções;
- lotes;
- edifícios;
- endereços;
- facilities;
- geração de Santa Aurora;
- importadores futuros;
- validação geográfica.

---

# 17. CityProvider

A aplicação deve depender de uma abstração equivalente a:

```text
CityProvider
```

Implementação inicial:

```text
SantaAuroraProvider
```

Futuros:

```text
OSMCityProvider
GISCityProvider
```

O optimizer nunca deve conhecer diretamente Santa Aurora.

---

# 18. Routing

O módulo Routing responde:

> Qual é o melhor caminho entre dois pontos?

Responsabilidades:

- grafo dirigido;
- A*;
- Dijkstra;
- travel time;
- trânsito;
- interdições;
- matriz de custos;
- cache.

Estrutura sugerida:

```text
routing/
├── graph/
├── shortest_path/
├── travel_time/
├── traffic/
├── closures/
├── matrix/
└── cache/
```

---

# 19. Optimization

O módulo Optimization responde:

> Como distribuir e ordenar as entregas entre os veículos?

Responsabilidades:

- cromossomo;
- população;
- seleção;
- crossover;
- mutação;
- decoder;
- fitness;
- pruning;
- repair;
- diversidade;
- stopping;
- Decision Trace;
- melhor solução;
- validação final.

Estrutura sugerida:

```text
optimization/
├── chromosome/
├── population/
├── selection/
├── crossover/
├── mutation/
├── decoder/
├── fitness/
├── pruning/
├── repair/
├── diversity/
├── stopping/
├── trace/
├── validation/
└── engine.py
```

---

# 20. Separação Routing x Optimization

Regra rígida:

```text
Routing:
A → B por onde?

Optimization:
Quem atende A, B, C e em qual ordem?
```

O GA não evolui sequências de ruas.

Ele trabalha sobre entregas e veículos.

Depois, o Routing calcula os caminhos urbanos reais.

---

# 21. OptimizationEngine

Interface conceitual:

```python
OptimizationEngine.optimize(problem) -> OptimizationResult
```

Entrada:

```text
OptimizationProblem
```

Contém:

- operação;
- entregas;
- veículos;
- equipe;
- matriz de tempos;
- restrições;
- custos;
- configurações;
- seed.

Saída:

```text
OptimizationResult
```

Contém:

- solução;
- rotas;
- métricas;
- equipe;
- custos;
- Decision Trace;
- stop reason;
- validação.

---

# 22. SolutionValidator

Componente independente do GA.

Fluxo:

```text
GA
 ↓
best solution
 ↓
SolutionValidator
 ↓
VALID / INVALID
```

Valida:

- todas as entregas;
- nenhuma duplicada;
- capacidade;
- volume;
- autonomia;
- refrigeração;
- equipe;
- HARD windows;
- jornada;
- retorno;
- compatibilidade viária.

Uma solução rejeitada nunca pode ser apresentada ao usuário como válida.

---

# 23. TeamAssignmentSolver

Separado do cromossomo.

Fluxo:

```text
rotas
 ↓
TeamAssignmentSolver
 ↓
motorista / ajudante / motoboy
 ↓
custo de equipe
```

Método:

- matching;
- alocação de custo mínimo;
- compatibilidade;
- disponibilidade.

Não usar outro GA para isso.

---

# 24. Banco de dados

Fonte de verdade:

```text
PostgreSQL + PostGIS
```

PostgreSQL armazena:

- usuários;
- operações;
- entregas;
- frota;
- equipe;
- revisões;
- relatórios;
- Decision Trace resumido;
- execuções do optimizer.

PostGIS armazena:

- geometrias;
- ruas;
- segmentos;
- interseções;
- bairros;
- endereços;
- facilities;
- rotas quando necessário.

---

# 25. GeoJSON

GeoJSON é formato de intercâmbio e visualização.

Usos:

- mapa;
- endpoints geográficos;
- debugging;
- exports.

GeoJSON não será a fonte principal de persistência geográfica.

---

# 26. SQLAlchemy

Usado como camada ORM.

Regra:

- modelos ORM não devem substituir entidades de domínio em regras críticas;
- persistência não deve contaminar o core algorítmico.

---

# 27. Alembic

Toda alteração de schema deve usar migration.

Regras:

- migrations versionadas;
- não editar banco manualmente em produção;
- seeds não devem ser migrations.

---

# 28. Seeds

Santa Aurora, frota demo, usuários demo e equipe demo são criados por scripts separados.

Exemplo:

```text
scripts/
├── generate_santa_aurora.py
├── seed_database.py
└── validate_city.py
```

---

# 29. API

Estilo:

```text
REST + SSE
```

Base recomendada:

```text
/api/v1/
```

Exemplo:

```text
/api/v1/operations
/api/v1/deliveries
/api/v1/vehicles
/api/v1/workers
/api/v1/reports
/api/v1/assistant
```

---

# 30. Versionamento da API

A V1 usa:

```text
/api/v1
```

Não criar versionamento complexo por header.

Mudanças incompatíveis futuras podem criar `/v2`.

---

# 31. OpenAPI

FastAPI gera OpenAPI.

Fluxo:

```text
Pydantic models
      ↓
OpenAPI
      ↓
TypeScript client
      ↓
React
```

Objetivo:

- reduzir duplicação;
- evitar contratos divergentes;
- tipar frontend.

---

# 32. DTOs

DTOs de API não precisam ser iguais às entidades internas.

Exemplo:

```text
OperationResponse
OperationCreateRequest
OptimizationRunResponse
RouteResponse
```

Não expor internals desnecessários.

---

# 33. Progresso de otimização

A otimização deve possuir entidade:

```text
OptimizationRun
```

Estados:

```text
QUEUED
RUNNING
COMPLETED
FAILED
CANCELLED
INTERRUPTED
```

---

# 34. SSE

O progresso será transmitido por:

```text
Server-Sent Events
```

Motivo:

- fluxo principalmente backend → frontend;
- implementação simples;
- adequado para snapshots;
- não exige WebSocket na V1.

---

# 35. Eventos SSE

Exemplos:

```text
optimization_started
generation_snapshot
best_solution_updated
pruning_summary
diversity_changed
optimization_completed
optimization_failed
```

---

# 36. Granularidade do SSE

Não transmitir toda a população.

Enviar apenas:

- snapshots periódicos;
- melhorias importantes;
- agregados de pruning;
- mudança de fase;
- métricas.

Isso reduz:

- tráfego;
- renderizações;
- armazenamento.

---

# 37. Reconexão SSE

Se a conexão cair:

- o algoritmo continua;
- o frontend consulta estado atual;
- reconecta;
- continua a partir do snapshot mais recente.

Não é necessário checkpoint completo da população do GA na V1.

---

# 38. Execução do optimizer

Na V1, o optimizer pode rodar dentro da aplicação Python.

Objetivo inicial:

- simplicidade;
- facilidade local;
- facilidade acadêmica.

Não usar inicialmente:

- Celery;
- Redis;
- RabbitMQ;
- Kubernetes.

Se os benchmarks mostrarem necessidade futura, o módulo poderá ser extraído.

---

# 39. Concorrência

Não otimizar para grande escala empresarial.

A V1 pode limitar execuções simultâneas.

Regra importante:

```text
uma revisão de operação
→ no máximo uma OptimizationRun ativa
```

Cliques duplicados devem reutilizar ou rejeitar a execução já ativa.

---

# 40. Idempotência

Ações críticas devem evitar duplicação acidental.

Aplicável principalmente a:

- optimization start;
- dispatch;
- import confirmation;
- report generation.

Implementação pode usar:

- estado atual;
- chave idempotente;
- constraint no banco.

---

# 41. Decision Trace

Estrutura persistida em formato estruturado.

Não armazenar “pensamento interno”.

Tipos:

```text
GenerationSnapshot
PruningEvent
ImprovementEvent
VehicleSelectionReason
RouteAssignmentChange
ConstraintViolation
FinalComparison
```

---

# 42. Persistência do Decision Trace

Não armazenar cada micro-operação.

Persistir:

- snapshots;
- melhorias;
- eventos relevantes;
- agregados;
- métricas finais.

Objetivo:

- replay;
- relatório;
- explicação;
- debugging.

---

# 43. Reports

Módulo responsável por:

- PDF;
- XLSX;
- dados estruturados;
- relatórios da operação.

O relatório deve usar snapshot persistido.

Não recalcular histórico a partir de valores atuais.

---

# 44. LLM

Arquitetura:

```text
LLMService
   ↓
LLMProvider
   ├── CohereProvider
   └── GeminiProvider
```

O restante da aplicação não deve saber qual provider está ativo.

---

# 45. LLMProvider

Interface conceitual:

```python
class LLMProvider:
    async def generate(...):
        ...
```

Modelo e provider configurados por ambiente.

Não hardcode de modelo em regras de domínio.

---

# 46. Tools da LLM

A LLM acessa dados via ferramentas controladas.

Nunca:

```text
LLM → SQL livre
```

Sempre:

```text
LLM
 ↓
Tool
 ↓
Application service
 ↓
dados autorizados
```

---

# 47. Segurança da LLM

Regras:

- tool whitelist;
- timeout;
- limites de tokens;
- sanitização;
- nenhum secret em prompt;
- nenhuma alteração sem confirmação;
- nenhuma resposta usada como fonte matemática oficial.

---

# 48. Autenticação

Implementação inicial:

```text
FastAPI + PostgreSQL
```

Senha:

```text
Argon2id
```

Não usar autenticação externa obrigatória.

Não usar Supabase/Auth0/Firebase na V1.

---

# 49. RBAC

Backend deve validar role.

Nunca confiar somente no frontend.

Roles:

```text
ADMIN
PLANNER
```

---

# 50. Secrets

Local:

```text
.env
```

Nunca versionado.

Repositório:

```text
.env.example
```

Produção:

- environment variables da plataforma.

Nunca colocar API key em:

```text
VITE_*
```

porque variáveis `VITE_*` podem chegar ao navegador.

---

# 51. Observabilidade

Componentes:

- logs estruturados;
- audit log;
- optimizer telemetry;
- LLM telemetry;
- Sentry;
- health endpoints.

---

# 52. Logs estruturados

Produção preferencialmente em JSON.

Contexto:

```text
request_id
user_id
operation_id
operation_revision_id
optimization_run_id
event
duration_ms
```

---

# 53. Audit Log

Persistente no banco.

Registra:

- alteração de operação;
- interdição;
- troca de equipe;
- aprovação;
- dispatch;
- ações administrativas relevantes.

---

# 54. Optimizer telemetry

Registrar:

- duração;
- gerações;
- time-to-first-valid;
- time-to-best;
- avaliações;
- podas;
- repairs;
- cache hits;
- métricas finais;
- stop reason.

---

# 55. LLM telemetry

Registrar:

- provider;
- modelo;
- latência;
- tokens;
- tools chamadas;
- sucesso/falha.

Nunca registrar:

- API keys;
- senha;
- token completo;
- authorization header.

---

# 56. Health endpoints

```text
GET /health/live
GET /health/ready
```

`live`:

- processo está vivo.

`ready`:

- API;
- banco;
- PostGIS;
- dataset principal.

LLM não precisa tornar todo sistema indisponível.

---

# 57. Degradação graciosa

Core:

```text
Database
City/Routing
Optimization
SolutionValidator
```

Auxiliar:

```text
LLM
PDF
XLSX
Sentry
```

Falha auxiliar não deve derrubar o core.

---

# 58. Erros tipados

Exemplos:

```text
ROAD_GRAPH_DISCONNECTED
NO_FEASIBLE_VEHICLE
HARD_WINDOW_INFEASIBLE
OPTIMIZATION_TIMEOUT_NO_SOLUTION
DATABASE_UNAVAILABLE
LLM_PROVIDER_UNAVAILABLE
REPORT_GENERATION_FAILED
IMPORT_VALIDATION_FAILED
```

Frontend usa esses códigos para mensagens úteis.

---

# 59. Transações

Ações críticas devem ser atômicas.

Exemplo de dispatch:

```text
validar revisão
 ↓
criar snapshot
 ↓
marcar DISPATCHED
 ↓
audit log
 ↓
commit
```

Ou tudo acontece, ou nada.

---

# 60. Retry

Retry apenas em falhas transitórias e seguras.

Pode usar retry para:

- LLM timeout;
- chamadas externas idempotentes.

Não repetir cegamente:

- dispatch;
- import confirmation;
- mutações sem idempotência.

---

# 61. Circuit breaker

Pode ser usado de forma simples para LLM.

Não é obrigatório implementar framework complexo.

Objetivo:

- evitar múltiplas tentativas lentas quando provider externo está indisponível.

---

# 62. Frontend state

Não introduzir Redux por padrão.

Preferir:

- React state;
- hooks;
- context quando necessário;
- query/cache library somente se justificar.

Evitar estado global excessivo.

---

# 63. Estilo e componentes

Componentes devem ser reutilizáveis.

Evitar:

- mega-componentes;
- páginas com centenas de linhas de lógica misturada;
- regras de negócio em JSX.

---

# 64. MapLibre

O mapa usa dados provenientes do backend.

Camadas:

- bairros;
- vias;
- facilities;
- entregas;
- depot;
- closures;
- rotas.

Não usar mapas externos como fonte de verdade da cidade.

---

# 65. Performance do mapa

Não enviar todos os detalhes urbanos sem necessidade.

Possíveis estratégias:

- simplificação de geometria;
- endpoints por viewport;
- camadas separadas;
- GeoJSON agregado;
- lazy loading.

Na V1, priorizar simplicidade e medir antes de sofisticar.

---

# 66. Cache

Pode existir cache local/backend para:

- matriz de viagem;
- caminhos;
- dados estáticos da cidade.

Não adicionar Redis somente por cache na V1.

Cache em memória ou persistido de forma simples pode ser suficiente.

---

# 67. Time-dependent routing

Chave conceitual de cache:

```text
(origin, destination, time_bucket, graph_version)
```

Time bucket inicial recomendado:

```text
15 minutos
```

Ajustável por benchmark.

---

# 68. Datas e horários

Regras:

- persistência preferencialmente timezone-aware;
- cidade possui timezone;
- API usa ISO 8601;
- frontend exibe horário local da operação.

Santa Aurora deve usar timezone configurável, inicialmente compatível com Brasil.

---

# 69. Unidades

Internamente padronizar:

- distância: metros ou quilômetros conforme domínio;
- peso: kg;
- volume: m³;
- tempo: segundos/minutos com tipo explícito;
- moeda: centavos ou Decimal, nunca float para valores financeiros.

---

# 70. Dinheiro

Usar:

```text
Decimal
```

ou centavos inteiros.

Nunca usar `float` como fonte de verdade de dinheiro.

---

# 71. IDs

Entidades persistentes:

```text
UUID
```

Podem coexistir com códigos operacionais humanos.

Exemplo:

```text
UUID técnico
+
DLV-NF45872-001
```

---

# 72. Soft delete

Para entidades históricas como:

- veículos;
- workers;

preferir:

```text
active = false
```

em vez de apagar quando já estiverem referenciadas.

---

# 73. Histórico

Snapshot deve ser autossuficiente o suficiente para preservar relatórios.

Não depender apenas de referências mutáveis.

---

# 74. CI

GitHub Actions deve validar:

- backend lint;
- frontend lint;
- type-check;
- unit tests;
- property tests;
- integration tests;
- contract tests;
- build;
- smoke/E2E críticos conforme maturidade;
- security checks.

Benchmarks pesados ficam separados.

---

# 75. Branching

Usar GitHub Flow simplificado.

Branches:

```text
feat/*
fix/*
test/*
docs/*
refactor/*
chore/*
```

Merge por PR.

---

# 76. Commits

Conventional Commits.

Exemplos:

```text
feat: add operation creation flow
fix: reject duplicated delivery assignment
test: add routing integration tests
docs: document city architecture
```

---

# 77. Architecture Decision Records

Local:

```text
docs/adr/
```

Exemplos:

```text
0001-use-postgresql-postgis.md
0002-use-modular-monolith.md
0003-use-maplibre.md
0004-use-sse.md
0005-use-indirect-ga-representation.md
0006-use-lexicographic-fitness.md
```

Criar ADR somente para decisões realmente relevantes.

---

# 78. Deploy

Primeira opção:

```text
Frontend → Vercel
Backend  → Vercel
Database → Neon
```

Essa escolha prioriza:

- simplicidade;
- custo baixo;
- integração fácil;
- projeto acadêmico.

---

# 79. Portabilidade do backend

Mesmo usando Vercel, evitar acoplamento desnecessário.

FastAPI deve poder migrar no futuro para:

- Railway;
- Render;
- Fly.io;
- outro host Python.

Não construir funcionalidade específica de Vercel dentro do domínio.

---

# 80. Infraestrutura local

Objetivo:

```text
docker compose up
```

ou comando equivalente simples.

Localmente:

- Postgres/PostGIS;
- API;
- frontend quando apropriado.

Também deve ser possível rodar frontend/backend diretamente para desenvolvimento.

---

# 81. Docker

Usar Docker para:

- reprodutibilidade;
- banco local;
- ambiente acadêmico;
- CI quando útil.

Não containerizar cada módulo separadamente.

---

# 82. IaC

O enunciado associa IaC à implementação em nuvem.

Para a V1 acadêmica, arquivos de configuração de deploy são suficientes inicialmente.

Não introduzir Terraform somente para parecer “enterprise” sem benefício real.

Se houver necessidade acadêmica específica, reavaliar.

---

# 83. Dependências

Toda nova dependência deve justificar:

- problema resolvido;
- manutenção;
- maturidade;
- peso;
- alternativa nativa.

Evitar instalar biblioteca para funções triviais.

---

# 84. Política de abstração

Criar abstrações quando existir:

- necessidade real de substituição;
- fronteira importante;
- teste facilitado;
- provider externo.

Exemplos bons:

```text
LLMProvider
CityProvider
Repository
OptimizationEngine
```

Evitar interfaces artificiais para classes que possuem apenas uma implementação e nenhuma fronteira relevante.

---

# 85. Política de complexidade

Não implementar na V1:

```text
Kafka
RabbitMQ
Celery obrigatório
Redis obrigatório
Kubernetes
service mesh
event sourcing
CQRS completo
microservices
GraphQL
gRPC
multi-tenant SaaS
```

A menos que um requisito futuro explícito torne necessário.

---

# 86. Fluxo principal técnico

```text
React
 ↓
POST /operations
 ↓
FastAPI
 ↓
CreateOperation
 ↓
Domain validation
 ↓
Repository
 ↓
PostgreSQL
 ↓
response
```

---

# 87. Fluxo de otimização

```text
React
 ↓
POST /operations/{id}/optimize
 ↓
OptimizeOperation
 ↓
load operation
 ↓
validate inputs
 ↓
build effective road graph
 ↓
build travel matrix
 ↓
GA
 ↓
TeamAssignmentSolver
 ↓
SolutionValidator
 ↓
persist result
 ↓
SSE / completed
```

---

# 88. Fluxo de mapa

```text
React
 ↓
GET city/map layers
 ↓
FastAPI
 ↓
CityProvider / repository
 ↓
PostGIS
 ↓
GeoJSON
 ↓
MapLibre
```

---

# 89. Fluxo da LLM

```text
User question
 ↓
React
 ↓
FastAPI
 ↓
AssistantService
 ↓
LLMProvider
 ↓
approved tools
 ↓
Application layer
 ↓
structured data
 ↓
LLM response
 ↓
React
```

---

# 90. Fluxo de relatório

```text
Operation snapshot
 ↓
Report service
 ├── deterministic metrics
 ├── route data
 ├── costs
 └── optional LLM narrative
 ↓
PDF / XLSX
```

LLM nunca cria números oficiais.

---

# 91. Architecture tests

Testes devem impedir dependências proibidas.

Exemplos:

```text
domain não importa fastapi
domain não importa sqlalchemy
domain não importa provider LLM
optimization não importa api
```

---

# 92. Definition of Done arquitetural

Uma nova feature deve:

- respeitar módulo correto;
- não vazar regra para frontend;
- não criar acoplamento desnecessário;
- possuir testes apropriados;
- atualizar contrato quando necessário;
- atualizar documentação quando alterar decisão relevante;
- manter CI verde.

---

# 93. Estratégia de implementação

A arquitetura será construída em fatias verticais.

Exemplo:

```text
1. fundação
2. auth
3. operações
4. Santa Aurora
5. entregas
6. frota/equipe
7. routing
8. optimizer
9. Decision Trace
10. LLM
11. reports
12. polish
```

Cada fase deve deixar o sistema funcional.

---

# 94. Regra para o Codex

O Codex não deve tentar implementar toda a arquitetura em uma única etapa.

Para cada fatia:

```text
entender docs
 ↓
criar branch
 ↓
implementar
 ↓
testar
 ↓
corrigir
 ↓
documentar
 ↓
PR / commit
 ↓
próxima fatia
```

---

# 95. Fonte de verdade

Prioridade documental:

```text
PRODUCT_SPEC.md
ARCHITECTURE.md
DOMAIN_MODEL.md
SANTA_AURORA_SPEC.md
OPTIMIZATION_SPEC.md
FRONTEND_SPEC.md
API_SPEC.md
LLM_SPEC.md
TESTING_STRATEGY.md
DEVELOPMENT_PLAN.md
CODEX_INSTRUCTIONS.md
```

Em caso de conflito:

1. não adivinhar;
2. identificar divergência;
3. corrigir documentação;
4. só depois continuar.

---

# 96. Regra final de arquitetura

> O FluxMed deve ter fronteiras fortes onde elas reduzem erros e acoplamento, e simplicidade onde abstrações adicionais não entregam valor.

A arquitetura deve proteger o núcleo do projeto:

- domínio;
- roteamento;
- otimização;
- validação;
- explicabilidade.

Sem transformar o projeto acadêmico em uma infraestrutura empresarial desnecessária.
