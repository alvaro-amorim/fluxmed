# FluxMed — contrato do assistente

## Entrada e saída

O assistente recebe mensagem, contexto da operação selecionada e histórico recente. Retorna texto, fontes consultadas e metadados do provider/modelo pelo contrato de `AssistantMessageRequest` e sua resposta em [API_SPEC.md](API_SPEC.md).

## Responsabilidades

A aplicação seleciona consultas autorizadas e constrói grounding estruturado. O provider redige explicações, instruções ao motorista, resumos e recomendações a partir dos fatos. Rotas, custos, viabilidade e impactos de simulação são calculados pelo backend.

O contexto é limitado por operação, allowlist, tamanho e quantidade de chamadas. O histórico resolve continuidade conversacional; os fatos são obtidos das consultas atuais. Pedidos com dados insuficientes devem receber uma resposta que explicite a informação necessária.

## Consultas e simulações

As ferramentas fornecem dados de operação, rotas, veículos, entregas, equipe, custos e busca genética. As simulações de troca de motorista e remoção de ajudante retornam impacto sem aplicação. Mudanças efetivas pertencem aos fluxos autorizados da aplicação.

## Avaliação

A avaliação qualitativa confronta fatos, fontes, sequência das paradas e instruções com o plano persistido. Testes com mock exercitam o contrato e os controles; ensaios com provider externo identificam modelo, contexto e resposta daquela execução.

O fluxo implementado, os providers, os controles e o protocolo estão em [LLM_IMPLEMENTATION.md](LLM_IMPLEMENTATION.md). O passo a passo de execução está em [ASSISTANT_EVALUATION.md](ASSISTANT_EVALUATION.md).
