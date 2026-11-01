# FluxMed — protocolo experimental

## Desenho

O protocolo combina quatro perfis (NORMAL, BUSY, HIGH_PRESSURE, EMERGENCY), quatro escalas (20, 40, 60, 80) e seed de demanda 20260917. Cada cenário é oferecido aos mesmos cinco métodos: Nearest Neighbor, Best Insertion, GA básico, GA + pruning e GA + pruning + repair.

As heurísticas executam uma vez por cenário. Cada GA usa seeds 101, 202, 303, 404 e 505: 16 cenários e 272 execuções únicas. A operação-modelo fixa recursos, data, janela e trânsito; as entregas são geradas em memória.

## Comparabilidade

- Mesmas entregas, matriz, recursos e janela dentro de cada cenário.
- Mesmo avaliador operacional e validação final independente.
- Ablação por flags de advanced pruning e repair, com parâmetros genéticos registrados.
- Custos comparados entre soluções viáveis e cenários equivalentes, considerando os critérios de atendimento que precedem custo.
- Pareamento de pruning/repair por cenário e seed quando ambos são viáveis.

## Registro

O experimento preserva input e resultados por cenário, seeds, configuração, código identificado por hashes e snapshot, convergência, logs e ambiente. Checkpoints verificam integridade e identidade na retomada, reutilizando cenários completos sem duplicação.

## Evidência e reprodução

A fonte dos resultados finais é [final-evidence-operational-20261031](../benchmarks/results/final-evidence-operational-20261031/academic-summary.md). O [guia do benchmark](../benchmarks/README.md) reúne números, gráficos, arquivos brutos, comandos de reprodução e condições de interpretação.
