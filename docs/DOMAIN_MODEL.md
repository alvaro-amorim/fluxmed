# FluxMed — Domain Model

**Documento:** `docs/DOMAIN_MODEL.md`  
**Status:** Modelo de domínio oficial da V1  
**Projeto:** FluxMed — Planejamento Inteligente de Rotas Médicas  
**Contexto:** Tech Challenge — Fase 2 — Projeto 2

---

# 1. Objetivo deste documento

Este documento define o modelo de domínio do FluxMed V1.

Ele estabelece:

- entidades principais;
- value objects;
- enums;
- relacionamentos;
- invariantes;
- estados;
- snapshots;
- regras de identidade;
- separação entre dados planejados e históricos;
- fronteiras entre operação, cidade, frota, equipe, roteamento e otimização.

Este documento não define detalhes de banco, ORM ou endpoints HTTP.

---

# 2. Princípios de modelagem

O domínio deve seguir estes princípios:

1. entidades com identidade própria usam UUID;
2. códigos humanos não substituem IDs técnicos;
3. regras críticas vivem no domínio;
4. histórico despachado é imutável;
5. dinheiro não usa `float`;
6. distâncias, tempos e unidades devem ser explícitos;
7. relações geográficas não devem ser inferidas apenas por proximidade quando existir ligação conhecida;
8. entidades históricas não devem ser apagadas fisicamente se já estiverem referenciadas;
9. planned e actual devem ser conceitos separados, mesmo quando actual ainda não for usado na V1;
10. regras futuras não devem poluir o domínio atual sem necessidade.

---

# 3. Contextos principais

O modelo pode ser entendido em seis áreas:

```text
Identity / Security
Operations
Deliveries
Fleet / Workforce
City / Routing
Optimization / Reporting
```

Essas áreas podem residir no mesmo monólito modular.

---

# 4. Entidade User

Representa um usuário autenticável.

Campos principais:

```text
id: UUID
email: str
display_name: str
password_hash: str
role: UserRole
active: bool
created_at
updated_at
last_login_at?
```

Enum:

```text
UserRole
├── ADMIN
└── PLANNER
```

Invariantes:

- email único;
- usuário inativo não autentica;
- password_hash nunca é exposto pela API;
- autorização é validada no backend.

---

# 5. Entidade Operation

Representa uma operação diária de planejamento.

Campos:

```text
id: UUID
operation_code: str
city_id: UUID
depot_facility_id: UUID
operation_date: date
operation_start_time: time
operation_end_time: time
traffic_mode: TrafficMode
status: OperationStatus
current_revision_number: int
created_by_user_id: UUID
created_at
updated_at
```

Enum:

```text
OperationStatus
├── DRAFT
├── READY
├── OPTIMIZING
├── OPTIMIZED
├── OUTDATED
├── APPROVED
└── DISPATCHED
```

Invariantes:

- `operation_end_time > operation_start_time`;
- exatamente um depósito por operação na V1;
- uma operação despachada não pode ser alterada;
- uma mudança relevante após otimização torna a operação `OUTDATED`.

---

# 6. Operation Code

Código humano legível.

Exemplo:

```text
OP-20260913-001
```

Não substitui o UUID.

Pode ser único por sistema.

---

# 7. Entidade OperationRevision

Representa o estado planejado de uma operação em um momento relevante.

Campos:

```text
id: UUID
operation_id: UUID
revision_number: int
status: RevisionStatus
created_at
created_by_user_id: UUID
optimized_at?
approved_at?
dispatched_at?
notes?
```

Enum sugerido:

```text
RevisionStatus
├── DRAFT
├── OPTIMIZED
├── OUTDATED
├── APPROVED
└── DISPATCHED
```

Invariantes:

- revision_number cresce monotonicamente dentro da operação;
- apenas revisões operacionalmente relevantes precisam ser persistidas;
- revisão `DISPATCHED` é imutável.

---

# 8. O que pertence a uma revisão

