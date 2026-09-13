# FluxMed — Codex Instructions

**Documento:** `docs/CODEX_INSTRUCTIONS.md`  
**Status:** Manual operacional oficial para o agente de desenvolvimento  
**Projeto:** FluxMed — Planejamento Inteligente de Rotas Médicas  
**Responsável pela implementação:** Codex  
**Estratégia:** desenvolvimento incremental em fatias verticais  
**Regra principal:** não implementar além do escopo aprovado sem atualizar a documentação

---

# 1. Objetivo deste documento

Este documento define **como o Codex deve trabalhar dentro do repositório FluxMed**.

Ele não descreve o produto em si.  
Ele descreve o comportamento esperado do agente ao:

- ler a documentação;
- planejar uma tarefa;
- criar branches;
- implementar;
- testar;
- corrigir;
- documentar;
- reportar resultados;
- decidir quando parar;
- lidar com ambiguidades;
- evitar overengineering.

Este arquivo deve ser lido antes do início da implementação e consultado durante todo o projeto.

---

# 2. Fonte de verdade

A documentação oficial do FluxMed deve ser lida nesta ordem:

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

Não implementar uma feature relevante sem consultar os documentos relacionados.

---

# 3. Prioridade entre documentos

Cada documento possui uma responsabilidade.

```text
PRODUCT_SPEC
→ o que o produto deve fazer

ARCHITECTURE
→ como o sistema é dividido

DOMAIN_MODEL
→ entidades, invariantes e relações

SANTA_AURORA_SPEC
→ cidade sintética

OPTIMIZATION_SPEC
→ routing, GA, pruning, repair e validação

FRONTEND_SPEC
→ UX e telas

API_SPEC
→ contrato HTTP

LLM_SPEC
→ integração com IA

TESTING_STRATEGY
→ qualidade e testes

DEVELOPMENT_PLAN
→ ordem de implementação

CODEX_INSTRUCTIONS
→ forma de trabalho do agente
```

---

# 4. Em caso de conflito

Se dois documentos parecerem contraditórios:

```text
NÃO escolher silenciosamente uma interpretação
```

Fazer:

1. identificar a divergência;
2. apontar os documentos envolvidos;
3. propor a interpretação mais coerente;
4. solicitar decisão humana quando necessário;
5. atualizar a documentação antes ou junto da implementação.

---

# 5. Não inventar requisitos

O Codex não deve criar funcionalidades relevantes apenas porque parecem interessantes.

Exemplos de coisas que **não devem aparecer espontaneamente**:

```text
Kafka
RabbitMQ
Redis obrigatório
Celery obrigatório
microserviços
Kubernetes
GraphQL
multi-tenant SaaS
pagamentos
GPS real
app de motorista
telemetria real
múltiplos depósitos
OpenStreetMap na V1
```

Se não estiver aprovado na documentação:

```text
não implementar
```

---

# 6. Filosofia de desenvolvimento

O FluxMed deve ser:

```text
profissional
+
testável
+
explicável
+
reproduzível
```

sem se tornar:

```text
enterprise por aparência
```

Antes de adicionar complexidade, perguntar:

> Este componente resolve um problema real da V1?

Se não:

```text
não adicionar
```

---

# 7. Estratégia oficial

Desenvolver em **fatias verticais**.

Não fazer:

```text
backend inteiro primeiro
```

nem:

```text
frontend inteiro com mocks primeiro
```

Fazer:

```text
capacidade de domínio
+
persistência
+
API
+
frontend
+
testes
```

sempre que a fase permitir.

---

# 8. Seguir DEVELOPMENT_PLAN.md

`docs/DEVELOPMENT_PLAN.md` define a ordem oficial.

O Codex não deve pular fases grandes sem motivo aprovado.

Exemplo:

```text
não implementar Assistente IA
antes de operações, rotas e métricas existirem
```

---

# 9. Uma fase por vez

Ao receber instrução para implementar uma fase:

1. ler a fase;
2. ler documentos relacionados;
3. inspecionar estado atual do repositório;
4. verificar branch atual;
5. planejar;
6. implementar;
7. testar;
8. corrigir;
9. validar;
10. reportar.

