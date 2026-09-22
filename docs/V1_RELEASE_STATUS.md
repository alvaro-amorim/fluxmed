# FluxMed — V1 Release Status

## Estado atual

A V1 está funcionalmente concluída até a Fase 18.

- Fases 0–18: implementadas/validadas conforme o plano de desenvolvimento;
- Fase 18 (hardening): encerrada;
- Fase 19 (deploy, smoke e release): pendente;
- nenhuma nova feature deve entrar antes do release salvo correção de bloqueador real.

## Evidência final local da Fase 18

### Backend

- Ruff: verde;
- `ruff format --check`: verde;
- mypy strict: verde;
- `pytest`: **169 passed**.

### Frontend

- ESLint: verde;
- TypeScript typecheck: verde;
- Vitest: **26 passed**;
- build de produção: verde.

### E2E manual

Fluxo validado:

```text
login
-> operation
-> deliveries
-> resources
-> closure/preflight
-> optimization
-> result
-> assistant
-> report
-> approve
-> dispatch
```

Também foram validados:

- relatório PDF;
- relatório XLSX;
- relatório CSV;
- Assistente IA com provider Gemini real;
- grounding agregado;
- transição `OPTIMIZED -> APPROVED -> DISPATCHED`;
- imutabilidade da revisão/equipe após dispatch.

## Estado Git / PR stack

A implementação final está empilhada nesta ordem:

1. PR #17 — `feat/llm-assistant` -> `main`;
2. PR #18 — `feat/academic-benchmarks` -> `feat/llm-assistant`;
3. PR #19 — `chore/v1-hardening` -> `feat/academic-benchmarks`.

A relação de ancestry foi verificada: cada branch está estritamente à frente da anterior, sem divergência no stack.

Não fazer merge fora dessa ordem.

## Limitação conhecida do GitHub Actions

Os jobs rápidos do PR #17 chegaram a `failure` antes de qualquer step (`steps=null`), enquanto o Full CI foi corretamente `skipped` pela política de Draft PR.

A limitação de runner/quota/billing está documentada em:

- `docs/HARDENING_PLAN.md`;
- `docs/CI_POLICY.md`.

Isso não é tratado como evidência de sucesso do CI. A evidência atual de código é a regressão local completa registrada acima.

## Gate para iniciar a Fase 19

Antes de criar `chore/v1-release`:

- [ ] revisar PR #17;
- [ ] mergear PR #17 em `main`;
- [ ] retarget/revisar PR #18 após o merge anterior;
- [ ] mergear PR #18;
- [ ] retarget/revisar PR #19;
- [ ] mergear PR #19;
- [ ] confirmar `main` contendo a V1 completa;
- [ ] criar `chore/v1-release` a partir de `main`.

## Gate técnico da Fase 19

Na branch de release:

- [ ] decidir o deploy real com base nas limitações medidas do backend/GA;
- [ ] configurar variáveis de produção sem versionar secrets;
- [ ] provisionar PostgreSQL/PostGIS;
- [ ] aplicar migrations em banco limpo;
- [ ] executar seed da cidade e usuário demo;
- [ ] validar health/readiness;
- [ ] configurar provider LLM real para a demonstração;
- [ ] executar smoke pós-deploy;
- [ ] executar secret/dependency/static-analysis checks disponíveis;
- [ ] registrar qualquer limitação de CI/infrastrutura que permaneça externa ao código;
- [ ] preparar release notes;
- [ ] criar tag `v1.0.0` somente após smoke verde.

## Smoke mínimo de release

```text
frontend abre
login funciona
operações carregam
Santa Aurora carrega
criar operação pequena
adicionar/gerar demanda
selecionar recursos
preflight válido
otimizar cenário pequeno
abrir resultado
consultar Assistente IA
gerar relatório
aprovar
despachar
confirmar imutabilidade
```

## Regra de congelamento

Durante a Fase 19:

> corrigir bloqueadores; não ampliar escopo.

O objetivo da próxima fase é disponibilizar, demonstrar e congelar a V1 acadêmica, não iniciar uma V2.
