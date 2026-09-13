# FluxMed — Santa Aurora Specification

**Documento:** `docs/SANTA_AURORA_SPEC.md`  
**Status:** Especificação oficial da cidade sintética da V1  
**Projeto:** FluxMed — Planejamento Inteligente de Rotas Médicas  
**Cidade inicial:** Santa Aurora  
**Contexto:** Tech Challenge — Fase 2 — Projeto 2

---

# 1. Objetivo deste documento

Este documento define como a cidade fictícia **Santa Aurora** será modelada, gerada, validada e utilizada pelo FluxMed.

A cidade existe para fornecer um ambiente urbano:

- reproduzível;
- plausível;
- suficientemente complexo para roteamento;
- visualmente convincente;
- academicamente defensável;
- independente de APIs de mapas externos.

Santa Aurora não deve ser tratada como exceção dentro do sistema.

Ela será a primeira implementação de um modelo de cidade genérico.

---

# 2. Princípio central

A arquitetura do FluxMed deve ser **city-agnostic**.

O restante do sistema deve consumir uma cidade normalizada por meio de uma abstração equivalente a:

```text
CityProvider
```

Implementação inicial:

```text
SantaAuroraProvider
```

Possíveis implementações futuras:

```text
OSMCityProvider
GISCityProvider
```

Não usar regras como:

```python
if city.name == "Santa Aurora":
    ...
```

fora do módulo responsável pela geração ou seed dessa cidade.

---

# 3. Identidade da cidade

Campos principais:

```text
name = Santa Aurora
country = Brazil
source_type = SYNTHETIC
timezone = America/Sao_Paulo
dataset_version = 1.0.0
```

A cidade deve possuir também uma `generation_seed`.

Exemplo:

```text
dataset_version = 1.0.0
generation_seed = 20260913
```

A mesma versão + mesma seed + mesmos catálogos devem gerar o mesmo dataset.

---

# 4. Objetivos de escala

A primeira versão de Santa Aurora deve ter aproximadamente:

```text
9 bairros
~800 interseções
~2.000 segmentos viários dirigidos
~150 ruas/logradouros
20.000–40.000 endereços válidos
~40–60 facilities relevantes
```

Esses números são alvos aproximados.

O gerador pode variar moderadamente desde que:

- a cidade permaneça coerente;
- os benchmarks continuem úteis;
- o mapa não fique pesado;
- os resultados sejam determinísticos para a mesma seed.

---

# 5. Forma geral da cidade

Santa Aurora deve parecer uma cidade brasileira de porte médio.

A morfologia não deve ser uma grade perfeita.

Ela deve combinar:

- centro mais antigo;
- bairros residenciais;
- área universitária;
- expansão moderna;
- áreas industriais;
- distrito logístico;
- vias arteriais;
- ruas locais irregulares;
- um rio;
- poucas pontes;
- anel viário.

---

# 6. Bairros oficiais da V1

## 6.1 Centro Histórico

Características:

- alta densidade;
- quadras menores;
- ruas estreitas;
- maior quantidade de sentidos únicos;
- comércio;
- clínicas;
- serviços;
- edifícios antigos;
- maior complexidade de roteamento.

Tema de nomes:

- personagens fictícios;
- datas fictícias;
- nomes históricos plausíveis.

---

## 6.2 Vila Aurora

Características:

- bairro residencial antigo;
- malha irregular;
- densidade média;
- comércio local;
- algumas clínicas e farmácias;
- vias com pequenas mudanças de direção.

Tema:

- nomes tradicionais fictícios;
- localidades fictícias;
- sobrenomes brasileiros plausíveis.

---

## 6.3 Jardim das Flores

Características:

- residencial planejado;
- ruas mais regulares;
- densidade média;
- praças;
- baixa presença de tráfego pesado.

Tema:

- flores;
- árvores;
- natureza.

---

## 6.4 Parque Universitário

Características:

- universidade;
- hospital universitário;
- laboratórios;
- clínicas;
- vias mais largas;
- alta demanda médica.

Tema:

- ciência;
- educação;
- pesquisadores fictícios;
- conhecimento.

---

## 6.5 Santa Cecília

Características:

- uso misto;
- alta densidade;
- residências;
- comércio;
- serviços;
- clínicas;
- farmácias.

