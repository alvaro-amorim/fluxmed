# FluxMed

Planejamento de rotas para distribuição de medicamentos e insumos em uma cidade sintética. O projeto implementa um algoritmo genético para uma variante de VRP com múltiplos veículos e restrições médicas, apresenta as rotas em um mapa e oferece um assistente de linguagem natural conectado aos resultados calculados pelo backend.

**Tech Challenge — Fase 2, Projeto 2.** Esta é uma aplicação acadêmica de planejamento antes da saída dos veículos. Santa Aurora, entregas e condições de trânsito são sintéticas; não há operação hospitalar real nem rastreamento em tempo real.

## Executar a aplicação

Pré-requisitos: Git, Docker com Compose v2, acesso a este repositório e portas locais 5432, 8000 e 5173 disponíveis.

```bash
git clone https://github.com/alvaro-amorim/fluxmed.git
cd fluxmed
```

Crie o arquivo de configuração local a partir de `.env.example`:

```powershell
# Windows / PowerShell
Copy-Item .env.example .env
```

```bash
# macOS / Linux
cp .env.example .env
```

Inicie a pilha:

```bash
docker compose up --build -d
docker compose ps -a
```

O primeiro início aplica as migrações e gera Santa Aurora. Aguarde `api` e `web` ficarem ativos; `init` terminar com `Exited (0)` é esperado. Abra **http://localhost:5173** e entre com a conta exclusiva de demonstração: `planner@fluxmed.demo` / `FluxMedDemo2026!`.

> O Compose publica os serviços somente em `127.0.0.1`. As credenciais demonstrativas são públicas e não devem ser usadas em um ambiente exposto à internet. Nunca versione o arquivo `.env`.

Para detalhes de instalação, diagnóstico e execução sem Docker para API/web, consulte [o guia local](docs/LOCAL_SETUP.md).

## Jornada de demonstração

1. Crie uma operação em Santa Aurora e escolha uma janela de planejamento.
2. Gere entregas sintéticas ou importe um arquivo; selecione frota e equipe.
3. Execute o preflight e a otimização. Acompanhe a evolução do GA e abra o mapa das rotas.
4. Confira viabilidade, prioridades, horários, veículos, custos e comparação com heurísticas.
5. Consulte o Assistente IA sobre o plano; peça instruções para o motorista de uma rota.
6. Gere os relatórios operacionais PDF, XLSX e CSV; aprove e despache a operação.

Após o despacho, a revisão do plano fica imutável. O banco é persistido em um volume Docker. A instalação inicial não traz uma operação otimizada pronta: a jornada acima cria uma.

Para capturar as telas e narrar depois, siga o [guia de gravação manual](docs/VIDEO_RECORDING_GUIDE.md). Ele separa a preparação da operação, a demonstração do GA e a chamada Gemini real.

## Como a solução atende ao desafio

| Requisito | Implementação e evidência |
|---|---|
| Algoritmo genético | Cromossomo como permutação de entregas, seleção por torneio, Order Crossover, mutações swap/insertion/inversion, elitismo e parada por estagnação. [Detalhes](docs/OPTIMIZATION_SPEC.md). |
| Código-base TSP da FIAP | [Comparação com o repositório oficial](docs/FIAP_TSP_BASE.md): os conceitos do GA foram reimplementados e ampliados para VRP. O FluxMed foi desenvolvido de forma independente, sem copiar o arquivo fornecido. |
| Restrições médicas e VRP | Múltiplos veículos, capacidade de peso e volume, autonomia, refrigeração, prioridades, janelas de entrega, equipe, jornada e retorno ao depósito. O backend valida a solução final independentemente do GA. |
| Visualização | Mapa interativo de Santa Aurora com rotas, paradas e indicadores operacionais. |
| Comparação experimental | Nearest Neighbor, Best Insertion e três configurações do GA avaliados na mesma matriz de cenários. [Resultados e método](benchmarks/README.md). |
| LLM | Assistente com ferramentas de consulta ao plano persistido, instruções para motoristas, resumo diário e perguntas sobre rotas e custos. O modelo interpreta dados; não recalcula rotas nem altera a operação. [Avaliação](docs/ASSISTANT_EVALUATION.md). |
| Qualidade e execução | FastAPI e React/TypeScript, migrações PostgreSQL/PostGIS, testes automatizados, CI e Docker Compose local. [Arquitetura](docs/ARCHITECTURE.md). |

O relatório técnico acadêmico e o vídeo de até 15 minutos são entregáveis separados dos relatórios operacionais gerados pela aplicação.

## Resultados do benchmark

