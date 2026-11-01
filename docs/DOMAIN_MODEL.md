# FluxMed — modelo persistido e tipos

Este guia reúne o modelo SQL e os tipos usados pelo planejamento. As tabelas descrevem persistência PostgreSQL; os campos HTTP e sua serialização pertencem ao [contrato da API](API_SPEC.md).

## Entidades e vínculos

Operações e revisões vinculam entregas, seleção de recursos e runs. Os runs vinculam planos de rota, paradas, equipes e eventos. Relatórios guardam o snapshot do resultado. O catálogo de Santa Aurora mantém os vínculos geográficos.

### AddressModel

Persistência: `addresses`, classe `AddressModel`.

| Campo | Tipo SQL | Aceita nulo | Chave |
|---|---|---|---|
| `id` | `UUID` | Não | PK |
| `city_id` | `UUID` | Não | FK cities.id |
| `street_id` | `UUID` | Não | FK streets.id |
| `district_id` | `UUID` | Não | FK districts.id |
| `building_id` | `UUID` | Não | FK buildings.id |
| `road_segment_id` | `UUID` | Não | FK road_segments.id |
| `house_number` | `VARCHAR(16)` | Não | — |
| `house_number_numeric` | `INTEGER` | Não | — |
| `suffix` | `VARCHAR(4)` | Sim | — |
| `complement` | `VARCHAR(80)` | Sim | — |
| `position_on_segment` | `FLOAT` | Não | — |
| `location` | `geometry(POINT,4326)` | Não | — |
| `active` | `BOOLEAN` | Não | — |

### AggregatedVehicleContractModel

Persistência: `aggregated_vehicle_contracts`, classe `AggregatedVehicleContractModel`.

| Campo | Tipo SQL | Aceita nulo | Chave |
|---|---|---|---|
| `id` | `UUID` | Não | PK |
| `vehicle_id` | `UUID` | Não | FK vehicles.id |
| `pricing_model` | `aggregated_pricing_model` | Não | — |
| `price_brl` | `NUMERIC(12, 2)` | Não | — |
| `fuel_included` | `BOOLEAN` | Não | — |
| `driver_included` | `BOOLEAN` | Não | — |
| `helper_included` | `BOOLEAN` | Não | — |
| `active` | `BOOLEAN` | Não | — |

### AssistantTelemetryModel

Persistência: `assistant_telemetry`, classe `AssistantTelemetryModel`.

| Campo | Tipo SQL | Aceita nulo | Chave |
|---|---|---|---|
| `id` | `UUID` | Não | PK |
| `request_id` | `UUID` | Não | — |
| `user_id` | `UUID` | Não | FK users.id |
| `operation_id` | `UUID` | Sim | FK operations.id |
| `provider` | `VARCHAR(40)` | Não | — |
| `model` | `VARCHAR(160)` | Não | — |
| `latency_ms` | `INTEGER` | Não | — |
| `input_tokens` | `INTEGER` | Não | — |
| `output_tokens` | `INTEGER` | Não | — |
| `tool_calls` | `JSONB` | Não | — |
| `tool_failures` | `INTEGER` | Não | — |
| `status` | `VARCHAR(24)` | Não | — |
| `fallback_used` | `BOOLEAN` | Não | — |
| `error_code` | `VARCHAR(80)` | Sim | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Não | — |

### AuthSessionModel

Persistência: `auth_sessions`, classe `AuthSessionModel`.

| Campo | Tipo SQL | Aceita nulo | Chave |
|---|---|---|---|
| `id` | `UUID` | Não | PK |
| `user_id` | `UUID` | Não | FK users.id |
| `token_hash` | `VARCHAR(64)` | Não | — |
| `expires_at` | `TIMESTAMP WITH TIME ZONE` | Não | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Não | — |

### BuildingModel

Persistência: `buildings`, classe `BuildingModel`.

| Campo | Tipo SQL | Aceita nulo | Chave |
|---|---|---|---|
| `id` | `UUID` | Não | PK |
| `city_id` | `UUID` | Não | FK cities.id |
| `district_id` | `UUID` | Não | FK districts.id |
| `lot_id` | `UUID` | Não | FK lots.id |
| `building_type` | `building_type` | Não | — |
| `entrance_location` | `geometry(POINT,4326)` | Não | — |

