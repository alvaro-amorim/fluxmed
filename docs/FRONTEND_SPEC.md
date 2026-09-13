# FluxMed — Frontend Specification

**Documento:** `docs/FRONTEND_SPEC.md`  
**Status:** Especificação oficial do frontend da V1  
**Projeto:** FluxMed — Planejamento Inteligente de Rotas Médicas  
**Responsável pela implementação:** Codex, seguindo os documentos oficiais do repositório  
**Stack principal:** React + Vite + TypeScript + MapLibre GL

---

# 1. Objetivo deste documento

Este documento define como o frontend do FluxMed deve funcionar e ser estruturado.

Ele cobre:

- navegação;
- hierarquia de telas;
- fluxos;
- UX;
- mapa;
- wizard de operação;
- visualização do GA;
- resultado final;
- replay;
- frota;
- equipe;
- entregas;
- relatórios;
- Assistente IA;
- estados de loading, erro e vazio;
- responsividade;
- acessibilidade;
- integração com API;
- regras visuais;
- limites de responsabilidade do frontend.

Este documento substitui qualquer abordagem anterior baseada em Lovable.

O frontend será criado do zero no próprio repositório pelo Codex.

---

# 2. Princípio central do frontend

O FluxMed deve parecer um:

> centro moderno de planejamento logístico médico.

Não deve parecer:

- dashboard genérico de SaaS;
- painel hospitalar clínico;
- aplicação de BI;
- laboratório de algoritmo;
- tela de telemetria em tempo real;
- site institucional.

A interface deve transmitir:

- controle;
- clareza;
- confiabilidade;
- precisão operacional;
- densidade de informação bem organizada.

---

# 3. Prioridade de plataforma

Prioridade principal:

```text
Desktop
```

Motivo:

- planejamento logístico;
- mapas;
- tabelas;
- comparação de rotas;
- visualização simultânea de métricas.

Também deve funcionar em:

- notebook;
- tablet;
- telas menores.

A V1 não precisa ser otimizada como app mobile-first.

---

# 4. Stack

Obrigatória:

```text
React
Vite
TypeScript
MapLibre GL
```

Testes:

```text
Vitest
React Testing Library
Playwright
```

O frontend deve consumir tipos gerados ou derivados do OpenAPI do FastAPI quando essa integração estiver disponível.

---

# 5. Estrutura sugerida

```text
apps/web/src/
├── app/
├── components/
├── features/
├── pages/
├── services/
├── hooks/
├── types/
├── lib/
├── assets/
└── test/
```

Organização por feature é preferível quando houver complexidade.

Exemplo:

```text
features/
├── operations/
├── deliveries/
├── fleet/
├── workforce/
├── optimization/
├── reports/
├── assistant/
└── city/
```

---

# 6. Regras de responsabilidade

Frontend pode:

- renderizar;
- formatar;
- filtrar;
- ordenar;
- controlar estado visual;
- validar formato simples de formulário;
- desenhar GeoJSON;
- reproduzir Decision Trace;
- mostrar gráficos;
- persistir preferências locais não críticas.

Frontend não pode decidir oficialmente:

- viabilidade de rota;
- custo operacional;
- fitness;
- atribuição de veículo;
- atribuição de equipe;
- capacidade;
- autonomia;
- janelas HARD;
- pruning;
- resultado do GA.

Essas decisões vêm do backend.

---

# 7. Navegação principal

Sidebar oficial:

```text
Operações
Entregas
Frota
Equipe
Relatórios
Assistente IA
Configurações        [ADMIN]
```

Não criar itens principais:

```text
Mapa
Analytics
Algoritmos
TSP
Pruning
Benchmarks
```

Esses elementos aparecem dentro de áreas contextuais.

---

# 8. Shell da aplicação

Layout principal:

```text
┌──────────────────────────────────────────────────────────┐
│ Header                                                   │
├───────────────┬──────────────────────────────────────────┤
│ Sidebar       │ Conteúdo                                 │
│               │                                          │
│               │                                          │
└───────────────┴──────────────────────────────────────────┘
```

Header pode conter:

- nome FluxMed;
- ambiente/demo;
- usuário;
- role;
- status de conexão;
- ações globais mínimas.

---

# 9. Login

Tela simples e profissional.

Conteúdo:

- logo/nome FluxMed;
- subtítulo;
- email;
- senha;
- botão Entrar;
- credenciais demo, quando habilitadas.