Uma revisão pode referenciar ou snapshotar:

- entregas selecionadas;
- veículos selecionados;
- workers disponíveis;
- restrições viárias;
- parâmetros operacionais;
- horário;
- trânsito;
- resultado de otimização;
- equipe sugerida;
- custos;
- métricas.

---

# 9. Entidade OperationVehicleSelection

Relaciona veículo e operação/revisão.

Campos:

```text
id: UUID
operation_revision_id: UUID
vehicle_id: UUID
selected: bool
available: bool
created_at
```

Regra:

- todos os veículos ativos/disponíveis podem vir selecionados por padrão;
- planejador pode desmarcar antes de otimizar.

---

# 10. Entidade OperationWorkerSelection

Relaciona worker e operação/revisão.

Campos:

```text
id: UUID
operation_revision_id: UUID
worker_id: UUID
selected: bool
available: bool
created_at
```

---

# 11. Entidade Delivery

Representa uma parada logística.

Campos:

```text
id: UUID
delivery_code: str
operation_id: UUID
invoice_number: str
invoice_series: str
issuer_document: str
issuer_name: str?
external_reference: str?
destination_address_id: UUID
recipient_name: str
package_count: int
total_weight_kg: Decimal
total_volume_m3: Decimal
priority: DeliveryPriority
time_window_start: datetime?
time_window_end: datetime?
time_window_policy: TimeWindowPolicy
service_time_minutes: int
service_time_source: ServiceTimeSource
temperature_class: TemperatureClass
handling_requirement: HandlingRequirement
status: DeliveryStatus
cargo_profile: CargoProfile?
notes: str?
created_at
updated_at
```

---

# 12. DeliveryPriority

```text
CRITICAL
HIGH
NORMAL
LOW
```

Regra:

- prioridade afeta qualidade de serviço;
- prioridade por si só não substitui janelas HARD.

---

# 13. TimeWindowPolicy

```text
HARD
SOFT
```

Regra:

- HARD violada invalida a rota;
- SOFT violada gera penalidade de serviço.

---

# 14. ServiceTimeSource

```text
ESTIMATED
MANUAL
IMPORTED
```

---

# 15. TemperatureClass

```text
AMBIENT
REFRIGERATED
```

---

# 16. HandlingRequirement

```text
STANDARD
TWO_PERSON
```

---

# 17. DeliveryStatus

Modelo future-ready:

```text
PENDING
PLANNED
LOADED
DISPATCHED
IN_TRANSIT
DELIVERED
FAILED
```

Na V1:

- uso efetivo termina essencialmente em `DISPATCHED`;
- estados de execução não precisam ser simulados.

---

# 18. CargoProfile

Usado principalmente no gerador sintético.

Valores sugeridos:

```text
MEDICATION_SMALL
REFRIGERATED_MEDICATION
LAB_MATERIAL
HOSPITAL_SUPPLIES
BULK_CONSUMABLES
MEDICAL_EQUIPMENT
```

Não é obrigatório para entregas importadas.

---

# 19. Identidade operacional da entrega

`delivery_code` é legível.

Exemplo:

```text
DLV-NF45872-001
```

A combinação documental relevante:

```text
issuer_document
invoice_series
invoice_number
```

pode identificar a NF de origem.

Uma mesma NF pode gerar múltiplas deliveries quando houver divisão logística.

---

# 20. Invariantes de Delivery

- `package_count > 0`;
- `total_weight_kg > 0`;
- `total_volume_m3 > 0`;
- endereço deve existir;
- janela final não pode ser anterior à inicial;
- `TWO_PERSON` exige equipe compatível;
- `REFRIGERATED` exige veículo compatível;
- não usar número de NF como chave primária.

---

# 21. Service Time

Valor oficial da entrega:

```text
service_time_minutes
```

O estimator pode produzir internamente:

```text
service_time_solo_minutes
service_time_with_helper_minutes
```

Esses valores podem ser armazenados quando úteis.