Tema:

- nomes urbanos tradicionais.

---

## 6.6 Vale Verde

Características:

- baixa densidade;
- condomínios;
- vias sinuosas;
- relevo visualmente sugerido pela geometria;
- maiores distâncias médias entre destinos.

Tema:

- montanhas;
- rios;
- paisagens;
- natureza.

---

## 6.7 Nova Esperança

Características:

- expansão urbana moderna;
- malha mais regular;
- avenidas largas;
- residências novas;
- clínicas de bairro;
- farmácias.

Tema:

- conceitos cívicos;
- desenvolvimento;
- modernidade.

---

## 6.8 Distrito Industrial

Características:

- grandes lotes;
- galpões;
- avenidas largas;
- menor densidade residencial;
- maior presença de caminhões;
- acessos diretos a vias arteriais.

Tema:

- indústria;
- produção;
- ofícios;
- manufatura.

---

## 6.9 Distrito Logístico

Características:

- armazéns;
- centros de distribuição;
- pátios;
- acesso ao anel viário;
- vias adequadas a veículos maiores;
- baixa densidade residencial.

O centro de distribuição principal do FluxMed fica aqui.

Tema:

- transporte;
- comércio;
- logística.

---

# 7. Rio

Santa Aurora deve possuir um rio que funcione como barreira urbana real.

Objetivos:

- criar gargalos de roteamento;
- tornar pontes relevantes;
- permitir impacto visual de interdições.

O rio não pode ser apenas decorativo.

A geometria da cidade deve realmente impedir cruzamento por vias comuns.

---

# 8. Pontes

A cidade deve possuir poucas pontes estratégicas.

Sugestão conceitual:

```text
ponte oeste
ponte central
ponte leste
```

Não é necessário usar exatamente três se a geração justificar outra quantidade pequena.

As pontes devem:

- conectar as duas margens;
- fazer parte do grafo;
- ser importantes para shortest path;
- poder receber interdição operacional.

Uma ponte pode ter nome próprio sem obrigatoriamente interromper o nome da avenida/corredor que passa sobre ela.

---

# 9. Anel viário

Santa Aurora deve possuir um corredor de alta capacidade:

```text
Anel Viário de Santa Aurora
```

Objetivos:

- permitir contorno da cidade;
- conectar Industrial e Logístico;
- oferecer rotas mais longas em distância, porém potencialmente mais rápidas;
- tornar tempo e distância objetivos diferentes.

---

# 10. Hierarquia viária

Classes oficiais:

```text
EXPRESSWAY
ARTERIAL
COLLECTOR
LOCAL
SERVICE
```

---

# 11. EXPRESSWAY

Características:

- maior velocidade;
- poucos acessos;
- longos segmentos;
- conexão regional/anel viário;
- tráfego pesado permitido quando aplicável.

---

# 12. ARTERIAL

Características:

- conecta bairros;
- atravessa grandes distâncias;
- maior capacidade;
- frequentemente nomeada como Avenida.

---

# 13. COLLECTOR

Características:

- conecta ruas locais a arteriais;
- importância intermediária;
- velocidade média.

---

# 14. LOCAL

Características:

- acesso a residências e comércio;
- menor velocidade;
- grande quantidade de endereços.

---

# 15. SERVICE

Características:

- acessos internos;
- vias de serviço;
- zonas industriais/logísticas;
- menor importância no tráfego geral.

---

# 16. Grafo dirigido

O grafo nasce dirigido.

Cada `RoadSegment` representa um edge com sentido definido.

Exemplo de via mão dupla:

```text
Intersection A → Intersection B
Intersection B → Intersection A
```

Via mão única:

```text
Intersection A → Intersection B
```

sem edge inverso.

---

# 17. Nós do grafo

Cada `Intersection` representa um nó.

Nós podem existir em:

- cruzamentos;
- bifurcações;
- início/fim de ruas;
- acessos relevantes;
- transições de corredor.

Evitar criar nós excessivos para cada pequeno ponto geométrico.

---

# 18. RoadSegment

Cada segmento deve possuir:

```text
id
street_id
from_intersection_id
to_intersection_id
geometry
length_m
speed_limit_kmh
road_class
lanes
active
```

Outros atributos podem ser adicionados somente se necessários.