Não iniciar a fase seguinte automaticamente.

---

# 10. Branches

Usar branches curtas.

Padrões:

```text
feat/*
fix/*
test/*
docs/*
refactor/*
chore/*
```

Exemplos:

```text
chore/project-foundation
feat/auth-and-app-shell
feat/operations
feat/santa-aurora-base
feat/routing-engine
feat/genetic-optimizer-core
```

---

# 11. main

Evitar implementar diretamente em:

```text
main
```

A menos que o usuário autorize explicitamente.

---

# 12. Antes de criar uma branch

Verificar:

```text
git status
git branch --show-current
```

Se houver mudanças não relacionadas:

```text
não sobrescrever
não descartar
```

Primeiro identificar a origem.

---

# 13. Worktree sujo

Se o repositório tiver mudanças existentes:

- preservar;
- inspecionar;
- não usar `git reset --hard`;
- não usar `git clean -fd` sem autorização;
- não sobrescrever trabalho humano.

---

# 14. Commits

Usar Conventional Commits.

Exemplos:

```text
feat: add Santa Aurora road graph
fix: reject stale operation dispatch
test: add optimizer permutation properties
docs: update API contract
refactor: isolate travel time service
```

---

# 15. Escopo de commit

Preferir commits coerentes.

Não criar um único commit com:

```text
auth
+
map
+
optimizer
+
reports
```

sem relação direta.

---

# 16. Não reescrever histórico

Não usar:

```text
git push --force
rebase destrutivo
reset --hard
```

sem pedido explícito.

---

# 17. Antes de implementar

O Codex deve responder internamente a estas perguntas:

```text
Qual fase estou implementando?
Qual documento define esta feature?
Qual comportamento é obrigatório?
Quais invariantes preciso preservar?
Quais testes precisam existir?
Qual é o critério de aceite?
```

---

# 18. Plano curto antes da alteração

Para tarefas relevantes, formular um plano objetivo.

Exemplo:

```text
1. criar entidades
2. migration
3. repository/use case
4. endpoint
5. frontend
6. tests
```

Evitar planos de 40 passos quando 6 resolvem.

---

# 19. Inspecionar antes de editar

Nunca assumir estrutura de arquivo.

Antes:

```text
listar arquivos
abrir arquivos relevantes
buscar símbolos
ver testes existentes
```

Depois editar.

---

# 20. Não duplicar implementação

Antes de criar:

```text
CostService
RouteDecoder
AddressResolver
```

buscar se algo equivalente já existe.

Reutilizar quando adequado.

---

# 21. Não criar abstração prematura

Evitar:

```text
interfaces
factories
managers
handlers
providers
```

sem necessidade real.

Abstrações justificadas no FluxMed incluem:

```text
LLMProvider
CityProvider
OptimizationEngine
Repositories
```

porque existem fronteiras reais.

---

# 22. Backend

Stack oficial:

```text
Python
FastAPI
Pydantic
SQLAlchemy
Alembic
PostgreSQL
PostGIS
```

Não substituir por outra stack sem decisão explícita.

---

# 23. Frontend

Stack oficial:

```text
React
Vite
TypeScript
MapLibre GL
Vitest
React Testing Library
Playwright
```

Não usar Lovable.

Não migrar para Next.js por conveniência.

---

# 24. Banco

Fonte de verdade:

```text
PostgreSQL + PostGIS
```

Não usar SQLite como banco oficial.

SQLite pode aparecer apenas em testes isolados que não dependam do comportamento PostgreSQL/PostGIS, se houver benefício real.

---

# 25. Domínio independente

O diretório de domínio não deve importar:

```text
fastapi
sqlalchemy
cohere
google generative ai sdk
React
```

Architecture tests devem proteger isso.

---

# 26. Regras críticas no backend

Nunca colocar autoridade de negócio apenas no frontend.

Exemplos:

```text
capacidade
autonomia
HARD window
refrigeração
custo
fitness
dispatch
validação de solução
```

devem ser validados pelo backend.