Se o usuário fornecer tempo manual/importado, ele prevalece sobre estimativa automática.

---

# 22. Entidade Vehicle

Campos:

```text
id: UUID
plate: str
type: VehicleType
ownership_type: VehicleOwnershipType
max_payload_kg: Decimal
max_volume_m3: Decimal
max_range_km: Decimal
refrigerated: bool
status: VehicleStatus
helper_policy: HelperPolicy
fuel_type: FuelType?
fuel_efficiency_km_per_l: Decimal?
active: bool
created_at
updated_at
```

---

# 23. VehicleType

```text
MOTO
VAN_COMPACT
CARGO_VAN
LIGHT_TRUCK
```

---

# 24. VehicleOwnershipType

```text
OWNED
AGGREGATED
```

---

# 25. VehicleStatus

Sugestão:

```text
AVAILABLE
UNAVAILABLE
MAINTENANCE
INACTIVE
```

---

# 26. HelperPolicy

```text
FORBIDDEN
OPTIONAL
REQUIRED
```

Regras padrão sugeridas:

```text
MOTO → FORBIDDEN
VAN_COMPACT → OPTIONAL
CARGO_VAN → OPTIONAL
LIGHT_TRUCK → OPTIONAL
```

Configuração pode sobrescrever.

---

# 27. FuelType

V1 pode começar com:

```text
GASOLINE
ETHANOL
DIESEL
FLEX
OTHER
```

A arquitetura pode receber energia elétrica no futuro.

---

# 28. Entidade OwnedVehicleCostProfile

Aplicável a veículo próprio.

Campos:

```text
id: UUID
vehicle_id: UUID
acquisition_value_brl: Decimal
residual_value_brl: Decimal
useful_life_km: Decimal
annual_ipva_brl: Decimal
annual_insurance_brl: Decimal
annual_fixed_costs_brl: Decimal
expected_productive_hours_per_year: Decimal
created_at
updated_at
```

Valores derivados:

```text
depreciation_per_km
fixed_cost_per_hour
```

---

# 29. Entidade VehicleMaintenanceItem

Representa custos periódicos de manutenção.

Campos:

```text
id: UUID
vehicle_id: UUID
name: str
cost_brl: Decimal
interval_km: Decimal
active: bool
```

Derivação:

```text
maintenance_per_km = Σ(cost / interval_km)
```

---

# 30. Entidade AggregatedVehicleContract

Aplicável a veículo agregado.

Campos:

```text
id: UUID
vehicle_id: UUID
pricing_model: AggregatedPricingModel
price_brl: Decimal
fuel_included: bool
driver_included: bool
helper_included: bool
active: bool
```

Enum:

```text
PER_ROUTE
```

Future-ready:

```text
PER_DAY
PER_KM
```

---

# 31. Entidade Worker

Campos:

```text
id: UUID
name: str
role: WorkerRole
engagement_type: WorkerEngagementType
compensation_model: CompensationModel
compensation_value_brl: Decimal
active: bool
created_at
updated_at
```

---

# 32. WorkerRole

```text
DRIVER
HELPER
MOTORCYCLE_COURIER
```

---

# 33. WorkerEngagementType

```text
EMPLOYEE
DAY_WORKER
AGGREGATED
```

---

# 34. CompensationModel

```text
HOURLY
DAILY
PER_ROUTE
INCLUDED_IN_VEHICLE_CONTRACT
```

---

# 35. Disponibilidade

Disponibilidade não deve ser confundida com cadastro ativo.

Pode existir entidade:

```text
WorkerAvailability
```

Campos:

```text
id: UUID
worker_id: UUID
date: date
available: bool
notes?
```

Ou disponibilidade específica por operação.

A implementação pode escolher a forma mais simples, desde que a regra de domínio seja preservada.

---

# 36. Entidade City

Campos:

```text
id: UUID
name: str
country_code: str
timezone: str
srid: int
source_type: CitySourceType
dataset_version: str
active: bool
```