---

# 19. Velocidade base

A velocidade não deve ser aleatória individualmente sem contexto.

Ela deve derivar principalmente de:

```text
road_class
+
district profile
+
specific corridor characteristics
```

Valores exatos serão calibrados.

O objetivo é manter coerência relativa:

```text
EXPRESSWAY > ARTERIAL > COLLECTOR > LOCAL
```

em condições livres.

---

# 20. Processo de geração da cidade

A ordem recomendada é:

```text
1. definir limites gerais da cidade
2. gerar rio e barreiras
3. definir bairros
4. gerar grandes corredores
5. gerar anel viário
6. gerar arteriais
7. gerar coletores
8. gerar ruas locais
9. criar interseções
10. criar RoadSegments dirigidos
11. identificar Streets lógicas
12. nomear Streets
13. gerar quadras/lotes
14. gerar edificações
15. gerar entradas
16. gerar endereços
17. gerar facilities
18. gerar perfis de trânsito
19. validar
20. persistir
```

---

# 21. Topologia antes dos nomes

A geometria deve ser criada antes da nomeação.

Não gerar uma lista de nomes e depois desenhar ruas aleatoriamente.

Primeiro deve existir:

```text
topologia
→ corredores lógicos
→ Street
→ nome
```

---

# 22. Street x RoadSegment

Uma `Street` é um logradouro lógico.

Ela pode possuir muitos `RoadSegments`.

Exemplo:

```text
Avenida Santa Aurora
├── SEG-001
├── SEG-002
├── SEG-003
└── SEG-004
```

O nome pertence à Street.

O segmento pertence ao grafo.

---

# 23. Detecção de continuidade de Street

Segmentos podem ser agrupados na mesma Street considerando:

- continuidade geométrica;
- ângulo;
- road class;
- largura/faixas;
- função urbana;
- conectividade;
- importância.

Uma arterial pode atravessar vários bairros mantendo o mesmo nome.

---

# 24. Mudanças de nome

Permitir raramente mudanças de nome em grandes corredores quando houver justificativa urbana.

Exemplo:

```text
Avenida X
→ atravessa marco importante
→ Avenida Y
```

Não usar mudanças frequentes apenas para aumentar variedade.

---

# 25. StreetNamingService

A nomeação deve ser determinística.

Entrada conceitual:

```text
road_type
urban_function
district
theme
importance
seed
catalog_version
```

Saída:

```text
street_name
```

---

# 26. Catálogos de nomes

Os nomes devem vir de arquivos versionados.

Exemplo:

```text
data/santa_aurora/catalogs/
├── flowers.json
├── scientists.json
├── traditional_names.json
├── civic_concepts.json
├── industrial_terms.json
├── logistics_terms.json
└── global_corridors.json
```

Não usar LLM durante a geração da cidade.

---

# 27. Nomes globais sugeridos

Exemplos possíveis:

```text
Avenida Santa Aurora
Avenida da Integração
Avenida Central
Avenida República
Anel Viário de Santa Aurora
```

Esses nomes podem atravessar bairros.

---

# 28. Nomes de pessoas

Quando usar nomes próprios:

- devem parecer brasileiros;
- devem ser fictícios;
- evitar homenagens diretas a pessoas reais famosas;
- podem ter pequena biografia fictícia apenas se isso for útil para documentação.

A cidade não precisa armazenar biografia para cada nome.

---

# 29. Tipo de logradouro

O tipo não deve ser escolhido aleatoriamente.

Exemplos:

```text
EXPRESSWAY → Via / Rodovia / Anel
ARTERIAL   → Avenida
COLLECTOR  → Avenida / Rua
LOCAL      → Rua
SERVICE    → Via / Rua de Serviço
```

---

# 30. Unicidade de nomes

Evitar nomes idênticos de Street dentro da cidade.

Comparação deve normalizar:

- maiúsculas/minúsculas;
- acentos;
- espaços.

Exemplo:

```text
Rua das Acácias
Rua das Acacias
```

devem ser consideradas conflitantes para o gerador.

---

# 31. Falta de nomes disponíveis

Se um catálogo acabar:

```text
erro de geração
```

Não reutilizar silenciosamente nomes.

Isso mantém o dataset confiável.

---

# 32. Lotes

