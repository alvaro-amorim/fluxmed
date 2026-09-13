# FluxMed — Product Specification

**Documento:** `docs/PRODUCT_SPEC.md`  
**Status:** Fonte de verdade de produto para a V1  
**Projeto:** FluxMed — Planejamento Inteligente de Rotas Médicas  
**Contexto:** Tech Challenge — Fase 2 — Projeto 2

---

# 1. Objetivo deste documento

Este documento define **o que o FluxMed deve ser como produto**, quais problemas resolve, quais usuários existem, quais fluxos fazem parte da V1, quais regras funcionais são obrigatórias e quais capacidades ficam explicitamente fora do escopo inicial.

Ele deve orientar:

- desenvolvimento frontend;
- desenvolvimento backend;
- criação da API;
- modelagem de domínio;
- testes;
- decisões de UX;
- implementação pelo Codex;
- validação acadêmica;
- demonstração final.

Este documento descreve **comportamentos de produto**.  
Detalhes arquiteturais e algorítmicos serão definidos em documentos separados.

---

# 2. Visão do produto

O **FluxMed** é um sistema de planejamento diário de distribuição de medicamentos e insumos médicos.

Ele recebe:

- uma cidade;
- um conjunto de entregas;
- frota disponível;
- equipe disponível;
- restrições operacionais;
- horário da operação;
- condições de trânsito;
- restrições viárias.

A partir disso, o sistema utiliza um **Algoritmo Genético** para construir um plano de rotas que:

- atenda as entregas;
- respeite restrições rígidas;
- reduza custos;
- evite atrasos;
- proteja entregas críticas;
- utilize adequadamente a frota;
- produza um plano explicável;
- permita análise visual.

O FluxMed não é um sistema de rastreamento em tempo real.

A V1 é um **planejador de operação antes da saída dos veículos**.

---

# 3. Problema que o produto resolve

Uma operação médica pode envolver, no mesmo dia:

- medicamentos críticos;
- insumos hospitalares;
- cargas refrigeradas;
- entregas domiciliares;
- hospitais;
- clínicas;
- laboratórios;
- farmácias;
- veículos com capacidades diferentes;
- motoristas;
- ajudantes;
- custos distintos;
- janelas de entrega;
- congestionamento;
- ruas interditadas.

Planejar isso manualmente tende a produzir:

- uso ineficiente de veículos;
- rotas mais longas;
- risco de atraso;
- excesso de capacidade desperdiçada;
- custos maiores;
- escolhas difíceis de explicar.

O FluxMed transforma essa decisão em um problema de otimização formal e apresenta ao planejador um plano operacional compreensível.

---

# 4. Princípios de produto

## 4.1 Planejamento antes de execução

A V1 termina quando o plano é aprovado e marcado como despachado.

Depois disso, o sistema não acompanha fisicamente os veículos.

---

## 4.2 Correção antes de aparência

O sistema nunca deve apresentar uma solução inválida como boa apenas porque ela parece visualmente correta no mapa.

---

## 4.3 Explicabilidade

O usuário deve conseguir compreender:

- por que um veículo foi utilizado;
- por que outro ficou parado;
- por que uma entrega foi movida;
- por que um ajudante foi recomendado;
- por que uma rota é mais cara;
- por que uma alternativa foi descartada.

---

## 4.4 Controle humano

A otimização recomenda.

O usuário analisa, altera quando permitido e confirma.

Nenhuma LLM poderá alterar silenciosamente uma operação.

---

## 4.5 Profissional sem overengineering

O FluxMed deve parecer uma ferramenta profissional, mas a V1 continua sendo um projeto acadêmico e de portfólio.

Funcionalidades que só fariam sentido em escala empresarial ficam para evolução futura.

---

# 5. Usuários da V1

Existem dois papéis reais na V1.

## 5.1 ADMIN

Pode:

- acessar todas as áreas;
- administrar usuários;
- administrar frota;
- administrar equipe;
- editar parâmetros operacionais expostos;
- visualizar configurações do sistema;
- consultar saúde básica do sistema;
- operar normalmente como planejador.

---

## 5.2 PLANNER

Pode:

- criar operações;
- configurar operações;
- selecionar entregas;
- importar entregas;
- gerar cenários;
- selecionar frota;
- selecionar equipe;
- criar restrições viárias;
- executar otimização;
- analisar resultados;
- alterar equipe;
- aprovar plano;
- despachar;
- gerar relatórios;
- usar Assistente IA.

---

# 6. Papéis futuros, fora da V1