### CityModel

Persistência: `cities`, classe `CityModel`.

| Campo | Tipo SQL | Aceita nulo | Chave |
|---|---|---|---|
| `id` | `UUID` | Não | PK |
| `name` | `VARCHAR(120)` | Não | — |
| `country` | `VARCHAR(80)` | Não | — |
| `source_type` | `city_source_type` | Não | — |
| `timezone` | `VARCHAR(80)` | Não | — |
| `dataset_version` | `VARCHAR(32)` | Não | — |
| `generation_seed` | `INTEGER` | Não | — |
| `generator_version` | `VARCHAR(64)` | Não | — |
| `boundary` | `geometry(POLYGON,4326)` | Não | — |
| `river_geometry` | `geometry(LINESTRING,4326)` | Não | — |
| `depot_name` | `VARCHAR(160)` | Não | — |
| `depot_geometry` | `geometry(POINT,4326)` | Não | — |

### DeliveryModel

Persistência: `deliveries`, classe `DeliveryModel`.

| Campo | Tipo SQL | Aceita nulo | Chave |
|---|---|---|---|
| `id` | `UUID` | Não | PK |
| `delivery_code` | `VARCHAR(64)` | Não | — |
| `operation_id` | `UUID` | Não | FK operations.id |
| `invoice_number` | `VARCHAR(80)` | Não | — |
| `invoice_series` | `VARCHAR(40)` | Não | — |
| `issuer_document` | `VARCHAR(40)` | Não | — |
| `issuer_name` | `VARCHAR(180)` | Sim | — |
| `external_reference` | `VARCHAR(120)` | Sim | — |
| `destination_address_id` | `UUID` | Não | FK addresses.id |
| `recipient_name` | `VARCHAR(180)` | Não | — |
| `package_count` | `INTEGER` | Não | — |
| `total_weight_kg` | `NUMERIC(12, 3)` | Não | — |
| `total_volume_m3` | `NUMERIC(12, 4)` | Não | — |
| `priority` | `delivery_priority` | Não | — |
| `time_window_start` | `TIMESTAMP WITH TIME ZONE` | Sim | — |
| `time_window_end` | `TIMESTAMP WITH TIME ZONE` | Sim | — |
| `time_window_policy` | `time_window_policy` | Não | — |
| `service_time_minutes` | `INTEGER` | Não | — |
| `service_time_source` | `service_time_source` | Não | — |
| `temperature_class` | `temperature_class` | Não | — |
| `handling_requirement` | `handling_requirement` | Não | — |
| `status` | `delivery_status` | Não | — |
| `cargo_profile` | `cargo_profile` | Sim | — |
| `notes` | `TEXT` | Sim | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Não | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | Não | — |

### DeliveryImportModel

Persistência: `delivery_imports`, classe `DeliveryImportModel`.

| Campo | Tipo SQL | Aceita nulo | Chave |
|---|---|---|---|
| `id` | `UUID` | Não | PK |
| `operation_id` | `UUID` | Não | FK operations.id |
| `created_by_user_id` | `UUID` | Não | FK users.id |
| `filename` | `VARCHAR(255)` | Não | — |
| `file_type` | `VARCHAR(16)` | Não | — |
| `status` | `VARCHAR(24)` | Não | — |
| `total_rows` | `INTEGER` | Não | — |
| `valid_rows` | `INTEGER` | Não | — |
| `warning_rows` | `INTEGER` | Não | — |
| `error_rows` | `INTEGER` | Não | — |
| `rows_json` | `JSONB` | Não | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Não | — |
| `confirmed_at` | `TIMESTAMP WITH TIME ZONE` | Sim | — |

### DistrictModel

Persistência: `districts`, classe `DistrictModel`.

| Campo | Tipo SQL | Aceita nulo | Chave |
|---|---|---|---|
| `id` | `UUID` | Não | PK |
| `city_id` | `UUID` | Não | FK cities.id |
| `name` | `VARCHAR(120)` | Não | — |
| `slug` | `VARCHAR(120)` | Não | — |
| `geometry` | `geometry(POLYGON,4326)` | Não | — |

### FacilityModel

Persistência: `facilities`, classe `FacilityModel`.

