# FluxMed

> Planejamento inteligente de rotas médicas com Algoritmos Genéticos, restrições operacionais realistas e integração com LLM.

## Status

**Fase atual:** Fase 6 — endereços e facilities de Santa Aurora.  
**Implementação:** fundação, domínio, autenticação, operações e cidade-base concluídos; dataset urbano completo em desenvolvimento.  
**Estratégia de desenvolvimento:** backend/domain-first com entregas em fatias verticais, mantendo frontend e backend evoluindo juntos.

---

## 1. Visão geral

O **FluxMed** é um projeto acadêmico e de portfólio desenvolvido para o **Tech Challenge — Fase 2**, com foco no **Projeto 2: Otimização de Rotas para Distribuição de Medicamentos e Insumos**.

O sistema será responsável por planejar operações diárias de distribuição médica em uma cidade fictícia chamada **Santa Aurora**, considerando múltiplos veículos, prioridades de entrega, capacidade, volume, autonomia, janelas de horário, trânsito, restrições viárias, equipes e custos operacionais.

O núcleo de otimização será baseado em **Algoritmos Genéticos (GA)**, complementado por:

- roteamento urbano em grafo dirigido;
- A*/Dijkstra para cálculo de caminhos entre pontos;
- decoder para transformar cromossomos em rotas de veículos;
- pruning e repair para reduzir avaliações inviáveis;
- validação independente da solução final;
- alocação de equipe por solver determinístico;
- visualização das rotas em mapa;
- integração com LLM para explicações, instruções e relatórios.

A aplicação deve ter aparência e engenharia de produto profissional, mas sem complexidade de infraestrutura incompatível com um projeto acadêmico e de portfólio.

---

## 2. Objetivo acadêmico

O FluxMed deverá atender aos requisitos do Projeto 2 do Tech Challenge, incluindo:

- implementação de Algoritmo Genético aplicado a roteamento;
- representação genética adequada;
- seleção, crossover e mutação;
- função fitness considerando distância, prioridade e restrições;
- prioridades diferentes entre entregas;
- capacidade limitada de veículos;
- autonomia limitada;
- múltiplos veículos, evoluindo o problema para VRP;
- visualização das rotas otimizadas em mapa;
- adaptação do código-base de TSP em Python fornecido pela instituição;
- integração com LLM;
- geração de instruções para motoristas/equipes;
- geração de relatórios;
- sugestões de melhoria;
- perguntas em linguagem natural sobre rotas e entregas;
- testes automatizados;
- documentação técnica e arquitetural;
- comparação com outras estratégias de roteamento;
- demonstração do sistema funcionando.

> O código-base de TSP fornecido pelo professor será analisado e incorporado quando estiver disponível no repositório.

---

## 3. Posicionamento do projeto

O FluxMed **não nasce como um produto SaaS comercial**.

Ele nasce como:

1. entrega acadêmica;
2. demonstração prática de algoritmos genéticos;
3. projeto forte de portfólio;
4. sistema com arquitetura profissional e código sustentável.

Por isso, a regra de escopo é:

> Se uma decisão melhora a entrega acadêmica, demonstração, qualidade arquitetural, confiabilidade ou valor de portfólio, ela pode entrar na V1.  
> Se serve apenas para preparar o sistema para uma escala empresarial hipotética, fica como evolução futura.

---

## 4. Escopo da V1

A V1 é um **sistema de planejamento diário**.

Fluxo principal:

```text
Login
  ↓
Criar operação
  ↓
Configurar data, saída, fim da jornada e tráfego
  ↓
Selecionar / importar / gerar entregas
  ↓
Selecionar frota e equipe disponíveis
  ↓
Validar viabilidade
  ↓
Executar otimização
  ↓
Acompanhar evolução do GA no mapa
  ↓
Analisar plano final
  ↓
Aprovar
  ↓
Despachar como estado lógico
  ↓
Gerar relatórios e consultar Assistente IA
```