A arquitetura poderá futuramente receber:

- `CONTROLLER`;
- `DRIVER`.

Esses papéis não precisam ser implementados agora.

---

# 7. Autenticação

A V1 deve possuir autenticação real simples.

Regras:

- não haverá cadastro público;
- usuários serão pré-criados ou administrados internamente;
- senhas serão armazenadas com hash seguro;
- login deve criar uma sessão/token válido;
- permissões devem ser respeitadas no backend;
- um usuário demo poderá ser disponibilizado para avaliação acadêmica.

A tela de login poderá mostrar credenciais demonstrativas claramente identificadas como demo.

---

# 8. Navegação principal

A navegação lateral da aplicação será:

```text
Operações
Entregas
Frota
Equipe
Relatórios
Assistente IA
Configurações        [ADMIN]
```

Não devem existir páginas principais separadas chamadas:

- Algoritmos;
- Pruning;
- Analytics;
- Mapa;
- TSP.

Esses conceitos aparecem dentro do contexto operacional.

---

# 9. Operação

Uma **Operação** representa um dia ou janela planejada de distribuição.

Exemplo:

```text
Operação 13/09/2026
Santa Aurora
Saída: 07:30
Fim máximo: 18:00
```

Cada operação contém:

- data;
- cidade;
- depósito;
- horário de saída;
- horário máximo de retorno;
- modo de trânsito;
- entregas;
- frota selecionada;
- equipe disponível;
- restrições viárias;
- revisões;
- execuções de otimização;
- plano aprovado;
- snapshot despachado.

---

# 10. Estados da operação

Sugestão funcional:

```text
DRAFT
READY
OPTIMIZING
OPTIMIZED
OUTDATED
APPROVED
DISPATCHED
```

Significado:

### DRAFT
Operação em preparação.

### READY
Dados mínimos válidos para otimização.

### OPTIMIZING
Existe uma execução de otimização em andamento.

### OPTIMIZED
Existe uma revisão atual com solução válida.

### OUTDATED
Alguma informação relevante mudou após a última otimização.

### APPROVED
O usuário aprovou o plano atual.

### DISPATCHED
O plano foi congelado como snapshot operacional.

---

# 11. Versionamento de operação

Uma operação pode ser otimizada mais de uma vez.

Mudanças relevantes após uma otimização devem invalidar o resultado atual.

Exemplos:

- adicionar entrega;
- remover entrega;
- alterar peso;
- alterar prioridade;
- alterar janela;
- alterar veículo disponível;
- alterar equipe;
- criar interdição;
- remover interdição;
- alterar horário de saída;
- alterar tráfego.

Resultado:

```text
OPTIMIZED
   ↓
mudança relevante
   ↓
OUTDATED
```

O usuário não pode despachar um plano `OUTDATED`.

É necessário reotimizar.

---

# 12. Revisões

Somente revisões operacionalmente relevantes precisam ser persistidas.

Não é necessário criar uma revisão a cada clique.

Uma nova revisão deve ser consolidada principalmente quando:

- uma otimização é executada;
- um plano é aprovado;
- um dispatch é realizado.

O histórico deve permitir comparar execuções e preservar decisões importantes.

---

# 13. Dispatch

Na V1, `DISPATCHED` é um **estado lógico**.

Ele significa:

> o plano foi confirmado como plano oficial daquela operação.

Não significa que os veículos começaram a se mover em tempo real.

Ao despachar:

- a revisão fica imutável;
- é criado um snapshot permanente;
- os dados históricos não devem mudar por alterações futuras de preços, pessoas ou veículos.

---

# 14. Snapshot de dispatch

O snapshot deve preservar pelo menos:

- entregas;
- ordem das paradas;
- rotas;
- veículos;
- equipe;
- custos;
- premissas de combustível;
- restrições;
- tráfego;
- horário de saída;
- horário máximo;
- resultado do GA;
- métricas;
- Decision Trace resumido;
- versão do algoritmo;
- versão da configuração;
- seed quando aplicável.

---

# 15. Wizard de nova operação

A criação deve ocorrer em um wizard único.

## Etapa 1 — Configuração

Campos:

- data;
- cidade;
- depósito;
- horário de saída;
- horário máximo de retorno;
- modo de trânsito;
- fonte das entregas.

---

## Etapa 2 — Entregas

Fontes:

- gerar cenário;
- importar arquivo;
- selecionar entregas cadastradas;
- adicionar manualmente.

---

## Etapa 3 — Recursos

Selecionar:

- veículos;
- motoristas;
- motoboys;
- ajudantes.

Todos os recursos ativos e disponíveis podem vir selecionados por padrão.

O planejador pode remover recursos daquela operação.

---

## Etapa 4 — Revisão

Antes da otimização, mostrar:

- total de entregas;
- peso total;
- volume total;
- prioridades;
- refrigeradas;
- janelas HARD;
- frota disponível;
- equipe;
- incompatibilidades;
- avisos;
- erros bloqueantes.

A ação final é:

```text
Otimizar rotas
```

---

# 16. Depósito

A V1 possui **um único centro de distribuição**.

Regras:

- todas as mercadorias começam no depósito;
- todos os veículos começam no depósito;
- todos saem no mesmo horário;
- todas as rotas devem retornar ao depósito;
- não existem múltiplos depósitos na V1.

---

# 17. Horário da operação

Cada operação tem:

```text
operation_start_time
operation_end_time
```

Exemplo:

```text
07:30 → 18:00
```

Todas as rotas devem retornar ao depósito até `operation_end_time`.

Ultrapassar esse limite torna a rota inviável.

---

# 18. Pausas e jornada trabalhista

Fora da V1:

- pausa de almoço;
- descanso obrigatório;
- hora extra;
- limite individual de jornada;
- legislação trabalhista detalhada.

A arquitetura poderá suportar isso futuramente.

---

# 19. Entregas

Uma entrega representa uma **parada logística**, não um item individual de estoque.

Ela pode conter múltiplos volumes.

Campos principais:

```text
id
delivery_code
operation_id
invoice_number
invoice_series
issuer_document
issuer_name
external_reference
destination_address_id
recipient_name
package_count
total_weight_kg
total_volume_m3
priority
time_window_start
time_window_end
time_window_policy
service_time_minutes
temperature_class
handling_requirement
status
notes
created_at
updated_at
```

---

# 20. Identificação da entrega

Cada entrega possui:

## UUID técnico

Usado internamente.

## Código operacional

Exemplo:

```text
DLV-NF45872-001
```

Esse código é adequado para:

- interface;
- mapa;
- relatórios;
- pesquisa;
- explicações.

---

# 21. NF e duplicidade

Número de NF sozinho não é chave única.

A identificação deve considerar:

- emissor;
- série;
- número.

Uma mesma NF pode gerar múltiplas entregas quando houver divisão logística legítima.

Exemplo:

```text
DLV-NF45872-001
DLV-NF45872-002
```

O sistema pode alertar sobre duplicidade, mas deve permitir uma divisão confirmada.

---

# 22. Prioridade

Valores:

```text
CRITICAL
HIGH
NORMAL
LOW
```

Prioridade influencia qualidade de serviço e risco.

Entregas críticas devem receber tratamento superior na avaliação do plano.

---

# 23. Janelas de entrega

Cada entrega pode possuir:

```text
time_window_start
time_window_end
```

Políticas:

```text
HARD
SOFT
```

### HARD

Violação torna o plano inválido.

### SOFT

Pode haver atraso, mas ele é penalizado.

---

# 24. Tempo de serviço

Cada parada possui um tempo de serviço.

Esse tempo entra no cálculo do ETA das entregas seguintes.

O sistema terá um `ServiceTimeEstimator`.

Ele poderá considerar:

- tipo do destino;
- quantidade de volumes;
- peso;
- volume;
- perfil da carga;
- presença de ajudante.

Origem do tempo:

```text
ESTIMATED
MANUAL
IMPORTED
```

O usuário poderá substituir a estimativa antes da otimização.

---

# 25. Temperatura

Classes da V1:

```text
AMBIENT
REFRIGERATED
```

Uma entrega refrigerada só pode ser atribuída a veículo compatível.

---

# 26. Manuseio

Valores:

```text
STANDARD
TWO_PERSON
```

`TWO_PERSON` exige composição de equipe compatível.

---

# 27. Status futuro da entrega

Modelo preparado para:

```text
PENDING
PLANNED
LOADED
DISPATCHED
IN_TRANSIT
DELIVERED
FAILED
```

Na V1, o fluxo real termina essencialmente em `DISPATCHED`.

Estados de execução futura podem permanecer sem uso.

---

# 28. Cadastro manual de entrega

O usuário deve conseguir informar:

- NF;
- série;
- emissor;
- destinatário;
- endereço;
- volumes;
- peso;
- volume;
- prioridade;
- janela;
- temperatura;
- necessidade de duas pessoas;
- tempo de serviço;
- observações.