A cidade deve possuir lotes conceituais.

Um lote pode ser:

```text
OCCUPIED
VACANT
```

Objetivo:

- produzir numeração com gaps;
- criar distribuição realista de endereços;
- distinguir terreno vazio de endereço válido.

---

# 33. Edificações

Tipos principais:

```text
HOUSE
APARTMENT_BUILDING
COMMERCIAL
CLINIC
HOSPITAL
PHARMACY
LABORATORY
WAREHOUSE
SCHOOL
PUBLIC_BUILDING
OTHER
```

Lote vazio não gera endereço de entrega válido.

---

# 34. Entrada da edificação

Cada Building deve possuir uma entrada principal:

```text
entrance_location
```

A entrada deve estar conectada logicamente a uma via.

O endereço representa a entrada operacional, não o centro geométrico do prédio.

---

# 35. Endereços reais no dataset

O dataset deve guardar números existentes individualmente.

Exemplo:

```text
Rua das Acácias:
7
11
15
25
31
43
...
```

Não armazenar apenas:

```text
1–1105
```

---

# 36. Numeração

A numeração deve ser progressiva ao longo da Street.

Pode se basear aproximadamente na distância desde a origem do logradouro.

Isso permite números crescentes sem exigir sequência perfeita.

---

# 37. Pares e ímpares

Sempre que geometricamente plausível:

```text
um lado → pares
outro lado → ímpares
```

A orientação pode ser calculada em relação ao sentido lógico da Street.

Não precisa ser perfeita em todos os casos sinuosos, mas deve manter boa consistência.

---

# 38. Gaps de numeração

Devem existir.

Motivos:

- lotes vazios;
- terrenos maiores;
- prédios ocupando vários lotes;
- numeração histórica;
- pequenas irregularidades sintéticas.

Isso torna busca de endereço mais realista.

---

# 39. Sufixos

Apoiar:

```text
155A
155B
```

Campos internos:

```text
house_number = "155A"
house_number_numeric = 155
suffix = "A"
```

Uso deve ser moderado.

---

# 40. Complementos

Apartamentos e salas podem utilizar:

```text
complement
```

O complemento não cria um novo ponto viário.

Exemplo:

```text
Rua X, 120, Apto 302
```

usa a entrada do prédio 120.

---

# 41. Address

Cada endereço deve mapear explicitamente para:

```text
street_id
district_id
building_id
road_segment_id
position_on_segment
location
```

Não resolver acesso apenas usando “interseção mais próxima”.

---

# 42. Busca de endereço

Autocomplete deve listar apenas endereços existentes.

Exemplo válido:

```text
Rua das Acácias, 593
```

Exemplo inexistente:

```text
Rua das Acácias, 600
```

não deve ser aceito silenciosamente.

---

# 43. Sugestões de número

Para número inexistente:

```text
Número não encontrado.
Sugestões próximas: 593, 611.
```

Essas sugestões não são confirmação automática.

---

# 44. Fuzzy street search

Pode corrigir erros de digitação.

Exemplo:

```text
Rua das Acassias
→ Rua das Acácias
```

Se houver ambiguidade, exigir escolha do usuário.

---

# 45. Facilities médicas

Santa Aurora deve possuir aproximadamente 40–60 facilities relevantes, distribuídas de forma plausível.

Tipos:

```text
DEPOT
HOSPITAL
CLINIC
LABORATORY
PHARMACY
WAREHOUSE
PUBLIC_FACILITY
```

---

# 46. Hospitais

Poucos e importantes.

Distribuição sugerida:

- hospital central;
- hospital universitário;
- hospital regional/privado;
- outras unidades menores se necessário.

Hospitais geram alta demanda.

---

# 47. Clínicas

Mais numerosas que hospitais.

Concentradas principalmente em:

- Centro Histórico;
- Parque Universitário;
- Santa Cecília;
- Nova Esperança.

---

# 48. Laboratórios

Quantidade intermediária.

Maior presença próxima de:

- hospitais;
- universidade;
- áreas de serviços.

---

# 49. Farmácias

Bem distribuídas.

Podem existir em praticamente todos os bairros residenciais.

---

# 50. Home care

Home care não precisa de Facility.

É uma Delivery gerada para um Address residencial válido.

