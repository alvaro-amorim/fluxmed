# FluxMed

Planejamento de rotas para distribuição de medicamentos e insumos em uma cidade sintética. O projeto implementa um algoritmo genético para uma variante de VRP com múltiplos veículos e restrições médicas, apresenta as rotas em um mapa e oferece um assistente de linguagem natural conectado aos resultados calculados pelo backend.

**Tech Challenge — Fase 2, Projeto 2.** A aplicação realiza planejamento pré-despacho com Santa Aurora, entregas e condições de trânsito sintéticas.

## Entrega acadêmica

- [Vídeo de apresentação e demonstração](https://youtu.be/gHc-irrihV0).
- [Relatório técnico final em PDF](docs/academic/Relatorio-Tecnico-FluxMed.pdf).
- [Método, resultados e reprodução do benchmark](benchmarks/README.md).

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

## Componentes da solução

| Requisito | Implementação e evidência |
|---|---|
| Algoritmo genético | Cromossomo como permutação de entregas, seleção por torneio, Order Crossover, mutações swap/insertion/inversion, elitismo e parada por estagnação. [Detalhes](docs/OPTIMIZATION_SPEC.md). |
| Código-base TSP da FIAP | [Referência conceitual e comparação técnica](docs/FIAP_TSP_BASE.md) entre o TSP didático e o VRP do FluxMed. |
| Restrições médicas e VRP | Múltiplos veículos, capacidade de peso e volume, autonomia, refrigeração, prioridades, janelas de entrega, equipe, jornada e retorno ao depósito. O backend valida a solução final independentemente do GA. |
| Visualização | Mapa interativo de Santa Aurora com rotas, paradas e indicadores operacionais. |
| Comparação experimental | Nearest Neighbor, Best Insertion e três configurações do GA avaliados na mesma matriz de cenários. [Resultados e método](benchmarks/README.md). |
| LLM | Assistente com ferramentas de consulta ao plano persistido, instruções para motoristas, resumo diário e perguntas sobre rotas e custos. O modelo interpreta dados; não recalcula rotas nem altera a operação. [Avaliação](docs/ASSISTANT_EVALUATION.md). |
| Qualidade e execução | FastAPI e React/TypeScript, migrações PostgreSQL/PostGIS, testes automatizados, CI e Docker Compose local. [Arquitetura](docs/ARCHITECTURE.md). |

O [relatório técnico acadêmico](docs/academic/Relatorio-Tecnico-FluxMed.pdf) e o [vídeo de apresentação](https://youtu.be/gHc-irrihV0) são entregáveis separados dos relatórios operacionais gerados pela aplicação.

## Resultados do benchmark

O estudo final de 31/10/2026 usa 4 perfis de demanda (`NORMAL`, `BUSY`, `HIGH_PRESSURE`, `EMERGENCY`), 4 escalas (20, 40, 60, 80 entregas) e 5 seeds para cada configuração do GA. São **16 cenários e 272 execuções únicas de métodos**; os baselines determinísticos executam uma vez por cenário.

| Método | Soluções viáveis | Tempo médio do otimizador |
|---|---:|---:|
| Nearest Neighbor | 5/16 | 0,015 s |
| Best Insertion | 3/16 | 0,111 s |
| GA básico | 13/80 | 51,325 s |
| GA com pruning | 62/80 | 49,810 s |
| **GA com pruning e repair** | **80/80** | **82,846 s** |

Nessa amostra, repair elevou a frequência de soluções viáveis e aumentou o tempo médio. Nos **62 pares viáveis de mesmo cenário e seed** entre pruning e pruning + repair, repair teve custo menor em **33**, maior em **25** e igual em **4**. A qualidade do atendimento também pode diferir entre esses pares; a interpretação conjunta está no método experimental.

O GA e os métodos comparados usam o mesmo custo operacional, incluindo combustível e equipe efetivamente atribuída. Falta de equipe torna o candidato inviável antes da escolha final. A espera por janela entra na duração, no makespan e nos componentes por hora. A fitness ordena: viabilidade, violações, atraso SOFT ponderado por prioridade, risco CRITICAL, inversões de prioridade, custo operacional, makespan, viagem, distância e veículos. Restrições e atendimento precedem custo. [Funcionamento e validação](docs/OPTIMIZATION_SPEC.md).

Os [dados finais, seeds, identidade do código e gráficos](benchmarks/results/final-evidence-operational-20261031/academic-summary.md) documentam a matriz oficial. O [método experimental](benchmarks/README.md) apresenta o pareamento e as condições de interpretação.

### Reexecutar o experimento

O benchmark usa a operação `OP-20260915-001` como modelo de recursos, data e janela. A pasta de resultados oficial preserva os dados medidos. Para uma nova execução, use uma pasta de saída diferente; a matriz completa consome CPU e pode levar bastante tempo.

```powershell
# Em um banco demo recém-inicializado, antes de criar outros recursos.
docker compose run --rm --no-deps init python -m fluxmed.scripts.seed_benchmark_template --seed

# Na raiz, com o Python/ambiente virtual da API ativo e PostgreSQL disponível.
python scripts/benchmark_optimizer.py --matrix-template-code OP-20260915-001 --preset final --output benchmarks/results/minha-reexecucao

# Após interrupção, retome a mesma pasta com os mesmos parâmetros e código:
python scripts/benchmark_optimizer.py --matrix-template-code OP-20260915-001 --preset final --output benchmarks/results/minha-reexecucao --resume
```

O seed acadêmico usa banco dedicado de demonstração recém-inicializado, com Santa Aurora e usuário demo, antes de criar outras operações ou recursos. Preserve o banco utilizado nas demonstrações. [Preparação e reprodução](benchmarks/README.md).

## Assistente IA: mock e provider real

Por padrão, a instalação usa `LLM_PROVIDER=mock`. Isso permite explorar a interface e as consultas ao backend **sem chamar uma LLM externa**. Para testar Gemini, configure uma chave própria **somente no arquivo local `.env` na raiz do repositório**, altere `LLM_PROVIDER`/`LLM_MODEL` conforme [o guia de avaliação](docs/ASSISTANT_EVALUATION.md) e reinicie a API. O modelo real pode exigir cota e gerar custos. Uma resposta identificada como `gemini` após uma pergunta é a evidência de chamada; o status de configuração sozinho não comprova conectividade.

Chaves não são fornecidas no repositório. O [vídeo acadêmico](https://youtu.be/gHc-irrihV0) apresenta perguntas sobre o plano e instruções para motorista com Gemini, sem fornecer credenciais ao avaliador. O procedimento de conferência está no [guia de avaliação](docs/ASSISTANT_EVALUATION.md).

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

O GA evolui uma permutação de entregas; o decoder constrói as rotas e atribui veículos de forma gulosa. O routing encontra os caminhos no grafo urbano dirigido: cada par da matriz e da geometria parte da referência inicial da operação, considerando fatores temporais das arestas dentro do caminho. O Assistente consulta resultados estruturados depois da otimização.

## Verificação e referência

Os comandos, o banco dedicado e os escopos de backend, frontend, E2E e ensaio manual estão em [TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md). O [workflow de CI](.github/workflows/ci.yml) define os jobs e o [registro experimental](benchmarks/results/final-evidence-operational-20261031/verification.json) identifica as verificações da fonte medida.

O [índice da documentação](docs/README.md) organiza os guias do problema, algoritmo, arquitetura, API, cidade, LLM, relatórios e experimento. O relatório técnico acadêmico e o vídeo apresentam o método e os resultados; os relatórios operacionais da aplicação descrevem cada operação.