O endereço deve ser validado contra o dataset da cidade.

---

# 29. Importação de entregas

Formatos:

- XLSX principal;
- CSV secundário.

O sistema deve disponibilizar template.

Campos obrigatórios recomendados:

```text
numero_nf
serie_nf
emissor_documento
destinatario
rua
numero
peso_kg
volume_m3
quantidade_volumes
```

Campos opcionais:

```text
emissor_nome
complemento
prioridade
janela_inicio
janela_fim
janela_tipo
tempo_servico_min
temperatura
duas_pessoas
referencia_externa
observacoes
```

O usuário nunca informa UUID interno.

---

# 30. Fluxo de importação

```text
Arquivo
   ↓
Parse
   ↓
Validação
   ↓
Resolução de endereço
   ↓
Tela de revisão
   ↓
Confirmação
   ↓
Persistência
```

A importação não deve persistir silenciosamente apenas as linhas boas.

Exemplo:

```text
40 linhas
35 válidas
3 warnings
2 erros
```

Nada é confirmado até o usuário resolver ou remover os erros bloqueantes.

---

# 31. Resolução de endereço

O FluxMed deve usar somente endereços realmente existentes no dataset da cidade.

Não usar ranges genéricos como:

```text
Rua X, números 1–1000
```

Se um número não existir:

```text
Rua das Acácias, 600
```

o sistema não deve aproximar silenciosamente.

Pode sugerir:

```text
Número não encontrado.
Mais próximos: 587, 593, 611.
```

Fuzzy matching pode ser utilizado para nome de rua:

```text
Acassias
→ Rua das Acácias
```

mas requer confirmação quando houver ambiguidade.

---

# 32. Geração de cenários

O usuário pode gerar entregas automaticamente.

Escolhas independentes:

## Perfil

```text
NORMAL
BUSY
HIGH_PRESSURE
EMERGENCY
CUSTOM
```

## Quantidade

```text
20
40
60
80
custom
```

---

# 33. Perfil NORMAL

Características:

- demanda equilibrada;
- janelas mais amplas;
- poucas entregas HARD;
- boa disponibilidade de recursos;
- baixa quantidade de incompatibilidades.

Ideal para demonstração inicial.

---

# 34. Perfil BUSY

Características:

- mais ocupação da frota;
- maior quantidade de volumes;
- janelas moderadamente menores;
- maior concentração operacional.

---

# 35. Perfil HIGH_PRESSURE

Características:

- maior competição por recursos;
- menor folga;
- mais entregas prioritárias;
- janelas significativamente mais restritas;
- maior pressão por capacidade.

---

# 36. Perfil EMERGENCY

Características:

- mais entregas críticas;
- maior presença de refrigeração;
- mais HARD windows;
- maior risco operacional;
- maior necessidade de recursos especializados.

Dificuldade não deve ser criada apenas aumentando peso.

---

# 37. Distribuição espacial sintética

A demanda não deve ser uniforme pela cidade.

Deve considerar:

- bairro;
- concentração médica;
- tipo de estabelecimento;
- home care;
- clusters de demanda.

Destinos típicos:

```text
HOSPITAL
CLINIC
LABORATORY
PHARMACY
HOME_CARE
OTHER
```

Pesos de demanda variam por tipo e bairro.

---

# 38. Arquétipos de carga

O gerador deve escolher um perfil de carga antes de gerar números.

Exemplos:

```text
MEDICATION_SMALL
REFRIGERATED_MEDICATION
LAB_MATERIAL
HOSPITAL_SUPPLIES
BULK_CONSUMABLES
MEDICAL_EQUIPMENT
```

A partir disso gera valores coerentes de:

- quantidade de volumes;
- peso;
- volume;
- temperatura;
- necessidade de ajudante;
- tempo de serviço.

---

# 39. Coerência de peso e volume

Peso e volume não serão sorteados independentemente.

O sistema deve permitir situações como:

```text
carga pesada e compacta
```

ou:

```text
carga leve e volumosa
```

mas dentro de faixas plausíveis.

Isso permite que kg e m³ realmente influenciem escolhas de veículo.

---

# 40. Janelas sintéticas

O gerador poderá construir internamente uma solução viável de referência.

A partir dos ETAs dessa solução, cria janelas plausíveis.

Essa solução:

- não é fornecida ao GA;
- não aparece para o usuário;
- serve apenas para evitar cenários impossíveis por geração aleatória.

O perfil de dificuldade controla:

- largura;
- folga;
- percentual HARD;
- prioridade.

