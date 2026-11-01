# FluxMed — Contrato HTTP da API

A API implementada utiliza FastAPI, JSON e Server-Sent Events. O prefixo funcional é `/api/v1`; os health checks usam `/health`. Este guia descreve as 68 operações HTTP registradas pela aplicação. A estrutura detalhada de campos, limites, enums e respostas está no OpenAPI gerado pelo mesmo código.

Com a API em execução, consulte `/docs` e `/openapi.json` na porta 8000. As fontes são [`main.py`](../apps/api/src/fluxmed/main.py) e os [routers e schemas](../apps/api/src/fluxmed/api/v1/).

## Autenticação e convenções

O login recebe `LoginRequest` e grava uma sessão em cookie HTTP-only. As requisições seguintes enviam esse cookie; o backend verifica a sessão persistida e as permissões da ação. O cookie usa SameSite configurável e Secure em ambiente de produção. Logout encerra a sessão correspondente e remove o cookie. Login e health checks permitem o acesso necessário à inicialização; os recursos operacionais exigem autenticação.

UUIDs identificam entidades. Datas, horas e timestamps usam os formatos declarados no schema; o planejamento usa o fuso da cidade. Campos monetários e quantitativos do domínio usam `Decimal`; o contrato de cada resposta determina sua serialização. Listas paginadas declaram `page` e `page_size`; outras consultas retornam listas diretamente.

As tabelas abaixo mostram o sucesso declarado de cada operação. Erros de autenticação, permissão, conflito e dados indisponíveis dependem da ação. Parâmetros ou corpos inválidos são tratados pela validação do FastAPI, normalmente com status 422.

## Endpoints implementados

### auth

| Operação | Corpo | Sucesso |
|---|---|---|
| `POST /api/v1/auth/login` | LoginRequest | 200: LoginResponse |
| `POST /api/v1/auth/logout` | Sem corpo | 204: sem corpo |
| `GET /api/v1/auth/me` | Sem corpo | 200: UserResponse |

### cities

| Operação | Corpo | Sucesso |
|---|---|---|
| `GET /api/v1/cities` | Sem corpo | 200: lista de CityResponse |
| `GET /api/v1/cities/{city_id}` | Sem corpo | 200: CityResponse |
| `GET /api/v1/cities/{city_id}/districts` | Sem corpo | 200: lista de DistrictResponse |
| `GET /api/v1/cities/{city_id}/addresses/search` | Sem corpo | 200: AddressSearchResponse |
| `GET /api/v1/cities/{city_id}/facilities` | Sem corpo | 200: lista de FacilityResponse |
| `GET /api/v1/cities/{city_id}/map` | Sem corpo | 200: object |

### operations

| Operação | Corpo | Sucesso |
|---|---|---|
| `GET /api/v1/operations` | Sem corpo | 200: OperationListResponse |
| `POST /api/v1/operations` | OperationCreateRequest | 201: OperationResponse |
| `GET /api/v1/operations/{operation_id}` | Sem corpo | 200: OperationResponse |
| `PATCH /api/v1/operations/{operation_id}` | OperationUpdateRequest | 200: OperationResponse |
| `POST /api/v1/operations/{operation_id}/dispatch` | Sem corpo | 200: OperationResponse |
| `POST /api/v1/operations/{operation_id}/validate` | Sem corpo | 200: PreflightResponse |

### deliveries

