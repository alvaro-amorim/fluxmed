# FluxMed — algoritmo de otimização

## Problema e entradas

O motor busca rotas de múltiplos veículos para atender entregas com carga, volume, prioridades, janelas, refrigeração e requisitos de manuseio. A aplicação prepara entregas, veículos, equipe disponível, matriz de distância/tempo e janela operacional.

O routing resolve os caminhos no grafo dirigido. O GA evolui a ordem das entregas; o decoder atribui veículos e forma rotas. As fontes são [`engine.py`](../apps/api/src/fluxmed/optimization/engine.py), [`operators.py`](../apps/api/src/fluxmed/optimization/operators.py), [`decoder.py`](../apps/api/src/fluxmed/optimization/decoder.py), [`fitness.py`](../apps/api/src/fluxmed/optimization/fitness.py) e [`models.py`](../apps/api/src/fluxmed/optimization/models.py).

## Cromossomo e população

Um gene é um UUID de entrega. O cromossomo é uma permutação de todos os IDs, sem repetição. Veículos, profissionais e ruas são tratados pelos módulos de decodificação e aplicação.

A população inicial combina Nearest Neighbor, Best Insertion, três variantes mutadas de cada baseline e permutações aleatórias até o tamanho configurado. A seed controla o gerador pseudoaleatório da busca.

## Operadores e evolução

- Seleção por torneio, comparando a fitness lexicográfica.
- Order Crossover (OX), com segmento herdado de um pai e preenchimento pelos genes do outro, preservando a permutação.
- Mutação swap, insertion ou inversion.
- Elitismo para preservar os melhores indivíduos.
- Taxa de mutação adaptativa e imigrantes conforme estagnação/diversidade.

Uma geração avalia os novos indivíduos e atualiza a melhor solução quando sua tupla melhora. A execução normal termina por `MAX_GENERATIONS` ou `EARLY_STOPPING`, segundo o limite de gerações e a estagnação. O cancelamento é uma interrupção cooperativa tratada pelo lifecycle do run.

## Formação das rotas

O decoder percorre os genes. Para cada entrega, constrói alternativas prospectivas e verifica os filtros ativos. Peso e volume são sempre limitados. Advanced pruning acrescenta compatibilidade de refrigeração/ajudante, autonomia, janelas HARD e fim de jornada.

Entre os veículos elegíveis, a escolha local minimiza:

1. atraso SOFT ponderado prospectivo;
2. risco CRITICAL prospectivo;
3. tempo marginal de viagem, incluindo o efeito sobre o retorno;
4. distância marginal;
5. capacidade de peso restante;
6. capacidade de volume restante;
7. ID do veículo, para desempate.

A atribuição é gulosa. Entregas sem alternativa permanecem não atribuídas e tornam a solução inviável. Custo operacional e inversões globais são avaliados na solução completa.

## Repair

Se houver entregas não atribuídas e repair estiver ativo, `repair_chromosome` embaralha esses genes e os intercala desde o início com os demais, preservando a ordem relativa dos já atribuídos. O candidato é decodificado e avaliado novamente; a alteração é aceita apenas se melhorar a fitness.

As variantes com e sem repair seguem trajetórias estocásticas distintas. O efeito observado é analisado no [experimento oficial](../benchmarks/README.md).

## Ordem lexicográfica

`FitnessVector.sort_key` minimiza a tupla abaixo, da esquerda para a direita. Um critério posterior desempata apenas quando os anteriores são iguais.

| Ordem | Critério |
|---|---|
| 1 | 0 se `feasible`, 1 caso contrário |
| 2 | `hard_violations` |
| 3 | `service_penalty` |
| 4 | `critical_risk` |
| 5 | `priority_inversion_minutes` |
| 6 | `total_cost_brl` |
| 7 | `makespan_minutes` |
| 8 | `travel_minutes` |
| 9 | `distance_km` |
| 10 | `vehicles_used` |

O indicador `team_feasible` reflete-se na viabilidade e nas violações. Restrições e atendimento precedem custo.

## Prioridades e atendimento

Os pesos são **LOW=1, NORMAL=2, HIGH=3 e CRITICAL=4**. Atraso é medido pelo início do atendimento após o fim da janela. Em SOFT, soma-se atraso em minutos multiplicado pelo peso; em HARD, a violação torna a solução inviável.

Para cada CRITICAL com fim de janela, o risco soma `max(0, 30 − folga)`, sendo folga = fim da janela − início do atendimento, em minutos. Soma-se ainda três vezes o atraso. Uma CRITICAL atendida 10 minutos antes do limite contribui com 20; cinco minutos depois contribui com `35 + 3 × 5 = 50`.