---

# 27. Frontend não calcula verdade operacional

O frontend pode:

```text
formatar
filtrar
ordenar
renderizar
animar
```

Não pode produzir o valor oficial de:

```text
route cost
route feasibility
fitness
vehicle eligibility
```

---

# 28. OpenAPI como contrato

Quando API e frontend existirem:

```text
FastAPI
→ OpenAPI
→ TypeScript client
```

Evitar copiar manualmente dezenas de interfaces.

---

# 29. Cliente gerado

Não editar manualmente arquivos gerados.

Se precisar adaptar comportamento:

```text
wrapper/service
```

em volta do client.

---

# 30. Migrations

Toda mudança de schema:

```text
Alembic migration
```

Não editar banco manualmente como solução permanente.

---

# 31. Migration review

Antes de concluir:

- ler migration gerada;
- confirmar constraints;
- confirmar nullable;
- confirmar indexes quando relevantes;
- confirmar PostGIS types.

---

# 32. Seeds

Seed não é migration.

Separar:

```text
migration
```

de:

```text
demo seed
city generation
```

---

# 33. Dinheiro

Usar:

```text
Decimal
```

ou centavos inteiros.

Nunca usar `float` como fonte oficial de valores financeiros.

---

# 34. Unidades

Campos devem ser explícitos.

Exemplos:

```text
weight_kg
volume_m3
distance_km
length_m
duration_minutes
elapsed_ms
```

---

# 35. IDs

Usar UUID para identidade técnica.

Códigos humanos continuam separados:

```text
OP-20260913-001
DLV-NF45872-001
```

---

# 36. Datas e timezone

Usar ISO 8601 na API.

Cidade possui timezone.

Não usar horário local implícito de máquina como verdade operacional.

---

# 37. Santa Aurora

Seguir integralmente:

```text
docs/SANTA_AURORA_SPEC.md
```

A cidade deve ser:

```text
determinística
versionada
validada
```

---

# 38. Não hardcode Santa Aurora no core

O optimizer, deliveries e operations não devem depender de:

```text
if city == "Santa Aurora"
```

---

# 39. Gerador da cidade

Mesma combinação de:

```text
generator version
catalog version
seed
```

deve gerar o mesmo dataset.

---

# 40. Validação da cidade

Não persistir cidade defeituosa como oficial.

Fluxo:

```text
generate
→ validate
→ persist
```

---

# 41. Routing

Separação obrigatória:

```text
Routing
→ caminho urbano A → B

Optimization
→ atribuição e ordem das deliveries
```

---

# 42. Não usar distância euclidiana como rota oficial

Distância euclidiana pode ser usada apenas como:

- heurística auxiliar;
- lower bound seguro quando matematicamente válido;
- visual/debug.

A rota final usa grafo viário.

---

# 43. Algoritmo genético

Seguir:

```text
docs/OPTIMIZATION_SPEC.md
```

Representação oficial:

```text
permutação global de deliveries
```

---

# 44. Operadores oficiais

```text
Tournament Selection
Order Crossover
Swap Mutation
Insertion Mutation
Inversion Mutation
```

Mudança exige justificativa e documentação.

---

# 45. Fitness

Fitness é lexicográfica.

Não substituir por soma arbitrária de pesos sem decisão explícita.

---

# 46. Pruning

Regra:

> só podar definitivamente quando houver justificativa segura.

Se for apenas preferência heurística:

```text
reordenar
```

não:

```text
eliminar
```

---

# 47. Repair

Repair deve preservar:

- unicidade;
- completude;
- regras HARD.

Todo repair relevante precisa de teste.

---

# 48. SolutionValidator

Regra absoluta:

```text
GA
→ Team Assignment
→ SolutionValidator
→ persist/display
```

Nunca exibir solução final sem validator.

---

# 49. Divergência entre GA e validator

Se:

```text
GA = valid
validator = invalid
```

tratar como bug crítico.

Não contornar.

---

# 50. Team Assignment

Não colocar Worker no cromossomo.

Usar solver determinístico separado.

---

# 51. Decision Trace

