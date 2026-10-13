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

## Fase 19 — Finalização e entrega acadêmica local

**Decisão de escopo:** sem deploy em nuvem. O professor executará o projeto a partir do GitHub em sua máquina. A execução em nuvem é opcional no Tech Challenge.

### Entrega executável

- [x] auditar dependências, banco, migrações, seed, autenticação e configurações de IA;
- [x] adicionar Docker Compose para banco + etapa de inicialização + API + frontend;
- [x] preservar um processo de API para o GA em segundo plano;
- [x] manter proxy HTTP/SSE com cookies no mesmo domínio do navegador;
- [x] adicionar Dockerfiles e .dockerignore de API e frontend;
- [x] escrever guia para clone e execução local;
- [x] criar workflow de smoke Docker Compose;
- [x] confirmar workflow Docker Compose **verde** no GitHub Actions ([smoke após correção de Docker](https://github.com/alvaro-amorim/fluxmed/actions/runs/38481422992));
- [x] validar clone limpo no Windows: Docker, PostGIS, migrations, seed, frontend e login; otimização de 20 entregas em 3 veículos (100% no prazo), PDF/XLSX/CSV e operação despachada, conforme prints enviados pelo autor;
- [ ] confirmar acesso do avaliador ao repositório (atualmente privado).

### Entregáveis acadêmicos

- [ ] consolidar relatório técnico: GA, representação, operadores, restrições, benchmarks, LLM, resultados e desafios;
- [ ] documentar a adaptação do código-base TSP do professor, se disponibilizado;
- [ ] preparar e publicar vídeo demonstrativo de até 15 minutos;
- [ ] concluir verificação final de segredos e das evidências antes da tag (documentação mock/Gemini pronta);
- [ ] abrir/revisar PR da release e integrar em main após checks e instalação limpa;
- [ ] criar tag `v1.0.0` somente após aceite.

### Roteiro de validação local

```text
clone → .env.example → docker compose up --build -d
PostGIS → migrations → Santa Aurora → login
operação pequena → demanda → frota/equipe → preflight
otimização/GA/SSE → resultado → assistente
PDF/XLSX/CSV → aprovação → dispatch → imutabilidade
```

O modo `mock` permite explorar a interface e o grounding, mas não produz chamadas reais à LLM. A integração Gemini real foi verificada manualmente durante o desenvolvimento e deverá ser demonstrada no vídeo acadêmico, sem expor credenciais.

O avaliador que desejar repetir uma chamada Gemini precisa configurar a própria chave no `.env` local. A documentação reproduzível está em [ASSISTANT_EVALUATION.md](ASSISTANT_EVALUATION.md).

A instalação limpa no Windows confirmou o estado `DISPATCHED` e os três relatórios `Pronto`; a tentativa específica de alteração após despacho não foi novamente evidenciada nos prints desta instalação e permanece coberta pelos testes anteriores.

### Congelamento

Durante a Fase 19, somente corrigir problemas impeditivos de instalação, segurança, testes e entrega — sem introduzir novas funcionalidades.