Enum:

```text
SYNTHETIC
OSM
GIS
OTHER
```

---

# 37. City dataset identity

Exemplo:

```text
name = Santa Aurora
dataset_version = 1.0.0
source_type = SYNTHETIC
```

A seed do gerador deve ser registrada separadamente.

---

# 38. Entidade District

Campos:

```text
id: UUID
city_id: UUID
name: str
geometry
profile: DistrictProfile?
```

Exemplos:

- Centro Histórico;
- Vila Aurora;
- Jardim das Flores;
- Parque Universitário;
- Santa Cecília;
- Vale Verde;
- Nova Esperança;
- Distrito Industrial;
- Distrito Logístico.

---

# 39. Entidade Street

Representa um corredor/logradouro lógico.

Campos:

```text
id: UUID
city_id: UUID
name: str
normalized_name: str
street_type: StreetType
active: bool
```

Uma Street pode conter muitos RoadSegments.

---

# 40. StreetType

Exemplos:

```text
STREET
AVENUE
ROAD
HIGHWAY
RING_ROAD
SERVICE_ROAD
```

A apresentação pode usar nomes locais como Rua, Avenida, Rodovia.

---

# 41. Entidade Intersection

Campos:

```text
id: UUID
city_id: UUID
location: POINT
```

Representa nó do grafo viário.

---

# 42. Entidade RoadSegment

Campos:

```text
id: UUID
street_id: UUID
from_intersection_id: UUID
to_intersection_id: UUID
geometry: LINESTRING
length_m: Decimal
speed_limit_kmh: Decimal
road_class: RoadClass
lanes: int?
active: bool
```

O grafo é dirigido.

Para via de mão dupla podem existir dois edges direcionados.

---

# 43. RoadClass

Sugestão:

```text
EXPRESSWAY
ARTERIAL
COLLECTOR
LOCAL
SERVICE
```

---

# 44. Direção

Não é obrigatório armazenar `one_way` se cada segmento já for direcionado.

Conceito recomendado:

```text
RoadSegment = edge dirigido
```

Isso simplifica routing.

---

# 45. Entidade Lot

Campos:

```text
id: UUID
district_id: UUID
geometry: POLYGON
status: LotStatus
```

Enum:

```text
OCCUPIED
VACANT
```

---

# 46. Entidade Building

Campos:

```text
id: UUID
lot_id: UUID
building_type: BuildingType
geometry: POLYGON
entrance_location: POINT
active: bool
```

---

# 47. BuildingType

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

Lote vazio não precisa de Building.

---

# 48. Entidade Address

Campos:

```text
id: UUID
street_id: UUID
house_number: str
house_number_numeric: int?
suffix: str?
district_id: UUID
building_id: UUID
location: POINT
road_segment_id: UUID
position_on_segment: Decimal
complement_default: str?
active: bool
```

---

# 49. Invariantes de Address

- existe apenas se houver entrada/edificação;
- mapeia para segmento viário específico;
- não depende apenas da interseção mais próxima;
- números podem ter gaps;
- números podem conter sufixo;
- complemento não altera o ponto de acesso rodoviário principal.

---

# 50. Entidade Facility

Representa um ponto de interesse operacional.

Campos:

```text
id: UUID
city_id: UUID
address_id: UUID
name: str
facility_type: FacilityType
active: bool
```

---

# 51. FacilityType

```text
DEPOT
HOSPITAL
CLINIC
LABORATORY
PHARMACY
WAREHOUSE
PUBLIC_FACILITY
OTHER
```

Home care normalmente usa um Address residencial, sem exigir Facility própria.

---

# 52. Entidade TrafficProfile

Representa fator temporal de trânsito.

Campos conceituais:

```text
id: UUID
city_id: UUID
district_id?
road_class?
time_bucket_start
time_bucket_end
traffic_factor
```

Pode haver perfis combinados.

---

# 53. TrafficMode

Na operação:

```text
AUTOMATIC
FREE
CUSTOM
```

---

# 54. Entidade RoadOverride

Restrição específica da revisão.

Campos:

```text
id: UUID
operation_revision_id: UUID
road_segment_id: UUID
override_type: RoadOverrideType
direction_scope: DirectionScope
traffic_factor: Decimal?
reason: RoadOverrideReason
notes?
created_by_user_id: UUID
created_at
```

---

# 55. RoadOverrideType

```text
CLOSURE
TRAFFIC
```

---

# 56. DirectionScope

```text
SEGMENT_DIRECTION
BOTH_DIRECTIONS
```

Se RoadSegment for dirigido, `SEGMENT_DIRECTION` atua apenas naquele edge.

---

# 57. RoadOverrideReason

```text
ACCIDENT
ROADWORK
EVENT
OTHER
```

---

# 58. Entidade Route

Representa uma rota planejada para um veículo.

Campos:

```text
id: UUID
optimization_run_id: UUID
vehicle_id: UUID
route_code: str
planned_start_at: datetime
planned_return_at: datetime
total_distance_km: Decimal
travel_time_minutes: int
service_time_minutes: int
total_duration_minutes: int
total_cost_brl: Decimal
weight_load_kg: Decimal
volume_load_m3: Decimal
status: RouteStatus
```

---

# 59. RouteStatus

Na V1:

```text
PLANNED
APPROVED
DISPATCHED
```

Future-ready:

```text
IN_PROGRESS
COMPLETED
FAILED
```

---

# 60. Entidade RouteStop

Representa uma parada ordenada.

Campos:

```text
id: UUID
route_id: UUID
sequence: int
stop_type: RouteStopType
delivery_id: UUID?
facility_id: UUID?
address_id: UUID
planned_arrival_at: datetime
planned_departure_at: datetime
planned_service_minutes: int
planned_load_before_kg: Decimal?
planned_load_after_kg: Decimal?
planned_volume_before_m3: Decimal?
planned_volume_after_m3: Decimal?
actual_arrival_at: datetime?
actual_departure_at: datetime?
```

---

# 61. RouteStopType

V1:

```text
DEPOT_START
DELIVERY
DEPOT_RETURN
```

Future-ready:

```text
PICKUP
```

---

# 62. Planned x Actual

Campos `actual_*` ficam `null` na V1.

Essa separação evita precisar remodelar tudo caso execução real seja adicionada no futuro.

---

# 63. Entidade RouteLeg

Opcional, mas recomendada.

Representa o trecho entre duas paradas.

Campos:

```text
id: UUID
route_id: UUID
from_stop_id: UUID
to_stop_id: UUID
distance_km: Decimal
travel_time_minutes: int
geometry
departure_time
arrival_time
```

Pode armazenar o caminho retornado pelo routing.

---

# 64. Entidade RouteAssignment

Liga rota e equipe.

Campos:

```text
id: UUID
route_id: UUID
driver_worker_id: UUID?
helper_worker_id: UUID?
motorcycle_courier_worker_id: UUID?
team_cost_brl: Decimal
helper_decision: HelperDecision
manual_override: bool
created_at
```

---

# 65. HelperDecision

```text
REQUIRED
OPTIONAL_SELECTED
OPTIONAL_NOT_SELECTED
NOT_NEEDED
FORBIDDEN
```

---

# 66. Entidade OptimizationRun

Representa uma execução do otimizador.

Campos:

```text
id: UUID
operation_revision_id: UUID
status: OptimizationRunStatus
algorithm_version: str
configuration_version: str
random_seed: int
started_at
finished_at?
elapsed_ms?
stop_reason?
generations_completed: int
total_candidates_evaluated: int
total_pruned: int
total_repaired: int
best_solution_id?
error_code?
error_message?
```

---

# 67. OptimizationRunStatus

```text
QUEUED
RUNNING
COMPLETED
FAILED
CANCELLED
INTERRUPTED
```

---