Persistir fatos estruturados.

Não persistir “pensamento interno”.

Eventos:

```text
GenerationSnapshot
PruningSummary
ImprovementEvent
VehicleSelectionReason
RouteAssignmentChange
ConstraintViolation
FinalComparison
```

---

# 52. SSE

Usar SSE para progresso.

Não adicionar WebSocket apenas por preferência técnica.

---

# 53. Não streamar população inteira

Transmitir:

- snapshots;
- best-so-far;
- pruning agregado;
- mudanças relevantes.

---

# 54. LLM

Seguir:

```text
docs/LLM_SPEC.md
```

Regra absoluta:

```text
LLM != solver
```

---

# 55. LLM não calcula fatos oficiais

Não usar resposta do modelo como fonte para:

```text
cost
ETA
fitness
validity
distance
capacity
route
```

---

# 56. Tool calling

LLM acessa dados por tools controladas.

Nunca:

```text
LLM → SQL livre
```

---

# 57. Alterações sugeridas pela LLM

Fluxo:

```text
suggest
→ simulate
→ validate
→ show impact
→ human confirmation
→ apply
```

---

# 58. Segurança de secrets

Nunca versionar:

```text
.env
API key
password
private token
database credential
```

---

# 59. Antes de commit

Buscar secrets acidentais.

Se encontrar:

- remover;
- não apenas adicionar ao `.gitignore` depois de commit;
- avisar se o secret já tiver sido versionado.

---

# 60. Dependências

Antes de instalar pacote novo, verificar:

```text
é necessário?
é mantido?
resolve problema real?
há alternativa nativa simples?
```

---

# 61. Lock files

Manter lock files consistentes conforme gerenciadores escolhidos.

Não apagar lock apenas para resolver conflito sem entender causa.

---

# 62. Testes são parte da implementação

Não implementar feature e “deixar testes para depois”.

Sempre que possível:

```text
feature
+
tests
```

na mesma fase/PR.

---

# 63. Estratégia de testes

Seguir:

```text
docs/TESTING_STRATEGY.md
```

---

# 64. Testes mínimos por feature backend

Normalmente considerar:

```text
unit
integration quando há DB
API quando há endpoint
regression se corrige bug
```

---

# 65. Testes mínimos por feature frontend

Normalmente considerar:

```text
component behavior
error/loading state
integration with service
E2E se pertence a jornada crítica
```

---

# 66. Property tests

Usar principalmente em:

```text
OX
mutations
decoder invariants
solution validation
```

---

# 67. Banco de teste

Integração importante deve usar PostgreSQL/PostGIS real.

---

# 68. Bugs

Ao corrigir bug relevante:

```text
reproduzir
→ criar teste falhando
→ corrigir
→ confirmar teste
```

---

# 69. Não mascarar falha de teste

Não:

- desabilitar teste;
- adicionar skip;
- ampliar tolerância arbitrariamente;
- remover assertion;

apenas para tornar CI verde.

Investigar a causa.

---

# 70. Flaky tests

Flakiness é defeito.

Corrigir causa.

---

# 71. Performance

Não otimizar por palpite.

Fluxo:

```text
benchmark
→ profile
→ optimize
→ benchmark novamente
```

---

# 72. Benchmarks

Toda comparação acadêmica precisa registrar:

```text
city version
scenario seed
GA seed
algorithm version
config version
```

---

# 73. Não alterar parâmetros sem registrar

Mudança em:

```text
population
mutation
elitism
stagnation
time budget
```

deve gerar nova configuração/versionamento quando relevante.

---

# 74. UI

Seguir:

```text
docs/FRONTEND_SPEC.md
```

---

# 75. Não criar dashboard genérico

A tela inicial autenticada é:

```text
Operações
```

---

# 76. Mapa é central

O mapa não deve virar subfeature escondida.

Em:

- planejamento;
- otimização;
- resultado;

ele deve ter presença relevante.

---

# 77. Não usar spinner falso para GA

Antes do SSE estar pronto:

```text
mostrar status real simples
```

Depois:

```text
usar eventos reais
```

Nunca simular gerações.

