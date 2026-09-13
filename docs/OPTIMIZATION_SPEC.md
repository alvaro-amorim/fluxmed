# FluxMed — Optimization Specification

**Documento:** `docs/OPTIMIZATION_SPEC.md`  
**Status:** Especificação oficial do motor de otimização da V1  
**Projeto:** FluxMed — Planejamento Inteligente de Rotas Médicas  
**Contexto:** Tech Challenge — Fase 2 — Projeto 2

---

# 1. Objetivo deste documento

Este documento define o comportamento técnico e funcional do motor de otimização do FluxMed.

Ele estabelece:

- separação entre routing urbano e otimização de frota;
- representação genética;
- população inicial;
- seleção;
- crossover;
- mutações;
- decoder;
- fitness;
- pruning;
- repair;
- diversidade;
- critérios de parada;
- Team Assignment Solver;
- Solution Validator;
- Decision Trace;
- benchmarks;
- comparações acadêmicas;
- parâmetros versionados;
- regras de validade.

Este documento deve orientar a implementação do GA e impedir que o algoritmo seja simplificado de forma que perca valor acadêmico ou realismo operacional.

---

# 2. Princípio central

O FluxMed possui duas camadas distintas:

```text
Routing urbano
+
Fleet/VRP Optimization
```

O GA não decide curva por curva da cidade.

O GA decide:

> qual entrega deve ser atendida por qual veículo e em qual ordem.

O módulo Routing decide:

> qual caminho urbano usar entre duas paradas.

---

# 3. Separação obrigatória

```text
Routing:
A → B por onde?

Optimization:
quem atende A, B, C e em qual sequência?
```

Essa separação é uma regra arquitetural.

O algoritmo genético não deve evoluir sequências de RoadSegments.

---

# 4. Problema de otimização

A V1 resolve uma variante de VRP com:

- múltiplos veículos;
- capacidade por peso;
- capacidade por volume;
- autonomia;
- refrigeração;
- prioridades;
- janelas HARD e SOFT;
- tempo de serviço;
- necessidade de ajudante;
- jornada máxima;
- retorno ao depósito;
- custos;
- trânsito dependente do horário;
- restrições viárias.

O problema é combinatório e não deve ser reduzido a um TSP puro.

---

# 5. Código-base acadêmico

O código-base TSP fornecido pelo professor deve ser utilizado como ponto de partida conceitual e/ou estrutural quando estiver disponível.

O objetivo não é preservar o código intacto.

O objetivo é demonstrar evolução clara de:

```text
TSP base
→ múltiplos veículos
→ restrições
→ VRP realista
→ custos
→ janelas
→ pruning/repair
→ integração com LLM e visualização
```

As mudanças relevantes em relação ao código-base devem ser documentadas no relatório técnico.

---

# 6. OptimizationProblem

Entrada conceitual do optimizer:

```text
OptimizationProblem
```

Deve conter:

- operação;
- revisão;
- entregas;
- veículos;
- workers disponíveis;
- depósito;
- matriz de viagem;
- custos;
- restrições;
- horário de saída;
- fim da jornada;
- versão da cidade;
- configuração do algoritmo;
- seed.

---

# 7. Representação genética

A representação oficial da V1 será:

> **permutação global de entregas**

Exemplo:

```text
[D7, D2, D9, D1, D5, D3, D8, D4, D6]
```

O cromossomo não armazena diretamente:

- veículo;
- motorista;
- ajudante;
- ruas;
- horários.

Esses elementos são derivados por decoder e módulos auxiliares.

---

# 8. Motivo da representação indireta

Benefícios:

- cromossomo menor;
- menos combinações inválidas;
- crossover mais simples;
- mutação mais estável;
- menor acoplamento com quantidade de veículos;
- possibilidade de decoder inteligente;
- pruning durante construção da solução.

---

# 9. RouteDecoder

O `RouteDecoder` transforma a permutação global em rotas reais.

Fluxo conceitual:

```text
chromosome
 ↓
delivery sequence
 ↓
candidate vehicle selection
 ↓
route construction
 ↓
constraint checks
 ↓
team feasibility
 ↓
cost calculation
 ↓
decoded solution
```

---

# 10. Responsabilidades do decoder

O decoder deve:

- percorrer entregas na ordem genética;
- avaliar veículos elegíveis;
- construir rotas;
- respeitar capacidade;
- respeitar volume;
- respeitar refrigeração;
- respeitar autonomia;
- respeitar HARD windows;
- respeitar fim da jornada;
- preservar recursos escassos quando possível;
- calcular custo marginal;
- permitir repair;
- produzir evidências para Decision Trace.

---

# 11. Hierarquia de escolha de veículo no decoder

Ordem recomendada:

1. viabilidade;
2. proteção de entregas críticas;
3. preservação de recursos escassos;
4. folga de janela;
5. custo marginal;
6. tempo marginal;
7. capacidade adequada.

---

# 12. Recurso escasso

Exemplos:

- único veículo refrigerado;
- único caminhão de alta capacidade;
- único veículo com autonomia suficiente.

O decoder não deve desperdiçar um recurso raro em uma entrega comum se isso puder inviabilizar uma entrega futura.

---

# 13. Look-ahead

O decoder pode verificar:

> se eu atribuir esta entrega a este veículo agora, alguma entrega futura ficará sem veículo elegível?

Se a resposta for comprovadamente sim, a atribuição pode ser rejeitada.

Esse mecanismo deve ser conservador.

---

# 14. População inicial

A população inicial deve ser híbrida.

Misturar:

- Best Insertion;
- Nearest Neighbor;
- versões perturbadas;
- indivíduos aleatórios diversos.

Não iniciar 100% da população de forma aleatória.

---

# 15. Objetivo da inicialização híbrida

Evitar:

- começar com população muito ruim;
- convergência lenta;
- baixa diversidade;
- dependência excessiva de sorte.

---

# 16. Nearest Neighbor seed

Pode gerar cromossomos priorizando proximidade.

Serve como baseline heurístico e como fonte de indivíduos iniciais.

---

# 17. Best Insertion seed

Pode construir sequência inserindo entregas no ponto de menor impacto.

Serve como baseline e como seed da população.

---

# 18. Perturbações

Indivíduos heurísticos podem ser perturbados com:

- swaps;
- pequenas inversões;
- inserções;
- shuffle parcial.

Objetivo:

- preservar qualidade;
- aumentar diversidade.

---

# 19. Seleção

Método oficial:

```text
Tournament Selection
```

---

# 20. Tournament Selection

Fluxo:

```text
selecionar k indivíduos
 ↓
comparar fitness lexicográfica
 ↓
vencedor entra como parent
```

O valor de `k` será calibrado por benchmark.

---

# 21. Crossover

Método oficial:

```text
Order Crossover (OX)
```

Motivo:

- adequado para permutações;
- preserva genes únicos;
- mantém ordem relativa;
- evita duplicação de entregas.

---

# 22. OX — comportamento

Exemplo conceitual:

```text
Parent A:
1 2 3 4 5 6 7 8

Parent B:
4 1 2 8 7 6 5 3
```

Seleciona-se um trecho de A e completa-se com a ordem relativa de B.

O resultado deve conter cada delivery exatamente uma vez.

---

# 23. Validação pós-crossover

O operador deve garantir:

- nenhuma entrega duplicada;
- nenhuma entrega perdida;
- tamanho do cromossomo preservado.

Se isso falhar, é bug de implementação.

---

# 24. Mutação

Operadores oficiais:

```text
SWAP
INSERTION
INVERSION
```

---

# 25. Swap Mutation

Troca duas posições.

Exemplo:

```text
A B C D E
→
A D C B E
```

---

# 26. Insertion Mutation

Remove uma entrega e insere em outra posição.

Exemplo:

```text
A B C D E
→
A C D B E
```

---

# 27. Inversion Mutation

Inverte um trecho.

Exemplo:

```text
A B C D E F
→
A E D C B F
```

---

# 28. Mutação adaptativa

A taxa de mutação não precisa ser fixa.

Pode aumentar quando:

- população estagna;
- diversidade cai;
- melhor solução não melhora.

Pode voltar ao normal quando diversidade recupera.

---

# 29. Diversidade populacional

O sistema deve medir diversidade de forma simples e útil.

Possíveis métricas:

- diferença posicional;
- diferença de adjacências;
- distância entre permutações;
- diversidade média por amostra.

Não precisa utilizar métrica extremamente sofisticada.

---