| Campo | Tipo SQL | Aceita nulo | Chave |
|---|---|---|---|
| `id` | `UUID` | Não | PK |
| `city_id` | `UUID` | Não | FK cities.id |
| `address_id` | `UUID` | Não | FK addresses.id |
| `building_id` | `UUID` | Não | FK buildings.id |
| `name` | `VARCHAR(180)` | Não | — |
| `facility_type` | `facility_type` | Não | — |
| `active` | `BOOLEAN` | Não | — |

### IntersectionModel

Persistência: `intersections`, classe `IntersectionModel`.

| Campo | Tipo SQL | Aceita nulo | Chave |
|---|---|---|---|
| `id` | `UUID` | Não | PK |
| `city_id` | `UUID` | Não | FK cities.id |
| `district_id` | `UUID` | Não | FK districts.id |
| `code` | `VARCHAR(40)` | Não | — |
| `geometry` | `geometry(POINT,4326)` | Não | — |

### LotModel

Persistência: `lots`, classe `LotModel`.

| Campo | Tipo SQL | Aceita nulo | Chave |
|---|---|---|---|
| `id` | `UUID` | Não | PK |
| `city_id` | `UUID` | Não | FK cities.id |
| `district_id` | `UUID` | Não | FK districts.id |
| `road_segment_id` | `UUID` | Não | FK road_segments.id |
| `position_on_segment` | `FLOAT` | Não | — |
| `status` | `lot_status` | Não | — |
| `location` | `geometry(POINT,4326)` | Não | — |

### OperationRevisionModel

Persistência: `operation_revisions`, classe `OperationRevisionModel`.

| Campo | Tipo SQL | Aceita nulo | Chave |
|---|---|---|---|
| `id` | `UUID` | Não | PK |
| `operation_id` | `UUID` | Não | FK operations.id |
| `revision_number` | `INTEGER` | Não | — |
| `status` | `revision_status` | Não | — |
| `operation_date` | `DATE` | Não | — |
| `operation_start_time` | `TIME WITHOUT TIME ZONE` | Não | — |
| `operation_end_time` | `TIME WITHOUT TIME ZONE` | Não | — |
| `traffic_mode` | `traffic_mode` | Não | — |
| `created_by_user_id` | `UUID` | Não | FK users.id |
| `notes` | `VARCHAR(500)` | Sim | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Não | — |
| `optimized_at` | `TIMESTAMP WITH TIME ZONE` | Sim | — |
| `approved_at` | `TIMESTAMP WITH TIME ZONE` | Sim | — |
| `dispatched_at` | `TIMESTAMP WITH TIME ZONE` | Sim | — |

### OperationVehicleSelectionModel

Persistência: `operation_vehicle_selections`, classe `OperationVehicleSelectionModel`.

| Campo | Tipo SQL | Aceita nulo | Chave |
|---|---|---|---|
| `operation_id` | `UUID` | Não | PK / FK operations.id |
| `vehicle_id` | `UUID` | Não | PK / FK vehicles.id |

### OperationWorkerSelectionModel

Persistência: `operation_worker_selections`, classe `OperationWorkerSelectionModel`.

| Campo | Tipo SQL | Aceita nulo | Chave |
|---|---|---|---|
| `operation_id` | `UUID` | Não | PK / FK operations.id |
| `worker_id` | `UUID` | Não | PK / FK workers.id |

### OperationModel

Persistência: `operations`, classe `OperationModel`.

| Campo | Tipo SQL | Aceita nulo | Chave |
|---|---|---|---|
| `id` | `UUID` | Não | PK |
| `operation_code` | `VARCHAR(40)` | Não | — |
| `operation_date` | `DATE` | Não | — |
| `operation_start_time` | `TIME WITHOUT TIME ZONE` | Não | — |
| `operation_end_time` | `TIME WITHOUT TIME ZONE` | Não | — |
| `traffic_mode` | `traffic_mode` | Não | — |
| `status` | `operation_status` | Não | — |
| `current_revision_number` | `INTEGER` | Não | — |
| `created_by_user_id` | `UUID` | Não | FK users.id |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Não | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | Não | — |

### OptimizationRunModel

Persistência: `optimization_runs`, classe `OptimizationRunModel`.

