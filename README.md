# FluxMed

> Planejamento inteligente de distribuição médica com Algoritmos Genéticos, restrições operacionais realistas, visualização de rotas, relatórios e Assistente IA grounded em dados do backend.

## Status

**V1 implementada e funcional.**  
**Fase 18 — hardening:** concluída e validada localmente.  
**Projeto:** Tech Challenge — Fase 2, Projeto 2: Otimização de Rotas para Distribuição de Medicamentos e Insumos.

A regressão final da V1 foi concluída com:

- backend: **169 testes aprovados**, Ruff, formatter e mypy verdes;
- frontend: **26 testes aprovados**, lint, typecheck e build de produção verdes;
- E2E manual completo validado;
- dispatch com imutabilidade pós-despacho validada;
- relatórios PDF/XLSX/CSV validados;
- Assistente IA validado com grounding operacional real.

O fluxo E2E validado foi:

```text
login
  -> operation
  -> deliveries
  -> resources
  -> closure / preflight
  -> optimization
  -> result
  -> assistant
  -> report
  -> approve
  -> dispatch
```

O fechamento técnico da Fase 18 está registrado em [`docs/HARDENING_PLAN.md`](docs/HARDENING_PLAN.md).

---

## 1. Visão geral

O **FluxMed** é um sistema acadêmico e de portfólio para planejamento diário de distribuição médica em uma cidade sintética chamada **Santa Aurora**.

A aplicação combina:

- operações persistidas e versionadas;
- entregas com prioridade, peso, volume, refrigeração e janelas de horário;
- frota heterogênea;
- motoristas, motociclistas e ajudantes;
- grafo viário dirigido;
- trânsito sintético dependente do horário;
- restrições viárias e operacionais;
- Algoritmo Genético para composição das rotas;
- alocação determinística de equipe;
- validação independente da solução;
- Decision Trace e replay do processo de otimização;
- mapa interativo das rotas;
- custos operacionais detalhados;
- relatórios operacionais;
- Assistente IA que interpreta dados estruturados do FluxMed sem substituir o otimizador.

A proposta não é simular um SaaS logístico completo. A V1 foi deliberadamente limitada ao que agrega valor acadêmico, arquitetural, demonstrável e de portfólio.

---

## 2. Fluxo funcional da V1

```text
Login
  ↓
Criar operação
  ↓
Configurar jornada e trânsito
  ↓
Selecionar / importar / gerar entregas
  ↓
Selecionar frota e equipe
  ↓
Executar preflight de viabilidade
  ↓
Otimizar rotas com GA
  ↓
Acompanhar execução / replay
  ↓
Analisar plano final e custos
  ↓
Consultar Assistente IA
  ↓
Gerar relatórios
  ↓
Aprovar plano
  ↓
Despachar operação
  ↓
Congelar a revisão despachada
```

Após o dispatch, a revisão operacional se torna imutável para ações de planejamento: edição, reotimização e alteração de equipe deixam de ser permitidas.

---

## 3. Capacidades implementadas

### Operações e demanda

- autenticação por sessão;
- papel de planejador;
- operações persistidas e versionadas;
- wizard de preparação operacional;
- entregas manuais;
- importação CSV/XLSX;
- geração determinística de cenários sintéticos;
- prioridades `LOW`, `NORMAL`, `HIGH` e `CRITICAL`;
- janelas `HARD` e `SOFT`;
- refrigeração;
- necessidade de duas pessoas;
- peso e volume tratados de forma independente.

### Frota e equipe

- motos, vans compactas, cargo vans e caminhões leves;
- veículos próprios e agregados;
- disponibilidade operacional;
- capacidade em peso e volume;
- autonomia;
- motoristas, motociclistas e ajudantes;
- alocação determinística de equipe;
- simulação de alterações de equipe antes do dispatch;
- congelamento da equipe após o dispatch.

### Otimização

- Algoritmo Genético próprio;
- Tournament Selection;
- Order Crossover (OX);
- mutações de swap, insertion e reverse/inversion;
- elitismo;
- mutação adaptativa;
- diversidade populacional;
- população inicial híbrida;
- decoder determinístico de cromossomo para rotas;
- pruning;
- repair;
- validação independente da solução final;
- early stopping;
- execução reproduzível por seed;
- Decision Trace persistido.

### Resultado operacional

- mapa das rotas;
- seleção visual por rota/veículo;
- entregas por rota;
- carga em peso e volume;
- distância e duração;
- makespan;
- atrasos críticos;
- percentual no prazo;
- custos por rota e total;
- equipe atribuída;
- replay da otimização;
- aprovação e dispatch.

