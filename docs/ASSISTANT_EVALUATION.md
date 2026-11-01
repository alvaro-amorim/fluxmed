# Avaliação do Assistente IA — mock vs. Gemini real

Este guia explica como avaliar a integração de linguagem natural do FluxMed **sem hospedagem** e sem divulgar chaves pessoais. Complementa o [guia de instalação local](LOCAL_SETUP.md) e a [documentação de implementação](LLM_IMPLEMENTATION.md).

## O que o modo padrão demonstra

Após `cp .env.example .env` (ou `Copy-Item .env.example .env` no PowerShell), a configuração é:

```dotenv
LLM_PROVIDER=mock
LLM_MODEL=fluxmed-mock-v1
```

Nesse modo, o FluxMed usa um provider simulado, sem chamadas ao Google. Ele permite avaliar a **interface do chat**, o vínculo com operações, as consultas estruturadas do backend e o fluxo da aplicação. **Não comprova que uma LLM externa foi chamada nem avalia a qualidade da geração por IA real.**

O algoritmo genético, o roteamento, a validação de restrições e a geração de relatórios funcionam independentemente do Gemini.

## Como executar a integração real no computador do avaliador

O avaliador que quiser verificar pessoalmente uma chamada à LLM precisará de uma chave de API **da própria conta**, com acesso ao modelo e cota disponível. A chave do autor **não é entregue** no repositório.

1. Tenha o FluxMed em execução pelo [Docker Compose](LOCAL_SETUP.md).
2. Obtenha sua própria chave no Google AI Studio, observando os limites e eventuais custos da conta.
3. Abra o **arquivo local `.env` na raiz** do repositório. **Substitua** as linhas existentes de provider/modelo (não adicione um segundo conjunto duplicado):
   ```dotenv
   LLM_PROVIDER=gemini
   LLM_MODEL=gemini-3.5-flash-lite
   LLM_THINKING_LEVEL=minimal
   GEMINI_API_KEY=SUA_CHAVE_PESSOAL_AQUI
   ```
4. Salve o arquivo e recrie somente o container da API:
   ```bash
   docker compose up -d --force-recreate api
   ```
5. Acesse <http://localhost:5173>, faça login, selecione uma operação **já otimizada** no Assistente IA e confirme que a interface mostra `gemini` e o modelo configurado.
6. Envie uma pergunta factual sobre essa operação e confira a resposta e as fontes do backend. Uma resposta bem-sucedida identificada como `gemini` é a evidência prática de que o modelo respondeu; o indicador de status `HEALTHY` **sozinho não é teste de conectividade externa**, pois verifica apenas a construção/configuração do provider.

Perguntas de exemplo após otimizar uma operação:

- "Quantas entregas, veículos e quilômetros tem esta operação?"
- "Qual rota tem mais entregas e quantas são?"
- "Gere instruções para o motorista da primeira rota."
- "Qual é o custo operacional total do plano?"

O sistema busca os fatos no backend antes de encaminhar o contexto relevante ao provider (Structured RAG). Os números devem corresponder ao plano calculado e persistido, não a estimativas inventadas.

**Erros comuns:** `DEGRADED` pode indicar chave ausente ou provider inválido; erros 429, 503 e 504 podem decorrer de cota, disponibilidade ou timeout do Gemini. O FluxMed não muda silenciosamente para `mock` quando uma chamada real falha.

## Como comprovar a integração sem entregar uma chave

O autor demonstrará a integração com Gemini real no **vídeo acadêmico** de até 15 minutos, usando sua chave somente na máquina local. O vídeo deve mostrar:

1. a operação otimizada e seus dados oficiais;
2. a tela do Assistente indicando `gemini` e o modelo;
3. ao menos uma pergunta factual e sua resposta, com fontes/consultas da operação;
4. uma pergunta para instruções de motorista;
5. a comparação visual de valores com o resultado/relatório gerado.

Uma chamada externa é identificada pela resposta concluída e pelos metadados do provider, confrontados com as fontes da operação. O ensaio independente utiliza chave e cota da conta configurada.

## Segurança das credenciais

- O arquivo `.env` é ignorado pelo Git: nunca use `git add -f .env`.
- Não cole sua chave em README, commits, issues, PRs, prints, vídeos ou relatórios.
- Não use variáveis `VITE_*` para chaves: elas são expostas ao navegador.
- O Docker Compose usa o `env_file` da API. A chave permanece no backend; **não compartilhe dumps de configuração Docker**, pois podem incluir variáveis sensíveis.
- O projeto roda apenas em `localhost` no modo acadêmico; não exponha o ambiente demonstrativo na internet.
- Caso grave vídeo, feche editores, terminais ou abas que mostrem a chave e não exiba o arquivo `.env`.

## Voltar ao modo gratuito sem chamadas externas

Edite novamente as linhas no `.env`:

```dotenv
LLM_PROVIDER=mock
LLM_MODEL=fluxmed-mock-v1
```

Remova a linha `GEMINI_API_KEY` e execute `docker compose up -d --force-recreate api`. Isso mantém as operações e o banco de dados.

## Limite de comprovação

Os testes automáticos em CI usam o provider simulado por padrão. Eles não são uma prova de acesso ao Google. O registro de um ensaio externo deve identificar operação/run, provider/modelo, perguntas, respostas e valores de referência. O vídeo pode apresentar essa conferência com a mesma operação.