| Operação | Corpo | Sucesso |
|---|---|---|
| `GET /api/v1/deliveries` | Sem corpo | 200: DeliveryListResponse |
| `GET /api/v1/deliveries/{delivery_id}` | Sem corpo | 200: DeliveryResponse |
| `GET /api/v1/operations/{operation_id}/deliveries` | Sem corpo | 200: DeliveryListResponse |
| `POST /api/v1/operations/{operation_id}/deliveries` | DeliveryCreateRequest | 201: DeliveryResponse |
| `PATCH /api/v1/operations/{operation_id}/deliveries/{delivery_id}` | DeliveryUpdateRequest | 200: DeliveryResponse |
| `DELETE /api/v1/operations/{operation_id}/deliveries/{delivery_id}` | Sem corpo | 204: sem corpo |
| `POST /api/v1/operations/{operation_id}/generate-scenario` | ScenarioRequest | 200: ScenarioResponse |
| `POST /api/v1/operations/{operation_id}/delivery-imports` | multipart: Body_create_delivery_import_api_v1_operations__operation_id__delivery_imports_post | 201: DeliveryImportResponse |
| `GET /api/v1/delivery-imports/{import_id}` | Sem corpo | 200: DeliveryImportResponse |
| `DELETE /api/v1/delivery-imports/{import_id}` | Sem corpo | 204: sem corpo |
| `POST /api/v1/delivery-imports/{import_id}/confirm` | Sem corpo | 200: DeliveryImportResponse |

### resources

| Operação | Corpo | Sucesso |
|---|---|---|
| `GET /api/v1/vehicles` | Sem corpo | 200: lista de VehicleResponse |
| `POST /api/v1/vehicles` | VehicleCreateRequest | 201: VehicleResponse |
| `GET /api/v1/vehicles/{vehicle_id}` | Sem corpo | 200: VehicleResponse |
| `PATCH /api/v1/vehicles/{vehicle_id}` | VehicleUpdateRequest | 200: VehicleResponse |
| `PUT /api/v1/vehicles/{vehicle_id}/cost-profile` | VehicleCostUpdateRequest | 200: VehicleResponse |
| `POST /api/v1/vehicles/{vehicle_id}/deactivate` | Sem corpo | 200: VehicleResponse |
| `GET /api/v1/workers` | Sem corpo | 200: lista de WorkerResponse |
| `POST /api/v1/workers` | WorkerCreateRequest | 201: WorkerResponse |
| `GET /api/v1/workers/{worker_id}` | Sem corpo | 200: WorkerResponse |
| `PATCH /api/v1/workers/{worker_id}` | WorkerUpdateRequest | 200: WorkerResponse |
| `POST /api/v1/workers/{worker_id}/deactivate` | Sem corpo | 200: WorkerResponse |
| `GET /api/v1/workers/{worker_id}/availability` | Sem corpo | 200: WorkerAvailabilityResponse |
| `PUT /api/v1/workers/{worker_id}/availability` | WorkerAvailabilityRequest | 200: WorkerAvailabilityResponse |
| `GET /api/v1/operations/{operation_id}/resources` | Sem corpo | 200: OperationResourcesResponse |
| `PUT /api/v1/operations/{operation_id}/resources` | OperationResourceSelectionRequest | 200: OperationResourcesResponse |
| `POST /api/v1/operations/{operation_id}/resources/demo` | Sem corpo | 200: OperationResourcesResponse |

### routing

| Operação | Corpo | Sucesso |
|---|---|---|
| `GET /api/v1/operations/{operation_id}/road-overrides` | Sem corpo | 200: lista de RoadOverrideResponse |
| `POST /api/v1/operations/{operation_id}/road-overrides` | RoadOverrideCreateRequest | 201: RoadOverrideResponse |
| `PATCH /api/v1/operations/{operation_id}/road-overrides/{override_id}` | RoadOverrideUpdateRequest | 200: RoadOverrideResponse |
| `DELETE /api/v1/operations/{operation_id}/road-overrides/{override_id}` | Sem corpo | 204: sem corpo |
| `POST /api/v1/operations/{operation_id}/route-preview` | RoutePreviewRequest | 200: RoutePreviewResponse |

### optimization

