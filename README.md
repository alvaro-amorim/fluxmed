# FluxMed

> Planejamento inteligente de rotas médicas com Algoritmos Genéticos, restrições operacionais realistas e integração com LLM.

## Status

**Fase atual:** documentação e preparação do repositório.  
**Implementação:** ainda não iniciada.  
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

A primeira cidade será **Santa Aurora**, uma cidade brasileira fictícia gerada de maneira determinística.

Características planejadas:

- aproximadamente 9 bairros;
- cerca de 800 interseções;
- cerca de 2.000 segmentos viários;
- aproximadamente 150 ruas nomeadas;
- dezenas de milhares de endereços válidos;
- hospitais;
- clínicas;
- laboratórios;
- farmácias;
- residências para home care;
- centro de distribuição;
- rio;
- pontes;
- anel viário;
- vias expressas, arteriais, coletoras, locais e de serviço;
- sentidos únicos e vias de mão dupla;
- perfis de trânsito por região, classe de via e horário.

A aplicação será **city-agnostic**. Santa Aurora será apenas o primeiro `CityProvider`.

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
- pruning
- repair
- Solution Validator independente

### Inteligência artificial

Interface abstrata:

```text
LLMProvider
├── CohereProvider
└── GeminiProvider
```

Cohere poderá ser utilizado durante o desenvolvimento e Gemini na versão final, sem alterar a aplicação.

---

## 8. Modelo de otimização

O GA **não otimizará cada curva da rua**.

Existem duas camadas:

### Camada 1 — Routing urbano

Responsável por:

> Qual o melhor caminho entre A e B?

Utiliza grafo dirigido e A*/Dijkstra, considerando:

- distância;
- velocidade;
- trânsito;
- sentidos;
- interdições;
- horário estimado de passagem.

### Camada 2 — Fleet/VRP Optimization

Responsável por:

> Qual veículo atende cada entrega e em qual ordem?

O cromossomo será uma **permutação global de entregas**.

Um `RouteDecoder` transforma essa permutação em rotas reais, respeitando as restrições operacionais.

---

## 9. Hierarquia da fitness

A avaliação será **lexicográfica**, e não uma soma arbitrária de pesos.

Prioridade:

1. viabilidade HARD;
2. qualidade de serviço;
3. risco de entregas críticas;
4. custo operacional;
5. makespan;
6. tempo total de viagem;
7. distância;
8. número/utilização de veículos como critério secundário.

Uma solução inválida nunca poderá vencer uma solução válida apenas por ser barata ou curta.

Se nenhuma solução válida for encontrada, o FluxMed deverá informar os gargalos em vez de apresentar uma rota “quase válida”.

---

## 10. Restrições principais

O planejamento deverá considerar, entre outras:

- capacidade máxima em kg;
- capacidade máxima em m³;
- autonomia operacional;
- refrigeração;
- prioridade;
- janelas `HARD` e `SOFT`;
- tempo de serviço;
- necessidade de duas pessoas;
- disponibilidade de veículos;
- disponibilidade de equipe;
- vias incompatíveis;
- ruas interditadas;
- fim máximo da jornada;
- retorno ao depósito;
- custos.

---

## 11. Frota

Tipos iniciais:

- `MOTO`
- `VAN_COMPACT`
- `CARGO_VAN`
- `LIGHT_TRUCK`

Veículos podem ser:

- `OWNED`;
- `AGGREGATED`.

O cálculo de custo deverá distinguir:

- combustível;
- depreciação por km;
- manutenção por km;
- custos fixos;
- custo da equipe;
- contrato de agregado.

Peso e volume devem ser restrições independentes.

---

## 12. Equipe

Papéis:

- `DRIVER`
- `HELPER`
- `MOTORCYCLE_COURIER`

A equipe **não fará parte do cromossomo**.

Um `TeamAssignmentSolver` determinístico fará a alocação de pessoas às rotas depois da composição das rotas, considerando:

- compatibilidade;
- disponibilidade;
- custo;
- ajudante obrigatório/opcional;
- contratos em que motorista/ajudante já estejam incluídos.

---

## 13. Entregas

Cada entrega será uma parada logística relacionada a uma NF/documento.

Identificação:

- UUID técnico interno;
- código operacional legível;
- NF;
- série;
- emissor.

Exemplo:

```text
DLV-NF45872-001
```

Campos relevantes incluem:

- endereço;
- destinatário;
- quantidade de volumes;
- peso;
- volume;
- prioridade;
- janela;
- política HARD/SOFT;
- tempo de serviço;
- temperatura;
- necessidade de duas pessoas.

---

## 14. Geração sintética de cenários

O usuário escolherá separadamente:

### Perfil

- `NORMAL`
- `BUSY`
- `HIGH_PRESSURE`
- `EMERGENCY`
- `CUSTOM`

### Quantidade

- 20;
- 40;
- 60;
- 80;
- personalizada.

A geração não será aleatória de forma ingênua.

O gerador deverá considerar:

- demanda por bairro;
- tipo de destino;
- hospitais/clinicas/laboratórios/farmácias;
- home care;
- arquétipos de carga;
- coerência entre peso, volume e número de volumes;
- prioridade;
- refrigeração;
- ajudante;
- janelas plausíveis.

