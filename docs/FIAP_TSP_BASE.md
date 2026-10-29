# Relação entre o código-base TSP da FIAP e o FluxMed

O [repositório oficial da FIAP](https://github.com/FIAP/genetic_algorithm_tsp/tree/d236a2ae6a08fefdb8ee9f1ca3f8201223a92da3) foi disponibilizado após a implementação do otimizador FluxMed. Esta análise usa o commit `d236a2a` e compara os componentes de forma verificável. **O código de produção do FluxMed foi desenvolvido independentemente; não é um fork nem uma modificação linha a linha do código da FIAP.**

## Correspondência técnica

| Conceito | Código-base da FIAP | FluxMed |
|---|---|---|
| Representação | Lista de coordenadas de cidades em uma única permutação. | Permutação de IDs de entregas, decodificada em rotas de múltiplos veículos. |
| População | Permutações aleatórias. | População inicial com heurísticas e variantes aleatórias. |
| Distância | Distância euclidiana entre pontos, incluindo retorno ao início. | Matriz de deslocamento no grafo viário dirigido, com distância e tempo por par de locais. |
| Fitness | Soma escalar das distâncias. | Ordenação lexicográfica: viabilidade, violações, atraso/risco, custo, duração, tempo, distância e frota. |
| Seleção | Amostragem dos melhores ou por probabilidade inversa da distância. | Torneio com semente controlada. |
| Crossover | Order Crossover entre permutações. | Order Crossover tipado, com validação de genes e preservação da permutação. |
| Mutação | Troca de duas cidades vizinhas. | Swap, insertion e inversion, com taxa adaptativa. |
| Elitismo | Mantém o melhor indivíduo. | Elitismo, imigrantes e parada por estagnação. |
| Visualização | Pygame desenha cidades, rota e evolução da distância. | Interface web exibe mapa, rotas, paradas, indicadores e progresso. |

Fontes do código-base: [`genetic_algorithm.py`](https://github.com/FIAP/genetic_algorithm_tsp/blob/d236a2ae6a08fefdb8ee9f1ca3f8201223a92da3/genetic_algorithm.py) e [`tsp.py`](https://github.com/FIAP/genetic_algorithm_tsp/blob/d236a2ae6a08fefdb8ee9f1ca3f8201223a92da3/tsp.py). Implementação FluxMed: [`operators.py`](../apps/api/src/fluxmed/optimization/operators.py), [`engine.py`](../apps/api/src/fluxmed/optimization/engine.py), [`decoder.py`](../apps/api/src/fluxmed/optimization/decoder.py), [`fitness.py`](../apps/api/src/fluxmed/optimization/fitness.py) e [`models.py`](../apps/api/src/fluxmed/optimization/models.py).

## Por que não substituir o motor atual

O exemplo da FIAP é didático e resolve uma rota TSP sem capacidade, autonomia, janelas ou múltiplos veículos. Importá-lo para a execução atual eliminaria invariantes e exigiria reescrever seus dados e funções. Além disso, o caminho ativo em `tsp.py` chama `order_crossover(parent1, parent1)`; os dois pais são iguais nessa chamada, então ela não combina informação de indivíduos distintos. O FluxMed usa dois pais selecionados e testa a preservação da permutação.

O fluxo acadêmico correspondente foi **reimplementado e ampliado**, mantendo os conceitos de população, crossover, mutação, avaliação e elitismo. A origem histórica deve ser descrita com precisão: o FluxMed já possuía essa implementação quando o link oficial chegou. A comparação documenta aderência conceitual e funcional; **não comprova que o arquivo fornecido foi usado como ponto de partida literal**. Se a avaliação exigir um histórico de alterações sobre o repositório da FIAP, é necessário esclarecer esse critério com a instituição.

## Evidência de validação

Os testes de otimização verificam permutação após crossover e mutações, preferência por soluções viáveis, detecção de entregas ausentes ou duplicadas, restrições de autonomia e refrigeração e reprodutibilidade com seed. O benchmark publicado compara duas heurísticas e três configurações do GA em 16 cenários: [método e resultados](../benchmarks/README.md).