| Operação | Corpo | Sucesso |
|---|---|---|
| `POST /api/v1/operations/{operation_id}/optimize` | OptimizeRequest | 202: OptimizeAcceptedResponse |
| `GET /api/v1/operations/{operation_id}/optimization-runs/latest-run` | Sem corpo | 200: OptimizationRunResponse |
| `GET /api/v1/optimization-runs/{run_id}` | Sem corpo | 200: OptimizationRunResponse |
| `GET /api/v1/optimization-runs/{run_id}/trace` | Sem corpo | 200: lista de OptimizationTraceEventResponse |
| `GET /api/v1/optimization-runs/{run_id}/events` | Sem corpo | 200: SSE |
| `POST /api/v1/optimization-runs/{run_id}/cancel` | Sem corpo | 200: OptimizationRunResponse |
| `GET /api/v1/operations/{operation_id}/optimization-runs/latest` | Sem corpo | 200: OptimizationResultResponse |
| `GET /api/v1/optimization-runs/{run_id}/result` | Sem corpo | 200: OptimizationResultResponse |
| `GET /api/v1/routes/{route_id}` | Sem corpo | 200: RouteResultResponse |
| `POST /api/v1/optimization-runs/{run_id}/approve` | Sem corpo | 200: OptimizationResultResponse |
| `POST /api/v1/routes/{route_id}/team-simulation` | TeamSimulationRequest | 200: TeamSimulationResponse |
| `PUT /api/v1/routes/{route_id}/team` | TeamSimulationRequest | 200: TeamSimulationResponse |

### reports

| Operação | Corpo | Sucesso |
|---|---|---|
| `GET /api/v1/reports` | Sem corpo | 200: ReportListResponse |
| `POST /api/v1/operations/{operation_id}/reports` | ReportCreateRequest | 202: ReportResponse |
| `POST /api/v1/reports/{report_id}/retry` | Sem corpo | 202: ReportResponse |
| `GET /api/v1/reports/{report_id}` | Sem corpo | 200: ReportResponse |
| `GET /api/v1/reports/{report_id}/download` | Sem corpo | 200: arquivo PDF, XLSX ou CSV |

### assistant

| Operação | Corpo | Sucesso |
|---|---|---|
| `GET /api/v1/assistant/status` | Sem corpo | 200: AssistantStatusResponse |
| `POST /api/v1/assistant/messages` | AssistantMessageRequest | 200: AssistantMessageResponse |

### health

| Operação | Corpo | Sucesso |
|---|---|---|
| `GET /health/live` | Sem corpo | 200: object |
| `GET /health/ready` | Sem corpo | 200: object |

## Parâmetros de consulta

Os parâmetros de caminho são os UUIDs indicados nas rotas. A tabela reúne os parâmetros de consulta e seus defaults; os limites numéricos e os valores de enum são definidos pelo schema OpenAPI.

| Operação | Parâmetros de consulta |
|---|---|
| `GET /api/v1/cities/{city_id}/addresses/search` | `q`: string; obrigatório; `limit`: integer; padrão `8` |
| `GET /api/v1/operations` | `page`: integer; padrão `1`; `page_size`: integer; padrão `20`; `status`: OperationStatus ou null; `date_from`: string (date) ou null; `date_to`: string (date) ou null; `q`: string ou null; `sort`: string com formato validado; padrão `"updated_at"`; `order`: string com formato validado; padrão `"desc"` |
| `GET /api/v1/deliveries` | `page`: integer; padrão `1`; `page_size`: integer; padrão `20`; `operation_id`: string (uuid) ou null; `priority`: DeliveryPriority ou null; `temperature_class`: TemperatureClass ou null; `status`: DeliveryStatus ou null; `district_id`: string (uuid) ou null; `q`: string ou null |
| `GET /api/v1/operations/{operation_id}/deliveries` | `page`: integer; padrão `1`; `page_size`: integer; padrão `100` |
| `GET /api/v1/vehicles` | `active`: boolean ou null; `status`: VehicleStatus ou null; `refrigerated`: boolean ou null; `q`: string ou null |
| `GET /api/v1/workers` | `active`: boolean ou null; `role`: WorkerRole ou null; `q`: string ou null |
| `GET /api/v1/workers/{worker_id}/availability` | `date`: string (date); obrigatório |
| `GET /api/v1/optimization-runs/{run_id}/events` | `after`: integer; padrão `0` |
| `GET /api/v1/reports` | `operation_id`: string (uuid) ou null |

## Corpos de requisição

Os modelos abaixo são os schemas de entrada usados pelas rotas. Campos obrigatórios são exigidos pela validação estrutural; regras de domínio e permissões são verificadas pelo serviço da ação. `null` representa um valor nulo, e não a ausência de um campo obrigatório. Modelos citados em outros campos são detalhados no OpenAPI.