Não deve parecer landing page.

Não incluir:

- signup;
- social login;
- onboarding comercial.

---

# 10. Home após login

A rota inicial deve ser:

```text
Operações
```

Não criar dashboard separado apenas para KPIs gerais se ele não agregar valor real.

---

# 11. Tela Operações

Objetivo:

- visualizar operações;
- criar nova operação;
- reabrir existente;
- consultar histórico.

Elementos:

- título;
- botão `Nova operação`;
- filtros;
- busca;
- tabela ou lista rica;
- status badges.

Campos resumidos:

- código;
- data;
- cidade;
- status;
- entregas;
- veículos utilizados;
- custo, se disponível;
- horário;
- última atualização.

---

# 12. Status visual de operação

Sugestão:

```text
DRAFT       → neutro
READY       → azul
OPTIMIZING  → azul animado
OPTIMIZED   → verde
OUTDATED    → âmbar
APPROVED    → verde/teal
DISPATCHED  → grafite/teal sólido
```

Evitar usar vermelho para estados normais.

---

# 13. Nova operação

Fluxo em wizard único.

Etapas:

```text
1. Configuração
2. Entregas
3. Recursos
4. Revisão
```

A otimização acontece em seguida dentro da mesma operação.

---

# 14. Etapa Configuração

Campos:

```text
Data da operação
Cidade
Depósito
Horário de saída
Fim máximo da operação
Modo de trânsito
Fonte das entregas
```

Cidade inicialmente:

```text
Santa Aurora
```

Depósito pode vir preenchido automaticamente.

---

# 15. Modo de trânsito

Opções:

```text
Automático
Livre
Personalizado
```

Descrição curta em tooltip ou helper text.

---

# 16. Fonte das entregas

Opções:

```text
Gerar cenário
Importar arquivo
Selecionar cadastradas
Adicionar manualmente
```

A escolha direciona a experiência da etapa seguinte.

---

# 17. Etapa Entregas — cenário gerado

Campos:

```text
Perfil
Quantidade
Seed avançada [opcional/oculta]
```

Perfis:

```text
Normal
Movimentado
Alta Pressão
Emergência
Personalizado
```

Quantidade:

```text
20
40
60
80
Personalizada
```

Após gerar, mostrar resumo antes de prosseguir.

---

# 18. Resumo do cenário

Exibir:

- total de entregas;
- peso total;
- volume total;
- críticas;
- refrigeradas;
- HARD windows;
- TWO_PERSON;
- distribuição por tipo de destino;
- bairros mais demandados.

---

# 19. Etapa Entregas — importação

Aceitar:

```text
XLSX
CSV
```

Mostrar:

- área de upload;
- template para download;
- resultado da validação;
- tabela de revisão.

Status por linha:

```text
Válida
Warning
Erro
```

---

# 20. Validação de importação

Resumo:

```text
35 válidas
3 avisos
2 erros
```

Erros bloqueiam confirmação.

Warnings podem ser confirmados quando permitido.

---

# 21. Correção de endereço

Quando endereço não for exato:

mostrar:

- entrada original;
- problema;
- sugestões;
- ação de confirmação.

Exemplo:

```text
Rua das Acassias, 600

Rua sugerida:
Rua das Acácias

Número 600 não existe.
Números próximos:
593
611
```

---

# 22. Entrega manual

Formulário organizado em grupos:

```text
Documento
Destino
Carga
Prioridade e janela
Requisitos
Observações
```

Não exibir todos os campos em uma lista vertical sem hierarquia.

---

# 23. Etapa Recursos

Subseções:

```text
Frota
Equipe
```

Todos os recursos elegíveis e disponíveis podem vir selecionados.

O planejador pode desmarcar.

---

# 24. Card de veículo

Mostrar de forma compacta:

- placa;
- tipo;
- próprio/agregado;
- peso máximo;
- volume máximo;
- autonomia;
- refrigeração;
- helper policy;
- status.

---

# 25. Card de worker

Mostrar:

- nome;
- função;
- vínculo;
- modelo de pagamento;
- disponibilidade.

---

# 26. Alertas na seleção de recursos

Exemplos:

```text
Atenção: apenas 1 veículo refrigerado selecionado.

Erro: existem entregas refrigeradas,
mas nenhum veículo refrigerado está selecionado.
```