| Campo | Tipo SQL | Aceita nulo | Chave |
|---|---|---|---|
| `id` | `UUID` | Não | PK |
| `operation_id` | `UUID` | Não | FK operations.id |
| `operation_revision_id` | `UUID` | Sim | FK operation_revisions.id |
| `status` | `VARCHAR(24)` | Não | — |
| `random_seed` | `INTEGER` | Não | — |
| `generations_completed` | `INTEGER` | Não | — |
| `stop_reason` | `VARCHAR(60)` | Não | — |
| `validated` | `BOOLEAN` | Não | — |
| `delivery_count` | `INTEGER` | Não | — |
| `vehicles_used` | `INTEGER` | Não | — |
| `total_cost_brl` | `NUMERIC(14, 2)` | Não | — |
| `distance_km` | `NUMERIC(14, 3)` | Não | — |
| `makespan_minutes` | `NUMERIC(14, 2)` | Não | — |
| `critical_delays` | `INTEGER` | Não | — |
| `on_time_percentage` | `NUMERIC(6, 2)` | Não | — |
| `average_weight_utilization_pct` | `NUMERIC(6, 2)` | Não | — |
| `average_volume_utilization_pct` | `NUMERIC(6, 2)` | Não | — |
| `pruning_counts` | `JSONB` | Não | — |
| `previous_operation_status` | `VARCHAR(24)` | Sim | — |
| `error_code` | `VARCHAR(80)` | Sim | — |
| `error_message` | `TEXT` | Sim | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Não | — |
| `started_at` | `TIMESTAMP WITH TIME ZONE` | Sim | — |
| `cancel_requested_at` | `TIMESTAMP WITH TIME ZONE` | Sim | — |
| `completed_at` | `TIMESTAMP WITH TIME ZONE` | Sim | — |

### OptimizationTraceEventModel

Persistência: `optimization_trace_events`, classe `OptimizationTraceEventModel`.

| Campo | Tipo SQL | Aceita nulo | Chave |
|---|---|---|---|
| `id` | `UUID` | Não | PK |
| `optimization_run_id` | `UUID` | Não | FK optimization_runs.id |
| `sequence` | `INTEGER` | Não | — |
| `event_type` | `VARCHAR(48)` | Não | — |
| `generation` | `INTEGER` | Sim | — |
| `elapsed_ms` | `INTEGER` | Sim | — |
| `payload` | `JSONB` | Não | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Não | — |

### OwnedVehicleCostProfileModel

Persistência: `owned_vehicle_cost_profiles`, classe `OwnedVehicleCostProfileModel`.

| Campo | Tipo SQL | Aceita nulo | Chave |
|---|---|---|---|
| `id` | `UUID` | Não | PK |
| `vehicle_id` | `UUID` | Não | FK vehicles.id |
| `acquisition_value_brl` | `NUMERIC(14, 2)` | Não | — |
| `residual_value_brl` | `NUMERIC(14, 2)` | Não | — |
| `useful_life_km` | `NUMERIC(14, 2)` | Não | — |
| `annual_ipva_brl` | `NUMERIC(14, 2)` | Não | — |
| `annual_insurance_brl` | `NUMERIC(14, 2)` | Não | — |
| `annual_fixed_costs_brl` | `NUMERIC(14, 2)` | Não | — |
| `expected_productive_hours_per_year` | `NUMERIC(12, 2)` | Não | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Não | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | Não | — |

### ReportModel

Persistência: `reports`, classe `ReportModel`.

| Campo | Tipo SQL | Aceita nulo | Chave |
|---|---|---|---|
| `id` | `UUID` | Não | PK |
| `operation_id` | `UUID` | Não | FK operations.id |
| `optimization_run_id` | `UUID` | Não | FK optimization_runs.id |
| `created_by_user_id` | `UUID` | Não | FK users.id |
| `report_type` | `VARCHAR(40)` | Não | — |
| `format` | `VARCHAR(12)` | Não | — |
| `status` | `VARCHAR(20)` | Não | — |
| `filename` | `VARCHAR(255)` | Sim | — |
| `content_type` | `VARCHAR(120)` | Sim | — |
| `snapshot` | `JSONB` | Não | — |
| `artifact` | `BYTEA` | Sim | — |
| `error_message` | `TEXT` | Sim | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Não | — |
| `completed_at` | `TIMESTAMP WITH TIME ZONE` | Sim | — |