### AggregatedVehicleContractRequest

| Campo | Tipo | Obrigatório | Padrão |
|---|---|---|---|
| `price_brl` | number ou string decimal | Sim | Sem default declarado |
| `pricing_model` | AggregatedPricingModel | Não | `"PER_ROUTE"` |
| `fuel_included` | boolean | Não | `false` |
| `driver_included` | boolean | Não | `false` |
| `helper_included` | boolean | Não | `false` |

### AssistantContextRequest

| Campo | Tipo | Obrigatório | Padrão |
|---|---|---|---|
| `operation_id` | string (uuid) ou null | Não | Sem default declarado |
| `route_id` | string (uuid) ou null | Não | Sem default declarado |
| `delivery_id` | string (uuid) ou null | Não | Sem default declarado |

### AssistantHistoryMessageRequest

| Campo | Tipo | Obrigatório | Padrão |
|---|---|---|---|
| `role` | string | Sim | Sem default declarado |
| `content` | string | Sim | Sem default declarado |

### AssistantMessageRequest

| Campo | Tipo | Obrigatório | Padrão |
|---|---|---|---|
| `message` | string | Sim | Sem default declarado |
| `context` | AssistantContextRequest | Não | Sem default declarado |
| `history` | lista de AssistantHistoryMessageRequest | Não | Sem default declarado |

### DeliveryCreateRequest

| Campo | Tipo | Obrigatório | Padrão |
|---|---|---|---|
| `invoice_number` | string | Sim | Sem default declarado |
| `invoice_series` | string | Sim | Sem default declarado |
| `issuer_document` | string | Sim | Sem default declarado |
| `issuer_name` | string ou null | Não | Sem default declarado |
| `external_reference` | string ou null | Não | Sem default declarado |
| `recipient_name` | string | Sim | Sem default declarado |
| `destination_address_id` | string (uuid) | Sim | Sem default declarado |
| `package_count` | integer | Sim | Sem default declarado |
| `total_weight_kg` | number ou string decimal | Sim | Sem default declarado |
| `total_volume_m3` | number ou string decimal | Sim | Sem default declarado |
| `priority` | DeliveryPriority | Não | `"NORMAL"` |
| `time_window_start` | string (date-time) ou null | Não | Sem default declarado |
| `time_window_end` | string (date-time) ou null | Não | Sem default declarado |
| `time_window_policy` | TimeWindowPolicy | Não | `"SOFT"` |
| `temperature_class` | TemperatureClass | Não | `"AMBIENT"` |
| `handling_requirement` | HandlingRequirement | Não | `"STANDARD"` |
| `service_time_minutes` | integer ou null | Não | Sem default declarado |
| `cargo_profile` | CargoProfile ou null | Não | Sem default declarado |
| `notes` | string ou null | Não | Sem default declarado |

### DeliveryUpdateRequest

| Campo | Tipo | Obrigatório | Padrão |
|---|---|---|---|
| `invoice_number` | string ou null | Não | Sem default declarado |
| `invoice_series` | string ou null | Não | Sem default declarado |
| `issuer_document` | string ou null | Não | Sem default declarado |
| `issuer_name` | string ou null | Não | Sem default declarado |
| `external_reference` | string ou null | Não | Sem default declarado |
| `recipient_name` | string ou null | Não | Sem default declarado |
| `destination_address_id` | string (uuid) ou null | Não | Sem default declarado |
| `package_count` | integer ou null | Não | Sem default declarado |
| `total_weight_kg` | number ou string decimal ou null | Não | Sem default declarado |
| `total_volume_m3` | number ou string decimal ou null | Não | Sem default declarado |
| `priority` | DeliveryPriority ou null | Não | Sem default declarado |
| `time_window_start` | string (date-time) ou null | Não | Sem default declarado |
| `time_window_end` | string (date-time) ou null | Não | Sem default declarado |
| `time_window_policy` | TimeWindowPolicy ou null | Não | Sem default declarado |
| `temperature_class` | TemperatureClass ou null | Não | Sem default declarado |
| `handling_requirement` | HandlingRequirement ou null | Não | Sem default declarado |
| `service_time_minutes` | integer ou null | Não | Sem default declarado |
| `cargo_profile` | CargoProfile ou null | Não | Sem default declarado |
| `notes` | string ou null | Não | Sem default declarado |