O experimento publicado usa 4 perfis de demanda (`NORMAL`, `BUSY`, `HIGH_PRESSURE`, `EMERGENCY`), 4 escalas (20, 40, 60, 80 entregas) e 5 seeds para cada configuração do GA. São **16 cenários e 272 execuções de métodos**; os baselines determinísticos executam uma vez por cenário.

| Método | Soluções viáveis | Tempo médio do otimizador |
|---|---:|---:|
| Nearest Neighbor | 5/16 | 0,012 s |
| Best Insertion | 3/16 | 0,115 s |
| GA básico | 14/80 | 41,893 s |
| GA com pruning | 60/80 | 37,046 s |
| **GA com pruning e repair** | **80/80** | **56,309 s** |

Nessa amostra, o repair elevou a frequência de soluções viáveis e aumentou o tempo médio. Os números **não** demonstram otimalidade global nem superioridade de custo em toda instância. Custos só são comparáveis entre soluções viáveis do mesmo cenário; a métrica de fitness não equivale necessariamente ao custo operacional final. Os dados, seeds, tabelas e gráficos estão em [benchmarks/results/final-evidence-20260917](benchmarks/results/final-evidence-20260917/academic-summary.md).

### Reexecutar o experimento

O benchmark usa a operação `OP-20260915-001` como modelo de recursos, data e janela. A pasta de resultados oficial preserva os dados medidos. Para uma nova execução, use uma pasta de saída diferente; a matriz completa consome CPU e pode levar bastante tempo.

```powershell
# Em um banco demo recém-inicializado, antes de criar outros recursos.
docker compose run --rm --no-deps init python -m fluxmed.scripts.seed_benchmark_template --seed

# Na raiz, com o Python/ambiente virtual da API ativo e PostgreSQL disponível.
python scripts/benchmark_optimizer.py --matrix-template-code OP-20260915-001 --preset final --output benchmarks/results/minha-reexecucao
```

O seed acadêmico é exclusivo da reprodução do experimento; **não o execute no banco da gravação**. Ele exige o banco de demonstração recém-inicializado, com Santa Aurora e usuário demo, antes de criar outras operações ou recursos. [Instruções e limitações de reexecução](benchmarks/README.md).

## Assistente IA: mock e provider real

Por padrão, a instalação usa `LLM_PROVIDER=mock`. Isso permite explorar a interface e as consultas ao backend **sem chamar uma LLM externa**. Para testar Gemini, configure uma chave própria **somente no `.env` da API**, altere `LLM_PROVIDER`/`LLM_MODEL` conforme [o guia de avaliação](docs/ASSISTANT_EVALUATION.md) e reinicie a API. O modelo real pode exigir cota e gerar custos. Uma resposta identificada como `gemini` após uma pergunta é a evidência de chamada; o status de configuração sozinho não comprova conectividade.

Chaves não são fornecidas no repositório. O vídeo acadêmico deve demonstrar uma pergunta factual e instruções para motorista com Gemini real sem mostrar credenciais.

## Arquitetura

```text
React + Vite + TypeScript + MapLibre
             │ HTTP / SSE
             ▼
FastAPI: API → aplicação → domínio / routing / GA / relatórios / LLM
             │
             ▼
      PostgreSQL + PostGIS
```

O GA decide quais entregas cada veículo atende e em qual ordem. O módulo de routing encontra os caminhos no grafo urbano dirigido. Essa separação permite aplicar restrições de carga, autonomia, tempo e prioridade sem tratar cada rua como um gene. O Assistente consulta resultados estruturados depois da otimização.

## Verificação

O [Full CI da `main`](https://github.com/alvaro-amorim/fluxmed/actions/runs/40573719652) executa lint, formatação, MyPy, migrations e testes de backend com PostGIS; lint, TypeScript, Vitest e build do frontend; além do E2E automatizado de login demo. Essa execução passou em 27/10/2026. A jornada operacional completa também foi verificada manualmente.

Para comandos de teste e banco isolado, consulte [a estratégia de testes](docs/TESTING_STRATEGY.md) e [o guia local](docs/LOCAL_SETUP.md). **Atenção:** confirme que `TEST_DATABASE_URL` aponta para um banco dedicado antes de executar pytest; os testes de integração podem modificar esse banco.

## Escopo e documentação

- Os dados e resultados refletem uma cidade e demandas sintéticas, não uma avaliação com pacientes ou logística hospitalar real.
- O produto gera relatórios operacionais **diários**; não agrega várias operações em um relatório semanal.
- A aplicação planeja a operação antes do despacho; não oferece GPS, telemetria, aplicativo do motorista ou reotimização em trânsito.
- O E2E automatizado cobre login; o fluxo operacional completo foi validado manualmente.

O [índice da documentação](docs/README.md) separa guias de avaliação, especificações técnicas e registros históricos de desenvolvimento.