### RoadOverrideModel

Persistência: `road_overrides`, classe `RoadOverrideModel`.

| Campo | Tipo SQL | Aceita nulo | Chave |
|---|---|---|---|
| `id` | `UUID` | Não | PK |
| `operation_id` | `UUID` | Não | FK operations.id |
| `road_segment_id` | `UUID` | Não | FK road_segments.id |
| `override_type` | `road_override_type` | Não | — |
| `direction_scope` | `road_override_direction_scope` | Não | — |
| `traffic_level` | `traffic_level` | Sim | — |
| `reason` | `VARCHAR(80)` | Não | — |
| `notes` | `VARCHAR(500)` | Sim | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Não | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | Não | — |

### RoadSegmentModel

Persistência: `road_segments`, classe `RoadSegmentModel`.

| Campo | Tipo SQL | Aceita nulo | Chave |
|---|---|---|---|
| `id` | `UUID` | Não | PK |
| `city_id` | `UUID` | Não | FK cities.id |
| `street_id` | `UUID` | Não | FK streets.id |
| `from_intersection_id` | `UUID` | Não | FK intersections.id |
| `to_intersection_id` | `UUID` | Não | FK intersections.id |
| `geometry` | `geometry(LINESTRING,4326)` | Não | — |
| `length_m` | `FLOAT` | Não | — |
| `speed_limit_kmh` | `INTEGER` | Não | — |
| `road_class` | `road_class` | Não | — |
| `lanes` | `INTEGER` | Não | — |
| `active` | `BOOLEAN` | Não | — |
| `is_bridge` | `BOOLEAN` | Não | — |
| `bridge_name` | `VARCHAR(120)` | Sim | — |

### RoutePlanModel

Persistência: `route_plans`, classe `RoutePlanModel`.

| Campo | Tipo SQL | Aceita nulo | Chave |
|---|---|---|---|
| `id` | `UUID` | Não | PK |
| `optimization_run_id` | `UUID` | Não | FK optimization_runs.id |
| `route_code` | `VARCHAR(24)` | Não | — |
| `sequence` | `INTEGER` | Não | — |
| `vehicle_id` | `UUID` | Não | FK vehicles.id |
| `total_weight_kg` | `NUMERIC(14, 3)` | Não | — |
| `total_volume_m3` | `NUMERIC(14, 4)` | Não | — |
| `distance_km` | `NUMERIC(14, 3)` | Não | — |
| `duration_minutes` | `NUMERIC(14, 2)` | Não | — |
| `weight_utilization_pct` | `NUMERIC(6, 2)` | Não | — |
| `volume_utilization_pct` | `NUMERIC(6, 2)` | Não | — |
| `depreciation_brl` | `NUMERIC(14, 2)` | Não | — |
| `maintenance_brl` | `NUMERIC(14, 2)` | Não | — |
| `fixed_time_brl` | `NUMERIC(14, 2)` | Não | — |
| `fuel_brl` | `NUMERIC(14, 2)` | Não | — |
| `team_brl` | `NUMERIC(14, 2)` | Não | — |
| `contract_brl` | `NUMERIC(14, 2)` | Não | — |
| `total_cost_brl` | `NUMERIC(14, 2)` | Não | — |
| `geometry` | `JSONB` | Não | — |

### RouteStopModel

Persistência: `route_stops`, classe `RouteStopModel`.

| Campo | Tipo SQL | Aceita nulo | Chave |
|---|---|---|---|
| `id` | `UUID` | Não | PK |
| `route_id` | `UUID` | Não | FK route_plans.id |
| `delivery_id` | `UUID` | Não | FK deliveries.id |
| `sequence` | `INTEGER` | Não | — |
| `planned_arrival_at` | `TIMESTAMP WITH TIME ZONE` | Sim | — |
| `planned_departure_at` | `TIMESTAMP WITH TIME ZONE` | Sim | — |
| `lateness_minutes` | `NUMERIC(12, 2)` | Não | — |

### RouteTeamAssignmentModel

Persistência: `route_team_assignments`, classe `RouteTeamAssignmentModel`.