### LoginRequest

| Campo | Tipo | Obrigatório | Padrão |
|---|---|---|---|
| `email` | string | Sim | Sem default declarado |
| `password` | string | Sim | Sem default declarado |

### MaintenanceItemRequest

| Campo | Tipo | Obrigatório | Padrão |
|---|---|---|---|
| `name` | string | Sim | Sem default declarado |
| `cost_brl` | number ou string decimal | Sim | Sem default declarado |
| `interval_km` | number ou string decimal | Sim | Sem default declarado |
| `active` | boolean | Não | `true` |

### OperationCreateRequest

| Campo | Tipo | Obrigatório | Padrão |
|---|---|---|---|
| `operation_date` | string (date) | Sim | Sem default declarado |
| `operation_start_time` | string (time) | Sim | Sem default declarado |
| `operation_end_time` | string (time) | Sim | Sem default declarado |
| `traffic_mode` | TrafficMode | Não | `"AUTOMATIC"` |

### OperationResourceSelectionRequest

| Campo | Tipo | Obrigatório | Padrão |
|---|---|---|---|
| `vehicle_ids` | lista de string (uuid) | Não | Sem default declarado |
| `worker_ids` | lista de string (uuid) | Não | Sem default declarado |

### OperationUpdateRequest

| Campo | Tipo | Obrigatório | Padrão |
|---|---|---|---|
| `operation_date` | string (date) ou null | Não | Sem default declarado |
| `operation_start_time` | string (time) ou null | Não | Sem default declarado |
| `operation_end_time` | string (time) ou null | Não | Sem default declarado |
| `traffic_mode` | TrafficMode ou null | Não | Sem default declarado |

### OptimizeRequest

| Campo | Tipo | Obrigatório | Padrão |
|---|---|---|---|
| `random_seed` | integer ou null | Não | Sem default declarado |

### OwnedVehicleCostRequest

| Campo | Tipo | Obrigatório | Padrão |
|---|---|---|---|
| `acquisition_value_brl` | number ou string decimal | Sim | Sem default declarado |
| `residual_value_brl` | number ou string decimal | Sim | Sem default declarado |
| `useful_life_km` | number ou string decimal | Sim | Sem default declarado |
| `annual_ipva_brl` | number ou string decimal | Sim | Sem default declarado |
| `annual_insurance_brl` | number ou string decimal | Sim | Sem default declarado |
| `annual_fixed_costs_brl` | number ou string decimal | Sim | Sem default declarado |
| `expected_productive_hours_per_year` | number ou string decimal | Sim | Sem default declarado |
| `maintenance_items` | lista de MaintenanceItemRequest | Não | Sem default declarado |

### ReportCreateRequest

| Campo | Tipo | Obrigatório | Padrão |
|---|---|---|---|
| `report_type` | string | Não | `"DAILY_OPERATION"` |
| `format` | string | Sim | Sem default declarado |

### RoadOverrideCreateRequest

| Campo | Tipo | Obrigatório | Padrão |
|---|---|---|---|
| `road_segment_id` | string (uuid) | Sim | Sem default declarado |
| `override_type` | RoadOverrideType | Sim | Sem default declarado |
| `direction_scope` | RoadOverrideDirectionScope | Não | `"SEGMENT_DIRECTION"` |
| `traffic_level` | TrafficLevel ou null | Não | Sem default declarado |
| `reason` | string | Sim | Sem default declarado |
| `notes` | string ou null | Não | Sem default declarado |

### RoadOverrideUpdateRequest

| Campo | Tipo | Obrigatório | Padrão |
|---|---|---|---|
| `traffic_level` | TrafficLevel ou null | Não | Sem default declarado |
| `reason` | string ou null | Não | Sem default declarado |
| `notes` | string ou null | Não | Sem default declarado |

