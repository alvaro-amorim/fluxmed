# FluxMed — interface e fluxos

## Organização

O frontend usa React, Vite, TypeScript e MapLibre. A navegação e as permissões visuais acompanham os contratos HTTP; o backend calcula viabilidade, custos e atribuições.

| Fluxo principal | Rota |
|---|---|
| Acesso | `/login` |
| Operações | `/operations` |
| Nova operação | `/operations/new` |
| Operação selecionada | `/operations/:operationId` |
| Entregas | `/deliveries` |
| Frota | `/fleet` |
| Equipe | `/workforce` |
| Relatórios | `/reports` |
| Assistente IA | `/assistant` |

Fonte: [`AppRouter.tsx`](../apps/web/src/app/AppRouter.tsx).

## Planejamento da operação

O usuário define data/janela, prepara entregas, seleciona recursos e confere o preflight. O formulário exibe erros de entrada e de domínio retornados pela API. A geração sintética usa os perfis definidos pelo backend; a importação passa por validação e confirmação.

## Busca e resultado

O painel de otimização acompanha o lifecycle e os eventos SSE persistidos. Exibe geração, melhor solução, critérios do fitness, diversidade, mutação, podas e alterações de atribuição. O replay consulta os eventos do run.

No resultado, mapa, legenda e paradas se referem à mesma execução. A interface apresenta distância, duração, custo, pontualidade, atrasos e utilização de peso/volume separadamente. Aprovação e despacho dependem das regras do plano.

## Equipe e custos

Os recursos mantêm capacidades, compatibilidades e perfis de remuneração/custo. A rota exibe equipe e componentes incluídos em contrato. A simulação de troca mostra o resultado calculado pelo backend antes de aplicar uma atribuição permitida.

Os componentes exibidos no resultado são combustível, depreciação, manutenção, custo temporal, equipe e contrato, conforme o recurso. Duração e cobrança por hora incluem a espera pela janela.

## Relatórios

A tela consulta a operação, escolhe PDF/XLSX/CSV e exibe o histórico, estado e download dos artefatos. O relatório operacional é `DAILY_OPERATION`, baseado no snapshot do plano validado. [REPORTS.md](REPORTS.md) descreve o conteúdo e o retry.

## Assistente

O chat envia mensagem, contexto selecionado e histórico recente. Exibe resposta formatada, fontes e provider/modelo. As ações de perguntar e copiar histórico mantêm a resposta associada à operação. Instruções ao motorista e resumos são redigidos com grounding do backend.

## Contratos e verificações

Os módulos tipados em [`services/`](../apps/web/src/services/) correspondem aos routers e schemas descritos em [API_SPEC.md](API_SPEC.md). Os testes de componentes e serviços usam Vitest/Testing Library; o E2E de autenticação usa Playwright. Comandos e escopos estão em [TESTING_STRATEGY.md](TESTING_STRATEGY.md).