| Campo | Tipo SQL | Aceita nulo | Chave |
|---|---|---|---|
| `route_id` | `UUID` | Não | PK / FK route_plans.id |
| `primary_role` | `VARCHAR(32)` | Sim | — |
| `primary_worker_id` | `UUID` | Sim | FK workers.id |
| `helper_worker_id` | `UUID` | Sim | FK workers.id |
| `primary_included` | `BOOLEAN` | Não | — |
| `helper_included` | `BOOLEAN` | Não | — |
| `team_cost_brl` | `NUMERIC(14, 2)` | Não | — |

### StreetModel

Persistência: `streets`, classe `StreetModel`.

| Campo | Tipo SQL | Aceita nulo | Chave |
|---|---|---|---|
| `id` | `UUID` | Não | PK |
| `city_id` | `UUID` | Não | FK cities.id |
| `key` | `VARCHAR(80)` | Não | — |
| `name` | `VARCHAR(160)` | Não | — |
| `road_class` | `road_class` | Não | — |

### UserModel

Persistência: `users`, classe `UserModel`.

| Campo | Tipo SQL | Aceita nulo | Chave |
|---|---|---|---|
| `id` | `UUID` | Não | PK |
| `email` | `VARCHAR(320)` | Não | — |
| `display_name` | `VARCHAR(120)` | Não | — |
| `password_hash` | `VARCHAR(255)` | Não | — |
| `role` | `user_role` | Não | — |
| `active` | `BOOLEAN` | Não | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Não | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | Não | — |

### VehicleMaintenanceItemModel

Persistência: `vehicle_maintenance_items`, classe `VehicleMaintenanceItemModel`.

| Campo | Tipo SQL | Aceita nulo | Chave |
|---|---|---|---|
| `id` | `UUID` | Não | PK |
| `vehicle_id` | `UUID` | Não | FK vehicles.id |
| `name` | `VARCHAR(120)` | Não | — |
| `cost_brl` | `NUMERIC(12, 2)` | Não | — |
| `interval_km` | `NUMERIC(12, 2)` | Não | — |
| `active` | `BOOLEAN` | Não | — |

### VehicleModel

Persistência: `vehicles`, classe `VehicleModel`.

| Campo | Tipo SQL | Aceita nulo | Chave |
|---|---|---|---|
| `id` | `UUID` | Não | PK |
| `plate` | `VARCHAR(16)` | Não | — |
| `type` | `vehicle_type` | Não | — |
| `ownership_type` | `vehicle_ownership_type` | Não | — |
| `max_payload_kg` | `NUMERIC(12, 3)` | Não | — |
| `max_volume_m3` | `NUMERIC(12, 4)` | Não | — |
| `max_range_km` | `NUMERIC(12, 2)` | Não | — |
| `refrigerated` | `BOOLEAN` | Não | — |
| `status` | `vehicle_status` | Não | — |
| `helper_policy` | `helper_policy` | Não | — |
| `fuel_type` | `fuel_type` | Sim | — |
| `fuel_efficiency_km_per_l` | `NUMERIC(10, 3)` | Sim | — |
| `active` | `BOOLEAN` | Não | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Não | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | Não | — |

### WorkerAvailabilityModel

Persistência: `worker_availability`, classe `WorkerAvailabilityModel`.

| Campo | Tipo SQL | Aceita nulo | Chave |
|---|---|---|---|
| `id` | `UUID` | Não | PK |
| `worker_id` | `UUID` | Não | FK workers.id |
| `date` | `DATE` | Não | — |
| `available` | `BOOLEAN` | Não | — |
| `notes` | `TEXT` | Sim | — |

### WorkerModel

Persistência: `workers`, classe `WorkerModel`.

| Campo | Tipo SQL | Aceita nulo | Chave |
|---|---|---|---|
| `id` | `UUID` | Não | PK |
| `name` | `VARCHAR(180)` | Não | — |
| `role` | `worker_role` | Não | — |
| `engagement_type` | `worker_engagement_type` | Não | — |
| `compensation_model` | `compensation_model` | Não | — |
| `compensation_value_brl` | `NUMERIC(12, 2)` | Não | — |
| `active` | `BOOLEAN` | Não | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | Não | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | Não | — |

## Tipos do domínio

Os enums abaixo são definidos pelo código. As ações e transições são verificadas pelos serviços de aplicação.