### RoutePreviewRequest

| Campo | Tipo | Obrigatório | Padrão |
|---|---|---|---|
| `destination_address_id` | string (uuid) | Sim | Sem default declarado |
| `departure_time` | string (time) ou null | Não | Sem default declarado |
| `algorithm` | RoutingAlgorithm | Não | `"ASTAR"` |

### ScenarioRequest

| Campo | Tipo | Obrigatório | Padrão |
|---|---|---|---|
| `profile` | ScenarioProfile | Não | `"NORMAL"` |
| `delivery_count` | integer | Não | `20` |
| `random_seed` | integer ou null | Não | Sem default declarado |

### TeamSimulationRequest

| Campo | Tipo | Obrigatório | Padrão |
|---|---|---|---|
| `primary_worker_id` | string (uuid) ou null | Não | Sem default declarado |
| `helper_worker_id` | string (uuid) ou null | Não | Sem default declarado |

### VehicleCostUpdateRequest

| Campo | Tipo | Obrigatório | Padrão |
|---|---|---|---|
| `owned_cost` | OwnedVehicleCostRequest ou null | Não | Sem default declarado |
| `aggregated_contract` | AggregatedVehicleContractRequest ou null | Não | Sem default declarado |

### VehicleCreateRequest

| Campo | Tipo | Obrigatório | Padrão |
|---|---|---|---|
| `plate` | string | Sim | Sem default declarado |
| `type` | VehicleType | Sim | Sem default declarado |
| `ownership_type` | VehicleOwnershipType | Sim | Sem default declarado |
| `max_payload_kg` | number ou string decimal | Sim | Sem default declarado |
| `max_volume_m3` | number ou string decimal | Sim | Sem default declarado |
| `max_range_km` | number ou string decimal | Sim | Sem default declarado |
| `refrigerated` | boolean | Não | `false` |
| `status` | VehicleStatus | Não | `"AVAILABLE"` |
| `helper_policy` | HelperPolicy | Não | `"OPTIONAL"` |
| `fuel_type` | FuelType ou null | Não | Sem default declarado |
| `fuel_efficiency_km_per_l` | number ou string decimal ou null | Não | Sem default declarado |
| `owned_cost` | OwnedVehicleCostRequest ou null | Não | Sem default declarado |
| `aggregated_contract` | AggregatedVehicleContractRequest ou null | Não | Sem default declarado |

### VehicleUpdateRequest

| Campo | Tipo | Obrigatório | Padrão |
|---|---|---|---|
| `plate` | string ou null | Não | Sem default declarado |
| `type` | VehicleType ou null | Não | Sem default declarado |
| `max_payload_kg` | number ou string decimal ou null | Não | Sem default declarado |
| `max_volume_m3` | number ou string decimal ou null | Não | Sem default declarado |
| `max_range_km` | number ou string decimal ou null | Não | Sem default declarado |
| `refrigerated` | boolean ou null | Não | Sem default declarado |
| `status` | VehicleStatus ou null | Não | Sem default declarado |
| `helper_policy` | HelperPolicy ou null | Não | Sem default declarado |
| `fuel_type` | FuelType ou null | Não | Sem default declarado |
| `fuel_efficiency_km_per_l` | number ou string decimal ou null | Não | Sem default declarado |

### WorkerAvailabilityRequest

| Campo | Tipo | Obrigatório | Padrão |
|---|---|---|---|
| `date` | string (date) | Sim | Sem default declarado |
| `available` | boolean | Sim | Sem default declarado |
| `notes` | string ou null | Não | Sem default declarado |

### WorkerCreateRequest

| Campo | Tipo | Obrigatório | Padrão |
|---|---|---|---|
| `name` | string | Sim | Sem default declarado |
| `role` | WorkerRole | Sim | Sem default declarado |
| `engagement_type` | WorkerEngagementType | Sim | Sem default declarado |
| `compensation_model` | CompensationModel | Sim | Sem default declarado |
| `compensation_value_brl` | number ou string decimal | Sim | Sem default declarado |