Isso utiliza a base completa de endereços e evita cenário formado somente por hospitais.

---

# 51. Centro de distribuição

Facility:

```text
DEPOT
```

Local:

```text
Distrito Logístico
```

Requisitos:

- acesso a arterial;
- fácil acesso ao anel;
- espaço plausível;
- endereço válido.

Todas as rotas da V1 começam e terminam aqui.

---

# 52. Demanda espacial

A geração de entregas deve consultar um modelo de demanda do bairro.

Exemplo conceitual:

```text
Parque Universitário
→ maior peso para hospital/lab/clinic

Distrito Logístico
→ warehouse / logistics

Vale Verde
→ maior proporção de home care

Centro Histórico
→ clinics / pharmacies / dense service
```

---

# 53. Clusters

O gerador pode criar clusters de demanda para representar:

- concentração médica;
- bairro com surtos de demanda;
- entregas próximas.

A quantidade e intensidade de clusters pode variar pelo cenário.

---

# 54. Trânsito sintético

O tráfego deve ser determinístico para um dado conjunto de parâmetros.

Não usar API de trânsito real.

Fatores principais:

```text
time_of_day
road_class
district
```

---

# 55. Buckets de tempo

Recomendação inicial:

```text
15 minutos
```

Exemplos:

```text
07:00–07:15
07:15–07:30
07:30–07:45
```

O tamanho pode ser ajustado por benchmark.

---

# 56. Padrão de trânsito diário

Santa Aurora deve possuir tendências plausíveis.

Exemplo:

```text
madrugada → livre
manhã cedo → crescimento
pico matinal → congestionamento
meio do dia → moderado
pico da tarde → congestionamento
noite → queda
```

Não é necessário modelar cada semáforo.

---

# 57. Trânsito por bairro

Centro Histórico:

- congestionamento maior;
- baixa velocidade local.

Distrito Logístico:

- tráfego de veículos grandes;
- melhor acesso arterial.

Vale Verde:

- menor congestionamento;
- maiores distâncias.

Parque Universitário:

- picos associados a hospital/universidade.

---

# 58. Fator de tráfego

Cada edge pode receber um multiplicador de travel time.

Exemplo conceitual:

```text
FREE        → 1.00
LIGHT       → >1.00
MODERATE    → > LIGHT
HEAVY       → > MODERATE
VERY_HEAVY  → maior fator
```

Valores exatos serão calibrados.

---

# 59. Não modelar na V1

Não implementar:

- semáforos individuais;
- ciclo de sinal;
- faixa por faixa;
- congestionamento microscópico;
- acidente automático;
- clima;
- fechamento parcial de lane;
- U-turn complexo;
- turn restrictions detalhadas.

---

# 60. Interdições operacionais

O dataset base não muda.

Uma operação aplica:

```text
EffectiveRoadGraph =
BaseGraph
+
Traffic
+
OperationOverrides
```

---

# 61. Fechamento de segmento

Uma interdição pode remover um RoadSegment do grafo efetivo.

Via de mão dupla pode exigir fechamento dos dois segmentos dirigidos.

---

# 62. Fechamento de rua

Na UI o usuário pode escolher uma Street inteira.

Internamente isso cria overrides sobre todos os RoadSegments relevantes.

---

# 63. Interdição de ponte

Deve poder isolar caminhos e forçar desvios.

É um bom caso para demonstração acadêmica.

---

# 64. Validação de conectividade

Após gerar a cidade:

- principais regiões devem permanecer conectadas;
- nenhum bairro pode ficar isolado por erro;
- depósito deve alcançar todos os destinos válidos;
- bridges precisam realmente conectar margens.

---

# 65. Validação de grafos dirigidos

Deve verificar:

- edges apontam para nós existentes;
- nenhuma geometria corrompida;
- sentidos fazem sentido;
- one-way não cria isolamento acidental;
- retorno ao depósito é possível a partir dos principais destinos.

---

# 66. Validação geométrica

Usar PostGIS ou biblioteca apropriada para garantir:

```text
valid geometry
```

Verificar:

- District polygons;
- Building polygons;
- Road lines;
- points.

---

# 67. Validação de endereços

Todo Address deve:

- pertencer a City;
- pertencer a District;
- pertencer a Street;
- apontar para Building;
- apontar para RoadSegment;
- possuir localização válida;
- não ficar no rio;
- não ficar fora do lote correspondente.

