# FluxMed — benchmarks acadêmicos e evidências reproduzíveis

Esta pasta reúne as evidências experimentais da Fase 2, Projeto 2: otimização de rotas médicas. O estudo avalia viabilidade, qualidade de atendimento, custo operacional e tempo computacional em cenários sintéticos controlados.

O [relatório técnico](../docs/academic/Relatorio-Tecnico-FluxMed.pdf) e o [vídeo acadêmico](https://youtu.be/gHc-irrihV0) apresentam o método e os resultados. A operação criada na demonstração da aplicação é distinta dos cenários da matriz oficial; seus indicadores não integram as 272 execuções do experimento.

## Evidência oficial

**[Abrir o relatório experimental final de 31/10/2026](results/final-evidence-operational-20261031/academic-summary.md)**

| Arquivo | Finalidade |
|---|---|
| [academic-summary.md](results/final-evidence-operational-20261031/academic-summary.md) | Tabelas por cenário, viabilidade, custo e tempo |
| [benchmark-summaries.csv](results/final-evidence-operational-20261031/benchmark-summaries.csv) | Estatísticas agregadas por cenário e método |
| [benchmark-runs.csv](results/final-evidence-operational-20261031/benchmark-runs.csv) | Resultados individuais, seeds, violações e tempos |
| [benchmark-convergence.csv](results/final-evidence-operational-20261031/benchmark-convergence.csv) | Evolução do GA por geração |
| [matrix-manifest.json](results/final-evidence-operational-20261031/matrix-manifest.json) | Parâmetros, operações, cenários e seeds efetivamente usados |
| [benchmark-report.json](results/final-evidence-operational-20261031/benchmark-report.json) | Registro completo, soluções decodificadas e ocorrências da validação |
| [experiment.json](results/final-evidence-operational-20261031/experiment.json) e [source-snapshot.zip](results/final-evidence-operational-20261031/source-snapshot.zip) | Identificação verificável e cópia dos arquivos de código relevantes |
| [scenarios/](results/final-evidence-operational-20261031/scenarios/) | Inputs e relatórios por cenário; `complete.json` certifica a conclusão com checksums |
| [audit.json](results/final-evidence-operational-20261031/audit.json) e [verification.json](results/final-evidence-operational-20261031/verification.json) | Conferências dos dados brutos, métricas e verificações locais |
| [paired-pruning-repair.csv](results/final-evidence-operational-20261031/paired-pruning-repair.csv) | Custos e qualidade nos 62 pares viáveis de mesmo cenário e seed |
| [hardware.json](results/final-evidence-operational-20261031/hardware.json) e [execution.log](results/final-evidence-operational-20261031/execution.log) | Ambiente e acompanhamento da execução |
| [charts/](results/final-evidence-operational-20261031/charts/) | Gráficos vetoriais da comparação |

A análise final usa exclusivamente `results/final-evidence-operational-20261031/`.

`experiment.json` e `source-snapshot.zip` identificam a fonte usada. O SHA-256 do conjunto de arquivos é `c4368d3b6e6ba81917b3ad47a6b28ad71ba73584a597ca616ab2a797c14a5830`. O registro inclui hashes por arquivo, receita e ambiente; o snapshot contém os arquivos permitidos de código, testes, migrações, scripts e fixtures.

## Desenho do experimento

A matriz experimental registrada no [manifesto](results/final-evidence-operational-20261031/matrix-manifest.json) combina:

- **4 perfis:** `NORMAL`, `BUSY`, `HIGH_PRESSURE`, `EMERGENCY`;
- **4 escalas:** 20, 40, 60 e 80 entregas;
- **16 cenários distintos** (perfis × escalas), com `scenario_seed=20260917`;
- **5 métodos:** Nearest Neighbor, Best Insertion, GA Basic, GA + Pruning, GA + Pruning + Repair;
- **5 seeds para cada variante de GA:** 101, 202, 303, 404 e 505;
- **1 execução determinística por cenário** para cada heurística.

Total: **272 execuções** (32 heurísticas + 240 de GA). Cada variante do GA tem 80 execuções. Isso **não representa 272 cenários independentes**. O preset final foi executado com `quick=false`, população de 48 indivíduos, até 120 gerações, cruzamento 0,90, mutação inicial 0,22, torneio de 3 indivíduos e parada por 25 gerações sem melhoria. Os demais parâmetros estão versionados no manifesto.

O experimento reutiliza as mesmas entregas, recursos, matriz de deslocamento e janela operacional dentro de cada cenário. As variantes diferem em pruning e repair; os baselines não recebem repair. Violações de restrições desativadas continuam contabilizadas como inviabilidade. Todos os métodos usam o mesmo avaliador operacional e a validação final independente. Cada método/seed recebe um avaliador próprio, sem compartilhar cache de custo entre execuções.

## Principais resultados observados

| Método | Soluções viáveis | Taxa | Tempo médio do otimizador |
|---|---:|---:|---:|
| Nearest Neighbor | 5/16 | 31,25% | 0,015 s |
| Best Insertion | 3/16 | 18,75% | 0,111 s |
| GA Basic | 13/80 | 16,25% | 51,325 s |
| GA + Pruning | 62/80 | 77,50% | 49,810 s |
| **GA + Pruning + Repair** | **80/80** | **100,00%** | **82,846 s** |

**Interpretação:** a configuração completa obteve 18 execuções viáveis a mais que GA + Pruning (62/80 versus 80/80), com maior tempo médio nesta amostra.

Nos **62 pares cenário + seed em que ambas as variantes foram viáveis**, repair teve custo menor em **33**, maior em **25** e igual em **4**. A qualidade lexicográfica do atendimento (atraso ponderado, risco CRITICAL, inversões) foi melhor em 37, pior em 21 e igual em 4. Portanto, mesmo os pares viáveis podem diferir em atendimento; o custo isolado não expressa toda a fitness. O repair aceita melhorias locais, mas as variantes seguem trajetórias estocásticas diferentes: o resultado é interpretado no conjunto de cenários e seeds observado.

**Escopo das métricas:** `cost_brl` usa o mesmo `TeamAssignmentSolver` e `FinalCostEngine` da aplicação: veículo/contrato, combustível quando não incluído e remuneração efetiva da equipe, respeitando seus regimes de cobrança. A indisponibilidade de equipe torna o candidato inviável durante a busca. Espera por janela entra na duração, no makespan e nos custos por hora. A ordem da fitness é viabilidade, violações, atraso SOFT ponderado por prioridade, risco CRITICAL, inversões de prioridade, custo operacional, makespan, viagem, distância e veículos. [Regras e validação](../docs/OPTIMIZATION_SPEC.md).

Custos só sustentam comparação econômica entre soluções viáveis de cenários equivalentes, com o mesmo critério; restrições e qualidade precedem custo. Custos de candidatos inviáveis não demonstram vantagem econômica. O tempo médio inclui execuções viáveis e inviáveis e mede somente o método de otimização, sem geração do cenário e exportação.

## Gráficos

- [Viabilidade por escala](results/final-evidence-operational-20261031/charts/feasibility-by-scale.svg)
- [Tempo de execução por escala](results/final-evidence-operational-20261031/charts/runtime-by-scale.svg)
- [Violações de restrições no GA](results/final-evidence-operational-20261031/charts/ga-hard-violations-by-scale.svg)
- [Custo dos pares pruning × repair](results/final-evidence-operational-20261031/charts/paired-pruning-repair-cost-by-scale.svg)
- [Convergência das violações](results/final-evidence-operational-20261031/charts/convergence-hard-violations.svg)

## Reexecução do estudo

O benchmark opera em modo de **leitura** sobre uma operação já existente em Santa Aurora, usando sua frota, equipe, janela e configurações de tráfego. O modelo é `OP-20260915-001`, de 15/09/2026, janela 07:30–18:00 e tráfego `AUTOMATIC`. As entregas de cada célula são geradas em memória.

O seed padrão do Docker cria a cidade e o usuário demo, mas não a operação-base. O [fixture acadêmico](../apps/api/src/fluxmed/benchmarks/fixtures/operation-OP-20260915-001.json) registra o ID da operação, a janela, os sete veículos e os 12 profissionais selecionados, com IDs e custos originais. Ele contém apenas recursos demonstrativos; as entregas da matriz são geradas em memória pelo benchmark. Não execute o seed acadêmico sobre um catálogo de recursos já preenchido: ele recusa substituir dados existentes.

Use uma instalação acadêmica separada, com banco/volume dedicado e portas sem conflito com a demonstração. Depois de `docker compose up --build -d` nessa instalação limpa, crie a operação-base com a imagem da API:

```powershell
docker compose run --rm --no-deps init python -m fluxmed.scripts.seed_benchmark_template --seed
```

O mesmo seed pode ser executado no host com `python scripts/seed_benchmark_template.py --seed`, usando o ambiente virtual da API. Sem `--seed`, o comando apenas confere em leitura se uma operação existente corresponde ao fixture. O seed é idempotente quando a operação já coincide e falha sem sobrescrever recursos divergentes.

Com o Python da API instalado e PostgreSQL disponível, execute **na raiz do repositório**:

```powershell
# Smoke: valida o mecanismo, não serve como evidência acadêmica de Santa Aurora.
python scripts/benchmark_optimizer.py --smoke --seeds 101 202 303

# Exemplo rápido com uma operação local existente:
python scripts/benchmark_optimizer.py --matrix-template-code CODIGO_DA_SUA_OPERACAO --profiles NORMAL --sizes 20 --scenario-seeds 20260917 --quick --seeds 101

# Preset final de 16 cenários × 5 seeds de GA; grava em uma pasta separada:
python scripts/benchmark_optimizer.py --matrix-template-code OP-20260915-001 --preset final --output benchmarks/results/minha-reexecucao

# Retomada da mesma execução, com os mesmos parâmetros, código e ambiente:
python scripts/benchmark_optimizer.py --matrix-template-code OP-20260915-001 --preset final --output benchmarks/results/minha-reexecucao --resume
```

A pasta de saída deve ser nova na primeira execução. Cada cenário concluído grava seu input e relatórios antes de criar atomicamente `complete.json`. Uma interrupção pode exigir repetir o cenário incompleto; os completos são conferidos e reutilizados. A retomada reconstrói os inputs, verifica hashes e recusa código, ambiente, parâmetros, inputs ou arquivos divergentes; o bloqueio da pasta impede escritores simultâneos. Os agregados são reconstruídos sem duplicar execuções. Não edite o código relevante durante a matriz nem use `--resume` para combinar experimentos diferentes.

Os inputs de cada célula, recursos, configuração e hashes ficam preservados no diretório oficial. Uma reprodução deve usar outra pasta de saída e manter seus próprios tempos e arquivos.

## Condições de interpretação

1. A cidade e as demandas são sintéticas, com quatro perfis e quatro escalas controlados.
2. Há uma seed de demanda por célula. As cinco seeds de GA exploram a aleatoriedade do otimizador sobre essas entradas.
3. As heurísticas executam uma vez por cenário; cada GA executa cinco vezes. As taxas usam denominadores diferentes.
4. O ambiente é Windows 11, Python 3.12.10, Intel Core i7-1355U (10 núcleos/12 processadores lógicos), com PostgreSQL/PostGIS em Docker dedicado e métodos sequenciais. Tempos dependem do hardware e da carga.
5. Custos são comparados entre soluções viáveis equivalentes. Qualidade de atendimento precede custo e pode diferir nos pares.
6. O desenho experimental caracteriza a heurística nas instâncias observadas; não comprova ótimo global ou superioridade universal.
7. Cada par da matriz e da geometria usa a referência inicial da operação. A cronologia do decoder reutiliza esses tempos, incluindo serviço e espera.