# 68. OptimizationStopReason

```text
EARLY_STOPPING
TIME_BUDGET
MAX_GENERATIONS
CONVERGED
USER_CANCELLED
FAILED
```

---

# 69. FitnessVector

Value object:

```text
feasible: bool
hard_violations: int
service_penalty: Decimal
critical_risk: Decimal
total_cost_brl: Decimal
makespan_minutes: int
travel_minutes: int
distance_km: Decimal
vehicles_used: int
```

Comparação é lexicográfica.

---

# 70. Entidade OptimizationSolution

Campos:

```text
id: UUID
optimization_run_id: UUID
rank: int
fitness_vector
is_validated: bool
created_at
```

A solução principal deve ser validada pelo `SolutionValidator`.

---

# 71. Decision Trace

Pode ser entidade pai:

```text
DecisionTrace
```

Campos:

```text
id: UUID
optimization_run_id: UUID
created_at
summary_json?
```

Eventos podem ser persistidos em tabela própria ou estrutura JSON controlada.

---

# 72. DecisionTraceEvent

Campos:

```text
id: UUID
decision_trace_id: UUID
sequence: int
event_type: DecisionTraceEventType
generation: int?
elapsed_ms: int?
payload: JSON
created_at
```

---

# 73. DecisionTraceEventType

```text
GENERATION_SNAPSHOT
PRUNING_SUMMARY
IMPROVEMENT
VEHICLE_SELECTION_REASON
ROUTE_ASSIGNMENT_CHANGE
CONSTRAINT_VIOLATION
DIVERSITY_CHANGE
FINAL_COMPARISON
```

---

# 74. PruningReason

Enum:

```text
CAPACITY_EXCEEDED
VOLUME_EXCEEDED
HARD_TIME_WINDOW_IMPOSSIBLE
RANGE_IMPOSSIBLE
REFRIGERATION_INCOMPATIBLE
TEAM_INFEASIBLE
ROAD_ACCESS_IMPOSSIBLE
END_OF_SHIFT_IMPOSSIBLE
FUTURE_INFEASIBILITY
DOMINATED_STATE
LOWER_BOUND
```

---

# 75. Entidade ReportGeneration

Campos:

```text
id: UUID
operation_revision_id: UUID
report_type: ReportType
status: ReportStatus
format: ReportFormat
generated_at?
file_reference?
error_code?
```

---

# 76. ReportType

```text
DISPATCH
DAILY_OPERATION
EXECUTIVE_SUMMARY
DRIVER_INSTRUCTIONS
```

---

# 77. ReportFormat

```text
PDF
XLSX
CSV
```

---

# 78. ReportStatus

```text
PENDING
GENERATING
COMPLETED
FAILED
```

---

# 79. Entidade AuditLog

Campos:

```text
id: UUID
user_id: UUID?
operation_id: UUID?
operation_revision_id: UUID?
action: str
entity_type: str?
entity_id: UUID?
metadata: JSON?
created_at
```

Nunca armazenar secrets.

---

# 80. Entidade SystemConfiguration

Pode armazenar apenas configurações operacionais simples.

Exemplos:

```text
fuel_price_brl
active_llm_provider
default_operation_start_time
default_operation_end_time
```

Parâmetros internos do GA devem preferencialmente usar configuração versionada de código/config file, não formulário de admin.

---

# 81. OptimizerConfiguration

Value object/versioned config.

Exemplos:

```text
version
population_size
tournament_size
elitism_rate
base_mutation_rate
max_generations
stagnation_limit
time_budget_seconds
hard_time_limit_seconds
diversity_threshold
```

Registrado em cada OptimizationRun.

---

# 82. ScenarioProfile

Para geração sintética:

```text
NORMAL
BUSY
HIGH_PRESSURE
EMERGENCY
CUSTOM
```

---

# 83. ScenarioGenerationRequest

Value object:

```text
profile
delivery_count
random_seed?
operation_date
operation_start_time
available_vehicle_ids
```

