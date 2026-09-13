# FluxMed — Development Plan

**Documento:** `docs/DEVELOPMENT_PLAN.md`  
**Status:** Plano oficial de implementação da V1  
**Projeto:** FluxMed — Planejamento Inteligente de Rotas Médicas  
**Responsável principal de implementação:** Codex  
**Estratégia:** backend/domain-first com entregas em fatias verticais  
**Ponto de partida:** repositório zerado, contendo apenas documentação

---

# 1. Objetivo deste documento

Este documento define a ordem oficial de desenvolvimento do FluxMed V1.

Ele existe para impedir que a implementação cresça de forma desorganizada, que o frontend seja construído inteiro sobre mocks ou que o backend seja construído isoladamente sem validação visual.

Cada fase deve produzir uma parte funcional do sistema.

A regra é:

```text
planejar
↓
implementar
↓
testar
↓
validar
↓
documentar
↓
só então avançar
```

---

# 2. Princípio de execução

O FluxMed será desenvolvido em **fatias verticais**.

Não fazer:

```text
todo o backend
↓
todo o frontend
```

Nem:

```text
todo o frontend com mocks
↓
tentar adaptar o backend depois
```

Fazer:

```text
domínio/contrato
↓
capacidade backend
↓
integração frontend
↓
teste real
↓
próxima capacidade
```

---

# 3. Regra de escopo

Toda nova ideia deve passar por este filtro:

```text
É requisito acadêmico?
    ↓ sim
entra

Melhora claramente a demonstração, qualidade ou portfólio?
    ↓ sim
avaliar

É necessária para uma feature já aprovada?
    ↓ sim
entra

Só prepara escala empresarial hipotética?
    ↓ sim
fica para futuro
```

---

# 4. Regra de início

A implementação só deve começar quando os documentos principais estiverem presentes:

```text
README.md
docs/PRODUCT_SPEC.md
docs/ARCHITECTURE.md
docs/DOMAIN_MODEL.md
docs/SANTA_AURORA_SPEC.md
docs/OPTIMIZATION_SPEC.md
docs/FRONTEND_SPEC.md
docs/API_SPEC.md
docs/LLM_SPEC.md
docs/TESTING_STRATEGY.md
docs/DEVELOPMENT_PLAN.md
docs/CODEX_INSTRUCTIONS.md
```

Antes disso:

```text
nenhum código de produto
```

---

# 5. Estratégia Git

Modelo:

```text
main
 ↑
Pull Request
 ↑
branch curta
```

Tipos de branch:

```text
feat/*
fix/*
test/*
docs/*
refactor/*
chore/*
```

---

# 6. Commits

Usar Conventional Commits.

Exemplos:

```text
feat: add operation creation flow
test: add route validator property tests
fix: prevent stale operation dispatch
docs: document city generation strategy
```

---

# 7. Regra para cada fase

Cada fase deve possuir:

1. branch própria;
2. escopo explícito;
3. implementação;
4. testes;
5. documentação atualizada quando necessário;
6. validação manual;
7. CI verde;
8. commit(s) coerentes;
9. PR;
10. merge somente após aceite.

---

# 8. Regra de não acumulação

Não iniciar uma nova fase grande se a anterior possuir:

- testes quebrados;
- TODO crítico;
- erro conhecido importante;
- contrato inconsistente;
- migration incompleta;
- fluxo principal quebrado.

---

# 9. Organização geral

A implementação oficial é dividida em:

```text
FASE 0  — Documentação
FASE 1  — Fundação do repositório
FASE 2  — Domínio base e infraestrutura mínima
FASE 3  — Autenticação e shell da aplicação
FASE 4  — Operações
FASE 5  — Santa Aurora base
FASE 6  — Endereços e facilities
FASE 7  — Entregas
FASE 8  — Frota e equipe
FASE 9  — Wizard completo e preflight
FASE 10 — Routing
FASE 11 — Baselines e GA básico
FASE 12 — Restrições avançadas, pruning e repair
FASE 13 — Team Assignment, validação e resultado
FASE 14 — Decision Trace, SSE e replay
FASE 15 — Relatórios
FASE 16 — Assistente IA
FASE 17 — Benchmarks e relatório acadêmico
FASE 18 — Polimento, segurança e resiliência
FASE 19 — Deploy, smoke e release final
```