---

# 78. Estados obrigatórios no frontend

Features relevantes devem considerar:

```text
loading
empty
success
error
disabled
blocked
```

---

# 79. Acessibilidade

Não remover:

- labels;
- foco;
- navegação por teclado;
- contraste;
- semantic table.

---

# 80. Responsividade

Desktop primeiro.

Não gastar grande esforço transformando V1 em aplicativo mobile.

---

# 81. Erros

Usar códigos tipados do backend.

Não mostrar ao usuário:

```text
500 Internal Server Error
```

sem explicação útil.

---

# 82. Logs

Logs devem ajudar diagnóstico.

Incluir quando relevante:

```text
request_id
operation_id
optimization_run_id
duration
```

---

# 83. Não logar

Nunca:

```text
password
password_hash
API key
authorization header
session cookie
full access token
```

---

# 84. Observabilidade

Implementar de forma incremental.

Não criar stack Prometheus/Grafana self-hosted na V1 sem necessidade.

---

# 85. Sentry

Pode ser adicionado quando frontend/backend estiverem maduros.

Não é pré-requisito para começar.

---

# 86. Erro externo não derruba core

LLM falhando:

```text
assistant DEGRADED
```

não:

```text
FluxMed indisponível
```

---

# 87. Transações

Usar em ações críticas.

Exemplos:

```text
import confirm
dispatch
snapshot creation
```

---

# 88. Idempotência

Proteger contra:

```text
double click optimize
double dispatch
double import confirm
```

---

# 89. Reportar estado real

Ao terminar uma tarefa, o Codex deve informar:

```text
o que foi feito
arquivos principais alterados
testes executados
resultado dos testes
limitações conhecidas
próximo passo sugerido
```

---

# 90. Não afirmar teste que não rodou

Se um teste não foi executado:

```text
dizer explicitamente
```

Nunca:

```text
"todos os testes passam"
```

sem execução real.

---

# 91. Não afirmar visual validado sem abrir

Se não houve inspeção visual real:

```text
dizer que o build passou,
mas que a validação visual ainda precisa ser feita
```

---

# 92. Não afirmar deploy concluído sem verificar

Deploy só está concluído quando:

- processo terminou;
- aplicação responde;
- smoke check foi executado.

---

# 93. Quando parar

Parar e pedir decisão humana se houver:

- requisito contraditório;
- decisão de produto não documentada;
- risco de perda de dados;
- necessidade de secret;
- escolha com impacto relevante de custo;
- migration destrutiva;
- mudança arquitetural grande.

---

# 94. Quando não parar

Não pedir confirmação para decisões pequenas e reversíveis já definidas.

Exemplos:

- nome interno de helper function;
- organização menor de arquivo;
- pequenos detalhes de teste.

---

# 95. Secrets necessários

Se uma fase precisar de API key:

- implementar interface/mock primeiro;
- documentar env var;
- pedir ao usuário configurar localmente;
- nunca solicitar que a chave seja enviada em chat se houver alternativa.

---

# 96. Erros de ambiente

Se falhar por:

- Docker ausente;
- PostgreSQL indisponível;
- Node/Python incorreto;
- porta ocupada;

reportar exatamente.

Não “corrigir” instalando software desconhecido sem autorização.

---

# 97. Comandos destrutivos

Não executar sem necessidade e autorização:

```text
rm -rf em diretórios amplos
git clean -fd
git reset --hard
DROP DATABASE de ambiente não identificado
truncate de dados persistentes
```

---

# 98. Arquivos do usuário

Nunca substituir arquivo externo ao repositório sem solicitação.

---

# 99. Formatação

Executar formatters oficiais antes de concluir.

Backend e frontend devem manter estilo consistente.

---

# 100. Lint

Warnings importantes devem ser corrigidos.

Não desativar regra global apenas para ocultar erro local.

---

# 101. Type checking

TypeScript:

```text
strict
```

quando possível.

Python:

usar typing progressivamente, especialmente em:

- domain;
- application;
- optimizer;
- APIs públicas.

---

# 102. `Any`