### UserRole

`ADMIN`, `PLANNER`

### OperationStatus

`DRAFT`, `READY`, `OPTIMIZING`, `OPTIMIZED`, `OUTDATED`, `APPROVED`, `DISPATCHED`

### RevisionStatus

`DRAFT`, `OPTIMIZED`, `OUTDATED`, `APPROVED`, `DISPATCHED`

### OptimizationRunStatus

`QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`, `INTERRUPTED`

### DeliveryPriority

`CRITICAL`, `HIGH`, `NORMAL`, `LOW`

### TimeWindowPolicy

`HARD`, `SOFT`

### ServiceTimeSource

`ESTIMATED`, `MANUAL`, `IMPORTED`

### TemperatureClass

`AMBIENT`, `REFRIGERATED`

### HandlingRequirement

`STANDARD`, `TWO_PERSON`

### DeliveryStatus

`PENDING`, `PLANNED`, `LOADED`, `DISPATCHED`, `IN_TRANSIT`, `DELIVERED`, `FAILED`

### CargoProfile

`MEDICATION_SMALL`, `REFRIGERATED_MEDICATION`, `LAB_MATERIAL`, `HOSPITAL_SUPPLIES`, `BULK_CONSUMABLES`, `MEDICAL_EQUIPMENT`

### VehicleType

`MOTO`, `VAN_COMPACT`, `CARGO_VAN`, `LIGHT_TRUCK`

### VehicleOwnershipType

`OWNED`, `AGGREGATED`

### VehicleStatus

`AVAILABLE`, `UNAVAILABLE`, `MAINTENANCE`, `INACTIVE`

### HelperPolicy

`FORBIDDEN`, `OPTIONAL`, `REQUIRED`

### FuelType

`GASOLINE`, `ETHANOL`, `DIESEL`, `FLEX`, `OTHER`

### AggregatedPricingModel

`PER_ROUTE`

### WorkerRole

`DRIVER`, `HELPER`, `MOTORCYCLE_COURIER`

### WorkerEngagementType

`EMPLOYEE`, `DAY_WORKER`, `AGGREGATED`

### CompensationModel

`HOURLY`, `DAILY`, `PER_ROUTE`, `INCLUDED_IN_VEHICLE_CONTRACT`

### TrafficMode

`AUTOMATIC`, `FREE`, `CUSTOM`

### TrafficLevel

`FREE`, `LIGHT`, `MODERATE`, `HEAVY`, `VERY_HEAVY`

### RoadOverrideType

`CLOSURE`, `TRAFFIC`

### RoadOverrideDirectionScope

`SEGMENT_DIRECTION`

### RoutingAlgorithm

`DIJKSTRA`, `ASTAR`

### CitySourceType

`SYNTHETIC`

### RoadClass

`EXPRESSWAY`, `ARTERIAL`, `COLLECTOR`, `LOCAL`, `SERVICE`

### LotStatus

`OCCUPIED`, `VACANT`

### BuildingType

`HOUSE`, `APARTMENT_BUILDING`, `COMMERCIAL`, `CLINIC`, `HOSPITAL`, `PHARMACY`, `LABORATORY`, `WAREHOUSE`, `SCHOOL`, `PUBLIC_BUILDING`, `OTHER`

### FacilityType

`DEPOT`, `HOSPITAL`, `CLINIC`, `LABORATORY`, `PHARMACY`, `WAREHOUSE`, `PUBLIC_FACILITY`

### ScenarioProfile

`NORMAL`, `BUSY`, `HIGH_PRESSURE`, `EMERGENCY`

## FitnessVector

Value object do núcleo:

```text
feasible: bool
hard_violations: int
service_penalty: Decimal
critical_risk: Decimal
priority_inversion_minutes: Decimal
total_cost_brl: Decimal
makespan_minutes: Decimal
travel_minutes: Decimal
distance_km: Decimal
vehicles_used: int
team_feasible: bool
```