---

# 84. ScenarioGenerationResult

Contém:

```text
deliveries
validation_summary
seed
feasibility_witness_metadata
```

A witness solution não deve ser exposta como solução do usuário.

---

# 85. AddressResolutionResult

Value object:

```text
status
matched_address_id?
confidence?
suggestions[]
normalized_input
```

Status:

```text
EXACT
FUZZY_CONFIRMATION_REQUIRED
NUMBER_NOT_FOUND
AMBIGUOUS
NOT_FOUND
```

---

# 86. TravelTime

Value object:

```text
distance_m
duration_seconds
time_bucket
path?
```

---

# 87. TravelMatrixKey

Conceito de cache:

```text
origin_id
destination_id
time_bucket
graph_version
```

---

# 88. EffectiveRoadGraph

Não precisa ser entidade persistida.

É um objeto de execução construído a partir de:

```text
base city graph
+
traffic profile
+
operation road overrides
```

---

# 89. GraphVersion

Derivada de:

- dataset_version;
- traffic context;
- overrides relevantes.

Serve para evitar cache incorreto.

---

# 90. Snapshot de dispatch

Entidade sugerida:

```text
DispatchSnapshot
```

Campos:

```text
id: UUID
operation_id: UUID
operation_revision_id: UUID
created_at
created_by_user_id: UUID
snapshot_version: str
payload: JSON / structured normalized data
```

Preferência:

- preservar dados estruturados em tabelas relacionais quando útil;
- snapshot JSON pode complementar para auditoria/reprodução.

---

# 91. Imutabilidade histórica

Depois do dispatch:

- Vehicle pode ser editado no cadastro;
- Worker pode mudar;
- preço de combustível pode mudar;
- cidade pode ganhar nova versão;

mas o relatório histórico deve continuar mostrando os dados usados naquele dispatch.

---

# 92. Soft delete e inativação

Aplicar principalmente a:

```text
Vehicle
Worker
User
Facility
```

Se houver referência histórica:

```text
active = false
```

em vez de delete físico.

---

# 93. Regras de dinheiro

Todo valor monetário usa:

```text
Decimal
```

ou inteiro em centavos.

Não usar `float`.

---

# 94. Regras de unidade

Padronização:

```text
peso → kg
volume → m³
distância persistida → metros ou km explicitamente
velocidade → km/h
duração → segundos/minutos explicitamente
moeda → BRL
```

Nomes de campos devem incluir unidade quando houver risco de ambiguidade.

Exemplo:

```text
max_range_km
length_m
total_weight_kg
```

---

# 95. Regras de data e hora

- API usa ISO 8601;
- datas persistidas timezone-aware quando aplicável;
- City possui timezone;
- horários planejados são calculados no timezone da cidade.

---

# 96. Entidades que não entram na V1

Não criar agora:

```text
Patient
Prescription
MedicationSKU
InventoryLot
ProofOfDelivery
GPSPosition
PickupRequest
ChargingStation
FuelStation
DriverShiftBreak
MultiDepot
Tenant
Subscription
BillingAccount
```

Só criar quando houver requisito real.

---

# 97. Relações principais

Diagrama conceitual simplificado:

```text
User
  │
  └── creates
        │
        ▼
Operation
  │
  ├── OperationRevision
  │      ├── Delivery
  │      ├── Vehicle selections
  │      ├── Worker selections
  │      ├── RoadOverride
  │      └── OptimizationRun
  │             ├── OptimizationSolution
  │             ├── DecisionTrace
  │             └── Route
  │                    ├── RouteStop
  │                    ├── RouteLeg
  │                    └── RouteAssignment
  │
  └── DispatchSnapshot

City
  ├── District
  ├── Street
  │     └── RoadSegment
  ├── Intersection
  ├── Lot
  │     └── Building
  │            └── Address
  └── Facility

Vehicle
  ├── OwnedVehicleCostProfile
  ├── VehicleMaintenanceItem
  └── AggregatedVehicleContract

Worker
  └── WorkerAvailability
```