Evitar `Any` em contratos centrais sem necessidade.

---

# 103. TODOs

TODO permitido apenas quando:

- não bloqueia fase;
- está claramente identificado;
- não representa requisito obrigatório omitido.

---

# 104. TODO crítico

Se requisito obrigatório ainda não está implementado:

```text
não declarar fase pronta
```

---

# 105. Comentários

Usar comentários para explicar:

```text
por que
```

não:

```text
o que a linha óbvia faz
```

---

# 106. Docstrings

Priorizar em:

- algoritmo;
- domínio complexo;
- interfaces;
- regras de pruning;
- public services.

---

# 107. Nomes

Código em inglês.

UI em português do Brasil.

Exemplos:

```text
Operation
Delivery
Vehicle
Worker
RouteDecoder
```

---

# 108. Não traduzir nomes técnicos de código de forma inconsistente

Evitar misturas como:

```text
EntregaService
VehicleRepositorio
```

Preferir inglês no código.

---

# 109. API JSON

Preferência:

```text
snake_case
```

---

# 110. Enums

Preferência:

```text
UPPER_SNAKE_CASE
```

---

# 111. Erro conhecido

Se uma fase terminar com limitação aceitável:

documentar explicitamente.

Exemplo:

```text
Map rendering valid, but geometry simplification is not yet implemented.
```

---

# 112. Não esconder dívida técnica

Dívida técnica real deve aparecer no relatório da tarefa.

---

# 113. Mas não criar backlog infinito

Só registrar dívida que:

- afeta manutenção;
- performance;
- segurança;
- requisito futuro provável;
- comportamento conhecido.

---

# 114. ADR

Criar ADR quando mudar decisão estrutural.

Exemplos:

```text
database
map engine
stream protocol
GA representation
fitness strategy
```

Não criar ADR para renomear função.

---

# 115. Atualização de documentação

Se implementação exigir mudança aprovada:

1. atualizar documento correspondente;
2. atualizar ADR se necessário;
3. implementar;
4. testar.

---

# 116. Documentação obsoleta é bug

Se o código mudou contrato relevante e docs não mudaram:

```text
tarefa não está concluída
```

---

# 117. README

README deve permanecer visão geral.

Não transformar README em cópia de toda documentação.

---

# 118. Dependência entre fases

Se uma fase descobrir que a anterior está incompleta:

```text
corrigir a base primeiro
```

Não criar workaround permanente.

---

# 119. Feature temporária

Mocks podem existir, mas devem ser claramente marcados.

Quando backend real chegar:

```text
remover mock do fluxo principal
```

---

# 120. Dados demo

Usar dados plausíveis de Santa Aurora.

Não usar:

```text
John Doe
123 Main Street
Test Vehicle 1
```

quando dados demonstrativos entrarem na UI.

---

# 121. Segurança acadêmica

Embora seja projeto acadêmico, implementar:

- password hashing;
- RBAC;
- secret handling;
- validation;
- file upload limits;
- CORS correto.

---

# 122. Não buscar perfeição empresarial

Não gastar semanas em:

- HA;
- cluster;
- distributed tracing completo;
- autoscaling;
- zero-downtime migrations avançadas.

---

# 123. Definition of Done da tarefa

Antes de declarar uma tarefa concluída:

```text
[ ] implementação corresponde à documentação
[ ] escopo foi respeitado
[ ] testes apropriados existem
[ ] testes executados passam
[ ] lint passa
[ ] type-check passa
[ ] build passa quando aplicável
[ ] nenhuma secret foi incluída
[ ] migrations foram revisadas
[ ] erros foram tratados
[ ] docs foram atualizadas quando necessário
[ ] git status foi revisado
```

---

# 124. Definition of Done da fase

Além do checklist acima:

```text
[ ] critério de aceite em DEVELOPMENT_PLAN foi cumprido
[ ] fluxo foi validado ponta a ponta
[ ] não há TODO crítico
[ ] main pode permanecer estável após merge
```

---

# 125. Formato do relatório final de uma tarefa

O Codex deve responder de forma semelhante a:

```text
Implementado:
- ...

Testes executados:
- ...
- ...

Resultado:
- todos passaram

Arquivos principais:
- ...

Observações:
- ...

Próximo passo:
- ...
```

---

# 126. Se houver falha

Reportar:

```text
O que falhou
Comando
Erro essencial
Impacto
O que já foi tentado
Próxima ação recomendada
```

Não mascarar erro.

---

# 127. Se houver rate limit ou interrupção

Ao retomar:

1. inspecionar repositório;
2. verificar `git status`;
3. verificar branch;
4. verificar último commit;
5. identificar o que ficou incompleto;
6. continuar dali.

Não refazer trabalho sem conferir.

---

# 128. Se receber “continue”

Interpretar como:

> retomar exatamente o desenvolvimento interrompido na branch e fase atuais.

Antes, inspecionar estado real.

---

# 129. Se receber screenshot de bug

Usar screenshot como evidência visual, mas:

- confirmar estado no código;
- reproduzir quando possível;
- não corrigir apenas CSS superficial se causa for lógica.

---

# 130. Se frontend parecer genérico

Revisar `FRONTEND_SPEC.md`.

A solução deve manter:

- mapa central;
- densidade profissional;
- identidade teal/grafite;
- contexto logístico;
- poucos cards desnecessários.

---

# 131. Se optimizer estiver lento

Não migrar imediatamente para worker distribuído.

Primeiro:

```text
profile
matrix cache
decoder
pruning
population/config
```

---

# 132. Se Vercel limitar o optimizer

Só depois de benchmark real:

- documentar evidência;
- considerar mover FastAPI/optimizer para host persistente.

Não redesenhar domínio.

---

# 133. Se LLM ficar cara

Primeiro reduzir:

- contexto;
- tool result size;
- chamadas redundantes;
- output.

Não remover grounding.

---

# 134. Se dataset ficar pesado

Primeiro medir:

- payload;
- query;
- map render.

Depois considerar:

- geometry simplification;
- layer separation;
- viewport loading.

---

# 135. Se endereço não for encontrado

Nunca criar aproximação silenciosa.

Retornar:

- erro;
- sugestões;
- confirmação.

---

# 136. Se nenhuma solução válida existir

Mostrar:

```text
não foi possível encontrar solução válida
```

com gargalos.

Nunca exibir plano inválido como sucesso.

---

# 137. Se o GA atingir timeout

Com best valid:

```text
usar best valid
+ registrar stop reason
```

Sem best valid:

```text
falhar explicitamente
```

---

# 138. Se LLM discordar do backend

Backend vence.

A resposta deve ser corrigida ou rejeitada.

---

# 139. Se frontend e OpenAPI divergirem

OpenAPI/backend é contrato operacional atual.

Corrigir client/frontend e docs.

Não duplicar workaround.

---

# 140. Se teste e documentação divergirem

Investigar qual representa a decisão aprovada.

Não alterar teste apenas para fazê-lo passar.

---

# 141. Ordem de leitura por tipo de tarefa

## Produto

```text
PRODUCT_SPEC
DOMAIN_MODEL
```

## Backend

```text
ARCHITECTURE
DOMAIN_MODEL
API_SPEC
TESTING_STRATEGY
```

## Frontend

```text
PRODUCT_SPEC
FRONTEND_SPEC
API_SPEC
```

## Cidade

```text
SANTA_AURORA_SPEC
DOMAIN_MODEL
ARCHITECTURE
TESTING_STRATEGY
```

## Optimizer

```text
OPTIMIZATION_SPEC
DOMAIN_MODEL
ARCHITECTURE
TESTING_STRATEGY
```

## LLM

```text
LLM_SPEC
API_SPEC
ARCHITECTURE
TESTING_STRATEGY
```

---

# 142. Antes de iniciar o projeto

O Codex deve confirmar que:

```text
README.md existe
docs estão presentes
git está inicializado
branch está clara
nenhuma implementação antiga precisa ser preservada
```

---

# 143. Repositório zerado

A implementação parte de um repositório novo.

Não importar código antigo do Lovable.