### Incluído na V1

- autenticação simples;
- roles `ADMIN` e `PLANNER`;
- operações versionadas;
- cidade sintética Santa Aurora;
- grafo viário dirigido;
- tráfego sintético dependente do horário;
- interdições manuais por operação;
- entregas manuais;
- importação XLSX/CSV;
- geração de cenários sintéticos;
- frota heterogênea;
- equipes e ajudantes;
- custos operacionais;
- planejamento com Algoritmo Genético;
- pruning;
- repair;
- Team Assignment Solver;
- Solution Validator;
- Decision Trace;
- animação da otimização;
- replay;
- relatórios;
- exportação PDF/XLSX;
- Assistente IA;
- testes automatizados;
- CI/CD;
- deploy acadêmico.

### Fora da V1

- GPS real;
- rastreamento de veículos;
- aplicativo de motorista;
- telemetria de frota;
- coleta/pickup;
- reotimização por eventos reais durante rota;
- Kafka/RabbitMQ;
- Redis/Celery obrigatórios;
- microserviços;
- Kubernetes;
- múltiplos centros de distribuição;
- carregamento 3D;
- integração com trânsito real;
- regras trabalhistas detalhadas;
- horas extras;
- pausas/almoço;
- processamento distribuído.

Esses pontos podem aparecer apenas como **evoluções futuras**.

---

## 5. Cidade de demonstração

A primeira cidade é **Santa Aurora**, uma cidade brasileira fictícia gerada de maneira determinística e persistida em PostgreSQL/PostGIS.

O dataset foi projetado para possuir aproximadamente:

- 9 bairros;
- ~800 interseções;
- mais de 2.000 segmentos viários dirigidos;
- ~150 ruas/logradouros com nomes determinísticos e normalizados;
- 20.000–40.000 endereços válidos individualmente armazenados;
- 40–60 facilities médicas e logísticas;
- residências utilizáveis para cenários de home care;
- centro de distribuição FluxMed no Distrito Logístico;
- rio como barreira real do grafo;
- três pontes estratégicas;
- anel viário;
- vias expressas, arteriais, coletoras, locais e de serviço;
- lotes ocupados e vazios, criando gaps realistas de numeração;
- endereços associados explicitamente a edificação, entrada e segmento viário.

A busca de endereços consulta somente números realmente existentes no dataset. Erros de digitação no logradouro podem gerar sugestão fuzzy, enquanto números inexistentes recebem sugestões próximas sem aproximação silenciosa.

A aplicação é **city-agnostic**. Santa Aurora é apenas o primeiro `CityProvider`.

---

## 6. Arquitetura de alto nível

```text
┌───────────────────────────────────────────────┐
│              React + Vite + TS                │
│                                               │
│ Dashboard · Operações · Mapa · Relatórios     │
└──────────────────────┬────────────────────────┘
                       │ HTTP / SSE
                       ▼
┌───────────────────────────────────────────────┐
│                  FastAPI                      │
│                                               │
│ Application · Domain · Routing · Optimization │
│ Fleet · Workforce · Reports · LLM             │
└──────────────────────┬────────────────────────┘
                       │
                       ▼
┌───────────────────────────────────────────────┐
│           PostgreSQL + PostGIS                │
└───────────────────────────────────────────────┘
```

### Deploy inicial

- **Frontend:** Vercel
- **Backend:** Vercel, enquanto os benchmarks mostrarem que é suficiente
- **Banco:** Neon PostgreSQL/PostGIS

A arquitetura deverá permitir mover o FastAPI/optimizer para um serviço Python persistente no futuro sem redesenhar o domínio.

---

## 7. Stack principal

### Frontend

- React
- Vite
- TypeScript
- MapLibre GL
- cliente TypeScript gerado a partir do OpenAPI
- Vitest
- React Testing Library
- Playwright