---

# 68. Validação de Building

Todo Building ativo deve:

- estar dentro de Lot;
- possuir entrance_location válida;
- ter acesso razoável à via;
- possuir tipo válido.

---

# 69. Validação de Facility

Facility deve:

- possuir Address válido;
- tipo compatível com Building quando aplicável;
- estar acessível no grafo.

---

# 70. Validação do depósito

O DEPOT deve:

- existir exatamente uma vez para a configuração padrão;
- ficar no Distrito Logístico;
- ter acesso ao grafo;
- aceitar saída/retorno de todos os tipos de veículo da V1.

---

# 71. Validação dos nomes

Verificar:

- nome não vazio;
- unicidade normalizada;
- quantidade de nomes suficiente;
- caracteres válidos;
- ausência de duplicidade causada por acento/case.

---

# 72. Validação de velocidades

Todo RoadSegment deve possuir:

```text
speed_limit_kmh > 0
```

Valores também devem estar dentro de intervalos plausíveis por classe.

---

# 73. Validação de comprimentos

`length_m` deve ser consistente com geometry.

Não aceitar:

```text
segmento de 500 m
length_m = 12
```

fora de pequena tolerância.

---

# 74. Validação de pontes

Toda ponte deve:

- conectar margens opostas;
- possuir edges correspondentes;
- não terminar dentro do rio;
- integrar o grafo.

---

# 75. Falha de geração

Se uma validação estrutural falhar:

```text
generation failed
```

Não persistir parcialmente uma cidade defeituosa como dataset oficial.

---

# 76. Persistência

Fluxo recomendado:

```text
generate in memory / staging
 ↓
validate
 ↓
persist transactionally
 ↓
mark dataset ready
```

Se falhar:

```text
rollback
```

---

# 77. Script principal

Planejado:

```text
scripts/generate_santa_aurora.py
```

Responsabilidades:

- receber seed;
- receber versão;
- executar gerador;
- validar;
- persistir/exportar.

---

# 78. Script de validação

Planejado:

```text
scripts/validate_city.py
```

Pode ser executado independentemente do gerador.

Objetivo:

- detectar corrupção;
- validar seed;
- validar CI;
- produzir relatório.

---

# 79. Export para debug

É permitido gerar:

```text
GeoJSON
```

para:

- inspeção;
- debugging;
- visualização;
- testes.

PostgreSQL/PostGIS continua sendo fonte de verdade depois de importado.

---

# 80. Seed determinística

Requisitos:

```text
same generator version
+
same catalog version
+
same seed
=
same city
```

Isso permite:

- testes;
- screenshots;
- benchmarks;
- reprodução acadêmica.

---

# 81. Versionamento do gerador

Registrar:

```text
generator_version
catalog_version
dataset_version
seed
```

Mudança significativa no algoritmo pode gerar nova `dataset_version`.

---

# 82. Alterações pequenas

Correções de catálogo ou bug podem resultar em:

```text
1.0.1
```

Mudança estrutural:

```text
1.1.0
```

Quebra de compatibilidade relevante:

```text
2.0.0
```

Não precisa automatizar release completo; seguir conceito semântico.

---

# 83. Dataset usado em benchmark

Toda execução acadêmica deve registrar:

```text
city = Santa Aurora
dataset_version
seed
```

Assim resultados permanecem comparáveis.

---

# 84. Renderização no frontend

A API deve fornecer dados suficientes para o MapLibre.

Camadas principais:

```text
districts
water
roads
facilities
depot
addresses when needed
```

Não enviar 40 mil endereços como marcadores simultaneamente por padrão.

---

# 85. Endereços no mapa

Endereços individuais aparecem quando:

- pesquisados;
- usados por Delivery;
- necessários em seleção;
- zoom suficientemente alto, caso a implementação permita.

Não renderizar todos em zoom geral.

---

# 86. Simplificação de geometria

Se necessário, usar geometria simplificada para:

- bairros;
- rio;
- ruas em zoom baixo.

Não otimizar prematuramente.

Primeiro medir desempenho.

---

# 87. Dados para autocomplete

Busca de endereço deve usar backend.

Não carregar 40 mil endereços no browser para filtrar localmente.