# 30. Imigrantes

Quando houver forte estagnação e baixa diversidade:

- inserir alguns indivíduos novos;
- usar random controlado;
- usar perturbações de heurísticas.

Esses indivíduos são “immigrants”.

---

# 31. Elitismo

Uma pequena fração dos melhores indivíduos deve passar para a próxima geração.

Valor exato será calibrado.

Conceito inicial:

```text
~5%
```

Não tratar esse número como obrigatório.

---

# 32. Fitness

A fitness oficial é **lexicográfica**.

Não usar uma soma arbitrária do tipo:

```text
score = 1000 * constraint
      + 50 * cost
      + 7 * distance
```

como regra principal.

---

# 33. FitnessVector

Estrutura:

```text
feasible
hard_violations
service_penalty
critical_risk
total_cost_brl
makespan_minutes
travel_minutes
distance_km
vehicles_used
```

---

# 34. Ordem lexicográfica

Comparação:

```text
1. feasible / hard violations
2. service quality
3. critical risk
4. total operational cost
5. makespan
6. travel time
7. distance
8. vehicles used
```

---

# 35. Viabilidade

Uma solução válida precisa respeitar:

- todas as entregas atribuídas;
- nenhuma duplicada;
- capacidade;
- volume;
- autonomia;
- refrigeração;
- HARD windows;
- equipe;
- retorno ao depósito;
- fim da jornada;
- acessibilidade viária.

---

# 36. Hard violation

Exemplos:

```text
delivery unassigned
duplicate delivery
capacity exceeded
volume exceeded
range exceeded
refrigeration mismatch
hard time window missed
team infeasible
route cannot return to depot
end of shift exceeded
```

---

# 37. Service penalty

Pode considerar:

- atraso SOFT;
- prioridade;
- folga reduzida;
- risco em CRITICAL/HIGH.

A fórmula exata deve ser documentada e testada.

---

# 38. Critical risk

Métrica separada ou derivada.

Objetivo:

- evitar que uma solução barata deixe entregas críticas próximas do limite de janela.

---

# 39. Custo operacional

Deve incluir:

- veículo próprio;
- veículo agregado;
- combustível;
- depreciação;
- manutenção;
- custo fixo temporal;
- equipe;
- contrato;
- extras futuros quando existirem.

LLM nunca participa do cálculo.

---

# 40. Makespan

Definição:

> tempo entre a saída da operação e o retorno do último veículo.

É métrica importante porque representa duração operacional global.

---

# 41. Distância

Usada como critério inferior ao custo e ao tempo.

Motivo:

> rota mais curta em km pode ser mais lenta ou mais cara.

---

# 42. Vehicles used

Critério secundário.

Não minimizar número de veículos de forma cega.

Usar menos veículos pode:

- atrasar entregas;
- aumentar jornada;
- aumentar risco.

---

# 43. Pruning

O FluxMed deve aplicar pruning somente quando houver razão segura.

Classes oficiais:

1. eligibility pruning;
2. hard constraint pruning;
3. future feasibility pruning;
4. state dominance;
5. lower bound pruning.

---

# 44. Eligibility Pruning

Executado antes ou no início da construção.

Remove combinações impossíveis por:

- peso;
- volume;
- refrigeração;
- autonomia evidente;
- helper obrigatório;
- incompatibilidade de veículo;
- restrição viária;
- falta de equipe possível.

---

# 45. Hard Constraint Pruning

Durante decode.

Exemplo:

```text
adding D7 to Vehicle V2
→ payload 1.240 kg
→ vehicle max 1.000 kg
→ prune
```

---

# 46. Future Feasibility Pruning

Exemplo:

```text
delivery X
→ only refrigerated van can handle

if current assignment consumes refrigerated van capacity
→ X becomes impossible

therefore:
reject current assignment
```

Só aplicar quando a inviabilidade futura puder ser demonstrada.

---

# 47. State Dominance

Se dois estados parciais representam situação equivalente e um é claramente pior, remover o pior.

Exemplo:

```text
same remaining deliveries
same vehicle state
same location

State A:
earlier
cheaper
more capacity

State B:
later
more expensive
less capacity

B is dominated
```

---

# 48. Lower Bound Pruning

Se:

```text
current cost
+
safe lower bound of remaining work
>
best known feasible solution
```