### Relatórios

A aplicação gera relatórios a partir de snapshot persistido do plano, com exportação em:

- PDF;
- XLSX;
- CSV.

Os relatórios incluem resumo operacional, rotas, veículos, equipes, entregas, horários e custos.

### Assistente IA

A LLM funciona como **camada de interpretação**, nunca como otimizador.

O backend resolve e valida o grounding antes da resposta textual. O Assistente pode, entre outras tarefas:

- resumir a operação;
- explicar custos;
- consultar métricas do plano;
- comparar informações presentes no grounding;
- explicar seleção de veículos e rotas;
- gerar instruções operacionais;
- responder perguntas sobre entregas e planejamento.

A LLM não pode despachar operações, alterar diretamente o banco, substituir restrições matemáticas ou inventar métricas ausentes.

A V1 possui provider mock para desenvolvimento e suporte a providers reais, incluindo Gemini. O caminho de resposta grounded do Gemini usa uma chamada de geração controlada pelo backend, com timeout, mensagens públicas sanitizadas e rate guard por usuário.

Detalhes: [`docs/LLM_SPEC.md`](docs/LLM_SPEC.md) e [`docs/LLM_IMPLEMENTATION.md`](docs/LLM_IMPLEMENTATION.md).

---

## 4. Santa Aurora

**Santa Aurora** é a cidade brasileira fictícia e determinística usada na demonstração.

Ela fornece o ambiente controlado necessário para testar:

- grafo urbano dirigido;
- ruas de mão única e mão dupla;
- diferentes classes viárias;
- trânsito variável;
- bairros e regiões;
- centro de distribuição;
- hospitais, clínicas, laboratórios, farmácias e home care;
- endereços válidos para geração de demanda;
- interdições e restrições de circulação.

O domínio foi desenhado para não depender conceitualmente de uma única cidade; Santa Aurora é a implementação de demonstração da V1.

Detalhes: [`docs/SANTA_AURORA_SPEC.md`](docs/SANTA_AURORA_SPEC.md).

---

## 5. Arquitetura

```text
┌──────────────────────────────────────────────┐
│            React + Vite + TypeScript         │
│ Operações · Entregas · Frota · Equipe · IA │
│ MapLibre · Relatórios · Resultado do GA      │
└─────────────────────┬────────────────────────┘
                      │ HTTP / SSE
                      ▼
┌──────────────────────────────────────────────┐
│                   FastAPI                    │
│ API · Application · Domain · Optimization   │
│ Routing · Reports · LLM · Security           │
└─────────────────────┬────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────┐
│            PostgreSQL + PostGIS              │
└──────────────────────────────────────────────┘
```

O monorepo mantém frontend e backend separados, mas evoluídos como uma única aplicação.

### Backend

- Python 3.12+
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- PostgreSQL/PostGIS
- psycopg
- GeoAlchemy2
- httpx
- Google Gen AI SDK
- ReportLab
- openpyxl

### Frontend

- React 18
- TypeScript
- Vite
- React Router
- MapLibre GL
- Vitest
- React Testing Library
- Playwright

### Qualidade

- Ruff
- mypy strict
- pytest
- ESLint
- TypeScript typecheck
- Vitest
- build de produção

Detalhes arquiteturais: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## 6. Modelo de otimização

O problema é separado em duas camadas.

### 6.1 Routing urbano

Responde:

> Qual é o caminho viário entre dois pontos?

O roteamento considera o grafo dirigido, distância, velocidade, trânsito, sentidos, restrições e horário estimado de passagem.

### 6.2 Fleet / VRP Optimization

Responde:

> Qual veículo atende cada entrega e em qual ordem?

O GA trabalha sobre uma permutação global de entregas. Um decoder transforma o cromossomo em rotas operacionais, respeitando restrições e recursos.

A avaliação prioriza viabilidade e qualidade operacional antes de critérios econômicos. Uma solução inviável não deve superar uma solução válida apenas por ser mais curta ou barata.

Mais detalhes: [`docs/OPTIMIZATION_SPEC.md`](docs/OPTIMIZATION_SPEC.md).

---

## 7. Evidência acadêmica e benchmarks

O repositório inclui infraestrutura reproduzível para comparar:

1. Nearest Neighbor;
2. Best Insertion;
3. GA basic;
4. GA + advanced pruning;
5. GA + advanced pruning + repair.