Erros críticos devem vir do backend.

---

# 27. Etapa Revisão

Tela de síntese antes do GA.

Mostrar KPIs:

```text
Entregas
Peso total
Volume total
Críticas
Refrigeradas
HARD windows
Veículos
Pessoas
Janela operacional
```

Também mostrar:

- warnings;
- bloqueios;
- resumo de restrições.

---

# 28. CTA principal

Se válido:

```text
Otimizar rotas
```

Se inválido:

botão desabilitado e explicação clara.

---

# 29. Página da operação

Depois de criada, a operação terá navegação interna contextual.

Subseções sugeridas:

```text
Visão geral
Planejamento
Resultado
```

Não criar muitas tabs.

---

# 30. Visão geral da operação

Mostrar:

- status;
- configuração;
- entregas;
- recursos;
- últimas ações;
- resumo de revisão;
- botão principal contextual.

---

# 31. Planejamento

Área central antes e durante otimização.

Deve conter:

- mapa;
- restrições;
- lista/resumo de entregas;
- recursos;
- ações de editar;
- botão otimizar.

---

# 32. Layout do mapa

Em desktop, mapa deve ter destaque real.

Exemplo:

```text
┌───────────────────────────────────────────────┐
│ KPIs / controles                             │
├──────────────────────────────┬────────────────┤
│                              │                │
│            MAPA              │ Inspector      │
│                              │                │
└──────────────────────────────┴────────────────┘
```

---

# 33. MapLibre

Camadas:

```text
water
districts
roads
facilities
depot
deliveries
closures
routes
```

Ordem deve evitar que ruas fiquem escondidas por polígonos.

---

# 34. Estilo do mapa

Visual:

- limpo;
- técnico;
- baixo ruído;
- vias principais destacadas;
- bairros discretos;
- rio claramente identificado;
- facilities com ícones simples.

Não usar visual de Google Maps.

---

# 35. Depósito

Marcador distinto.

Deve ser facilmente reconhecível.

Exemplo visual:

- ícone de warehouse/depot;
- cor primária;
- label opcional.

---

# 36. Facilities

Ícones distintos para:

- hospital;
- clínica;
- laboratório;
- farmácia;
- warehouse.

Não exagerar no tamanho dos ícones.

---

# 37. Deliveries

Marcadores podem variar por:

- prioridade;
- tipo de destino;
- sequência após otimização.

Antes da otimização, evitar poluição visual.

---

# 38. Interdição no mapa

Fluxo:

```text
Ativar modo "Adicionar restrição"
 ↓
clicar segmento
 ↓
abrir painel
 ↓
escolher fechamento/trânsito
 ↓
motivo
 ↓
confirmar
```

---

# 39. Road override inspector

Mostrar:

- rua;
- segmento;
- direção;
- tipo;
- motivo;
- impacto quando disponível.

---

# 40. Planejamento desatualizado

Se o usuário alterar algo após otimização:

mostrar banner forte:

```text
Este plano está desatualizado.
Reotimize antes de aprovar ou despachar.
```

---

# 41. Tela de otimização

Ao iniciar GA, não mostrar spinner genérico.

A tela deve mudar para modo de acompanhamento.

---

# 42. Estrutura da tela de otimização

Elementos principais:

- mapa;
- progresso;
- KPIs do algoritmo;
- convergência;
- pruning;
- fase;
- cancelamento.

---

# 43. Header da otimização

Exemplo:

```text
Otimizando rotas

Geração 37
Tempo 08,4 s
Melhor custo R$ 1.742
0 violações HARD
```

---

# 44. KPIs ao vivo

Mostrar quando disponíveis:

```text
Geração
Tempo
Melhor custo
Makespan
Distância
Diversidade
Mutação
Podados
```

Não exibir 20 métricas simultaneamente.

---

# 45. Fases da execução

Exemplo:

```text
Validando operação
Preparando matriz de viagens
Criando população inicial
Executando algoritmo genético
Alocando equipe
Validando solução
Finalizando resultado
```

---

# 46. Mapa durante GA

As rotas candidatas resumidas podem mudar no mapa.

Regras:

- animação suave;
- não redesenhar milhares de elementos;
- destacar best-so-far;
- linhas por veículo;
- alterações visuais baseadas em eventos reais.

---

# 47. Visualização de pruning

Não fingir que pruning é necessariamente espacial.