Uma solução viável de referência poderá ser usada internamente para gerar janelas realistas sem revelar essa solução ao GA.

---

## 15. Visualização da otimização

A otimização deverá ser visível no mapa.

Durante a execução serão exibidos dados reais do algoritmo, como:

- geração;
- tempo decorrido;
- melhor custo;
- makespan;
- diversidade;
- taxa de mutação;
- candidatos podados;
- melhorias;
- alterações de rotas;
- convergência.

Não será usada animação falsa de “IA pensando”.

Após o cálculo:

```text
Ver replay do cálculo
```

utilizará o mesmo `Decision Trace` armazenado.

---

## 16. Decision Trace

O sistema armazenará evidências estruturadas do processo, e não raciocínio interno.

Exemplos:

- `GenerationSnapshot`
- `PruningEvent`
- `ImprovementEvent`
- `RouteAssignmentChange`
- `VehicleSelectionReason`
- `ConstraintViolation`
- `FinalComparison`

O Decision Trace alimentará:

- animação ao vivo;
- replay;
- explicações técnicas;
- relatórios;
- Assistente IA.

---

## 17. LLM

A LLM é uma **camada de interpretação**, não o otimizador.

Ela poderá:

- explicar rotas;
- explicar seleção de veículos;
- explicar uso de ajudantes;
- gerar instruções para equipes;
- gerar relatórios;
- comparar resultados;
- responder perguntas em linguagem natural;
- sugerir melhorias;
- simular alterações por meio de ferramentas controladas.

Ela não poderá:

- modificar o banco diretamente;
- alterar rotas autonomamente;
- despachar uma operação;
- substituir regras matemáticas;
- inventar custos ou métricas;
- executar alterações sem validação do backend e confirmação humana.

---

## 18. Qualidade e testes

O FluxMed terá testes desde o início.

Tipos planejados:

- unitários;
- integração;
- contrato da API;
- property-based;
- regressão algorítmica;
- E2E;
- smoke;
- performance;
- carga;
- resiliência;
- migrations;
- validação da cidade;
- LLM evals;
- architecture tests;
- segurança.

O `SolutionValidator` será independente do GA e validará toda solução antes que ela possa ser apresentada como válida.

---

## 19. Git e engenharia

Fluxo:

```text
main
  ↑
Pull Request
  ↑
feature/fix/test/chore branch
```

Regras:

- nenhuma feature relevante diretamente em `main`;
- branches curtas;
- PR;
- CI verde;
- Conventional Commits;
- Semantic Versioning;
- changelog/releases quando aplicável.

Exemplos:

```text
feat: add Santa Aurora city generator
fix: reject invalid hard time window route
test: add decoder property tests
docs: document optimization architecture
```

---

## 20. Estratégia de desenvolvimento

O projeto será implementado em **fatias verticais**.

Não será feito primeiro todo o frontend nem primeiro todo o backend.

Ordem conceitual:

```text
Fundação
   ↓
Domínio + contratos
   ↓
primeira feature backend + frontend
   ↓
Santa Aurora + mapa
   ↓
Entregas/frota/equipe
   ↓
Routing
   ↓
GA
   ↓
Decision Trace
   ↓
LLM
   ↓
Relatórios
   ↓
Polimento
```

Cada etapa deve terminar executável e testada antes da próxima grande etapa.

---

## 21. Estrutura planejada do monorepo

```text
fluxmed/
├── apps/
│   ├── web/
│   └── api/
├── data/
├── benchmarks/
├── docs/
├── infra/
├── scripts/
├── tests/
├── .github/
├── docker-compose.yml
├── .env.example
├── README.md
├── CONTRIBUTING.md
└── LICENSE
```

A estrutura será criada progressivamente. O repositório deve começar simples e crescer somente conforme as fases de implementação exigirem.

---

## 22. Fonte de verdade

Este `README.md` apresenta a visão geral.

As regras detalhadas serão documentadas separadamente em `docs/` durante a preparação do projeto.

Documentos planejados:

```text
docs/
├── PRODUCT_SPEC.md
├── ARCHITECTURE.md
├── DOMAIN_MODEL.md
├── SANTA_AURORA_SPEC.md
├── OPTIMIZATION_SPEC.md
├── FRONTEND_SPEC.md
├── API_SPEC.md
├── LLM_SPEC.md
├── TESTING_STRATEGY.md
├── DEVELOPMENT_PLAN.md
├── CODEX_INSTRUCTIONS.md
└── adr/
```

Em caso de divergência entre implementação e documentação, a divergência deverá ser resolvida explicitamente. Decisões arquiteturais relevantes serão registradas em ADRs.

---

## 23. Princípio central

> O FluxMed deve demonstrar profundidade técnica sem confundir profissionalismo com complexidade desnecessária.

A prioridade é construir uma solução:

- academicamente defensável;
- tecnicamente correta;
- visualmente convincente;
- testável;
- explicável;
- organizada;
- reproduzível;
- apresentável em portfólio.