O preset acadêmico final utiliza os perfis `NORMAL`, `BUSY`, `HIGH_PRESSURE` e `EMERGENCY`, tamanhos de 20/40/60/80 entregas e seeds explicitamente registradas.

Exemplo:

```powershell
cd "$HOME\Desktop\fluxmed"
.\apps\api\.venv\Scripts\Activate.ps1
python scripts\benchmark_optimizer.py --matrix-template-code OP-20260915-001 --preset final
```

Os artefatos incluem CSV/JSON, estatísticas consolidadas, séries de convergência, tabelas acadêmicas e gráficos SVG.

Consulte [`benchmarks/README.md`](benchmarks/README.md) e [`docs/BENCHMARK_PLAN.md`](docs/BENCHMARK_PLAN.md).

---

## 8. Como executar localmente

### Pré-requisitos

- Python `>=3.12,<3.14`;
- Node.js `>=20`;
- Docker / Docker Compose;
- Git.

### 8.1 Configuração inicial

Na raiz do repositório:

```powershell
Copy-Item .env.example .env

docker compose up -d db
```

### 8.2 Backend

```powershell
cd apps\api

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

alembic upgrade head
python -m fluxmed.scripts.seed_demo

uvicorn fluxmed.main:app --app-dir src --reload
```

Backend local:

```text
http://127.0.0.1:8000
```

### 8.3 Frontend

Em outro terminal:

```powershell
cd apps\web
npm ci
npm run dev
```

Frontend local:

```text
http://localhost:5173
```

### 8.4 Conta demonstrativa

Os valores padrão estão em `.env.example` e podem ser substituídos no `.env` local:

```text
E-mail: planner@fluxmed.demo
Senha: FluxMedDemo2026!
```

Nunca versione o `.env` real nem chaves de providers externos.

---

## 9. Reiniciar uma instalação já configurada

Depois da configuração inicial, normalmente são necessários três terminais.

### Terminal 1 — PostgreSQL/PostGIS

```powershell
cd "$HOME\Desktop\fluxmed"
docker compose up -d db
```

### Terminal 2 — API

```powershell
cd "$HOME\Desktop\fluxmed\apps\api"
.\.venv\Scripts\Activate.ps1

Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
Remove-Item Env:TEST_DATABASE_URL -ErrorAction SilentlyContinue

uvicorn fluxmed.main:app --app-dir src --reload
```

### Terminal 3 — Web

```powershell
cd "$HOME\Desktop\fluxmed\apps\web"
npm run dev
```

Os comandos equivalentes também estão disponíveis no `Makefile` para ambientes com `make`.

---

## 10. Banco de testes isolado

Os testes de integração possuem uma proteção explícita para não executar contra o banco da aplicação.

Crie o banco de testes uma única vez:

```powershell
cd "$HOME\Desktop\fluxmed"

docker compose exec db psql -U fluxmed -d postgres -c "CREATE DATABASE fluxmed_test OWNER fluxmed;"
docker compose exec db psql -U fluxmed -d fluxmed_test -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

Aplique as migrations:

```powershell
cd apps\api
.\.venv\Scripts\Activate.ps1

$env:TEST_DATABASE_URL="postgresql+psycopg://fluxmed:fluxmed@localhost:5432/fluxmed_test"
$env:DATABASE_URL=$env:TEST_DATABASE_URL

alembic upgrade head
```

> Atenção: um terminal configurado com `DATABASE_URL=$env:TEST_DATABASE_URL` é um terminal de testes. Limpe essas variáveis antes de iniciar a aplicação normal.

---

## 11. Validação local

### Backend

```powershell
cd apps\api
.\.venv\Scripts\Activate.ps1

$env:TEST_DATABASE_URL="postgresql+psycopg://fluxmed:fluxmed@localhost:5432/fluxmed_test"
$env:DATABASE_URL=$env:TEST_DATABASE_URL

python -m ruff check src tests
python -m ruff format --check src tests
python -m mypy src
python -m pytest -q
```

Na regressão final da V1: **169 testes aprovados**.

### Frontend

```powershell
cd apps\web

