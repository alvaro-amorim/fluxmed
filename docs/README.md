# Documentação do FluxMed

O [README principal](../README.md) apresenta o projeto, a execução local e os resultados experimentais. Os guias abaixo descrevem a implementação e suas evidências.

## Leitura acadêmica

| Documento | Conteúdo |
|---|---|
| [Problema e fluxo operacional](PRODUCT_SPEC.md) | Entradas, planejamento, recursos e resultado. |
| [Algoritmo genético](OPTIMIZATION_SPEC.md) | Cromossomo, operadores, decoder, fitness, equipe, custos e validação. |
| [Referência TSP da FIAP](FIAP_TSP_BASE.md) | Relação conceitual e comparação técnica. |
| [Experimento e resultados](../benchmarks/README.md) | Matriz oficial, parâmetros, seeds, gráficos, pareamento e reprodução. |
| [Arquitetura](ARCHITECTURE.md) | Componentes, fluxo de dados e persistência. |
| [Assistente IA](LLM_IMPLEMENTATION.md) | Grounding, ferramentas, providers e avaliação qualitativa. |
| [Relatórios operacionais](REPORTS.md) | Snapshot por operação e formatos PDF/XLSX/CSV. |

## Referência técnica e reprodução

- [Instalação local](LOCAL_SETUP.md) e [avaliação do assistente](ASSISTANT_EVALUATION.md).
- [API](API_SPEC.md), [modelo persistido e tipos](DOMAIN_MODEL.md) e [interface](FRONTEND_SPEC.md).
- [Santa Aurora e routing](SANTA_AURORA_SPEC.md), [Decision Trace](OPTIMIZATION_TRACE.md) e [contrato da LLM](LLM_SPEC.md).
- [Testes e verificações](TESTING_STRATEGY.md), [protocolo experimental](BENCHMARK_PLAN.md) e [política de CI](CI_POLICY.md).

O relatório técnico acadêmico e o vídeo são artefatos de apresentação. Os relatórios PDF/XLSX/CSV da aplicação documentam uma operação específica.
