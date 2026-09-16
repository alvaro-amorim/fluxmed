# FluxMed — Relatórios da operação

**Fase:** 15  
**Status:** implementação da V1  
**Escopo:** PDF, XLSX e CSV a partir do plano otimizado validado

## Objetivo

A camada de relatórios transforma um resultado operacional validado em artefatos que podem ser
compartilhados, auditados e usados como evidência acadêmica sem recalcular o algoritmo genético.

A regra central é:

```text
plano otimizado validado
↓
snapshot imutável
↓
artefato persistido
↓
download posterior reproduz exatamente aquele snapshot
```

Um relatório já concluído nunca consulta novamente a operação para montar o arquivo. Se a operação
for reotimizada, um novo relatório deve ser gerado e passa a ter um novo snapshot e um novo
`optimization_run_id`.

## Horários e fuso operacional

O snapshot preserva timestamps timezone-aware como evidência auditável. O fuso operacional da V1
para Santa Aurora é `America/Sao_Paulo`.

Regras de apresentação:

- PDF exibe horários convertidos para o fuso operacional;
- XLSX grava chegada e saída já convertidas para o fuso operacional, como células de data/hora do
  Excel;
- CSV preserva `chegada_planejada` no timestamp original e adiciona
  `chegada_planejada_local` com o instante convertido para `America/Sao_Paulo`;
- conversão de fuso nunca usa remoção simples de `tzinfo` antes da conversão.

## Formatos

### PDF

Relatório de leitura e apresentação com:

- identificação da operação;
- revisão e status capturados;
- KPIs do plano;
- resumo das rotas;
- veículo e equipe por rota;
- sequência de entregas por rota;
- custos e pontualidade;
- horários apresentados no fuso operacional;
- conclusões determinísticas derivadas das métricas persistidas.

### XLSX

A planilha possui seis abas estáveis:

```text
Resumo
Rotas
Entregas
Veículos
Equipe
Custos
```

Valores quantitativos são gravados como células numéricas reais, e não texto. Custos, distâncias,
durações, peso, volume e percentuais recebem formatos de célula adequados para permitir fórmulas,
ordenação, filtros e gráficos no Excel. Chegada e saída são células de data/hora locais.

### CSV

Exportação tabular orientada a entregas, contendo operação, rota, veículo, sequência, entrega,
destinatário, endereço, prioridade, chegada planejada original, chegada planejada local e atraso.

## Persistência

A tabela `reports` guarda:

- operação;
- execução de otimização que originou o relatório;
- usuário que solicitou;
- tipo e formato;
- status;
- nome e MIME type do arquivo;
- snapshot JSONB imutável;
- bytes do artefato;
- mensagem de erro quando aplicável;
- timestamps de criação e conclusão.

Para a V1 a geração é síncrona dentro da request, mas o recurso mantém lifecycle explícito
`QUEUED/COMPLETED/FAILED`. O contrato HTTP continua usando `202 Accepted`, permitindo mover a
geração para background futuramente sem quebrar o frontend.

## Falhas e retry

Falhas de renderização são persistidas como `FAILED` com `error_message`. O usuário pode usar
`Tentar novamente` no histórico. O retry cria uma nova entrada de relatório, mas reutiliza uma cópia
exata do snapshot persistido e o mesmo `optimization_run_id`; ele não consulta o estado atual da
operação nem executa novamente o algoritmo genético. A tentativa que falhou permanece no histórico
para auditoria.

Operações `OUTDATED` não podem gerar um relatório novo; é necessário reotimizar primeiro.

## API

```text
GET  /api/v1/reports
GET  /api/v1/reports?operation_id={operation_id}
POST /api/v1/operations/{operation_id}/reports
POST /api/v1/reports/{report_id}/retry
GET  /api/v1/reports/{report_id}
GET  /api/v1/reports/{report_id}/download
```

Request de criação:

```json
{
  "report_type": "DAILY_OPERATION",
  "format": "PDF"
}
```

Formatos aceitos:

```text
PDF
XLSX
CSV
```

## Frontend

A rota `/reports` oferece:

- seleção de uma operação com plano válido;
- escolha do formato;
- geração;
- histórico de artefatos;
- indicação de falha;
- retry de falhas mantendo o snapshot original;
- download dos arquivos concluídos.

A UI explicita que o relatório é baseado em snapshot para não sugerir que arquivos antigos mudam
quando a operação é reotimizada.

## Critério de aceite da Fase 15

A fase pode ser encerrada quando:

1. migrations passam em banco limpo;
2. PDF é válido, contém as seções operacionais, usa o fuso operacional e é baixável;
3. XLSX contém as seis abas especificadas, horários locais e células quantitativas numéricas;
4. CSV contém as entregas das rotas e distingue timestamp original de horário local;
5. histórico sobrevive a reload;
6. snapshot de um relatório concluído não muda após alterações posteriores;
7. falha de geração permanece visível e retry usa exatamente o snapshot que falhou;
8. frontend gera e baixa os três formatos;
9. CI completo está verde;
10. validação manual confirma arquivos reais de uma operação otimizada.