Pode mostrar:

- contador;
- categorias;
- badge temporário;
- linhas candidatas desaparecendo;
- painel lateral.

Exemplo:

```text
Podados: 1.842

Capacidade            812
Janela HARD           327
Dominância            529
Autonomia              83
```

---

# 48. Convergência

Gráfico simples:

```text
best cost vs generation
```

ou outra métrica principal.

Não precisa de gráfico científico complexo na tela normal.

---

# 49. Cancelar otimização

Botão visível:

```text
Cancelar otimização
```

Deve pedir confirmação curta se houver risco de perder execução.

---

# 50. Queda do SSE

Mostrar:

```text
Reconectando ao cálculo...
```

Não assumir que o GA parou.

Ao reconectar, recuperar estado atual.

---

# 51. Execução concluída

Transição para Resultado.

Mostrar feedback positivo sem animação exagerada.

---

# 52. Tela Resultado

Essa é uma das telas mais importantes.

Deve combinar:

- KPIs;
- mapa final;
- rotas;
- inspector;
- custos;
- equipe;
- explicações;
- ações.

---

# 53. KPIs finais

Topo:

```text
Entregas
Veículos usados
Custo total
Distância
Makespan
Atrasos críticos
Utilização média
```

---

# 54. Cores por veículo

Cada rota recebe cor distinta.

A mesma cor deve aparecer em:

- linha do mapa;
- legenda;
- card;
- badge;
- stop list.

---

# 55. Legenda

Exemplo:

```text
● ABC1D23  Cargo Van
● DEF4G56  Light Truck
● XYZ7H89  Moto
```

---

# 56. Inspector de veículo

Ao clicar em rota ou legenda:

mostrar:

- placa;
- tipo;
- propriedade;
- motorista;
- ajudante;
- entregas;
- peso;
- volume;
- utilização;
- km;
- duração;
- custo;
- sequência.

---

# 57. Foco de rota

Ao selecionar uma rota:

- destacar a selecionada;
- reduzir opacidade das demais;
- mostrar stops;
- manter legenda.

---

# 58. Stops

Lista ordenada:

```text
1. DLV-NF...
2. DLV-NF...
3. DLV-NF...
```

Cada item mostra:

- código;
- destinatário;
- endereço;
- prioridade;
- ETA;
- janela;
- service time.

---

# 59. Detalhes de custo

Breakdown:

```text
Combustível
Depreciação
Manutenção
Custo fixo
Equipe
Contrato agregado
Total
```

Mostrar apenas componentes relevantes ao veículo.

---

# 60. Utilização

Mostrar separadamente:

```text
Peso: 82%
Volume: 54%
```

Não criar “utilização média” única que esconda qual limite está próximo.

---

# 61. Helper decision

Exemplo:

```text
Ajudante recomendado
Motivo:
redução de 22 min em serviço
menor risco de atraso em 2 entregas
custo adicional: R$ 64
```

Explicação matemática/determinística antes da LLM.

---

# 62. Explain decision

Ações:

```text
Por que este veículo?
Por que esta entrega está aqui?
Por que ajudante?
```

Podem abrir painel com:

1. explicação estruturada;
2. opção de pedir explicação natural à IA.

---

# 63. Aprovação

Se plano atual válido:

```text
Aprovar plano
```

Depois:

```text
Despachar operação
```

Não pular diretamente para dispatch sem clareza.

---

# 64. Dispatch

Antes de despachar, modal de confirmação:

mostrar:

- revisão;
- entregas;
- veículos;
- custo;
- horário;
- aviso de imutabilidade.

CTA:

```text
Confirmar dispatch
```

---

# 65. Operação despachada

Estado visual:

- somente leitura;
- snapshot;
- sem edição relevante;
- acesso a relatórios e replay.

---

# 66. Replay

Botão:

```text
Ver replay do cálculo
```

Abrir:

- modal grande;
- drawer amplo;
- overlay.

Não criar rota/página separada.

---

# 67. Replay controls

Controles:

```text
Play
Pause
Velocidade
Timeline
Anterior
Próximo
```

Pode permitir:

```text
1x
2x
4x
```

---

# 68. Replay content

Usar:

- mapa;
- geração;
- best metrics;
- pruning;
- melhorias.

Não recalcular GA.

---

# 69. Tela Entregas

Lista global de deliveries.