### WorkerUpdateRequest

| Campo | Tipo | Obrigatório | Padrão |
|---|---|---|---|
| `name` | string ou null | Não | Sem default declarado |
| `role` | WorkerRole ou null | Não | Sem default declarado |
| `engagement_type` | WorkerEngagementType ou null | Não | Sem default declarado |
| `compensation_model` | CompensationModel ou null | Não | Sem default declarado |
| `compensation_value_brl` | number ou string decimal ou null | Não | Sem default declarado |

## Exemplos estruturais

Criação de operação (`OperationCreateRequest`):

```json
{
  "operation_date": "2026-09-15",
  "operation_start_time": "07:30:00",
  "operation_end_time": "18:00:00",
  "traffic_mode": "AUTOMATIC"
}
```

Otimização (`OptimizeRequest`) de uma operação com entregas e recursos já selecionados:

```json
{
  "random_seed": 101
}
```

Esses corpos são exemplos sintéticos validados pelos modelos de entrada. A existência dos recursos e a viabilidade da operação são verificações de domínio feitas ao executar a ação.

## Otimização, resultado e equipe

O POST de otimização retorna `202 Accepted` com `optimization_run_id`, estado e URLs de resultado, status e eventos. O run é persistido antes de ser encaminhado ao coordenador em processo. O resultado concluído passa pela validação independente, atribuição efetiva de equipe e cálculo de custo antes da conclusão transacional.

`latest-run` retorna os dados do run mais recente; `latest` consulta o resultado operacional. Aprovação recebe o ID do run. Despacho recebe o ID da operação e congela a revisão. A simulação de equipe calcula o impacto sem aplicar; o PUT da equipe aplica a atribuição quando permitida pelas regras do plano.

O stream de eventos usa `text/event-stream`, sequência persistida e os campos SSE `id`, `event` e `data`. A retomada usa `Last-Event-ID` ou `after`; o cabeçalho válido prevalece. Há mensagem de retry, keep-alive e encerramento após o estado terminal e o consumo dos eventos. Veja [Decision Trace](OPTIMIZATION_TRACE.md).

## Upload, relatórios e assistente

A importação de entregas usa `multipart/form-data` com o campo `file`; a confirmação da importação é uma ação separada. O download de relatórios devolve o arquivo persistido no formato solicitado, com nome e MIME type apropriados. Criação e retry retornam 202; a geração atual é síncrona na requisição e preserva o snapshot, conforme [REPORTS.md](REPORTS.md).

O assistente recebe `AssistantMessageRequest`, com mensagem, contexto e histórico. As consultas e simulações são limitadas ao contexto autorizado. O status informa configuração do provider; a evidência de uma resposta externa depende da requisição de mensagem. Veja [LLM_IMPLEMENTATION.md](LLM_IMPLEMENTATION.md).

## Erros e disponibilidade

Erros de aplicação tratados por `ApiError` usam o envelope:

```json
{
  "error": {
    "code": "DATABASE_UNAVAILABLE",
    "message": "Serviço de dados temporariamente indisponível.",
    "details": {}
  }
}
```

Esse exemplo corresponde ao tratamento de indisponibilidade de dados, com status 503. Erros estruturais de validação mantêm o formato do FastAPI (`detail`). Erros internos são sanitizados e podem incluir `request_id` para correlação; a API retorna `X-Request-ID` nas respostas do middleware.

`/health/live` informa vida do processo. `/health/ready` verifica o banco e pode responder 503 quando indisponível. O health check não executa otimização nem uma chamada de LLM.

## Fontes do contrato

- [Routers e modelos de entrada/saída](../apps/api/src/fluxmed/api/v1/).
- [Dependências de autenticação](../apps/api/src/fluxmed/api/dependencies.py).
- [Tratamento de erros](../apps/api/src/fluxmed/api/errors.py).
- [Configuração do cookie e limites HTTP](../apps/api/src/fluxmed/security/http.py).
- [Modelo de domínio](DOMAIN_MODEL.md) e [arquitetura](ARCHITECTURE.md).
