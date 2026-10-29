# Documentação do FluxMed

O [README principal](../README.md) é o ponto de partida para avaliar e executar a aplicação. Esta página organiza os documentos de apoio sem misturar requisitos entregues com decisões e planos históricos de desenvolvimento.

## Para avaliar a entrega

| Documento | Uso |
|---|---|
| [Instalação local](LOCAL_SETUP.md) | Subir Docker, fazer login, percorrer a demonstração e diagnosticar falhas. |
| [Avaliação do Assistente IA](ASSISTANT_EVALUATION.md) | Distinguir mock de Gemini real e testar a integração sem divulgar uma chave. |
| [Evidências de benchmark](../benchmarks/README.md) | Entender método, números, gráficos, seeds e limites dos experimentos. |
| [Relatórios operacionais](REPORTS.md) | Entender PDF/XLSX/CSV gerados pela aplicação. Esses arquivos são diferentes do relatório técnico acadêmico. |
| [Arquitetura](ARCHITECTURE.md) | Ver módulos, responsabilidades e fluxo entre frontend, API e banco. |
| [Otimização](OPTIMIZATION_SPEC.md) | Ver representação genética, operadores, fitness, restrições e validação. |
| [Código-base TSP da FIAP](FIAP_TSP_BASE.md) | Comparar o exemplo oficial com o GA do FluxMed e entender o limite da adaptação. |
| [Implementação da LLM](LLM_IMPLEMENTATION.md) | Ver providers, grounding, ferramentas e tratamento de falhas. |
| [Guia de gravação do vídeo](VIDEO_RECORDING_GUIDE.md) | Preparar a operação e capturar a demonstração em tela para narração posterior. |

## Contratos e detalhes técnicos

- [API](API_SPEC.md), [domínio](DOMAIN_MODEL.md) e [frontend](FRONTEND_SPEC.md);
- [cidade sintética](SANTA_AURORA_SPEC.md), [Decision Trace](OPTIMIZATION_TRACE.md) e [relatórios](REPORTS.md);
- [estratégia de testes](TESTING_STRATEGY.md) e [política de CI](CI_POLICY.md).

## Registros de desenvolvimento

Os arquivos abaixo preservam decisões e progresso do projeto, mas não substituem a aplicação, os resultados medidos nem o relatório técnico da entrega:

- [plano de desenvolvimento](DEVELOPMENT_PLAN.md);
- [instruções de implementação](CODEX_INSTRUCTIONS.md);
- [plano de hardening](HARDENING_PLAN.md);
- [estado da release](V1_RELEASE_STATUS.md);
- [plano experimental](BENCHMARK_PLAN.md).

Algumas especificações foram escritas antes da implementação e podem conter alternativas ou etapas planejadas. Para confirmar uma capacidade entregue, use o código, os testes e as evidências referenciadas no README principal.