Não adicionar arquivos Lovable.

---

# 144. Artefatos Lovable

Arquivos como:

```text
LOVABLE_MASTER_PROMPT.md
LOVABLE_BRIEF.md
```

não fazem parte da nova arquitetura.

Não recriá-los.

---

# 145. Ferramentas externas

Não adicionar SaaS/BaaS sem requisito.

Especialmente evitar como dependência central:

```text
Supabase
Firebase
Auth0
Google Maps
```

---

# 146. Licenças

Ao adicionar bibliotecas, preferir licenças compatíveis e bem conhecidas.

Se houver dúvida significativa, sinalizar.

---

# 147. Código acadêmico fornecido

Quando o código-base TSP da instituição for adicionado:

1. preservar cópia/referência conforme necessário;
2. entender o código;
3. documentar evolução;
4. adaptar ao FluxMed;
5. não copiar sem explicação.

---

# 148. Relatório técnico

Durante desenvolvimento, guardar evidências que ajudem depois:

- benchmark results;
- screenshots;
- architecture decisions;
- optimizer metrics;
- ablation results.

---

# 149. Vídeo final

O sistema deve permanecer demonstrável em fluxo contínuo.

Evitar depender de passos manuais frágeis ou dados aleatórios imprevisíveis.

---

# 150. Cenário demo

Manter seed conhecida para demonstração final.

Exemplo conceitual:

```text
Santa Aurora 1.0.0
NORMAL
40 deliveries
fixed scenario seed
fixed GA seed
```

A seed definitiva será escolhida após benchmarks.

---

# 151. Reprodutibilidade

Toda demo importante deve poder ser reproduzida.

---

# 152. Não otimizar estética antes da função

Polimento visual importante entra progressivamente.

Mas não atrasar:

- domínio;
- mapa;
- routing;
- optimizer;
- validator;

por microajustes de UI.

---

# 153. Não deixar UI ruim até o final

Também não esperar a última fase para validar UX.

Cada vertical slice deve ficar utilizável.

---

# 154. Decisão humana

O usuário continua sendo responsável por:

- aceitar mudanças de escopo;
- aprovar mudança arquitetural;
- fornecer secrets;
- validar visualmente telas importantes;
- decidir trade-offs relevantes.

---

# 155. Autonomia permitida ao Codex

O Codex pode decidir sozinho:

- nomes internos;
- pequenas estruturas de arquivo;
- helpers;
- refactors locais;
- detalhes de testes;
- pequenas melhorias de DX;

desde que respeite os documentos.

---

# 156. Autonomia não permitida

Não decidir sozinho:

- trocar stack;
- trocar banco;
- mudar representação do GA;
- mudar fitness;
- adicionar microserviços;
- mudar deploy alvo;
- remover requisito acadêmico;
- mudar fluxo principal do produto.

---

# 157. Regra de parada entre fases

Ao concluir uma fase:

```text
parar
reportar
aguardar validação
```

Não avançar automaticamente para a próxima grande fase, a menos que o usuário peça explicitamente para continuar.

---

# 158. Regra de entrega incremental

A cada fase, o projeto deve continuar executável.

Não aceitar:

```text
"ficará funcionando quando as próximas 4 fases forem concluídas"
```

como padrão.

---

# 159. Critério de excelência

Uma implementação excelente do FluxMed é aquela em que:

- a regra está no lugar correto;
- o código é simples de ler;
- a solução é testável;
- os contratos são claros;
- o comportamento é reproduzível;
- o frontend explica o resultado;
- a documentação continua verdadeira.

---

# 160. Regra final

> O Codex deve agir como engenheiro responsável pelo projeto, não como gerador de grandes quantidades de código.

A prioridade é:

```text
correção
→ clareza
→ testes
→ integração
→ experiência
→ performance medida
```

e nunca:

```text
complexidade
→ quantidade de arquivos
→ aparência de arquitetura enterprise
```

O FluxMed deve chegar à V1 como um sistema acadêmico tecnicamente defensável, visualmente convincente e suficientemente organizado para ser apresentado como projeto de portfólio profissional.
