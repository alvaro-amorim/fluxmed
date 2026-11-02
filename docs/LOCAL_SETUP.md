# FluxMed — guia de instalação local

O ambiente local utiliza Docker Compose, que reúne as dependências de execução da API, frontend e banco espacial.

## Pré-requisitos

- Git, Docker Desktop (Windows com WSL2 ou macOS) ou Docker Engine + Compose v2 (Linux);
- memória e armazenamento suficientes para o banco espacial e Santa Aurora;
- portas 5432, 8000 e 5173 disponíveis;
- acesso ao repositório no GitHub.

## Instalação inicial

```bash
git clone https://github.com/alvaro-amorim/fluxmed.git
cd fluxmed
```

Crie seu arquivo local de configuração:

```powershell
# Windows — PowerShell
Copy-Item .env.example .env
```

```bash
# macOS / Linux
cp .env.example .env
```

Na raiz do projeto:

```bash
docker compose up --build -d
docker compose ps -a
```

O Compose prepara PostgreSQL/PostGIS, aplica as migrations, cria Santa Aurora e o usuário de demonstração, e inicia o backend e frontend. **A primeira carga pode demorar** porque Santa Aurora contém muitos registros geográficos.

O serviço `init` terminar como **Exited (0)** é normal: significa que as migrations e o seed finalizaram. A API mantém um único processo, pois o executor de otimização da V1 funciona dentro dele.

Abra **http://localhost:5173**. A API responde também em **http://localhost:8000/health/ready** e através do proxy do frontend em **http://localhost:5173/health/ready**.

### Credenciais de demonstração

E-mail: `planner@fluxmed.demo`
Senha: `FluxMedDemo2026!`

Essas credenciais são públicas e exclusivas do ambiente demonstrativo, nunca de produção. Alterando a conta no `.env`, mantenha `DEMO_PLANNER_*` e `VITE_DEMO_*` sincronizados.

## Fluxo sugerido para avaliação

Entre, selecione Santa Aurora, crie uma operação, gere uma demanda pequena, configure veículos e equipe, valide o preflight e execute a otimização. Acompanhe o GA e o SSE; depois confira resultado, Assistente IA, relatórios PDF/XLSX/CSV, aprovação, despacho e imutabilidade.

A primeira inicialização **não cria uma operação pré-otimizada**; o avaliador precisa gerar sua própria operação no aplicativo.

## IA simulada ou Gemini real

A instalação padrão usa `LLM_PROVIDER=mock` e `LLM_MODEL=fluxmed-mock-v1`. Isso permite explorar o Assistente e suas consultas ao backend, **mas não faz chamadas reais ao Gemini**.

Para testar a integração real, use uma **chave própria** no arquivo local `.env` (nunca versionado) e **substitua** as linhas existentes de provider/modelo:

```dotenv
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3.5-flash-lite
LLM_THINKING_LEVEL=minimal
GEMINI_API_KEY=SUA_CHAVE_PESSOAL_AQUI
```

Aplique a mudança usando `docker compose up -d --force-recreate api`. No Assistente, selecione uma operação já otimizada, confira `gemini`/modelo na interface e **envie uma pergunta**. O status saudável sozinho não comprova acesso ao Google. Se houver limitação de cota, indisponibilidade ou timeout, a API informa erro; não muda silenciosamente para o mock.

A chave fica exclusivamente no container da API. Nunca a mostre em vídeo, print ou comando de diagnóstico. A conta do avaliador é responsável por seus limites e eventuais custos. O modo mock permite explorar o fluxo com respostas simuladas; o ensaio externo utiliza chave e cota da conta configurada.

O passo a passo completo, exemplos de perguntas, conferência das respostas e cuidados com a chave estão no **[guia de avaliação do Assistente IA](ASSISTANT_EVALUATION.md)**. A demonstração gravada está disponível no [vídeo acadêmico](https://youtu.be/gHc-irrihV0).

## Diagnóstico e desligamento

```bash
docker compose ps -a
docker compose logs -f init api web
docker compose logs --tail 100 db
docker compose down
docker compose up -d
```

Se a interface não abrir, confira se `init` terminou com código zero e se API e frontend estão ativos. Em caso de portas ocupadas, encerre servidores locais anteriores. No primeiro start, aguarde o seed.

`docker compose down` **preserva** os dados. O comando `docker compose down -v` **apaga** o volume de dados: não o use para apenas reiniciar.

## Modo alternativo (sem Docker para API e web)

Suba só o banco com `docker compose up -d db`. Em `apps/api`, usando Python 3.12, instale `python -m pip install -e ".[dev]"`, execute `alembic upgrade head`, `python -m fluxmed.scripts.seed_demo` e `uvicorn fluxmed.main:app --app-dir src --reload`. Em `apps/web`, com Node 22, execute `npm ci` e `npm run dev`. Nesse modo, o proxy usa localhost:8000. Variáveis personalizadas precisam ser carregadas no shell.

## Verificação técnica

O [workflow de smoke local](../.github/workflows/local-compose-smoke.yml) prepara a pilha e verifica acesso pelo proxy. O [CI](../.github/workflows/ci.yml) e a [estratégia de testes](TESTING_STRATEGY.md) descrevem os comandos e os escopos automatizados. Para a conferência operacional, use a mesma operação no resultado, mapa, assistente e relatórios.