o estado pode ser podado.

O lower bound deve ser seguro.

---

# 49. Regra de segurança do pruning

Nunca podar apenas porque:

```text
"parece caro"
"parece longe"
"não parece promissor"
```

sem garantia suficiente.

Heurística incerta deve ordenar candidatos, não eliminá-los permanentemente.

---

# 50. Pruning reasons

Enums recomendados:

```text
CAPACITY_EXCEEDED
VOLUME_EXCEEDED
HARD_TIME_WINDOW_IMPOSSIBLE
RANGE_IMPOSSIBLE
REFRIGERATION_INCOMPATIBLE
TEAM_INFEASIBLE
ROAD_ACCESS_IMPOSSIBLE
END_OF_SHIFT_IMPOSSIBLE
FUTURE_INFEASIBILITY
DOMINATED_STATE
LOWER_BOUND
```

---

# 51. Métricas de pruning

Registrar:

```text
total_pruned
pruned_by_reason
avoided_full_evaluations
pruning_rate
```

---

# 52. Repair

Antes de descartar uma solução, o sistema pode tentar corrigir violações reparáveis.

Exemplos:

- mover entrega para outro veículo;
- reorganizar posição;
- separar carga entre rotas quando permitido;
- trocar veículo elegível.

---

# 53. Regra de Repair

Não tentar reparar violações estruturalmente impossíveis.

Exemplo:

```text
refrigerated delivery
+
zero refrigerated vehicles
```

não é problema de repair.

---

# 54. Repair x pruning

Fluxo preferido:

```text
candidate
 ↓
violation
 ↓
repair feasible?
 ├── yes → repair
 └── no  → prune/reject
```

---

# 55. Team Assignment Solver

Equipe não entra no cromossomo.

Após a construção de rotas:

```text
routes
 ↓
TeamAssignmentSolver
 ↓
team assignments
 ↓
true cost
```

---

# 56. Método do Team Assignment Solver

Usar problema de:

```text
matching / minimum cost assignment
```

Não usar outro GA.

---

# 57. Compatibilidade de equipe

Considerar:

- role;
- disponibilidade;
- helper requirement;
- vehicle helper policy;
- motorista incluído em contrato;
- ajudante incluído em contrato;
- custo.

---

# 58. Ajudante opcional

Para rota `OPTIONAL`:

comparar:

```text
without helper
vs
with helper
```

Considerando:

- custo;
- redução de service time;
- impacto em janelas;
- disponibilidade;
- risco operacional.

---

# 59. Team solver e fitness

O custo real de equipe deve participar da avaliação final.

A implementação pode:

- executar subsolver leve durante fitness;
- ou usar estimativa segura durante busca e solver exato no final.

A decisão concreta deve ser testada em benchmark.

---

# 60. SolutionValidator

Depois do GA:

```text
best solution
 ↓
SolutionValidator
```

Obrigatório.

---

# 61. Responsabilidade do SolutionValidator

Validar independentemente:

- todas as deliveries;
- unicidade;
- capacity;
- volume;
- range;
- refrigeration;
- HARD windows;
- team;
- return to depot;
- end of shift;
- route continuity;
- road accessibility.

---

# 62. Mismatch crítico

Se:

```text
GA says valid
SolutionValidator says invalid
```

resultado:

```text
OPTIMIZER_VALIDATION_MISMATCH
```

A solução não pode ser apresentada como válida.

---

# 63. Critérios de parada

Parada ocorre no primeiro dos critérios atingidos:

- early stopping;
- time budget;
- hard time limit;
- max generations;
- convergence.

---

# 64. Time budget

Meta inicial para operação comum:

```text
~30 segundos
```

Não é promessa de UX.

Será calibrado.

---

# 65. Hard time limit

Valor conceitual inicial:

```text
60 segundos
```

Se atingido:

- usar melhor solução válida encontrada;
- registrar `TIME_BUDGET`/limite;
- nunca apresentar inválida.

---

# 66. Early stopping

Se não houver melhora significativa por determinado número de gerações:

```text
stop
```

Valor deve ser calibrado.

---

# 67. Max generations

Existe como proteção.

Não deve ser único critério de parada.

---

# 68. Best solution so far

O optimizer deve manter continuamente:

```text
best_valid_solution_so_far
```