---

# 41. Frota

Veículos são entidades persistentes.

Podem ser:

```text
OWNED
AGGREGATED
```

Tipos iniciais:

```text
MOTO
VAN_COMPACT
CARGO_VAN
LIGHT_TRUCK
```

O usuário poderá:

- cadastrar;
- editar;
- inativar;
- visualizar histórico.

Evitar exclusão física quando houver histórico associado.

---

# 42. Campos principais do veículo

```text
id
plate
type
ownership_type
max_payload_kg
max_volume_m3
max_range_km
refrigerated
allowed_road_classes
status
helper_policy
fuel_type
fuel_efficiency_km_per_l
```

Campos de custo variam por propriedade.

---

# 43. Veículo próprio

Custos podem considerar:

```text
acquisition_value
residual_value
useful_life_km
depreciation_per_km
maintenance_per_km
annual_ipva
annual_insurance
annual_fixed_costs
productive_hours_per_year
fixed_cost_per_hour
fuel_efficiency
```

Custo aproximado de rota:

```text
distância * depreciação/km
+
distância * manutenção/km
+
tempo * custo fixo/h
+
combustível
```

---

# 44. Veículo agregado

Suporta inicialmente contrato:

```text
PER_ROUTE
```

Arquitetura pode permitir depois:

```text
PER_DAY
PER_KM
```

Flags:

```text
fuel_included
driver_included
helper_included
```

O sistema nunca deve cobrar novamente um custo já incluído no contrato.

---

# 45. Combustível

Preço do combustível é configuração operacional global, e não atributo isolado de cada veículo.

Fórmula:

```text
route_fuel_cost =
route_distance_km
/
fuel_efficiency_km_per_l
*
fuel_price
```

---

# 46. Autonomia

Autonomia é restrição separada do consumo financeiro.

Cada veículo possui:

```text
max_range_km
```

Pode existir fator de segurança configurável.

Todos os veículos selecionados começam a operação considerados operacionalmente aptos.

Não haverá:

- abastecimento;
- posto;
- nível atual de tanque;
- recarga elétrica.

---

# 47. Equipe

Entidades:

```text
Worker
```

Papéis:

```text
DRIVER
HELPER
MOTORCYCLE_COURIER
```

Vínculo:

```text
EMPLOYEE
DAY_WORKER
AGGREGATED
```

Pagamento:

```text
HOURLY
DAILY
PER_ROUTE
INCLUDED_IN_VEHICLE_CONTRACT
```

---

# 48. Disponibilidade da equipe

`active` e `available` são conceitos diferentes.

Uma pessoa pode estar cadastrada e ativa, mas indisponível para uma operação específica.

Todos os disponíveis podem vir selecionados por padrão.

---

# 49. Ajudantes

Resultado possível para uma rota:

```text
REQUIRED
OPTIONAL
NOT_NEEDED
```

Política do veículo:

```text
FORBIDDEN
OPTIONAL
REQUIRED
```

Exemplo:

- moto → `FORBIDDEN`;
- van → `OPTIONAL`;
- caminhão → normalmente `OPTIONAL`, configurável.

---

# 50. Quando ajudante é obrigatório

Obrigatório quando:

- a entrega exige `TWO_PERSON`;
- o veículo exige;
- outra regra operacional HARD exigir.

---

# 51. Quando ajudante é opcional

O sistema compara:

```text
rota sem ajudante
vs
rota com ajudante
```

Considerando:

- custo adicional;
- redução no tempo de serviço;
- risco de atraso;
- disponibilidade;
- impacto em outras rotas.

---

# 52. Alteração manual de equipe

Depois da recomendação automática, o planejador pode trocar equipe.

Antes de confirmar, o sistema recalcula:

- validade;
- custo;
- impacto de tempo.

Exemplo:

```text
Equipe recomendada:
Carlos + Paulo
R$ 230

Nova equipe:
Marcelo + Bruno
R$ 258

Impacto:
+ R$ 28
```

---

# 53. Cidade

A primeira cidade será:

```text
Santa Aurora
```

Brasil.

Santa Aurora é sintética, mas deve parecer plausível.

O sistema não deve conter lógica específica como:

```text
if city == "Santa Aurora":
```

O restante da aplicação usa um modelo de cidade normalizado.

---

# 54. Bairros iniciais

Conjunto conceitual:

1. Centro Histórico
2. Vila Aurora
3. Jardim das Flores
4. Parque Universitário
5. Santa Cecília
6. Vale Verde
7. Nova Esperança
8. Distrito Industrial
9. Distrito Logístico

