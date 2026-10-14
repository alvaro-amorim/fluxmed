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

No repositório, a operação-base **não é criada automaticamente** pelo seed padrão do Docker. Por isso um clone limpo, apesar de executar perfeitamente a aplicação, **ainda não possui os dados suficientes para reproduzir exatamente o experimento original**. Não descreva o comando abaixo como reprodutível a partir do zero sem restaurar/reconstituir previamente a operação-base com as mesmas características. O registro de resultados e o manifesto permitem **inspecionar e auditar** o estudo já executado; a reprodução integral requer a entrada operacional equivalente.

Depois de inicializar o banco Santa Aurora, criar uma operação-base com recursos selecionados e instalar as dependências de `apps/api`, execute **na raiz do repositório** (Python da API/ambiente virtual ativo):

```powershell
# Smoke: valida o mecanismo, não serve como evidência acadêmica de Santa Aurora.
python scripts/benchmark_optimizer.py --smoke --seeds 101 202 303

# Exemplo rápido com uma operação local existente:
python scripts/benchmark_optimizer.py --matrix-template-code CODIGO_DA_SUA_OPERACAO --profiles NORMAL --sizes 20 --scenario-seeds 20260917 --quick --seeds 101

# Preset final de 16 cenários × 5 seeds de GA; exige a operação original no banco:
python scripts/benchmark_optimizer.py --matrix-template-code OP-20260915-001 --preset final
```

A execução completa pode demorar e utiliza CPU. O último comando não deve sobrescrever os artefatos acadêmicos versionados sem comparação com a evidência original. Se for executar um novo estudo, informe uma pasta de saída diferente por meio do argumento `--output`.

## Limitações e cuidados metodológicos

1. A cidade Santa Aurora e as demandas são **sintéticas**, não uma validação em logística hospitalar real.
2. Há uma única seed de geração de cenário para cada célula; as cinco seeds de GA exploram **aleatoriedade do otimizador**, não cinco cidades ou demandas independentes.
3. Os tempos foram medidos no ambiente do experimento; não são garantias de performance em computadores diferentes.
4. As heurísticas determinísticas executam uma vez por cenário, enquanto cada GA executa cinco vezes; a comparação de percentuais exige reconhecer essa diferença.
5. O benchmark não comprova otimalidade matemática nem garante superioridade de custo do GA em toda instância.
6. A reexecução byte a byte depende dos dados e parâmetros da operação-base original. **Fornecer um fixture/export sanitizado dessa operação é uma melhoria pendente de reprodutibilidade**.
7. Os gráficos e as tabelas são gerados automaticamente dos dados experimentais, mas as interpretações são limitadas às instâncias testadas.

Para o relatório acadêmico, priorize viabilidade e restrições, apresente custo apenas nos pares comparáveis e discuta o trade-off com tempo computacional. Para a arquitetura e restrições do algoritmo, consulte [docs/OPTIMIZATION_SPEC.md](../docs/OPTIMIZATION_SPEC.md) e [docs/BENCHMARK_PLAN.md](../docs/BENCHMARK_PLAN.md).
