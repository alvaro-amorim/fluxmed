# Gravação manual do vídeo acadêmico

Este guia prepara uma **captura de tela sem narração**. Depois, grave câmera e voz por cima da edição. O vídeo final deve ter até 15 minutos e mostrar o sistema em execução, o algoritmo genético, os resultados e uma resposta de **Gemini real**. Use os valores da operação que estiver visível; os números do relatório técnico pertencem a um run específico.

## Antes de abrir o OBS

1. Inicie o Docker Desktop. Na raiz do repositório, execute `docker compose up --build -d` e depois `docker compose ps -a`. Espere `db` e `api` saudáveis, `web` ativo e `init` com `Exited (0)`. Abra `http://localhost:5173/health/ready` para conferir a API pelo proxy.
2. Abra `http://localhost:5173` em uma janela de navegador dedicada à gravação. Faça login pela opção **Usar acesso demo**. Não mostre `.env`, saída de `docker compose config`, tokens, chave do Gemini ou outras janelas pessoais.
3. Confirme na tela do Assistente IA que o provider é `gemini` e faça **uma pergunta de ensaio** sobre uma operação otimizada. O indicador `HEALTHY` sozinho não comprova chamada externa; precisa haver resposta concluída identificada como `gemini`. Se houver falha de cota/rede, resolva antes da gravação. O modo `mock` não satisfaz essa parte do desafio.
4. Confirme que há uma operação com resultado válido ou crie uma operação pequena para o vídeo: **Operações → Nova operação → Salvar e continuar → Gerar cenário (Normal, 20 entregas) → Continuar para recursos → Ir para revisão**. Ajuste frota/equipe até o preflight mostrar **Operação pronta para otimização**. Na página da operação, abra **Resultado → Otimizar rotas** e aguarde a conclusão.
5. Confira os dados dessa mesma operação nas telas **Resultado**, **Assistente IA** e **Relatórios**. Se for usar um run anterior, mostre **Reproduzir otimização** e diga na narração que é um replay de uma execução persistida. Não apresente replay como cálculo novo em tempo real.
6. Deixe abertas as abas do [benchmark final](../benchmarks/README.md), da [relação com a base da FIAP](FIAP_TSP_BASE.md), do código relevante e do relatório técnico PDF. O seed acadêmico do benchmark é para um banco demo limpo; **não o execute no banco da gravação**.
7. No OBS, grave 10 segundos de teste e reproduza o arquivo. Verifique enquadramento, legibilidade, movimento do cursor e ausência de avisos sobrepostos. Desative notificações. Capture só a janela necessária e use resolução/zoom que mantenha texto e mapa legíveis.

## Ordem de captura sugerida (até 14 min de material final)

| Tempo editado | Tela e ação | Evidência que precisa aparecer |
|---|---|---|
| 0:00–0:40 | Capa do relatório técnico e login FluxMed; entrar com acesso demo. | Projeto, Fase 2, Projeto 2 e aplicação aberta. |
| 0:40–2:05 | **Operações**: abrir a operação; mostrar demanda em **Entregas**, prioridade/refrigeração; **Frota** e **Equipe**; revisão/preflight. | Dados de entrada e restrições reais antes da otimização. |
| 2:05–3:25 | Código: `optimization/operators.py`, `engine.py`, `decoder.py` e `fitness.py`; voltar à aba **Resultado** e mostrar cálculo ao vivo ou replay identificado. | Permutação, torneio, OX, mutações, decodificação, fitness e evolução por geração. |
| 3:25–5:05 | **Resultado**: KPIs, mapa, selecionar duas rotas na legenda e abrir a sequência de paradas. | Viabilidade, múltiplos veículos, distância, custo, prazo e visualização. |
| 5:05–6:45 | [Benchmark](../benchmarks/README.md): tabela geral e gráfico de viabilidade/tempo; mostrar um cenário comparável. | 16 cenários, 272 execuções, denominadores diferentes e custo computacional do repair. |
| 6:45–9:45 | **Assistente IA**: selecionar a mesma operação; mostrar provider `gemini`; perguntar fatos, pedir instruções da primeira rota e, se houver tempo, resumo diário. Aguardar respostas completas e fontes. | LLM pré-treinada em execução, grounding e conteúdo coerente com o plano. |
| 9:45–10:45 | **Relatórios**: gerar ou abrir PDF, XLSX e CSV da mesma operação; mostrar histórico e prévia. | Artefatos operacionais diários, separados do relatório técnico acadêmico. |
| 10:45–11:40 | **Resultado**: aprovar plano e, se fizer parte do caso gravado, despachar; voltar à visão geral. | Estados `OPTIMIZED → APPROVED → DISPATCHED` e revisão congelada. Faça isso só depois das demais telas da operação. |
| 11:40–13:10 | [Base FIAP](FIAP_TSP_BASE.md), diagrama no [README](../README.md) e estrutura do repositório. | Correspondência conceitual com TSP, extensão para VRP e transparência sobre implementação independente. |
| 13:10–14:00 | Conclusão e limitações no relatório técnico. | Cidade sintética, planejamento pré-despacho, sem ótimo global nem validação hospitalar real. |

Deixe cada tela importante estável por alguns segundos para facilitar a narração posterior. Grave trechos curtos separados quando isso evitar espera longa; na edição, preserve a relação entre início e resultado da **mesma** otimização. Não misture números de runs diferentes. Não é necessário mostrar páginas administrativas ou percorrer todas as tabelas do benchmark.

## Perguntas prontas para o Assistente IA

1. `Quantas entregas e veículos há nesta operação, qual é a distância total e qual é o custo calculado?`
2. `Gere instruções para o motorista da primeira rota, respeitando a ordem das paradas e as janelas de atendimento.`
3. `Gere um resumo diário da operação e sugira uma melhoria baseada apenas nos resultados disponíveis. Separe fatos de recomendações.`

Depois da primeira resposta, confira seus números na aba **Resultado**. Espere a resposta acabar antes de mudar de página. Se o provider real falhar, repita a gravação desse trecho quando a chamada funcionar; não substitua por uma resposta `mock`.

## Conferência antes do envio

- Vídeo editado com menos de 15 minutos, voz e tela legíveis, sem segredos ou notificações.
- GA, restrições, mapa, benchmark, relatórios e **resposta Gemini real** visíveis.
- Valores narrados iguais aos do run mostrado; se forem diferentes do caso do relatório técnico, explique que é outra operação.
- Vídeo publicado no YouTube/Vimeo como público ou não listado e link testado sem login.
- Relatório técnico final atualizado com link do vídeo e repositório acessível ao avaliador.