Assim timeout não perde o melhor resultado válido.

---

# 69. Nenhuma solução válida

Se o limite terminar sem solução válida:

```text
NO_FEASIBLE_SOLUTION_FOUND
```

Mostrar gargalos.

Não mostrar “quase solução”.

---

# 70. Infeasibilidade pré-GA

Antes de iniciar o GA, executar validações.

Exemplos:

```text
refrigerated delivery with zero refrigerated vehicle
delivery heavier than all vehicles
road closure isolates address
total required team impossible
```

Se inviabilidade for comprovada:

```text
do not start GA
```

---

# 71. PreflightValidator

Componente recomendado:

```text
OptimizationPreflightValidator
```

Responsável por identificar inviabilidades óbvias antes do custo do GA.

---

# 72. Routing matrix

Antes do GA, construir ou obter matriz de viagem entre pontos relevantes.

Pontos:

- depot;
- deliveries.

Pode ser time-dependent.

---

# 73. Time-dependent travel

O custo A → B depende do horário estimado de saída de A.

Portanto não assumir uma única matriz estática universal quando o trânsito estiver ativo.

Pode usar:

```text
(origin, destination, time_bucket)
```

---

# 74. Time bucket

Inicial:

```text
15 min
```

Ajustável por benchmark.

---

# 75. Cache

Cache pode armazenar:

```text
origin
destination
time_bucket
graph_version
→ TravelTime
```

Não exige Redis.

---

# 76. Travel time oficial

Baseado em:

```text
RoadSegment.length
RoadSegment.speed
TrafficProfile
RoadOverride
```

Não usar distância euclidiana como tempo oficial.

---

# 77. Service time

Cada Delivery adiciona tempo após chegada.

Esse tempo altera:

- ETA das próximas;
- HARD/SOFT windows;
- return time;
- helper benefit.

---

# 78. Espera por janela

Se veículo chega antes do início da janela:

```text
wait
```

Esse tempo deve entrar na rota.

---

# 79. HARD time window

Se chegada prevista ultrapassa fim:

```text
route invalid
```

---

# 80. SOFT time window

Atraso gera:

```text
service_penalty
```

Não invalida automaticamente.

---

# 81. Retorno ao depósito

Toda rota deve terminar no depósito.

Ao avaliar autonomia e jornada, considerar o retorno.

Nunca aceitar rota apenas porque conseguiu fazer a última entrega.

---

# 82. Autonomia

Regra:

```text
total route distance
<= usable operational range
```

Pode haver safety factor configurável.

---

# 83. Capacidade

Verificar simultaneamente:

```text
weight
volume
```

Não converter um no outro.

---

# 84. Load evolution

V1 só possui deliveries.

Portanto:

```text
initial load = sum of route deliveries
```

e carga diminui a cada parada.

O modelo pode ser future-ready para pickup.

---

# 85. Refrigeration

Se qualquer entrega da rota exigir refrigeração:

```text
vehicle must be refrigerated
```

Não modelar compartimentos mistos na V1.

---

# 86. Manual override após otimização

Se usuário trocar equipe ou recurso:

- backend revalida;
- custo recalculado;
- plano pode ficar OUTDATED se mudança exigir reotimização.

Mudança de equipe isolada pode ser revalidada sem novo GA se não alterar rota/tempo de forma incompatível.

---

# 87. Decision Trace

O optimizer deve produzir eventos observáveis.

Não armazenar chain-of-thought.

Eventos:

```text
GenerationSnapshot
PruningSummary
ImprovementEvent
RouteAssignmentChange
VehicleSelectionReason
ConstraintViolation
DiversityChange
FinalComparison
```

---

# 88. GenerationSnapshot

Campos possíveis:

```text
generation
elapsed_ms
best_cost
best_makespan
best_distance
hard_violations
critical_risk
diversity
mutation_rate
pruned_total
```

---

# 89. ImprovementEvent

Emitido quando:

```text
new best valid solution
```

Pode incluir:

- métricas anteriores;
- novas métricas;
- alterações principais.

---

# 90. RouteAssignmentChange

Usado para animação.

Exemplo:

```text
D12 moved
Vehicle V1 → Vehicle V3
position 4 → 2
```

Não precisa registrar toda movimentação microscópica.

---

# 91. VehicleSelectionReason