### Backend

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- PostgreSQL
- PostGIS

### Otimização

- Algoritmo Genético próprio
- Tournament Selection
- Order Crossover (OX)
- mutações Swap, Insertion e Inversion/Reverse
- elitismo
- mutação adaptativa
- diversidade populacional
- população inicial híbrida
- decoder determinístico

### LLM

- provider abstraction (`LLMProvider`);
- Cohere durante desenvolvimento;
- Gemini opcional para entrega final;
- ferramentas controladas no backend;
- LLM não participa da decisão matemática do solver.

---

## 8. Princípios arquiteturais

### Modular monolith

O backend será um **modular monolith**.

A estrutura separará claramente:

```text
domain
application
infrastructure
api
optimization
routing
city
deliveries
fleet
workforce
operations
reports
llm
observability
security
```

### Dependências

Regra conceitual:

```text
API → Application → Domain
                ↘ Infrastructure
```

O domínio não deve conhecer:

- FastAPI;
- SQLAlchemy;
- Cohere;
- Gemini;
- Vercel;
- Neon;
- React;
- MapLibre.

---

## 9. Estrutura do repositório

```text
fluxmed/
├── apps/
│   ├── web/
│   │   └── src/
│   │       ├── app/
│   │       ├── components/
│   │       ├── features/
│   │       ├── pages/
│   │       ├── services/
│   │       └── types/
│   │
│   └── api/
│       ├── src/fluxmed/
│       │   ├── domain/
│       │   ├── application/
│       │   ├── infrastructure/
│       │   ├── api/
│       │   ├── optimization/
│       │   ├── routing/
│       │   ├── city/
│       │   ├── deliveries/
│       │   ├── fleet/
│       │   ├── workforce/
│       │   ├── operations/
│       │   ├── reports/
│       │   ├── llm/
│       │   ├── observability/
│       │   └── security/
│       ├── migrations/
│       └── tests/
│
├── data/
│   ├── santa_aurora/
│   └── import_templates/
│
├── benchmarks/
│   ├── scenarios/
│   ├── algorithms/
│   ├── results/
│   └── notebooks/
│
├── tests/
│   ├── e2e/
│   ├── smoke/
│   └── resilience/
│
├── scripts/
├── docs/
├── infra/
├── .github/
├── docker-compose.yml
├── .env.example
├── Makefile
├── README.md
└── CONTRIBUTING.md
```

---

## 10. Execução local

### Pré-requisitos

- Python 3.12+
- Node.js 20+
- Docker

### Banco

```bash
docker compose up -d db
```

### Backend

```bash
cd apps/api
python -m venv .venv
```

Ativar ambiente virtual.

Windows:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Instalar:

```bash
pip install -e ".[dev]"
```

Rodar migrations:

```bash
alembic upgrade head
```

Gerar/atualizar Santa Aurora:

```bash
python ../../scripts/generate_santa_aurora.py --replace
python ../../scripts/validate_city.py
```

Criar usuário demo:

```bash
python -m fluxmed.scripts.seed_demo
```

Rodar API:

```bash
uvicorn fluxmed.main:app --reload
```

### Frontend

```bash
cd apps/web
npm install
npm run dev
```

---

## 11. Documentos oficiais

A especificação detalhada está em `docs/`.

Documentos principais:

- `PRODUCT_SPEC.md`
- `ARCHITECTURE.md`
- `DOMAIN_MODEL.md`
- `SANTA_AURORA_SPEC.md`
- `OPTIMIZATION_SPEC.md`
- `FRONTEND_SPEC.md`
- `API_SPEC.md`
- `LLM_SPEC.md`
- `TESTING_STRATEGY.md`
- `DEVELOPMENT_PLAN.md`
- `CODEX_INSTRUCTIONS.md`

---

## 12. Licença e contexto

Projeto acadêmico e de portfólio.

Os dados de Santa Aurora são sintéticos e não representam uma cidade real.