Filtros:

- data/operação;
- prioridade;
- temperatura;
- status;
- destinatário;
- bairro.

Ações:

- adicionar;
- editar;
- visualizar;
- importar.

---

# 70. Tabela de entregas

Colunas úteis:

```text
Código
NF
Destinatário
Endereço
Prioridade
Peso
Volume
Janela
Temperatura
Status
```

Evitar colunas técnicas desnecessárias.

---

# 71. Tela Frota

Tabela/cards com:

```text
Placa
Tipo
Propriedade
Payload
Volume
Autonomia
Refrigeração
Status
```

Ações:

```text
Adicionar
Editar
Inativar
Ver custos
```

---

# 72. Formulário de veículo

Organizar em seções:

```text
Identificação
Capacidade
Operação
Custos
Contrato
```

Campos mudam conforme:

```text
OWNED
AGGREGATED
```

---

# 73. Tela Equipe

Mostrar:

```text
Nome
Função
Vínculo
Pagamento
Disponibilidade
Status
```

Ações:

```text
Adicionar
Editar
Inativar
```

---

# 74. Tela Relatórios

Objetivo:

- consultar relatórios;
- filtrar por operação;
- abrir;
- exportar.

Não construir dashboard de BI complexo.

---

# 75. Tipos de relatório

Exibir quando disponíveis:

```text
Resumo da operação
Dispatch
Instruções de equipe
Resumo executivo
```

---

# 76. Exports

Ações:

```text
Baixar PDF
Baixar XLSX
Baixar CSV
```

Mostrar estado de geração.

---

# 77. Falha de export

Exemplo:

```text
Não foi possível gerar o PDF.
A operação permanece salva.
[Tentar novamente]
```

---

# 78. Assistente IA

Tela dedicada.

Layout sugerido:

```text
┌────────────────────────────┬───────────────────────┐
│ Conversa                   │ Contexto              │
│                            │ Operação selecionada  │
│                            │ Rotas / métricas      │
└────────────────────────────┴───────────────────────┘
```

---

# 79. Contexto do Assistente

Usuário pode selecionar:

- operação;
- rota;
- veículo;
- delivery.

O assistente deve deixar claro qual contexto está usando.

---

# 80. Sugestões de perguntas

Exemplos:

```text
Por que a Van ABC1D23 foi escolhida?
Quais entregas têm maior risco de atraso?
Por que o caminhão não foi usado?
Como o custo está distribuído?
O que mudaria se eu removesse o ajudante?
```

---

# 81. Tool actions da IA

Quando a IA sugerir simulação:

exibir resultado estruturado.

Exemplo:

```text
Simular remoção do ajudante
```

Resultado:

```text
+18 min
+R$ 0 em equipe
2 entregas passam a ter risco alto
```

---

# 82. Alterações via IA

A IA não aplica mudanças diretamente.

Fluxo:

```text
IA sugere
 ↓
backend simula
 ↓
frontend mostra impacto
 ↓
usuário confirma
 ↓
backend aplica
```

---

# 83. Configurações

Somente ADMIN.

Seções:

```text
Operação
Custos
IA
Sistema
```

---

# 84. Configurações de custo

Exemplo:

```text
Preço da gasolina
Preço do diesel
```

Somente valores realmente usados.

---

# 85. Configurações de IA

Mostrar:

- provider ativo;
- modelo;
- status;
- sem exibir API key.

---

# 86. Saúde do sistema

Seção simples:

```text
API          Online
Banco        Online
PostGIS      Online
Cidade       Santa Aurora 1.0.0
Optimizer    FluxMed-GA 1.0.0
LLM          Online / Degraded
```

Não criar Grafana dentro do produto.

---

# 87. Design system

Direção visual:

```text
Primary: teal / azul-petróleo
Neutral: graphite / white / gray
Success: green
Warning: amber
Critical: red
```

Rotas usam paleta própria.

---

# 88. Cor vermelha

Reservada para:

- erro;
- bloqueio;
- entrega crítica;
- interdição;
- falha.

Não usar como cor decorativa genérica.

---

# 89. Tipografia

Preferência:

```text
Inter
```

ou fonte sans moderna de alta legibilidade.

Prioridade:

- tabelas;
- números;
- labels;
- mapa.

---

# 90. Densidade

A interface pode ser relativamente densa em desktop.

Mas deve manter:

- espaço;
- agrupamento;
- hierarquia;
- alinhamento.

Evitar cards gigantes para poucas informações.

---

# 91. Cards

Usar cards somente quando ajudarem agrupamento.

Não transformar toda informação em card.

Tabelas são preferíveis para listas operacionais.

---

# 92. Botões

Hierarquia:

```text
Primary
Secondary
Ghost
Danger
```

Apenas uma ação primária forte por contexto.

---

# 93. Icons

Usar ícones consistentes.

Evitar:

- emojis;
- mistura de bibliotecas;
- ícones excessivamente decorativos.

---

# 94. Animação

Permitida para:

- transição de rota;
- loading contextual;
- replay;
- SSE;
- feedback.

Evitar:

- bounce;
- efeitos chamativos;
- animação de marketing.

---

# 95. Loading states

Exemplos:

```text
Carregando operações...
Validando arquivo...
Calculando rota...
Gerando relatório...
```

Sempre contextual.

---

# 96. Skeletons

Usar em:

- listas;
- tabelas;
- cards;
- inspector.

Não usar skeleton no mapa se uma mensagem contextual for mais clara.

---

# 97. Empty states

Exemplo:

```text
Nenhuma operação ainda.
Crie sua primeira operação para começar.
```

CTA:

```text
Nova operação
```

---

# 98. Error states

Erro deve explicar:

- o que falhou;
- impacto;
- ação possível.

Exemplo:

```text
Assistente IA temporariamente indisponível.
A otimização e os dados da operação continuam funcionando.
```

---

# 99. Connectivity state

Se API indisponível:

mostrar banner.

Se dados atuais já carregados:

```text
Modo somente leitura temporário
```

quando aplicável.

---

# 100. Form validation

Frontend pode validar:

- obrigatório;
- formato;
- número positivo;
- data;
- tipo.

Backend continua sendo autoridade final.

---

# 101. Toasts

Usar para feedback curto:

```text
Operação criada.
Veículo atualizado.
Relatório pronto.
```

Não usar toast para erro crítico que exige ação.

---

# 102. Modals

Usar para:

- confirmação;
- ação destrutiva;
- dispatch;
- pequenos formulários contextualizados.

Não usar modal para fluxo inteiro de cadastro grande.

---

# 103. Drawers

Úteis para:

- route inspector;
- stop detail;
- explanation;
- road override;
- replay em tela ampla.

---

# 104. Acessibilidade

Obrigatório:

- contraste adequado;
- foco visível;
- labels;
- navegação por teclado nas principais telas;
- aria labels em ícones;
- não depender apenas de cor;
- tabelas semanticamente corretas.

---

# 105. Responsividade do sidebar

Desktop:

```text
expanded
```

Tela menor:

```text
collapsed / overlay
```

---

# 106. Responsividade do mapa

Em telas menores:

- mapa pode ocupar largura total;
- inspector vira drawer;
- KPIs quebram em linhas;
- tabelas usam scroll horizontal controlado.

---

# 107. Performance

Evitar:

- renderizar todos os endereços;
- recalcular GeoJSON em todo render;
- grandes objetos recreados sem necessidade;
- animações de alta frequência.

---

# 108. Map data strategy

Carregar:

```text
base map layers
```

e depois dados operacionais.

Entregas e rotas devem ser camadas separadas.

---

# 109. State management

Não adicionar Redux automaticamente.

Começar com:

- React state;
- hooks;
- context limitado;
- cache de API se necessário.

Adicionar biblioteca de server state somente se justificar.

---

# 110. API service layer

Frontend deve possuir camada como:

```text
services/
```

Não fazer `fetch()` espalhado por componentes.

---

# 111. OpenAPI client

Quando backend estiver disponível:

```text
FastAPI OpenAPI
 ↓
generated TypeScript client
```

Preferir geração automática para contratos.

---

# 112. Mocking durante desenvolvimento

Mocks são permitidos apenas temporariamente enquanto uma fatia backend ainda não existe.

Regra:

> mock deve ser substituível pelo service real sem reescrever a página.

Não criar lógica de negócio no mock.

---

# 113. Feature flags

Não criar sistema complexo.

Se necessário, usar flags simples por ambiente para:

- IA;
- replay;
- recursos ainda em desenvolvimento.

---

# 114. URLs sugeridas