npm run lint
npm run typecheck
npm test -- --run
npm run build
```

Na regressão final da V1: **26 testes aprovados** e build de produção concluído.

O build pode emitir aviso de bundle/chunk grande do mapa; isso é tratado como otimização futura e não como falha funcional da V1.

---

## 12. Configurando o Assistente IA

Por padrão, o projeto pode operar com provider mock sem consumo externo:

```env
LLM_PROVIDER=mock
LLM_MODEL=fluxmed-mock-v1
```

Para testar Gemini localmente, configure somente no `.env` não versionado:

```env
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3.5-flash-lite
LLM_THINKING_LEVEL=minimal
GEMINI_API_KEY=replace-me
```

O backend aplica timeout, limite de contexto, limite de saída, sanitização de falhas e rate limiting por usuário.

---

## 13. Hardening e segurança da V1

A Fase 18 adicionou ou validou, entre outros pontos:

- liveness separado de readiness;
- falhas de banco sanitizadas;
- correlation ID em erros inesperados;
- logs sem query string/body sensível;
- auditoria de autenticação sem credenciais;
- sessão same-origin;
- cookies `Secure` forçados em produção;
- upload/import com limite de tamanho e normalização de nome;
- proteção contra execução dos testes em banco não dedicado;
- falhas do otimizador sanitizadas;
- cancelamento terminal-safe;
- recuperação de SSE e reidratação de trace persistido;
- histórico append-only de relatórios;
- rate guard do Assistente IA;
- erros de providers externos sem exposição de segredo;
- imutabilidade operacional após dispatch.

Veja [`docs/HARDENING_PLAN.md`](docs/HARDENING_PLAN.md) e [`docs/CI_POLICY.md`](docs/CI_POLICY.md).

---

## 14. Estrutura do monorepo

```text
fluxmed/
├── apps/
│   ├── api/                 # FastAPI, domínio, routing, GA, relatórios e LLM
│   └── web/                 # React/Vite/TypeScript
├── benchmarks/              # definição e artefatos de benchmark acadêmico
├── data/                    # dados auxiliares/versionados
├── docs/                    # especificações, ADRs e planos
├── infra/                   # infraestrutura de apoio
├── scripts/                 # launchers e utilitários
├── tests/                   # testes de nível de repositório quando aplicável
├── .github/                 # workflows e configuração de automação
├── docker-compose.yml
├── Makefile
├── .env.example
└── README.md
```

---

## 15. Documentação técnica

Principais referências:

- [`docs/PRODUCT_SPEC.md`](docs/PRODUCT_SPEC.md) — escopo e comportamento do produto;
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — arquitetura e responsabilidades;
- [`docs/DOMAIN_MODEL.md`](docs/DOMAIN_MODEL.md) — entidades e regras de domínio;
- [`docs/SANTA_AURORA_SPEC.md`](docs/SANTA_AURORA_SPEC.md) — cidade sintética;
- [`docs/OPTIMIZATION_SPEC.md`](docs/OPTIMIZATION_SPEC.md) — GA, decoder e restrições;
- [`docs/OPTIMIZATION_TRACE.md`](docs/OPTIMIZATION_TRACE.md) — evidências estruturadas do otimizador;
- [`docs/API_SPEC.md`](docs/API_SPEC.md) — contratos da API;
- [`docs/FRONTEND_SPEC.md`](docs/FRONTEND_SPEC.md) — UX e superfícies do frontend;
- [`docs/LLM_SPEC.md`](docs/LLM_SPEC.md) — regras do Assistente IA;
- [`docs/LLM_IMPLEMENTATION.md`](docs/LLM_IMPLEMENTATION.md) — implementação dos providers/grounding;
- [`docs/TESTING_STRATEGY.md`](docs/TESTING_STRATEGY.md) — estratégia de testes;
- [`docs/BENCHMARK_PLAN.md`](docs/BENCHMARK_PLAN.md) — metodologia acadêmica;
- [`docs/HARDENING_PLAN.md`](docs/HARDENING_PLAN.md) — fechamento da V1;
- [`docs/CI_POLICY.md`](docs/CI_POLICY.md) — política de CI.

---

## 16. Limites deliberados da V1

Ficam fora do escopo atual:

- GPS e telemetria reais;
- aplicativo do motorista;
- rastreamento durante a execução física da rota;
- reotimização disparada por eventos reais em trânsito;
- múltiplos centros de distribuição;
- microserviços;
- Kafka/RabbitMQ;
- Kubernetes;
- processamento distribuído;
- trânsito real de terceiros;
- carregamento 3D;
- regras trabalhistas completas e folha/ponto.

Esses itens são possibilidades de evolução, não requisitos faltantes da V1 acadêmica.

---

## 17. Princípio central

> O FluxMed deve demonstrar profundidade técnica sem confundir profissionalismo com complexidade desnecessária.

A V1 busca ser:

- academicamente defensável;
- tecnicamente correta;
- visualmente demonstrável;
- testável;
- explicável;
- reproduzível;
- segura para demonstração;
- organizada como projeto de portfólio.