`sort_key` minimiza, nessa ordem: 0 se viável/1 se inviável; violações; atraso SOFT ponderado; risco CRITICAL; inversões; custo operacional; makespan; viagem; distância; veículos. `team_feasible` reflete-se na viabilidade e nas violações. A equipe efetiva e o combustível são avaliados pela aplicação. Veja [a ordem completa](OPTIMIZATION_SPEC.md#ordem-lexicográfica).

## Solução avaliada

O núcleo usa `EvaluatedIndividual`, que contém cromossomo, `DecodedSolution` e `FitnessVector`. A solução decodificada reúne rotas, entregas não atribuídas e contagens de poda. O resultado publicado é vinculado ao run e à revisão após validação, atribuição final de equipe e persistência.

## GeneticOptimizerConfig

Configuração tipada do núcleo:

```text
population_size: int = 48
max_generations: int = 120
tournament_size: int = 3
crossover_rate: float = 0.9
mutation_rate: float = 0.22
max_mutation_rate: float = 0.55
elitism_fraction: float = 0.05
stagnation_generations: int = 25
low_diversity_threshold: float = 0.35
immigrant_fraction: float = 0.1
advanced_pruning_enabled: bool = True
repair_enabled: bool = True
```

O manifesto experimental registra os parâmetros do estudo, seeds e identidade da fonte. O run operacional registra sua seed e seus indicadores nos campos de `OptimizationRunModel`.

## ScenarioRequest

O corpo HTTP de geração usa `profile`, `delivery_count` e `random_seed`. `ScenarioProfile` define os quatro perfis. A data, a janela e os recursos são obtidos da operação selecionada. Tipos, defaults e limites estão no [contrato da API](API_SPEC.md).

## Resultado da geração de cenário

O gerador retorna `ScenarioBatch` com seed e especificações de entregas; o serviço retorna os seguintes objetos:

`ScenarioSummary`:

```text
generated_count: int
critical_count: int
refrigerated_count: int
hard_window_count: int
total_weight_kg: Decimal
total_volume_m3: Decimal
```

`ScenarioResult`:

```text
seed: int
summary: ScenarioSummary
deliveries: list[DeliveryView]
```

## Métricas e caminho

`TravelMetric` contém `distance_km: Decimal` e `travel_minutes: Decimal`. O routing retorna `RoutePath`, com métricas em metros/segundos e geometria:

```text
origin_node_id: uuid.UUID
destination_node_id: uuid.UUID
node_ids: tuple[uuid.UUID, ...]
edge_ids: tuple[uuid.UUID, ...]
distance_m: float
travel_time_seconds: float
departure_at: datetime
arrival_at: datetime
algorithm: RoutingAlgorithm
traffic_mode: TrafficMode
time_bucket: str
geometry: dict[str, object]
```

A aplicação converte as métricas do routing para a matriz do núcleo.

## Chaves da matriz de viagem

`TravelMatrix` mapeia pares `(origem, destino)` a `TravelMetric`. Cada local é um UUID de entrega ou `None`, que representa o depósito. O horário de referência é usado na preparação da matriz; não faz parte da chave interna de cada par.

## Grafo e condições efetivas

`DirectedGraph` reúne nós e arestas da cidade. O routing recebe os segmentos fechados e os níveis de trânsito sobrescritos para a operação. A construção da matriz verifica também o acesso dos endereços ao grafo dirigido.

## Identidade do dataset

A cidade registra `dataset_version`, `generation_seed` e `generator_version`, conforme `CityModel`. O experimento também registra a identidade das entradas e do código em seu manifesto e em `experiment.json`.

## Despacho e revisão

O despacho é uma transição da operação aprovada e registra `dispatched_at` na revisão. A operação/revisão despachada fica imutável pelos serviços operacionais. Runs, rotas, equipe e custos mantêm seus vínculos persistidos; relatórios guardam seu próprio snapshot de geração.

## Regras operacionais

- IDs e chaves estrangeiras identificam os recursos utilizados por operação, revisão e execução.
- Distância e tempo do núcleo usam km e minutos; o routing expõe metros e segundos.
- Carga e volume usam kg e m³. Valores quantitativos e monetários do domínio usam `Decimal`.
- A cronologia considera o fuso da cidade e inclui viagem, serviço, espera e retorno.
- A aprovação e o despacho são verificados pelos serviços; a revisão despachada fica imutável.
- A validação independente reconstrói as restrições das entradas originais, conforme [OPTIMIZATION_SPEC.md](OPTIMIZATION_SPEC.md).