```text
/login
/operations
/operations/new
/operations/:id
/deliveries
/fleet
/workforce
/reports
/assistant
/settings
```

Subestado da operação pode usar:

```text
/operations/:id?tab=planning
```

ou nested routes.

Manter simples.

---

# 115. Guard de autenticação

Rotas privadas exigem sessão.

Configurações exige ADMIN.

Frontend melhora UX, mas backend valida autorização.

---

# 116. Erros HTTP

Frontend deve mapear códigos de domínio.

Exemplo:

```text
NO_FEASIBLE_VEHICLE
```

para mensagem humana.

Não mostrar stack trace.

---

# 117. Formato de dinheiro

Brasil:

```text
R$ 1.742,30
```

Fonte de verdade numérica vem do backend.

---

# 118. Formato de data/hora

Exemplo:

```text
13/09/2026
07:30
```

API usa ISO.

Frontend localiza.

---

# 119. Formato de distância

Exemplo:

```text
42,8 km
```

Pequenas distâncias podem usar metros quando útil.

---

# 120. Peso e volume

Exemplo:

```text
286 kg
2,8 m³
```

---

# 121. Placeholders visuais

Durante skeleton/mock:

não utilizar lorem ipsum.

Usar conteúdo plausível de Santa Aurora.

---

# 122. Dados demo

Exemplos devem parecer coerentes com o domínio.

Evitar:

```text
John Doe
123 Main Street
Vehicle 1
```

Preferir:

```text
Hospital Universitário de Santa Aurora
Avenida da Integração, 420
ABC1D23
```

---

# 123. Visual regression

Telas críticas recomendadas:

- login;
- operações;
- wizard;
- optimization;
- result.

Pode ser adicionada quando frontend estabilizar.

---

# 124. E2E prioritários

Fluxos:

```text
login
→ nova operação
→ gerar cenário
→ selecionar recursos
→ otimizar
→ resultado
→ aprovar
```

Também:

```text
importar XLSX
→ corrigir endereço
→ confirmar
```

E:

```text
criar interdição
→ plano OUTDATED
→ reotimizar
```

---

# 125. Critérios de aceite — frontend base

Frontend base está pronto quando:

- autenticação visual funciona;
- navegação funciona;
- Operações funciona;
- wizard funciona;
- mapa renderiza;
- API layer existe;
- loading/erro/vazio existem;
- testes básicos passam.

---

# 126. Critérios de aceite — optimization UI

Está pronta quando:

- consome SSE;
- mostra geração real;
- atualiza KPIs;
- atualiza mapa;
- mostra pruning;
- permite cancelar;
- reconecta;
- termina em resultado.

---

# 127. Critérios de aceite — result UI

Está pronta quando:

- rotas são visíveis;
- cores são consistentes;
- vehicle inspector funciona;
- stops estão ordenados;
- custos aparecem;
- equipe aparece;
- métricas aparecem;
- approve/dispatch funcionam.

---

# 128. Critérios de aceite — Assistente IA

Está pronto quando:

- contexto está claro;
- perguntas funcionam;
- tools retornam dados estruturados;
- simulações mostram impacto;
- alteração exige confirmação;
- fallback/degraded state existe.

---

# 129. Ordem recomendada de implementação

O frontend deve crescer junto com backend.

Ordem:

```text
1. app shell + routing
2. login
3. operações
4. criação simples de operação
5. Santa Aurora map
6. entregas
7. frota
8. equipe
9. wizard completo
10. routing visualization
11. optimization UI
12. result UI
13. replay
14. reports
15. assistant
16. polish
```

---

# 130. O que não fazer

Não:

- criar dashboard genérico primeiro;
- implementar toda UI com mocks antes do backend;
- usar Google Maps;
- colocar regras de negócio no React;
- usar 30 cards em toda página;
- criar uma página “Algoritmo Genético” separada;
- usar spinner falso no lugar do GA real;
- depender de Supabase/Firebase;
- esconder o mapa em navegação secundária;
- criar visual excessivamente clínico/hospitalar.

---

# 131. Regra final

> O frontend do FluxMed deve tornar uma operação combinatoriamente complexa fácil de entender, sem esconder as decisões importantes e sem fingir inteligência que não exista no backend.

A interface deve ser o ponto de encontro entre:

- cidade;
- operação;
- algoritmo;
- custos;
- equipe;
- explicabilidade;
- decisão humana.
