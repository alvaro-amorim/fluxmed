# FluxMed — problema e fluxo operacional

## Objetivo

Planejar a distribuição de medicamentos e insumos em Santa Aurora, cidade sintética, a partir de entregas, frota, equipe, horários e condições viárias. A saída é um plano de rotas de múltiplos veículos, com custos, cronologia, indicadores e visualização no mapa.

O algoritmo compara soluções por viabilidade e qualidade de atendimento antes do custo operacional. O planejador acompanha a busca, analisa o resultado e controla aprovação e despacho.

## Entradas

| Área | Dados utilizados |
|---|---|
| Operação | Data, início, fim, trânsito e ocorrências viárias. |
| Entregas | Endereço, peso, volume, prioridade, janela, serviço, temperatura e manuseio. |
| Frota | Peso/volume máximos, autonomia, refrigeração, política de ajudante, eficiência e perfil de custo. |
| Equipe | Papel, atividade, disponibilidade na data e remuneração. |
| Cidade | Grafo dirigido, depósito, endereços e geometrias. |

As entregas podem ser cadastradas, importadas ou geradas pelos perfis `NORMAL`, `BUSY`, `HIGH_PRESSURE` e `EMERGENCY`. O serviço valida os registros e a resolução de endereços antes de confirmar uma importação.

## Jornada

1. Criar a operação e definir data, janela e trânsito.
2. Preparar as entregas e selecionar veículos e profissionais.
3. Conferir o preflight e iniciar a otimização.
4. Acompanhar progresso e analisar rotas, paradas, horários, custos e comparação com heurísticas.
5. Consultar o assistente e gerar relatórios da operação.
6. Aprovar o resultado e despachar a revisão.

A autenticação usa sessão persistida. As ações respeitam as permissões dos papéis ADMIN e PLANNER. A revisão despachada fica imutável pelos serviços operacionais.

## Restrições e atendimento

- Cobertura de todas as entregas, com unicidade e veículos conhecidos.
- Capacidade de peso e volume, autonomia e retorno ao depósito.
- Refrigeração e manuseio compatíveis.
- Janelas HARD, atraso SOFT, espera e jornada.
- Equipe compatível e disponível, sem reutilização de profissional entre rotas.

LOW, NORMAL, HIGH e CRITICAL têm pesos 1, 2, 3 e 4 no atendimento. As regras completas e a ordem lexicográfica estão em [OPTIMIZATION_SPEC.md](OPTIMIZATION_SPEC.md).

## Equipe e custo

O backend atribui o profissional principal e o ajudante exigido pela política do veículo ou por entrega `TWO_PERSON`. O matching minimiza o custo da equipe para as rotas construídas, considerando disponibilidade e pessoal incluído em contrato.

O custo operacional combina veículo próprio ou contrato agregado, combustível quando não incluído e remuneração efetiva. A referência sintética de combustível é R$ 6,00/L. Viagem, serviço e espera compõem a duração usada nos componentes por hora.

## Resultado e interação

O resultado apresenta viabilidade, frota utilizada, distância, makespan, custo, atrasos, pontualidade, utilização de peso/volume, paradas e geometria. O trace registra a evolução real da busca e permite replay.

A simulação de equipe permite conferir uma atribuição antes de aplicar uma mudança autorizada. O backend revalida a ação e seu impacto. O assistente consulta os fatos do plano e redige explicações, instruções e resumos.

## Referências

- [Arquitetura](ARCHITECTURE.md), [API](API_SPEC.md) e [interface](FRONTEND_SPEC.md).
- [Relatórios operacionais](REPORTS.md) e [assistente](LLM_IMPLEMENTATION.md).
- [Experimento oficial](../benchmarks/README.md).
