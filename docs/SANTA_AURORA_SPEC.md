# FluxMed — Santa Aurora e routing

## Dataset sintético

Santa Aurora fornece a rede geográfica para planejamento e experimentação controlada. O gerador cria bairros, ruas, interseções, segmentos dirigidos, lotes, edifícios, endereços e instalações, incluindo o depósito.

Os defaults do [gerador](../apps/api/src/fluxmed/city/generator.py) são `dataset_version=1.1.0`, `generation_seed=20260913` e `generator_version=santa-aurora-v2`. A cidade registra sua identidade e o fuso operacional. O experimento usa a identidade registrada no manifesto.

## Vínculos geográficos

Endereços pertencem ao catálogo da cidade e referenciam um segmento viário e uma posição nele. A construção do percurso considera os acessos da origem e do destino ao grafo. Interseções e segmentos definem conexões dirigidas; o routing respeita os sentidos e os segmentos fechados.

O banco mantém geometria e vínculos por PostGIS. A interface consulta dados e GeoJSON para apresentar mapa, endereços e rotas. Campos e relações estão em [DOMAIN_MODEL.md](DOMAIN_MODEL.md); consultas estão em [API_SPEC.md](API_SPEC.md).

## Caminhos

`RoutingEngine.shortest_path` recebe nós de origem/destino, horário de partida, modo de trânsito, algoritmo e condições da operação. O motor oferece A* e Dijkstra. O resultado contém nós/arestas, distância, tempo, partida, chegada, bucket e geometria.

Durante a exploração do caminho, o horário de entrada em cada aresta é estimado pela partida e pelo tempo acumulado. O tempo base é combinado com o fator de trânsito correspondente.

## Trânsito

Os modos são `FREE`, `AUTOMATIC` e `CUSTOM`. Um override aplicável determina o fator do segmento; sem override, FREE/CUSTOM usam 1,00 e AUTOMATIC combina horário, classe de via e bairro, com mínimo de 1,00.

| Intervalo local, início inclusivo e fim exclusivo | Fator temporal AUTOMATIC |
|---|---:|
| 06:00–07:00 | 1,12 |
| 07:00–09:00 | 1,38 |
| 09:00–11:00 | 1,18 |
| 11:00–14:00 | 1,24 |
| 14:00–16:00 | 1,16 |
| 16:00–19:00 | 1,48 |
| 19:00–22:00 | 1,10 |
| Demais horários | 1,00 |

| Nível de override | Multiplicador |
|---|---:|
| FREE | 1,00 |
| LIGHT | 1,10 |
| MODERATE | 1,25 |
| HEAVY | 1,55 |
| VERY_HEAVY | 1,90 |

O rótulo de bucket usa 15 minutos por padrão, como `07:30-07:45`. Os fatores de horário são os intervalos da tabela. A implementação está em [traffic.py](../apps/api/src/fluxmed/routing/traffic.py).

## Matriz usada pelo GA

[`RoutingMatrixBuilder`](../apps/api/src/fluxmed/application/optimization/routing_matrix.py) calcula cada par de endereços com a partida de referência no início da operação. O cálculo de cada caminho considera os fatores temporais das arestas. Os resultados são convertidos de metros/segundos para km/minutos na matriz.

O decoder reutiliza essa matriz ao formar as rotas e a cronologia de atendimento. Serviço e espera afetam os horários subsequentes; os pares da matriz permanecem os preparados para aquela execução. O desenho das rotas usa a mesma referência por par, mantendo a correspondência com as métricas.

## Reprodução

A inicialização local aplica migrações e gera o catálogo demonstrativo. O [guia local](LOCAL_SETUP.md) documenta o ambiente; o [benchmark](../benchmarks/README.md) documenta operação-modelo, demanda, seeds, identidade dos inputs e resultados.