---

# 98. Aggregate boundaries sugeridas

Não aplicar DDD de forma rígida, mas tratar como agregados conceituais:

## Operation Aggregate

- Operation;
- Revision;
- selections;
- overrides;
- approval/dispatch state.

## Delivery Aggregate

- Delivery;
- window;
- service requirements.

## Vehicle Aggregate

- Vehicle;
- cost profile;
- maintenance;
- contract.

## Worker Aggregate

- Worker;
- compensation;
- availability.

## City Aggregate

Persistência grande e geoespacial, com entidades próprias.

---

# 99. Invariantes críticas

O domínio deve impedir:

- delivery duplicada na mesma rota;
- delivery perdida na solução final;
- veículo acima de peso;
- veículo acima de volume;
- veículo excedendo autonomia;
- carga refrigerada em veículo incompatível;
- TWO_PERSON sem equipe compatível;
- janela HARD violada;
- retorno após fim da operação;
- rota sem retorno ao depósito;
- worker em duas rotas simultaneamente;
- mesmo veículo em duas rotas simultaneamente;
- dispatch de revisão OUTDATED;
- alteração de snapshot despachado;
- custo oficial vindo da LLM.

---

# 100. Compatibilidade futura com pickup

O modelo `RouteStop` já deve permitir expansão futura.

V1:

```text
DEPOT_START
DELIVERY
DEPOT_RETURN
```

Futuro:

```text
PICKUP
```

Não implementar lógica de pickup agora.

---

# 101. Compatibilidade futura com execução

Campos `actual_*` podem existir ou ser previstos.

Não implementar:

- tracking;
- GPS;
- completion events.

Apenas evitar nomes que tornem futura evolução impossível.

---

# 102. Nomenclatura

Código-fonte pode usar inglês.

Exemplos:

```text
Operation
Delivery
Vehicle
Worker
Route
RoadSegment
OptimizationRun
```

Interface pode usar português.

Essa separação é recomendada para consistência técnica.

---

# 103. Regras para ORM

ORM deve mapear o domínio, não ditá-lo.

Evitar regras como:

```text
if model.column_x ...
```

espalhadas pela aplicação.

Validação importante deve existir em serviços/entidades/value objects.

---

# 104. Regras para Pydantic

Pydantic valida fronteira de API.

Não usar schemas Pydantic como substitutos universais das entidades internas.

---

# 105. Regras para JSON

JSON é apropriado para:

- metadata;
- Decision Trace payload;
- snapshots complementares;
- configurações versionadas.

Não usar JSON para evitar modelar entidades claramente relacionais.

---

# 106. Regras de versionamento de dataset

Cada operação otimizada deve conhecer a versão da cidade.

Exemplo:

```text
Santa Aurora 1.0.0
```

Isso ajuda reprodução de benchmark e histórico.

---

# 107. Regras de versionamento do algoritmo

Cada run registra:

```text
algorithm_version
configuration_version
random_seed
```

Isso permite reproduzir e explicar resultados.

---

# 108. Consistência entre docs e implementação

Ao implementar uma entidade:

1. comparar com este documento;
2. não adicionar campo por conveniência sem necessidade;
3. se o domínio mudar, atualizar este documento;
4. mudanças grandes podem gerar ADR.

---

# 109. Definition of Done do domínio

O modelo de domínio está corretamente implementado quando:

- entidades principais existem;
- invariantes críticas têm testes;
- enums são centralizados;
- dinheiro não usa float;
- UUID é usado como identidade técnica;
- histórico é preservado;
- domínio não importa frameworks externos;
- SolutionValidator consegue validar uma solução sem depender da API.

---

# 110. Regra final

> O modelo de domínio deve representar a operação logística que o FluxMed precisa planejar, e não detalhes de frameworks, telas ou banco de dados.

A prioridade é preservar clareza, invariantes e rastreabilidade.