---

# 10. FASE 0 — Documentação

## Branch

```text
docs/initial-specification
```

## Objetivo

Fechar toda a especificação antes do código.

## Entregáveis

```text
README.md
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

## Critério de aceite

- documentos coerentes entre si;
- nenhuma dependência de Lovable;
- stack definida;
- V1 definida;
- escopo futuro separado;
- ordem de desenvolvimento definida.

---

# 11. FASE 1 — Fundação do repositório

## Branch

```text
chore/project-foundation
```

## Objetivo

Criar a estrutura mínima do monorepo e garantir que frontend, backend e banco possam ser executados localmente.

## Criar

```text
apps/
├── api/
└── web/

docs/
data/
scripts/
tests/
.github/
infra/
```

Sem criar subpastas vazias desnecessárias.

---

# 12. Backend inicial

Criar:

```text
FastAPI app
pyproject.toml
src layout
pytest
lint/format/type-check
```

A API inicialmente precisa apenas de:

```text
GET /health/live
```

---

# 13. Frontend inicial

Criar:

```text
React
Vite
TypeScript
ESLint
Prettier
Vitest
```

Página inicial mínima:

```text
FluxMed
API status
```

---

# 14. Banco local

Criar:

```text
docker-compose.yml
```

com:

```text
PostgreSQL + PostGIS
```

---

# 15. Environment

Criar:

```text
.env.example
```

e garantir:

```text
.env
```

no `.gitignore`.

---

# 16. Developer commands

Desejável:

```text
make dev
make test
make lint
make typecheck
```

ou scripts equivalentes.

Não é obrigatório usar Make se houver alternativa simples e clara.

---

# 17. CI inicial

GitHub Actions:

```text
backend lint
backend tests
frontend lint
frontend tests
frontend build
```

---

# 18. Testes da Fase 1

Backend:

```text
health endpoint
```

Frontend:

```text
renders app shell
```

Builds:

```text
api imports correctly
web builds successfully
```

---

# 19. Aceite da Fase 1

Considerar concluída quando:

```text
docker compose up
```

inicia banco;

backend inicia;

frontend inicia;

`/health/live` responde;

testes básicos passam;

CI verde.

---

# 20. FASE 2 — Domínio base e persistência mínima

## Branch

```text
feat/domain-foundation
```

## Objetivo

Criar o núcleo de domínio sem ainda implementar otimização.

---

# 21. Criar enums base

Exemplos:

```text
UserRole
OperationStatus
DeliveryPriority
TimeWindowPolicy
TemperatureClass
HandlingRequirement
VehicleType
VehicleOwnershipType
WorkerRole
TrafficMode
```

---

# 22. Criar value objects

Prioridade:

```text
Money
Weight
Volume
Distance
Duration
TimeWindow
```

A implementação pode simplificar se tipos explícitos aumentarem complexidade sem benefício real.

Dinheiro deve permanecer Decimal.

---

# 23. Configurar SQLAlchemy

Criar:

- engine;
- session;
- metadata;
- base models;
- repositories mínimos.

---

# 24. Configurar Alembic

Primeira migration deve criar:

- extensão PostGIS;
- usuários;
- estrutura mínima de operação.

Não criar todas as tabelas do projeto em uma única migration antecipadamente.

---

# 25. Test database

Criar estratégia de integração com PostgreSQL/PostGIS real.

---

# 26. Testes da Fase 2

- migration from empty;
- database connection;
- basic repository;
- domain enum tests;
- money precision.

---

# 27. Aceite da Fase 2

- migrations funcionam;
- banco sobe do zero;
- testes de integração usam Postgres/PostGIS;
- domínio não importa FastAPI ou SQLAlchemy indevidamente.

---

# 28. FASE 3 — Autenticação e shell da aplicação

## Branch

```text
feat/auth-and-app-shell
```

## Objetivo

Criar primeira fatia vertical completa.

---

# 29. Backend

Implementar:

```text
User
Argon2id
login
logout
/me
RBAC
demo seed
```

Roles:

```text
ADMIN
PLANNER
```

---

# 30. Frontend

Implementar:

```text
/login
protected routes
sidebar
header
session handling
role-aware navigation
```

---

# 31. Navegação inicial

Sidebar:

```text
Operações
Entregas
Frota
Equipe
Relatórios
Assistente IA
Configurações [ADMIN]
```

Páginas ainda não implementadas podem mostrar estado claro:

```text
Em desenvolvimento
```

sem mocks elaborados.

---

# 32. Testes da Fase 3

Backend:

- login válido;
- senha inválida;
- usuário inativo;
- role.

Frontend:

- login;
- protected route;
- logout;
- sidebar role.

E2E:

```text
login demo
→ operations page
```

---

# 33. Aceite da Fase 3

Usuário demo consegue:

```text
entrar
→ ver shell
→ sair
```

com sessão real backend.

---

# 34. FASE 4 — Operações

## Branch

```text
feat/operations
```

## Objetivo

Criar operações reais persistidas e primeira feature operacional útil.

---

# 35. Backend

Implementar:

```text
Operation
OperationRevision
operation_code
state transitions
CRUD necessário
```

Endpoints:

```text
GET /operations
POST /operations
GET /operations/{id}
PATCH /operations/{id}
```

---

# 36. Frontend

Implementar:

```text
/operations
/operations/new
/operations/:id
```

Ainda sem wizard completo.

Nova operação inicialmente recebe:

- data;
- horários;
- cidade placeholder configurada;
- trânsito.

---

# 37. Testes da Fase 4

- create;
- list;
- detail;
- update;
- invalid operation end time;
- dispatched immutable, quando estado já existir;
- UI create flow.

---

# 38. Aceite da Fase 4

Usuário consegue:

```text
criar operação
→ salvar no PostgreSQL
→ reabrir no frontend
```

sem mock.

---

# 39. FASE 5 — Santa Aurora base

## Branch

```text
feat/santa-aurora-base
```

## Objetivo

Criar a cidade mínima roteável e visualizável.

---

# 40. Implementação inicial da cidade

Criar:

```text
City
District
Intersection
Street
RoadSegment
river
bridges
major roads
depot
```

---

# 41. Gerador determinístico

Criar:

```text
scripts/generate_santa_aurora.py
```

com:

```text
seed
generator_version
dataset_version
```

---

# 42. Escopo inicial da geração

Nesta fase:

- 9 bairros;
- rio;
- pontes;
- anel viário;
- arteriais;
- coletores;
- ruas principais;
- grafo conectado;
- depot.

Ainda não é necessário gerar dezenas de milhares de endereços.

---

# 43. API

Criar:

```text
GET /cities
GET /cities/{id}
GET /cities/{id}/districts
GET /cities/{id}/map
```

---

# 44. Frontend

Integrar MapLibre.

Mostrar:

- bairros;
- rio;
- ruas;
- pontes;
- depot.

---

# 45. Testes da Fase 5

- determinismo;
- geometry validity;
- graph connectivity;
- depot exists;
- bridges connect;
- map GeoJSON valid.

---

# 46. Aceite da Fase 5

Abrir FluxMed e ver Santa Aurora real gerada pelo backend no MapLibre.

---

# 47. FASE 6 — Endereços e facilities

## Branch

```text
feat/city-addresses-facilities
```

## Objetivo

Completar a cidade necessária para entregas reais.

---

# 48. Implementar

```text
Lot
Building
Address
Facility
StreetNamingService
catalogs
```

---

# 49. Gerar

Meta:

```text
~150 streets
20k–40k valid addresses
~40–60 facilities
```

A meta é aproximada.

---

# 50. Facilities

Gerar:

- hospital;
- clinic;
- laboratory;
- pharmacy;
- warehouse;
- depot;
- public facilities.

---

# 51. Address search

Backend:

```text
GET /cities/{id}/addresses/search
```

Frontend:

autocomplete real.

---

# 52. Validação

Criar:

```text
scripts/validate_city.py
```

---

# 53. Testes da Fase 6

- address exists only with building;
- address → road segment;
- no river addresses;
- normalized street uniqueness;
- fuzzy search;
- nearest number suggestion;
- facilities reachable.

---

# 54. Aceite da Fase 6

Usuário consegue pesquisar:

```text
Rua + número
```

e localizar um endereço realmente existente no mapa.

---

# 55. FASE 7 — Entregas

## Branch

```text
feat/deliveries
```

## Objetivo

Implementar Delivery completa.

---

# 56. Backend

Implementar:

```text
Delivery
manual create
edit
list
delete when allowed
ServiceTimeEstimator
address validation
```

---

# 57. Frontend

Implementar:

```text
/deliveries
manual delivery form
filters
delivery detail
```

---

# 58. Scenario Generator — versão inicial

Implementar geração:

```text
NORMAL
20 deliveries
```

primeiro.

Depois expandir para:

```text
BUSY
HIGH_PRESSURE
EMERGENCY
40/60/80
```

---

# 59. XLSX/CSV import

Implementar:

```text
parse
validate
review
confirm
```

Pode ser concluído nesta fase ou no final dela.

---

# 60. Testes da Fase 7

- delivery invariants;
- address validation;
- service time;
- scenario determinism;
- import validation;
- no silent address approximation.

---

# 61. Aceite da Fase 7

Operação consegue receber deliveries por:

```text
manual
scenario
import
```

com endereços reais.

---

# 62. FASE 8 — Frota e equipe

## Branch

```text
feat/fleet-workforce
```

## Objetivo

Criar recursos operacionais reais.

---

# 63. Fleet

Implementar:

```text
Vehicle
OWNED
AGGREGATED
cost profiles
maintenance
autonomy
refrigeration
helper policy
```

---

# 64. Workforce

Implementar:

```text
Worker
roles
engagement
compensation
availability
```

---

# 65. Frontend

Implementar:

```text
/fleet
/workforce
CRUD
deactivation
cost views
```

---

# 66. Operation resource selection

Implementar:

```text
GET /operations/{id}/resources
PUT /operations/{id}/resources
```

---

# 67. Testes da Fase 8

- vehicle cost;
- aggregated inclusion flags;
- worker compensation;
- deactivation/history;
- operation resource selection.

---

# 68. Aceite da Fase 8

Usuário consegue:

```text
cadastrar
→ selecionar
→ remover da operação
```

veículos e equipe.

---

# 69. FASE 9 — Wizard completo e preflight

## Branch

```text
feat/operation-wizard
```

## Objetivo

Fechar experiência de preparação da operação antes do optimizer.

---

# 70. Wizard

Implementar:

```text
Configuração
Entregas
Recursos
Revisão
```

---

# 71. PreflightValidator

Criar validações:

- nenhuma delivery;
- nenhum vehicle;
- refrigeration impossible;
- capacity impossible individual;
- range obvious impossible;
- team impossible;
- invalid address;
- operation window invalid.

---

# 72. API

```text
POST /operations/{id}/validate
```

---

# 73. Frontend

Mostrar:

```text
blocking errors
warnings
summary
```

Botão `Otimizar rotas` só habilitado quando válido.

---

# 74. Testes da Fase 9

- each blocking rule;
- warnings;
- UI wizard navigation;
- invalid plan blocks optimize.

---

# 75. Aceite da Fase 9

Usuário consegue preparar uma operação completa e receber validação real.

---

# 76. FASE 10 — Routing

## Branch

```text
feat/routing-engine
```

## Objetivo

Criar roteamento real sobre Santa Aurora.

---

# 77. Implementar

```text
directed graph
Dijkstra
A*
travel time
traffic
closures
time buckets
cache
```

---

# 78. Traffic profiles

Implementar:

```text
AUTOMATIC
FREE
CUSTOM
```

---

# 79. Road overrides

Backend:

```text
closure
traffic override
```

Frontend:

seleção no mapa.

---

# 80. Route path

API interna deve conseguir responder:

```text
depot → address
```

com:

- geometry;
- distance;
- travel time.

---

# 81. Testes da Fase 10

- one-way;
- closure;
- bridge closure;
- traffic;
- time bucket;
- no-path;
- route return.

---

# 82. Aceite da Fase 10

No mapa:

```text
selecionar origem/destino
→ visualizar caminho real
```

e uma interdição altera esse caminho.

---

# 83. FASE 11 — Baselines e GA básico

## Branch

```text
feat/genetic-optimizer-core
```

## Objetivo

Criar primeiro motor de otimização real.

---

# 84. Implementar primeiro baselines

```text
Nearest Neighbor
Best Insertion
```

Antes do GA.

---

# 85. GA básico

Implementar:

```text
global permutation chromosome
RouteDecoder
FitnessVector
Tournament Selection
OX
Swap
Insertion
Inversion
elitism
initial population
basic stopping
```

---

# 86. Escopo inicial

Primeiro fazer funcionar para:

```text
NORMAL
20 deliveries
weight/volume
multiple vehicles
return to depot
```

Depois ampliar restrições.

---

# 87. SolutionValidator — versão inicial

Implementar desde já:

- delivery uniqueness;
- all deliveries;
- weight;
- volume;
- depot return.

---

# 88. Testes da Fase 11

- OX properties;
- mutation properties;
- fitness order;
- decoder;
- validator;
- deterministic seed;
- baseline comparison.

---

# 89. Aceite da Fase 11

Backend consegue:

```text
operation
→ GA
→ valid multi-vehicle route plan
```

Frontend pode inicialmente mostrar resultado simples.

---

# 90. FASE 12 — Restrições avançadas, pruning e repair

## Branch

```text
feat/optimizer-constraints-pruning
```

## Objetivo

Completar o valor acadêmico e operacional do GA.

---

# 91. Adicionar constraints

```text
range
refrigeration
HARD windows
SOFT windows
service time
end of operation
scarce resource preservation
```

---

# 92. Pruning

Implementar:

```text
eligibility
hard constraints
future feasibility
dominance
safe lower bound
```

progressivamente.

---

# 93. Repair

Implementar apenas repairs comprovadamente úteis.

---

# 94. Diversity

Adicionar:

```text
diversity metric
adaptive mutation
controlled immigrants
```

---

# 95. Stopping

Adicionar:

```text
stagnation
time budget
hard limit
max generations
```

---

# 96. Testes da Fase 12

Muito fortes em:

- pruning correctness;
- hard windows;
- range;
- refrigeration;
- repair;
- adaptive mutation;
- timeout.

---

# 97. Aceite da Fase 12

GA encontra soluções válidas para cenários:

```text
NORMAL
BUSY
HIGH_PRESSURE
EMERGENCY
```

em tamanhos razoáveis.

---

# 98. FASE 13 — Team Assignment, validação final e resultado

## Branch

```text
feat/team-assignment-results
```

## Objetivo

Transformar solução algorítmica em plano operacional completo.

---

# 99. TeamAssignmentSolver

Implementar:

- drivers;
- motorcycle couriers;
- helpers;
- REQUIRED;
- OPTIONAL;
- NOT_NEEDED;
- cost minimum.

---

# 100. SolutionValidator final

Adicionar:

- team;
- range;
- refrigeration;
- HARD windows;
- shift end;
- route continuity;
- road access.

---

# 101. Cost Engine final

Consolidar:

- fuel;
- depreciation;
- maintenance;
- fixed time;
- team;
- aggregated contract.

---

# 102. Result API

Criar:

```text
GET /optimization-runs/{id}/result
GET /routes/{id}
```

---

# 103. Result UI

Implementar:

- KPI header;
- route colors;
- legend;
- inspector;
- stops;
- costs;
- utilization;
- team;
- approve.

---

# 104. Manual team simulation

Implementar:

```text
simulate
apply
revalidate
```

---

# 105. Testes da Fase 13

- team matching;
- helper optional;
- full validator;
- cost breakdown;
- result API;
- result frontend.

---

# 106. Aceite da Fase 13

Usuário consegue:

```text
otimizar
→ analisar mapa final
→ entender veículo/equipe/custo
→ aprovar
```

---

# 107. FASE 14 — Decision Trace, SSE e replay

## Branch

```text
feat/optimization-trace
```

## Objetivo

Criar experiência ao vivo e explicabilidade técnica.

---

# 108. OptimizationRun

Completar estados:

```text
QUEUED
RUNNING
COMPLETED
FAILED
CANCELLED
INTERRUPTED
```

---

# 109. SSE

Implementar:

```text
optimization_started
generation_snapshot
best_solution_updated
pruning_summary
optimization_completed
optimization_failed
```

---

# 110. Decision Trace

Persistir:

- snapshots;
- improvements;
- pruning summaries;
- route changes;
- selection reasons;
- final comparison.

---

# 111. Frontend live view

Mostrar:

- generation;
- elapsed;
- cost;
- makespan;
- diversity;
- mutation;
- pruning;
- map changes;
- convergence.

---

# 112. Replay

Usar trace persistido.

Não recalcular GA.

---

# 113. Cancel/reconnect

Implementar:

- cancel;
- SSE reconnect;
- recovery via run status.

---

# 114. Testes da Fase 14

- SSE schema;
- reconnection;
- cancel;
- trace ordering;
- replay;
- interrupted run.

---

# 115. Aceite da Fase 14

Usuário vê o cálculo real acontecendo e consegue reproduzir o processo depois.

---

# 116. FASE 15 — Relatórios

## Branch

```text
feat/reports
```

## Objetivo

Gerar artefatos profissionais da operação.

---

# 117. Implementar

```text
PDF
XLSX
CSV
```

---

# 118. XLSX

Abas:

```text
Resumo
Rotas
Entregas
Veículos
Equipe
Custos
```

---

# 119. PDF

Conteúdo:

- operação;
- resumo;
- métricas;
- rotas;
- equipe;
- custos;
- conclusões.

---

# 120. Snapshot

Relatórios de dispatch devem usar snapshot imutável.

---

# 121. Frontend

Tela:

```text
/reports
```

e ações dentro da operação.

---

# 122. Testes da Fase 15

- file generation;
- XLSX sheets;
- PDF content;
- history snapshot;
- failure retry.

---

# 123. Aceite da Fase 15

Usuário consegue gerar PDF/XLSX confiáveis da operação.

---

# 124. FASE 16 — Assistente IA

## Branch

```text
feat/llm-assistant
```

## Objetivo

Cumprir requisitos acadêmicos de LLM sem permitir autonomia insegura.

---

# 125. Ordem interna

```text
LLMProvider
MockLLMProvider
tool registry
read tools
AssistantService
CohereProvider
chat UI
generation tools
simulation tools
GeminiProvider
evals
```

---

# 126. Primeiro caso

Começar por:

```text
"Qual o custo total da operação?"
```

Tool:

```text
get_operation_summary
```

---

# 127. Depois

Adicionar:

- why vehicle;
- why helper;
- critical risk;
- driver instructions;
- daily report;
- executive summary.

---

# 128. Simulation tools

Adicionar depois que read tools estiverem estáveis.

---

# 129. Frontend Assistant

Implementar:

```text
/assistant
context selector
chat
suggested questions
structured simulations
degraded state
```

---

# 130. Testes da Fase 16

- Mock provider;
- tool authorization;
- factuality;
- no hallucination;
- confirmation;
- prompt injection;
- degraded mode;
- real provider manual eval.

---

# 131. Aceite da Fase 16

Demo deve provar:

1. pergunta factual;
2. explicação;
3. instrução;
4. relatório;
5. sugestão/simulação.

---

# 132. FASE 17 — Benchmarks e evidências acadêmicas

## Branch

```text
feat/academic-benchmarks
```

## Objetivo

Produzir evidência reproduzível para relatório e vídeo.

---

# 133. Scripts

Criar:

```text
scripts/benchmark_optimizer.py
```

e estrutura:

```text
benchmarks/
├── scenarios/
├── algorithms/
├── results/
└── notebooks/
```

---

# 134. Algoritmos comparados

```text
Nearest Neighbor
Best Insertion
GA basic
GA + pruning
GA + pruning + repair
```

---

# 135. Cenários

Combinar:

```text
NORMAL
BUSY
HIGH_PRESSURE
EMERGENCY
```

com:

```text
20
40
60
80
```

sem obrigação de executar toda matriz em toda rodada se custo ficar alto.

---

# 136. Repetições

GA deve executar múltiplas vezes por cenário.

Salvar:

```text
best
mean
std
worst
runtime
```

---

# 137. Métricas

Primárias:

```text
feasibility
hard violations
cost
makespan
runtime
```

Secundárias:

```text
distance
vehicles
on-time
utilization
pruning
evaluations
time-to-best
```

---

# 138. Gráficos

Gerar:

- convergence;
- method cost;
- runtime;
- pruning impact;
- scale impact.

---

# 139. Aceite da Fase 17

Resultados reproduzíveis e utilizáveis diretamente no relatório técnico.

---

# 140. FASE 18 — Polimento, segurança e resiliência

## Branch

```text
chore/v1-hardening
```

## Objetivo

Tornar a V1 demonstrável com segurança e estabilidade.

---

# 141. Frontend polish

Revisar:

- spacing;
- typography;
- table density;
- map behavior;
- responsive;
- loading;
- error;
- empty state;
- accessibility;
- route colors.

---

# 142. Backend hardening

Revisar:

- error taxonomy;
- transactions;
- idempotency;
- audit log;
- rate limit;
- redaction;
- health checks;
- logging.

---

# 143. Resilience

Testar:

- LLM down;
- DB down;
- report failure;
- SSE disconnect;
- optimizer failure;
- validation mismatch.

---

# 144. Security

Ativar:

- secret scanning;
- dependency scanning;
- CodeQL/SAST;
- upload validation.

---

# 145. E2E completo

Revalidar jornadas:

```text
login
operation
scenario/import
resources
closure
optimization
result
assistant
report
dispatch
```

---

# 146. Aceite da Fase 18

Sem bugs conhecidos bloqueantes e todos os fluxos de apresentação estáveis.

---

# 147. FASE 19 — Deploy e release final

## Branch

```text
chore/v1-release
```

## Objetivo

Disponibilizar V1 demonstrável e congelar entrega acadêmica.

---

# 148. Deploy alvo

```text
Frontend → Vercel
Backend  → Vercel
Database → Neon/PostGIS
```

Caso benchmark mostre limitação real no backend:

documentar e mover somente o backend para host Python apropriado.

Não mudar infraestrutura sem necessidade medida.

---

# 149. Production setup

Configurar:

- env vars;
- DB migration;
- seed demo;
- Santa Aurora;
- demo users;
- CORS;
- health;
- LLM provider;
- Sentry quando configurado.

---

# 150. Smoke pós-deploy

Executar:

```text
frontend
login
operations
city
create operation
scenario small
optimize small
result
assistant
report
```

---

# 151. Release

Criar tag:

```text
v1.0.0
```

Release notes com:

- escopo;
- requisitos;
- limitações;
- demo;
- documentação.

---

# 152. Critério de aceite final

Antes da entrega:

```text
CI green
E2E green
city validation green
optimizer regression green
benchmarks executed
LLM eval executed
security checks green
production smoke green
```

---

# 153. Ordem de prioridade em caso de atraso

Se o cronograma apertar, preservar nesta ordem:

```text
1. requisitos obrigatórios do Tech Challenge
2. GA correto
3. múltiplos veículos e constraints
4. mapa
5. LLM obrigatória
6. testes
7. relatório
8. visual polish
9. features adicionais
```

---

# 154. Features que podem ser simplificadas primeiro

Se necessário:

- quantidade de visualizações secundárias;
- visual regression;
- weekly report avançado;
- settings muito detalhadas;
- replay sofisticado;
- load test amplo.

---

# 155. Features que não devem ser removidas

Não remover:

- GA;
- selection;
- crossover;
- mutation;
- multiple vehicles;
- capacity;
- autonomy;
- priority;
- map;
- LLM;
- tests;
- technical documentation.

Esses elementos fazem parte do valor central e/ou requisitos acadêmicos.

---

# 156. Regra de vertical slice

Ao concluir uma capacidade, ela deve existir de ponta a ponta.

Exemplo:

```text
Create Operation
```

não significa apenas tabela no banco.

Significa:

```text
domain
+
migration
+
repository
+
application use case
+
endpoint
+
frontend
+
tests
```

---

# 157. Regra de mocks

Mocks podem existir temporariamente quando:

- backend da mesma fatia ainda está em construção;
- teste exige provider fake;
- LLM paga não deve ser chamada.

Mocks não podem se tornar fonte de verdade da aplicação final.

---

# 158. Regra de refactor

Refatorar quando houver:

- duplicação real;
- fronteira ruim;
- dificuldade de teste;
- acoplamento;
- código difícil de entender.

Não fazer “grande refactor arquitetural” apenas por estética.

---

# 159. Regra de dependências

Antes de instalar biblioteca:

```text
qual problema ela resolve?
é necessária?
há alternativa nativa simples?
é mantida?
```

---

# 160. Regra de documentação durante desenvolvimento

Atualizar docs quando mudar:

- arquitetura;
- domínio;
- API;
- GA;
- escopo;
- fluxo principal.

Não permitir que documentação vire registro histórico obsoleto.

---

# 161. ADRs

Criar ADR apenas para decisões arquiteturais relevantes.

Exemplo:

```text
use-postgis
use-sse
use-indirect-ga
use-lexicographic-fitness
```

---

# 162. Regra de benchmark antes de otimização prematura

Não otimizar performance baseado em suposição.

Fluxo:

```text
measure
↓
identify bottleneck
↓
optimize
↓
measure again
```

---

# 163. Regra de segurança algorítmica

Toda solução:

```text
GA
↓
TeamAssignment
↓
SolutionValidator
↓
persist/display
```

Nunca:

```text
GA
↓
display directly
```

---

# 164. Regra de frontend durante GA

Não simular atividade falsa.

Se backend ainda não envia trace:

mostrar estado real simples.

Depois adicionar animação quando eventos existirem.

---

# 165. Regra de LLM

Não integrar IA antes que os dados que ela precisa estejam estruturados.

A LLM entra depois de:

```text
operations
routes
costs
trace
reports data
```

---

# 166. Regra de relatório

Não gerar relatório final antes que snapshot e métricas estejam estáveis.

---

# 167. Regra de deploy

Deploy cedo pode acontecer para validar infraestrutura.

Mas a release final só acontece após hardening.

---

# 168. Checklist antes de cada PR

```text
[ ] escopo da branch está claro
[ ] docs relevantes foram lidas
[ ] código compila
[ ] lint passa
[ ] type-check passa
[ ] testes passam
[ ] nenhuma secret foi adicionada
[ ] migration foi revisada
[ ] contratos foram atualizados
[ ] nenhum TODO crítico foi escondido
[ ] comportamento foi validado manualmente
```

---

# 169. Checklist antes de merge

```text
[ ] CI verde
[ ] PR descreve o que mudou
[ ] riscos conhecidos documentados
[ ] screenshots quando mudança visual for relevante
[ ] benchmark quando mudança afetar optimizer
[ ] docs atualizadas quando necessário
```

---

# 170. Checklist antes de avançar de fase

```text
[ ] critério de aceite da fase cumprido
[ ] sistema executável
[ ] testes essenciais existem
[ ] bugs bloqueantes corrigidos
[ ] documentação alinhada
[ ] branch merged
[ ] main está estável
```

---

# 171. Definition of Done global

O FluxMed V1 estará pronto quando for possível demonstrar, do zero:

```text
1. login
2. Santa Aurora
3. nova operação
4. entregas
5. frota/equipe
6. validação
7. interdição/trânsito
8. otimização real
9. animação/trace
10. resultado validado
11. custos/equipe
12. aprovação/dispatch
13. relatório
14. Assistente IA
15. benchmarks
```

com testes e documentação.

---

# 172. Sequência visual resumida

```text
DOCUMENTAÇÃO
      ↓
FUNDAÇÃO
      ↓
AUTH
      ↓
OPERAÇÕES
      ↓
SANTA AURORA
      ↓
ENDEREÇOS
      ↓
ENTREGAS
      ↓
FROTA + EQUIPE
      ↓
WIZARD + PREFLIGHT
      ↓
ROUTING
      ↓
GA BÁSICO
      ↓
PRUNING + REPAIR
      ↓
TEAM + VALIDATOR
      ↓
RESULTADO
      ↓
SSE + TRACE + REPLAY
      ↓
RELATÓRIOS
      ↓
LLM
      ↓
BENCHMARKS
      ↓
HARDENING
      ↓
DEPLOY
      ↓
v1.0.0
```

---

# 173. Regra final

> O desenvolvimento do FluxMed deve avançar de forma incremental, mantendo o sistema executável e confiável em cada etapa.

O objetivo não é escrever a maior quantidade de código possível.

O objetivo é chegar à V1 com:

- domínio correto;
- algoritmo defensável;
- mapa funcional;
- UX convincente;
- LLM útil;
- testes fortes;
- evidência acadêmica;
- documentação coerente.
