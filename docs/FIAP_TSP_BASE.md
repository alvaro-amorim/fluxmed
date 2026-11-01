# FluxMed — referência TSP da FIAP

O exemplo [FIAP/genetic_algorithm_tsp](https://github.com/FIAP/genetic_algorithm_tsp/tree/d236a2ae6a08fefdb8ee9f1ca3f8201223a92da3), fixado no commit `d236a2a`, é a referência conceitual desta comparação. O FluxMed é uma implementação própria para VRP com restrições; essa relação conceitual não corresponde à modificação literal dos arquivos do exemplo.

## Correspondência técnica


| Conceito | Código-base da FIAP | FluxMed |
|---|---|---|
| Representação | Lista de coordenadas de cidades em uma única permutação. | Permutação de IDs de entregas, decodificada em rotas de múltiplos veículos. |
| População | Permutações aleatórias. | População inicial com heurísticas e variantes aleatórias. |
| Distância | Distância euclidiana entre pontos, incluindo retorno ao início. | Matriz de deslocamento no grafo viário dirigido, com distância e tempo por par de locais. |
| Fitness | Soma escalar das distâncias. | Ordenação lexicográfica: viabilidade, violações, atraso SOFT ponderado, risco CRITICAL, inversões de prioridade, custo operacional com combustível/equipe, makespan, viagem, distância e veículos. |
| Seleção | Amostragem dos melhores ou por probabilidade inversa da distância. | Torneio com semente controlada. |
| Crossover | Order Crossover entre permutações. | Order Crossover tipado, com validação de genes e preservação da permutação. |
| Mutação | Troca de duas cidades vizinhas. | Swap, insertion e inversion, com taxa adaptativa. |
| Elitismo | Mantém o melhor indivíduo. | Elitismo, imigrantes e parada por estagnação. |
| Visualização | Pygame desenha cidades, rota e evolução da distância. | Interface web exibe mapa, rotas, paradas, indicadores e progresso. |

Fontes do código-base: [`genetic_algorithm.py`](https://github.com/FIAP/genetic_algorithm_tsp/blob/d236a2ae6a08fefdb8ee9f1ca3f8201223a92da3/genetic_algorithm.py) e [`tsp.py`](https://github.com/FIAP/genetic_algorithm_tsp/blob/d236a2ae6a08fefdb8ee9f1ca3f8201223a92da3/tsp.py). Implementação FluxMed: [`operators.py`](../apps/api/src/fluxmed/optimization/operators.py), [`engine.py`](../apps/api/src/fluxmed/optimization/engine.py), [`decoder.py`](../apps/api/src/fluxmed/optimization/decoder.py), [`fitness.py`](../apps/api/src/fluxmed/optimization/fitness.py) e [`models.py`](../apps/api/src/fluxmed/optimization/models.py).


## Verificação

Os operadores do FluxMed preservam a permutação. O decoder forma rotas de múltiplos veículos; o avaliador considera atendimento e custo operacional; a validação reconstrói as restrições das entradas originais. O [guia do algoritmo](OPTIMIZATION_SPEC.md) descreve essas regras e o [experimento](../benchmarks/README.md) compara as configurações e heurísticas sob entradas equivalentes.