Estruturado.

Exemplo:

```text
vehicle V3 selected because:
- refrigeration required
- only 2 eligible vehicles
- V3 had lower marginal cost
- preserved V5 for heavier remaining load
```

---

# 92. FinalComparison

Comparar:

- initial heuristic;
- best GA;
- baseline quando aplicável.

---

# 93. Streaming

Decision Trace ao vivo alimenta SSE.

Não transmitir toda população.

Frequência:

- a cada N gerações;
- em nova melhor solução;
- em mudança importante;
- em pruning agregado.

---

# 94. Replay

Replay usa os eventos persistidos.

Não executar GA novamente.

---

# 95. Benchmark methodology

Experimentos acadêmicos devem ser reproduzíveis.

Registrar:

```text
scenario profile
delivery count
scenario seed
city dataset version
algorithm version
config version
GA seed
```

---

# 96. Tamanhos principais

```text
20 deliveries
40 deliveries
60 deliveries
80 deliveries
```

80 é stress test.

---

# 97. Perfis principais

```text
NORMAL
BUSY
HIGH_PRESSURE
EMERGENCY
```

---

# 98. Repetições

GA é estocástico.

Cada cenário de benchmark deve rodar múltiplas vezes.

Medir:

```text
best
mean
std
worst
mean runtime
```

Quantidade exata de repetições será definida no benchmark script conforme custo computacional.

---

# 99. Baselines

Obrigatórios para comparação técnica:

```text
Nearest Neighbor
Best Insertion
GA basic
GA + pruning
GA + pruning + repair
```

---

# 100. Random baseline

Pode ser usado como sanity check.

Não precisa ser apresentado como concorrente sério.

---

# 101. OR-Tools / exact methods

Opcional.

Pode ser usado em pequenas instâncias para referência.

Não deve substituir o GA como núcleo do projeto.

---

# 102. Ablation de pruning

Comparar:

```text
GA without pruning
vs
GA with pruning
```

Medir:

- runtime;
- evaluations;
- pruned count;
- final quality.

---

# 103. Ablation de repair

Comparar:

```text
GA + pruning
vs
GA + pruning + repair
```

---

# 104. Métricas primárias

```text
feasibility
hard violations
total operational cost
makespan
computational time
```

---

# 105. Métricas secundárias

```text
distance
travel time
vehicles used
on-time percentage
weighted tardiness
capacity utilization
cost per delivery
pruned count
avoided evaluations
generations
time-to-first-valid
time-to-best
```

---

# 106. Interface normal x pesquisa

A aplicação normal mostra métricas úteis.

Benchmarks pesados ficam em:

```text
benchmarks/
scripts/
notebooks/
```

Não transformar UI em laboratório científico.

---

# 107. Configuração do GA

Parâmetros internos:

```text
population_size
tournament_size
elitism_rate
mutation_rate
max_generations
stagnation_limit
time_budget
diversity_threshold
```

Não são campos normais para PLANNER.

---

# 108. Config version

Cada conjunto calibrado recebe nome/versão.

Exemplo:

```text
production-v1
```

---

# 109. Algorithm version

Exemplo:

```text
FluxMed-GA 1.0.0
```

---

# 110. Seed

Toda run deve registrar seed.

Objetivos:

- reprodução;
- debugging;
- relatório acadêmico.

---

# 111. Determinismo controlado

Com:

```text
same problem
same algorithm version
same config
same seed
```

o resultado deve ser reprodutível dentro do razoável.

Evitar paralelismo não determinístico no core da V1 se prejudicar reprodução.

---

# 112. Performance budget

Objetivo inicial de UX:

```text
small scenario: few seconds
medium: ideally < 15 s
large: < 30 s when possible
hard cap: ~60 s
```

Esses valores são metas, não requisitos rígidos até benchmark real.

---

# 113. Profiling

Registrar tempo por etapa:

```text
preflight
travel matrix
initial population
GA
team assignment
validation
persistence
```

---

# 114. Exemplo de breakdown

```text
Preflight             80 ms
Travel matrix       1.900 ms
Initial population    220 ms
GA                   8.500 ms
Team assignment         35 ms
Validation              18 ms
```

Isso ajuda a encontrar gargalos reais.

---

# 115. Falhas

Erros possíveis:

