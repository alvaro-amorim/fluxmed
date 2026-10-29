# FluxMed — benchmarks acadêmicos e evidências reproduzíveis

Esta pasta contém o **código de avaliação comparativa** e o conjunto oficial de evidências da Fase 2 do Tech Challenge (Projeto 2: otimização de rotas médicas). O objetivo não é afirmar que o algoritmo genético sempre encontra a rota mais barata, mas avaliar sua capacidade de obter soluções viáveis sob restrições hospitalares, qualidade das soluções e custo computacional.

## Evidência oficial

**[Abrir o relatório experimental consolidado](results/final-evidence-20260917/academic-summary.md)**

| Arquivo | Finalidade |
|---|---|
| [academic-summary.md](results/final-evidence-20260917/academic-summary.md) | Tabelas por cenário, viabilidade, custo e tempo |
| [benchmark-summaries.csv](results/final-evidence-20260917/benchmark-summaries.csv) | Estatísticas agregadas por cenário e método |
| [benchmark-runs.csv](results/final-evidence-20260917/benchmark-runs.csv) | Resultados individuais, seeds, violações e tempos |
| [benchmark-convergence.csv](results/final-evidence-20260917/benchmark-convergence.csv) | Evolução do GA por geração |
| [matrix-manifest.json](results/final-evidence-20260917/matrix-manifest.json) | Parâmetros, operações, cenários e seeds efetivamente usados |
| [benchmark-report.json](results/final-evidence-20260917/benchmark-report.json) | Registro estruturado completo da execução |
| [charts/](results/final-evidence-20260917/charts/) | Gráficos vetoriais da comparação |

A pasta `results/final-evidence-20260917/` é a **evidência acadêmica final publicada**. As demais pastas locais de `results/` (`smoke`, `*-quick`, `validation-*`) são testes exploratórios/de desenvolvimento e **não** integram a análise final.

## Desenho do experimento

A matriz experimental registrada no [manifesto](results/final-evidence-20260917/matrix-manifest.json) combina:

- **4 perfis:** `NORMAL`, `BUSY`, `HIGH_PRESSURE`, `EMERGENCY`;
- **4 escalas:** 20, 40, 60 e 80 entregas;
- **16 cenários distintos** (perfis × escalas), com `scenario_seed=20260917`;
- **5 métodos:** Nearest Neighbor, Best Insertion, GA Basic, GA + Pruning, GA + Pruning + Repair;
- **5 seeds para cada variante de GA:** 101, 202, 303, 404 e 505;
- **1 execução determinística por cenário** para cada heurística.

Total: **272 execuções** (32 heurísticas + 240 de GA). Cada variante do GA tem 80 execuções. Isso **não representa 272 cenários independentes**. O preset final foi executado com `quick=false`, população de 48 indivíduos, até 120 gerações, cruzamento 0,90, mutação inicial 0,22, torneio de 3 indivíduos e parada por 25 gerações sem melhoria. Os demais parâmetros estão versionados no manifesto.

O experimento reutiliza as mesmas entregas, recursos, matriz de deslocamento e janela operacional dentro de cada cenário. As variantes diferem em pruning e repair; os baselines não recebem repair. Violações de restrições desativadas continuam contabilizadas como inviabilidade, não são descartadas da análise.

## Principais resultados observados

| Método | Soluções viáveis | Taxa | Tempo médio do otimizador |
|---|---:|---:|---:|
| Nearest Neighbor | 5/16 | 31,25% | 0,012 s |
| Best Insertion | 3/16 | 18,75% | 0,115 s |
| GA Basic | 14/80 | 17,50% | 41,893 s |
| GA + Pruning | 60/80 | 75,00% | 37,046 s |
| **GA + Pruning + Repair** | **80/80** | **100,00%** | **56,309 s** |

**Interpretação:** a configuração completa aumentou a frequência de soluções viáveis dentro desta matriz experimental, ao custo de maior tempo médio. A diferença entre GA + Pruning e GA + Pruning + Repair é de 20 execuções viáveis (60/80 versus 80/80). Não se deve concluir, a partir disso, que o GA é universalmente superior a qualquer heurística ou que a melhora de viabilidade é gratuita.