Fluxo:

```text
user types
 ↓
GET address suggestions
 ↓
backend query
 ↓
limited results
```

---

# 88. Busca de Street

Normalização pode remover:

- acentos;
- case;
- espaços extras.

Pode utilizar fuzzy matching moderado.

---

# 89. Busca por número

Depois de Street selecionada:

```text
known numbers
```

devem vir do dataset.

Não inferir range.

---

# 90. CityProvider contract

Interface conceitual pode expor:

```text
get_city_metadata()
get_road_graph()
get_districts()
get_facilities()
search_addresses()
get_address()
get_traffic_profile()
get_map_layers()
```

A implementação concreta pode organizar métodos de forma diferente se preservar a fronteira.

---

# 91. Importadores futuros

Estrutura futura possível:

```text
city_importers/
├── synthetic/
│   └── santa_aurora.py
├── osm/
│   └── osm_importer.py
└── gis/
    └── gis_importer.py
```

Não implementar OSM/GIS na V1.

---

# 92. Modelo canônico de cidade

Qualquer futuro importer deve normalizar para:

```text
City
District
Street
Intersection
RoadSegment
Lot
Building
Address
Facility
TrafficProfile
```

O GA não muda.

---

# 93. O que não fazer

Não criar Santa Aurora como:

```text
array manual de 30 pontos
```

Não usar:

```text
distância euclidiana
```

como routing oficial.

Não usar:

```text
random street names sem lógica
```

Não usar:

```text
endereços por range genérico
```

Não usar:

```text
Google Maps
```

como dependência obrigatória.

---

# 94. Testes obrigatórios do gerador

Cobrir:

- determinismo;
- bairros;
- connectivity;
- one-way;
- street names;
- duplicate names;
- addresses;
- parity;
- gaps;
- buildings;
- facilities;
- depot;
- bridges;
- river;
- road geometry;
- speed;
- PostGIS validity.

---

# 95. Property-based tests úteis

Exemplos:

> Todo Address ativo possui Building e RoadSegment válidos.

> Nenhuma Facility ativa existe fora de um Address válido.

> Todo RoadSegment possui nós existentes.

> Todo endereço gerado para cenário sintético existe no dataset.

---

# 96. Smoke test da cidade

Um smoke test deve conseguir:

```text
load Santa Aurora
 ↓
find depot
 ↓
find hospital
 ↓
route depot → hospital
 ↓
route hospital → depot
```

com sucesso.

---

# 97. Cenário visual mínimo

Na primeira implementação visual, a cidade deve mostrar:

- limites dos bairros;
- rio;
- pontes;
- arteriais;
- ruas principais;
- depot;
- facilities médicas.

Antes de gerar milhares de endereços visualmente.

---

# 98. Ordem recomendada de implementação

Para evitar construir tudo de uma vez:

```text
1. City + District
2. river
3. major roads
4. intersections / graph
5. RoadSegments
6. routing smoke test
7. Streets + naming
8. lots/buildings
9. addresses
10. facilities
11. traffic profiles
12. full validation
13. map polish
```

---

# 99. Critério de aceite técnico

Santa Aurora é considerada pronta para a V1 quando:

- geração é determinística;
- 9 bairros existem;
- grafo é roteável;
- rio cria barreira real;
- pontes funcionam;
- depósito é acessível;
- milhares de endereços válidos existem;
- facilities estão distribuídas;
- routing utiliza os RoadSegments;
- busca de endereço funciona;
- trânsito temporal funciona;
- validação completa passa;
- mapa é renderizado com desempenho aceitável.

---

# 100. Critério de aceite acadêmico

A cidade deve permitir demonstrar claramente:

- diferença entre distância e tempo;
- impacto de sentidos únicos;
- impacto de trânsito;
- impacto de interdição;
- necessidade de múltiplos veículos;
- agrupamento espacial;
- roteamento entre destinos reais do dataset;
- diferença entre solução simples e solução otimizada.

---

# 101. Regra final

> Santa Aurora deve ser complexa o suficiente para tornar o problema de roteamento interessante, mas simples o suficiente para ser inteiramente controlada, reproduzível e explicável dentro de um projeto acadêmico.

A cidade é um ambiente de teste do FluxMed, não um simulador urbano completo.