As inversões abrangem todas as rotas. Para cada atendimento de prioridade menor iniciado antes de outro de prioridade maior, soma-se `(peso maior − peso menor) × intervalo entre inícios`. LOW às 08:00 antes de HIGH às 08:10 contribui com 20. Prioridades iguais e inícios simultâneos acrescentam zero.

O efeito de alterar uma prioridade depende das alternativas disponíveis e dos critérios anteriores na tupla; a regra não exige mudar toda rota.

## Cronologia e espera

```text
chegada = saída anterior + viagem
início do atendimento = máximo(chegada, abertura da janela)
espera = início do atendimento − chegada
saída = início do atendimento + serviço
duração = viagem total + serviço total + espera total
```

A viagem inclui ida, trechos entre entregas e retorno ao depósito. Como as rotas partem no início da operação, makespan é a maior duração. A jornada considera o retorno.

Exemplo: partida 08:00, viagem 10 min, abertura 09:00, serviço 5 min e retorno 10 min produzem chegada 08:10, espera 50 min e retorno 09:15. A duração é `20 + 5 + 50 = 75 min`.

## Equipe e avaliação operacional

[`OperationalFitnessEvaluator`](../apps/api/src/fluxmed/application/optimization/evaluation.py) usa os mesmos [`TeamAssignmentSolver`](../apps/api/src/fluxmed/application/optimization/team_assignment.py) e [`FinalCostEngine`](../apps/api/src/fluxmed/application/optimization/cost_engine.py) da persistência.

O matching atribui profissionais compatíveis de custo mínimo para as rotas construídas. Considera papel, atividade, disponibilidade selecionada na data e pessoal incluído em contrato. Cada profissional atende uma rota. Ajudante é exigido por política `REQUIRED` ou entrega `TWO_PERSON`; `FORBIDDEN` impede a atribuição incompatível.

Falha de atribuição marca `team_feasible=false`, torna o candidato inviável e acrescenta uma violação antes da escolha final. O cache de até 512 combinações por avaliador reutiliza equipe/custo para veículo, distância, duração e necessidade de duas pessoas equivalentes; a qualidade é recalculada.

## Custo operacional

| Parcela | Regra |
|---|---|
| Veículo próprio | km × depreciação/km + km × manutenção/km + horas × custo fixo/hora |
| Agregado | Preço do contrato por rota |
| Combustível não incluído | km / eficiência × R$ 6,00/L, referência sintética do modelo |
| Equipe | Remuneração efetiva por hora, diária ou rota, conforme cadastro |

Pessoal e combustível incluídos em contrato não geram cobrança adicional. A espera integra os componentes por hora; diárias, contratos e valores por rota seguem seus regimes.

O custo interno do decoder é provisório; a avaliação operacional substitui esse total pelas regras acima. O benchmark de Santa Aurora usa esse avaliador em todos os métodos, com cache próprio por método/seed.

## Validação independente

`SolutionValidator` recebe entregas, veículos, matriz e início/fim originais. Reconstrói:

- cobertura, unicidade, IDs conhecidos e ausência de entregas pendentes;
- veículos conhecidos e uso de cada veículo em uma única rota;
- carga/volume e comparação com capacidades e totais declarados;
- trechos de ida/retorno, distância, viagem, autonomia e métricas válidas;
- quantidade/ordem das paradas, prioridade, chegada, espera, serviço e saída;
- janelas HARD, atraso, duração, retorno, jornada e compatibilidade.

A acessibilidade viária é tratada na preparação da matriz. O solver verifica a disponibilidade global da equipe durante avaliação e persistência. Divergências de validação ou inviabilidade impedem publicar o plano como válido.

## Matriz e routing

Cada par da matriz e sua geometria usam o horário inicial da operação como referência de partida. Dentro de cada caminho, o routing considera o horário estimado de entrada nas arestas. A cronologia do VRP reutiliza os tempos da matriz, incluindo os efeitos de serviço e espera sobre os atendimentos.

## Configuração e evidências

`GeneticOptimizerConfig` define população, torneio, crossover, mutação, elitismo, estagnação, diversidade, imigrantes, pruning e repair. O [manifesto](../benchmarks/results/final-evidence-operational-20261031/matrix-manifest.json) registra os parâmetros e seeds do estudo.

A busca é heurística. A avaliação de qualidade e custo e os limites das conclusões são apresentados junto aos [resultados experimentais](../benchmarks/README.md). A [comparação com a FIAP](FIAP_TSP_BASE.md) documenta a referência conceitual. O [trace](OPTIMIZATION_TRACE.md) descreve progresso, eventos e replay.