Na comparação pareada dos **60 pares cenário + seed em que as duas variantes encontraram soluções viáveis**, adicionar repair resultou em menor custo em 31 pares, maior custo em 24 e empate em 5. Logo, repair **não reduziu o custo em todas as execuções**, e comparar médias de custo entre grupos com taxas de viabilidade diferentes exige cuidado.

**Escopo das métricas:** `cost_brl` neste conjunto é o **custo do fitness do benchmark**, não necessariamente o custo operacional final persistido (que pode incluir composição posterior de equipe). Custos são comparáveis principalmente **dentro do mesmo cenário e com soluções viáveis**. Quando um método não encontra solução viável, seu custo não deve ser usado para afirmar vantagem econômica. O tempo de execução mede somente o otimizador, sem geração do cenário e exportação de artefatos.

## Gráficos

- [Viabilidade por escala](results/final-evidence-20260917/charts/feasibility-by-scale.svg)
- [Tempo de execução por escala](results/final-evidence-20260917/charts/runtime-by-scale.svg)
- [Violações de restrições no GA](results/final-evidence-20260917/charts/ga-hard-violations-by-scale.svg)
- [Custo dos pares pruning × repair](results/final-evidence-20260917/charts/paired-pruning-repair-cost-by-scale.svg)
- [Convergência das violações](results/final-evidence-20260917/charts/convergence-hard-violations.svg)

## Reexecução do estudo

O benchmark opera em modo de **leitura** sobre uma operação já existente em Santa Aurora, usando sua frota, equipe, janela e configurações de tráfego. A execução original utilizou `OP-20260915-001`, conforme o manifesto.

O seed padrão do Docker cria a cidade e o usuário demo, mas não a operação-base. O [fixture acadêmico](../apps/api/src/fluxmed/benchmarks/fixtures/operation-OP-20260915-001.json) registra o ID da operação, a janela, os sete veículos e os 12 profissionais selecionados, com IDs e custos originais. Ele contém apenas recursos demonstrativos; as entregas da matriz são geradas em memória pelo benchmark. Não execute o seed acadêmico sobre um catálogo de recursos já preenchido: ele recusa substituir dados existentes.

Depois de `docker compose up --build -d` em um clone limpo, crie a operação-base com a imagem da API:

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
```

A execução completa pode demorar e utiliza CPU. Preserve os artefatos acadêmicos versionados. A reconstrução do cenário `NORMAL-20` foi comparada com a operação original em um banco de teste transacional: entregas, veículos, janela e matriz de deslocamento coincidiram exatamente. O teste de regressão registra um hash desse input. Tempos de execução variam conforme hardware e carga; resultados de uma nova execução devem ser apresentados separadamente dos dados arquivados.

## Limitações e cuidados metodológicos

1. A cidade Santa Aurora e as demandas são **sintéticas**, não uma validação em logística hospitalar real.
2. Há uma única seed de geração de cenário para cada célula; as cinco seeds de GA exploram **aleatoriedade do otimizador**, não cinco cidades ou demandas independentes.
3. Os tempos foram medidos no ambiente do experimento; não são garantias de performance em computadores diferentes.
4. As heurísticas determinísticas executam uma vez por cenário, enquanto cada GA executa cinco vezes; a comparação de percentuais exige reconhecer essa diferença.
5. O benchmark não comprova otimalidade matemática nem garante superioridade de custo do GA em toda instância.
6. O fixture restaura os parâmetros operacionais e IDs usados pela matriz em um banco limpo. A igualdade dos inputs foi validada para `NORMAL-20`; não se promete repetição byte a byte de tempos ou de todos os artefatos em outro ambiente.
7. Os gráficos e as tabelas são gerados automaticamente dos dados experimentais, mas as interpretações são limitadas às instâncias testadas.

Para o relatório acadêmico, priorize viabilidade e restrições, apresente custo apenas nos pares comparáveis e discuta o trade-off com tempo computacional. Para a arquitetura e restrições do algoritmo, consulte [docs/OPTIMIZATION_SPEC.md](../docs/OPTIMIZATION_SPEC.md) e [docs/BENCHMARK_PLAN.md](../docs/BENCHMARK_PLAN.md).
