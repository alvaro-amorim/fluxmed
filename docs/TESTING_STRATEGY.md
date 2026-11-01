# FluxMed — testes e verificações

## Escopos

| Área | Ferramentas e verificações |
|---|---|
| Backend | Pytest, Ruff, formatação e MyPy strict. |
| Algoritmo | Permutação, operadores, prioridades, espera, restrições e validação independente. |
| Avaliação operacional | Equipe, combustível, contratos, custo e coerência com a persistência. |
| Routing e cidade | Grafo dirigido, caminhos, trânsito, geração e integração espacial. |
| API e persistência | Schemas, autorização, lifecycle, relatórios e transações em banco dedicado. |
| Assistente | Grounding, seleção semântica, follow-up, controles de prompt e falhas com respostas controladas. |
| Frontend | Vitest/Testing Library para componentes e serviços; lint, TypeScript e build. |
| E2E automatizado | Playwright: login demo, acesso a Operações e logout. |
| Verificação manual | Jornada operacional, mapa, formatos de relatório e conferência de resposta externa da LLM. |

As suítes de frontend, backend, integração e E2E têm alcances distintos. Resultados de uma execução devem identificar revisão, comando e ambiente; contagens de subconjuntos não são somadas como se fossem testes únicos.

## Backend e banco dedicado

Use Python 3.12 e o ambiente virtual da API, com dependências de desenvolvimento instaladas. Antes de executar pytest, configure `TEST_DATABASE_URL` para um banco exclusivo de testes e confira sua identificação. O [conftest](../apps/api/tests/conftest.py) exige `test` no nome quando essa variável está definida e a usa como `DATABASE_URL` durante a coleta.

Em `apps/api`, com o banco de teste configurado:

```powershell
$env:LLM_PROVIDER = "mock"
python -m ruff check src tests
python -m ruff format --check src tests
python -m mypy src
python -m pytest -q -m "not integration"
```

Para a suíte completa, disponibilize PostgreSQL/PostGIS dedicado e use o mesmo ambiente de teste:

```powershell
python -m pytest -q
```

Os testes marcados `integration` podem preparar ou modificar estruturas/dados do banco indicado. Os providers nos testes são controlados por mocks/fakes; a validação externa da LLM é um ensaio separado.

## Regressões de otimização e experimento

As fontes de teste incluem:

- [Núcleo](../apps/api/tests/test_optimization_core.py), [restrições](../apps/api/tests/test_optimization_advanced.py) e [regressões](../apps/api/tests/test_optimization_regressions.py).
- [Fitness operacional](../apps/api/tests/test_operational_fitness.py) e [integração](../apps/api/tests/test_optimization_integration.py).
- [Geometria](../apps/api/tests/test_optimization_geometry.py), [trace](../apps/api/tests/test_optimization_trace.py) e [resiliência](../apps/api/tests/test_optimization_resilience.py).
- [Runner do benchmark](../apps/api/tests/test_benchmark_runner.py), [matriz](../apps/api/tests/test_benchmark_matrix.py), [fixture](../apps/api/tests/test_benchmark_template_fixture.py) e [checkpoints](../apps/api/tests/test_benchmark_checkpoint.py).

Os casos cobrem alternativas com prioridades diferentes, espera, equipe indisponível, componentes de custo, carga declarada incorretamente, janela HARD violada e reutilização de veículo. Os checkpoints verificam retomada, integridade e rejeição de experimentos incompatíveis.

## Frontend

Em `apps/web`, com as dependências instaladas:

```powershell
npm.cmd run lint
npm.cmd run typecheck
npm.cmd test
npm.cmd run build
```

Os scripts são definidos em [package.json](../apps/web/package.json). Em shells Unix, use `npm` no lugar de `npm.cmd`.

O E2E exige a aplicação e o banco demonstrativo de testes preparados; seu escopo é o de [auth.spec.ts](../apps/web/e2e/auth.spec.ts):

```powershell
npm.cmd run test:e2e
```

## Verificação manual e LLM

Conferir a mesma operação nas telas de entradas, resultado, mapa, assistente e relatórios. Registrar o run observado e confrontar horários, sequência, custos e indicadores entre os artefatos.

Para provider externo, registrar provider/modelo, pergunta, resposta, fontes e valores esperados. O status de configuração e os testes com mock possuem escopo diferente de uma chamada externa concluída. O procedimento está em [ASSISTANT_EVALUATION.md](ASSISTANT_EVALUATION.md).

## Evidências e CI

A configuração dos jobs está em [ci.yml](../.github/workflows/ci.yml); os checks rápidos estão em [pr-backend.yml](../.github/workflows/pr-backend.yml) e [pr-frontend.yml](../.github/workflows/pr-frontend.yml). A [política de CI](CI_POLICY.md) descreve os gatilhos.

A evidência experimental de 31/10 contém seu [registro de verificações](../benchmarks/results/final-evidence-operational-20261031/verification.json), vinculado à fonte identificada por hashes. Esse registro documenta o escopo verificado naquela execução. O [guia do benchmark](../benchmarks/README.md) apresenta a matriz e a reprodução.