O centro de distribuição fica no Distrito Logístico.

---

# 55. Facilities

Devem existir:

- hospitais;
- clínicas;
- laboratórios;
- farmácias;
- armazéns;
- edifícios públicos;
- residências;
- apartamentos;
- home care.

Os endereços precisam corresponder a edifícios/entradas realmente gerados.

---

# 56. Mapa

Tecnologia:

```text
MapLibre GL
```

Não usar Google Maps como dependência central.

Mapa final deve mostrar:

- depósito;
- vias;
- bairros;
- entregas;
- facilities;
- interdições;
- rotas;
- legenda;
- cores por veículo.

---

# 57. Rotas finais

Cada veículo utilizado recebe uma cor estável no contexto daquela operação.

Exemplo:

```text
Van ABC1D23       azul
Moto XYZ2E34      laranja
Caminhão DEF5G67  verde
```

A legenda precisa preservar o pareamento.

---

# 58. Marcadores

Paradas devem ter:

- sequência;
- identificação;
- prioridade quando relevante;
- tipo do destino;
- estado visual.

Exemplo:

```text
1
2
3
4
```

com destaque para entregas críticas.

---

# 59. Inspector de rota

Ao selecionar um veículo, o usuário vê:

- placa;
- tipo;
- equipe;
- entregas;
- peso;
- volume;
- distância;
- tempo;
- custo;
- utilização;
- sequência de paradas.

As demais rotas podem ser visualmente reduzidas para facilitar análise.

---

# 60. Interdições

O usuário pode criar restrições viárias específicas da operação.

Interação principal:

- clicar no mapa;
- selecionar segmento;
- bloquear sentido ou segmento.

Alternativa:

- formulário/lista.

Motivos:

```text
ACCIDENT
ROADWORK
EVENT
OTHER
```

A interdição não altera permanentemente a cidade-base.

---

# 61. Trânsito

Modos:

```text
AUTOMATIC
FREE
CUSTOM
```

### AUTOMATIC

Usa perfis sintéticos por:

- horário;
- região;
- classe de via.

### FREE

Usa velocidade-base sem congestionamento.

### CUSTOM

Permite ajustes manuais de tráfego.

---

# 62. Trânsito customizado

Categorias:

```text
FREE
LIGHT
MODERATE
HEAVY
VERY_HEAVY
```

Cada categoria será mapeada para um fator numérico interno.

Valores exatos devem ser calibrados.

---

# 63. Resultado da otimização

A tela de resultado deve priorizar métricas operacionais reais.

KPIs:

- entregas;
- veículos utilizados;
- distância;
- tempo;
- makespan;
- custo;
- atrasos críticos;
- entregas dentro da janela;
- utilização média;
- número de podas.

---

# 64. Otimização em andamento

Durante o cálculo, exibir:

- fase;
- geração;
- tempo;
- melhor custo;
- melhor makespan;
- diversidade;
- mutação;
- podas;
- evolução;
- mapa;
- convergência.

Os dados devem vir da execução real do algoritmo.

---

# 65. Cancelamento

Enquanto a otimização estiver rodando:

```text
Cancelar otimização
```

deve estar disponível.

Se já existir melhor solução válida, o produto pode informar que existe uma solução parcial válida encontrada, mas ela deve ser claramente marcada como proveniente de execução interrompida.

---

# 66. Replay

Após conclusão:

```text
Ver replay do cálculo
```

Abre modal, drawer ou overlay.

Não criar página separada apenas para replay.

---

# 67. Assistente IA

Área dedicada:

```text
Assistente IA
```

O usuário pode perguntar:

- por que uma entrega está naquela rota;
- por que determinado veículo foi escolhido;
- por que um caminhão não foi usado;
- por que o ajudante foi recomendado;
- qual rota é mais cara;
- quais entregas têm maior risco;
- como reduzir custo;
- quais mudanças podem melhorar o plano.

---

# 68. Ferramentas permitidas à LLM

Leitura:

```text
get_operation_summary
get_route_details
get_vehicle_details
get_delivery_details
get_cost_breakdown
get_comparison_results
get_algorithm_run_summary
get_team_assignment_details
```

Simulação:

```text
simulate_driver_swap
simulate_helper_removal
simulate_vehicle_swap
simulate_route_reassignment
validate_manual_change
```

Geração:

```text
generate_driver_instructions
generate_dispatch_report
generate_daily_operation_report
generate_executive_summary
```

---