```text
PRECHECK_INFEASIBLE
NO_FEASIBLE_SOLUTION_FOUND
OPTIMIZATION_TIMEOUT_NO_SOLUTION
OPTIMIZER_INTERNAL_ERROR
OPTIMIZER_VALIDATION_MISMATCH
USER_CANCELLED
```

---

# 116. Cancelamento

O algoritmo deve consultar flag de cancelamento em pontos seguros.

Ao cancelar:

- encerra controladamente;
- persiste status;
- preserva best valid solution encontrada se desejado;
- não marca como run normal completada.

---

# 117. Reinício de backend

Na V1 não é necessário persistir população inteira.

Run interrompida:

```text
INTERRUPTED
```

O usuário executa novamente.

---

# 118. Testes unitários

Cobrir:

- selection;
- OX;
- mutation;
- fitness compare;
- decoder;
- capacity;
- volume;
- range;
- HARD windows;
- pruning;
- repair;
- team assignment;
- stop conditions.

---

# 119. Property-based tests

Exemplos:

> OX sempre produz permutação válida.

> Mutação nunca perde delivery.

> Solução validada nunca contém delivery duplicada.

> Rota válida nunca ultrapassa payload.

> Rota válida sempre retorna ao depot.

---

# 120. Regression scenarios

Criar cenários com seed fixa.

Exemplos:

```text
REG-001 normal 20
REG-002 refrigerated
REG-003 hard window
REG-004 limited range
REG-005 bridge closure
REG-006 two-person handling
```

---

# 121. Teste de pruning

Toda regra de pruning deve possuir:

- caso positivo;
- caso negativo;
- caso limite.

Especialmente importante para evitar poda incorreta.

---

# 122. Teste do SolutionValidator

Deve detectar propositalmente:

- duplicate;
- missing delivery;
- overload;
- volume;
- range;
- window;
- team;
- return;
- shift.

---

# 123. Architecture tests

Optimization não deve importar:

```text
FastAPI
React
API routers
LLM provider
```

---

# 124. Relatório acadêmico

O relatório deve explicar:

- representação;
- seleção;
- crossover;
- mutação;
- fitness;
- decoder;
- restrições;
- pruning;
- repair;
- baselines;
- benchmarks;
- resultados.

---

# 125. Visualização acadêmica

Gráficos recomendados:

- convergência;
- custo por método;
- runtime;
- pruning rate;
- qualidade por tamanho do problema;
- estabilidade entre seeds/runs.

---

# 126. O que não fazer

Não implementar:

- GA em JavaScript no frontend;
- GA que usa distância euclidiana como rota real;
- cromossomo contendo every RoadSegment;
- fitness única arbitrária sem explicação;
- pruning agressivo sem garantia;
- LLM decidindo solução;
- solução inválida exibida como válida;
- benchmark sem seed/versão.

---

# 127. Ordem recomendada de implementação

```text
1. baseline Nearest Neighbor
2. baseline Best Insertion
3. chromosome model
4. decoder simples
5. fitness
6. Tournament Selection
7. OX
8. mutations
9. basic GA
10. SolutionValidator
11. pruning
12. repair
13. diversity
14. adaptive mutation
15. TeamAssignmentSolver
16. Decision Trace
17. benchmarks
18. tuning
```

---

# 128. Critério de aceite funcional

O motor está pronto quando:

- recebe cenário válido;
- encontra plano válido quando existir;
- respeita restrições;
- retorna rotas;
- retorna custos;
- passa no SolutionValidator;
- produz métricas;
- produz Decision Trace;
- pode ser comparado com baselines.

---

# 129. Critério de aceite acadêmico

O motor deve permitir demonstrar claramente:

- evolução de TSP para VRP;
- uso real de GA;
- operadores genéticos;
- impacto das restrições;
- impacto do pruning;
- comparação com métodos simples;
- estabilidade por múltiplas execuções;
- trade-offs de custo/tempo/serviço.

---

# 130. Regra final

> O objetivo do motor não é encontrar uma “rota bonita”, mas produzir a melhor solução válida encontrada dentro do orçamento computacional, preservando restrições, explicabilidade e reprodutibilidade.

O valor acadêmico do FluxMed depende tanto da qualidade da solução quanto da clareza com que o processo de otimização pode ser explicado e comparado.
