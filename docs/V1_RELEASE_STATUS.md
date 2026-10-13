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

## Estado Git / PR stack — concluído em 13/10/2026

As três PRs foram revisadas, executaram Full CI com sucesso e foram integradas na `main` com commits de merge (sem squash):

1. PR #17 — Fase 16 (Assistente IA), merge `0c6ec5af377871b10b043d7bfd478a453e3e4cf2`;
2. PR #18 — Fase 17 (Benchmarks), merge `1e172f8e77ea44bf3124273173ca3f16c3d5dc70`;
3. PR #19 — Fase 18 (Hardening), merge `ec51744863cd49dcfada994e6bec8e6a78b28276`.

A `main` foi verificada no commit `ec51744863cd49dcfada994e6bec8e6a78b28276`.
A branch `chore/v1-release` foi criada exatamente a partir desse commit para iniciar a Fase 19.

## Evidência de CI após os merges

O GitHub Actions retomou a execução de jobs em 13/10/2026, permitindo a validação real dos três PRs:

- [PR #17 — Full CI verde](https://github.com/alvaro-amorim/fluxmed/actions/runs/38416081953);
- [PR #18 — Full CI verde](https://github.com/alvaro-amorim/fluxmed/actions/runs/38416715739);
- [PR #19 — Full CI verde](https://github.com/alvaro-amorim/fluxmed/actions/runs/38417442393).

O último Full CI validou:

- Backend: Ruff, formatação, MyPy strict (126 arquivos), migrations e **169 testes aprovados**;
- Frontend: lint, typecheck, **26 testes aprovados** e build de produção;
- E2E automatizado: jornada de login demo com banco real.

Os testes da jornada operacional ponta a ponta registrada acima são evidência de validação manual; o job E2E automatizado do CI cobre especificamente o login demo.

O primeiro CI reativado identificou 71 erros de tipagem com SQLAlchemy 2.1.4, que era aceito pela faixa aberta `>=2.0,<3.0`. A dependência foi restringida à série estável `sqlalchemy>=2.0,<2.1` no PR #17 e o Full CI seguinte passou. Falhas históricas anteriores ao início dos jobs eram relacionadas a quota/billing do GitHub Actions, e não constituíam aprovação automática.

## Gate para iniciar a Fase 19 — concluído

- [x] revisar PR #17;
- [x] mergear PR #17 em `main`;
- [x] retarget/revisar PR #18 após o merge anterior;
- [x] mergear PR #18;
- [x] retarget/revisar PR #19;
- [x] mergear PR #19;
- [x] confirmar `main` contendo a V1 completa;
- [x] criar `chore/v1-release` a partir de `main`.

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