# 69. Limites da LLM

A LLM não pode:

- alterar banco livremente;
- inventar valores;
- afirmar que uma alteração foi aplicada sem confirmação;
- ignorar regras HARD;
- despachar;
- substituir o algoritmo;
- fazer decisão operacional final sozinha.

---

# 70. Relatórios

O FluxMed deverá fornecer:

## Resultado interativo

Principal forma de análise.

## PDF

Relatório profissional.

## XLSX

Com abas como:

```text
Resumo
Rotas
Entregas
Veículos
Equipe
Custos
```

## CSV

Disponível para tabelas específicas quando útil.

---

# 71. Conteúdo do relatório de rota

Cada rota deve conter:

- veículo;
- placa;
- equipe;
- entregas em ordem;
- código da entrega;
- NF;
- endereço;
- prioridade;
- janela;
- ETA;
- distância;
- duração;
- custo;
- utilização de peso;
- utilização de volume.

---

# 72. Histórico

Operações anteriores devem permanecer consultáveis.

Relatórios históricos são gerados a partir do snapshot correspondente.

Alterações posteriores em:

- preço de combustível;
- funcionário;
- veículo;
- configuração;

não alteram o histórico.

---

# 73. Tela Operações

Deve permitir:

- listar operações;
- filtrar;
- ver status;
- criar nova;
- abrir existente;
- consultar histórico.

Informações resumidas:

- data;
- cidade;
- status;
- entregas;
- veículos;
- custo quando houver;
- horário.

---

# 74. Tela Entregas

Permite:

- consultar entregas cadastradas;
- adicionar;
- editar quando permitido;
- importar;
- filtrar;
- localizar endereço;
- visualizar prioridade e compatibilidades.

---

# 75. Tela Frota

Permite:

- listar veículos;
- cadastrar;
- editar;
- inativar;
- visualizar capacidade;
- ver refrigeração;
- ver autonomia;
- visualizar custo/configuração contratual.

---

# 76. Tela Equipe

Permite:

- listar pessoas;
- cadastrar;
- editar;
- inativar;
- ver função;
- ver vínculo;
- ver modelo de pagamento;
- disponibilidade.

---

# 77. Tela Relatórios

Permite consultar relatórios por operação e gerar exports quando apropriado.

Não deve ser um sistema de BI genérico.

---

# 78. Tela Configurações

Apenas `ADMIN`.

Pode incluir:

- preço de combustível;
- defaults operacionais;
- provider LLM ativo;
- versão do algoritmo;
- versão do dataset;
- saúde básica;
- configurações permitidas.

Parâmetros técnicos detalhados do GA não devem ser expostos como formulário comum.

---

# 79. Parâmetros do GA

O usuário normal não altera:

```text
population_size
mutation_rate
elitism_rate
tournament_size
stagnation_limit
```

Esses parâmetros são:

- calibrados;
- versionados;
- registrados na execução.

Experimentos acadêmicos utilizam scripts/notebooks próprios.

---

# 80. Comparações acadêmicas

A aplicação poderá mostrar comparação resumida entre estratégias.

Abordagens planejadas:

- Random — sanity check;
- Nearest Neighbor;
- Best Insertion;
- GA básico;
- GA + pruning;
- GA + pruning + repair.

OR-Tools ou método exato pode ser usado como referência opcional em instâncias pequenas.

---

# 81. Métricas acadêmicas

Medir:

- viabilidade;
- violações HARD;
- custo;
- makespan;
- tempo de viagem;
- distância;
- tempo computacional;
- veículos;
- entregas no prazo;
- tardiness;
- utilização;
- podas;
- avaliações evitadas;
- gerações;
- tempo até melhor solução.

---

# 82. UX e identidade visual

O FluxMed deve ter aparência de:

> centro moderno de planejamento logístico.

Não deve parecer:

- dashboard genérico de SaaS;
- prontuário médico;
- sistema hospitalar cheio de cruzes;
- site institucional;
- laboratório de algoritmo.

Características visuais:

- profissional;
- limpo;
- mapa central;
- alta densidade de informação organizada;
- hierarquia clara;
- animações discretas;
- cores funcionais.

---

# 83. Identidade cromática

Direção:

- teal / azul-petróleo como cor primária;
- grafite;
- branco;
- cinzas;
- verde para sucesso;
- âmbar para atenção;
- vermelho somente para erro, bloqueio ou situação crítica.

Rotas usam cores distintas por veículo, independentemente da cor primária da marca.

---

# 84. Responsividade

Prioridade:

```text
Desktop
```

porque planejamento logístico e mapa se beneficiam de tela ampla.

Deve continuar funcional em tablets e telas menores, mas a V1 não precisa otimizar toda a experiência para smartphone.

---

# 85. Estados de interface obrigatórios

Toda feature relevante deve possuir:

- loading;
- vazio;
- sucesso;
- erro;
- bloqueado;
- desabilitado quando apropriado.

Não assumir que dados sempre existem.

---

# 86. Mensagens de erro

Erros devem ser específicos.

Ruim:

```text
Algo deu errado.
```

Bom:

```text
A entrega DLV-NF45872-001 exige refrigeração,
mas nenhum veículo refrigerado está selecionado.
```

O backend terá códigos de erro tipados.

---

# 87. Degradação

Se LLM falhar:

- otimização continua;
- mapas continuam;
- operação continua;
- IA fica indisponível.

Se PDF falhar:

- plano continua;
- usuário tenta exportar novamente.

Se banco falhar:

- nenhuma alteração deve fingir que foi persistida.

---

# 88. Dados sintéticos

O ambiente acadêmico utilizará prioritariamente dados fictícios.

Nenhuma demonstração depende de informações médicas pessoais reais.

Isso reduz risco de privacidade e facilita reprodução.

---

# 89. Critérios de sucesso da V1

A V1 é considerada funcional quando for possível:

1. autenticar;
2. visualizar Santa Aurora;
3. criar uma operação;
4. obter entregas válidas;
5. selecionar frota e equipe;
6. configurar horário e tráfego;
7. criar uma interdição;
8. validar a operação;
9. executar o GA;
10. acompanhar progresso real;
11. obter solução validada;
12. visualizar rotas no mapa;
13. inspecionar cada veículo;
14. entender métricas e custos;
15. aprovar/despachar;
16. gerar relatório;
17. consultar Assistente IA;
18. executar testes automatizados;
19. reproduzir benchmarks;
20. demonstrar tudo em vídeo.

---

# 90. Não objetivos da V1

A V1 não pretende:

- substituir TMS comercial;
- controlar estoque;
- gerenciar medicamentos por lote;
- fazer prescrição;
- realizar diagnóstico;
- controlar paciente;
- acompanhar temperatura de carga em tempo real;
- assinar comprovante de entrega;
- realizar faturamento;
- emitir NF;
- operar GPS;
- controlar motorista em rota;
- ser multiempresa SaaS;
- escalar automaticamente para grande volume empresarial.

---

# 91. Evoluções futuras documentáveis

Possíveis evoluções:

- pickups;
- pickups dinâmicos;
- GPS;
- aplicativo do motorista;
- central do controlador;
- reotimização em tempo real;
- múltiplos depósitos;
- frota elétrica;
- carregamento/recarga;
- trânsito real;
- cidades importadas do OpenStreetMap;
- GIS externo;
- eventos/mensageria;
- jornadas individuais;
- turn restrictions avançadas;
- lanes;
- telemetria;
- notificações.

Nada disso deve atrasar a V1.

---

# 92. Regra de decisão de escopo

Sempre que surgir uma nova ideia, aplicar:

```text
É requisito acadêmico?
        ↓ sim
entra

Melhora fortemente demonstração/portfólio?
        ↓ sim
avaliar

É necessária para uma feature já aprovada?
        ↓ sim
entra

Só seria útil em produto comercial de grande escala?
        ↓ sim
futuro
```

---

# 93. Definição de produto pronto para desenvolvimento

O produto está suficientemente definido quando os documentos seguintes estiverem fechados:

```text
README.md
docs/PRODUCT_SPEC.md
docs/ARCHITECTURE.md
docs/DOMAIN_MODEL.md
docs/SANTA_AURORA_SPEC.md
docs/OPTIMIZATION_SPEC.md
docs/FRONTEND_SPEC.md
docs/API_SPEC.md
docs/LLM_SPEC.md
docs/TESTING_STRATEGY.md
docs/DEVELOPMENT_PLAN.md
docs/CODEX_INSTRUCTIONS.md
```

A implementação só deve começar após as fronteiras principais estarem documentadas.

---

# 94. Regra final

> O FluxMed deve ser simples de explicar, difícil de implementar de forma ingênua e convincente quando demonstrado.

A complexidade do projeto deve estar no problema que realmente importa:

- modelagem;
- otimização;
- roteamento;
- restrições;
- validação;
- explicabilidade;
- visualização.

Não em infraestrutura desnecessária.
