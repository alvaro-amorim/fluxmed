# FluxMed — API Specification

**Documento:** `docs/API_SPEC.md`  
**Status:** Especificação oficial da API da V1  
**Projeto:** FluxMed — Planejamento Inteligente de Rotas Médicas  
**Backend:** FastAPI  
**Contrato:** REST + JSON + Server-Sent Events (SSE)  
**Versão inicial:** `/api/v1`

---

# 1. Objetivo deste documento

Este documento define o contrato HTTP de alto nível do FluxMed V1.

Ele estabelece:

- versionamento;
- autenticação;
- convenções REST;
- requests e responses;
- paginação;
- filtros;
- códigos de erro;
- endpoints principais;
- streaming SSE;
- GeoJSON;
- operações;
- entregas;
- frota;
- equipe;
- cidade;
- otimização;
- relatórios;
- Assistente IA;
- health checks.

Este documento descreve a API pública entre frontend e backend.

Detalhes internos de implementação continuam definidos em `ARCHITECTURE.md`, `DOMAIN_MODEL.md` e documentos específicos.

---

# 2. Princípios da API

A API deve ser:

- previsível;
- tipada;
- documentada automaticamente por OpenAPI;
- consistente;
- segura;
- orientada a recursos;
- simples de consumir no frontend;
- explícita em erros;
- sem lógica duplicada no cliente.

---

# 3. Base URL

Versão inicial:

```text
/api/v1
```

Exemplo:

```text
GET /api/v1/operations
```

---

# 4. Versionamento

A V1 usa:

```text
/api/v1
```

Não usar versionamento por header na primeira versão.

Se houver mudança incompatível futura:

```text
/api/v2
```

---

# 5. Formato padrão

Requests e responses usam:

```text
application/json
```

Exceções:

- upload multipart;
- SSE;
- arquivos PDF/XLSX/CSV;
- GeoJSON ainda transportado via JSON.

---

# 6. Datas e horários

Usar ISO 8601.

Exemplos:

```text
2026-09-13
2026-09-13T07:30:00-03:00
```

O backend deve considerar timezone da cidade.

---

# 7. IDs

Entidades usam UUID.

Exemplo:

```text
550e8400-e29b-41d4-a716-446655440000
```

Além disso, algumas entidades possuem códigos humanos:

```text
OP-20260913-001
DLV-NF45872-001
```

---

# 8. Dinheiro

Valores monetários devem ser serializados com precisão segura.

Preferência:

```json
{
  "total_cost_brl": "1742.30"
}
```

ou schema decimal compatível com OpenAPI.

Evitar depender de float binário como fonte oficial.

---

# 9. Unidades nos campos

Campos devem indicar unidade.

Exemplos:

```text
weight_kg
volume_m3
distance_km
length_m
duration_minutes
elapsed_ms
speed_limit_kmh
```

---

# 10. Envelope de resposta

Para recursos simples, retornar o recurso diretamente.

Exemplo:

```json
{
  "id": "...",
  "operation_code": "OP-20260913-001",
  "status": "DRAFT"
}
```

Não criar envelope genérico desnecessário como:

```json
{
  "success": true,
  "data": {}
}
```

para toda resposta.

---

# 11. Respostas paginadas

Formato recomendado:

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 127,
  "total_pages": 7
}
```

---

# 12. Query params de paginação

Padrão:

```text
?page=1&page_size=20
```

Limite sugerido:

```text
page_size <= 100
```

---

# 13. Ordenação

Quando aplicável:

```text
?sort=created_at&order=desc
```

Valores inválidos devem retornar erro 422.

---

# 14. Busca textual

Padrão:

```text
?q=texto
```

Cada endpoint decide campos pesquisáveis.

---

# 15. Filtros

Exemplo:

```text
GET /operations?status=OPTIMIZED
GET /deliveries?priority=CRITICAL
GET /vehicles?status=AVAILABLE
```

Filtros combinados usam semântica AND.

---

# 16. Autenticação

A V1 usa autenticação própria via FastAPI + PostgreSQL.

Endpoints:

```text
POST /auth/login
POST /auth/logout
GET  /auth/me
```

---

# 17. POST /auth/login

Request:

```json
{
  "email": "planner@fluxmed.demo",
  "password": "..."
}
```

Response:

```json
{
  "user": {
    "id": "...",
    "email": "planner@fluxmed.demo",
    "display_name": "Planner Demo",
    "role": "PLANNER"
  }
}
```

O mecanismo de sessão/token pode ser cookie seguro ou bearer token, conforme implementação.

Preferir solução simples e segura.

---

# 18. GET /auth/me

Response:

```json
{
  "id": "...",
  "email": "planner@fluxmed.demo",
  "display_name": "Planner Demo",
  "role": "PLANNER"
}
```

---

# 19. RBAC

Backend valida roles.

Exemplo:

```text
/admin-only endpoint
→ ADMIN
```

Frontend pode esconder ação, mas isso não substitui autorização no backend.

---

# 20. Erro padrão

Formato recomendado:

```json
{
  "error": {
    "code": "NO_FEASIBLE_VEHICLE",
    "message": "Nenhum veículo elegível foi encontrado.",
    "details": {
      "delivery_id": "...",
      "delivery_code": "DLV-NF45872-001"
    },
    "request_id": "..."
  }
}
```

---

# 21. Códigos HTTP

Uso recomendado:

```text
200 OK
201 Created
202 Accepted
204 No Content
400 Bad Request
401 Unauthorized
403 Forbidden
404 Not Found
409 Conflict
422 Unprocessable Entity
429 Too Many Requests
500 Internal Server Error
503 Service Unavailable
```

---

# 22. Erros de domínio

Códigos previstos:

```text
INVALID_OPERATION_STATE
OPERATION_OUTDATED
OPERATION_ALREADY_DISPATCHED
NO_FEASIBLE_VEHICLE
HARD_WINDOW_INFEASIBLE
CAPACITY_INFEASIBLE
VOLUME_INFEASIBLE
RANGE_INFEASIBLE
TEAM_INFEASIBLE
ROAD_GRAPH_DISCONNECTED
ADDRESS_NOT_FOUND
ADDRESS_AMBIGUOUS
IMPORT_VALIDATION_FAILED
OPTIMIZATION_ALREADY_RUNNING
OPTIMIZATION_TIMEOUT_NO_SOLUTION
OPTIMIZER_VALIDATION_MISMATCH
LLM_PROVIDER_UNAVAILABLE
REPORT_GENERATION_FAILED
DATABASE_UNAVAILABLE
FORBIDDEN_ACTION
```

---

# 23. Request ID

Toda request pode receber/gerar:

```text
X-Request-ID
```

Se cliente não enviar, backend gera.

Esse ID deve aparecer em logs e erros.

---

# 24. Health checks

Endpoints:

```text
GET /health/live
GET /health/ready
```

---

# 25. GET /health/live

Response:

```json
{
  "status": "ok"
}
```

Não verificar dependências externas pesadas.

---

# 26. GET /health/ready

Response exemplo:

```json
{
  "status": "healthy",
  "components": {
    "database": "healthy",
    "postgis": "healthy",
    "city_dataset": "healthy",
    "llm": "degraded"
  }
}
```

LLM degradada não torna core indisponível.

---

# 27. Operações — endpoints principais

```text
GET    /operations
POST   /operations
GET    /operations/{operation_id}
PATCH  /operations/{operation_id}
DELETE /operations/{operation_id}   [apenas quando permitido]
```

Preferir inativação/estado em vez de delete se houver histórico.

---

# 28. GET /operations

Filtros possíveis:

```text
status
date_from
date_to
q
page
page_size
sort
order
```

Response:

```json
{
  "items": [
    {
      "id": "...",
      "operation_code": "OP-20260913-001",
      "operation_date": "2026-09-13",
      "city_name": "Santa Aurora",
      "status": "OPTIMIZED",
      "delivery_count": 40,
      "vehicles_used": 6,
      "total_cost_brl": "1742.30",
      "updated_at": "..."
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 1,
  "total_pages": 1
}
```

---

# 29. POST /operations

Request:

```json
{
  "operation_date": "2026-09-13",
  "city_id": "...",
  "depot_facility_id": "...",
  "operation_start_time": "07:30:00",
  "operation_end_time": "18:00:00",
  "traffic_mode": "AUTOMATIC"
}
```

Response:

```text
201 Created
```

com `OperationResponse`.

---

# 30. PATCH /operations/{id}

Permitido apenas antes de dispatch.

Exemplo:

```json
{
  "operation_start_time": "08:00:00",
  "traffic_mode": "FREE"
}
```

Mudança relevante após otimização deve marcar plano como `OUTDATED`.

---

# 31. Operation detail

`GET /operations/{id}` deve retornar visão de produto, não payload gigantesco.

Exemplo:

```json
{
  "id": "...",
  "operation_code": "OP-20260913-001",
  "status": "OPTIMIZED",
  "operation_date": "2026-09-13",
  "operation_start_time": "07:30:00",
  "operation_end_time": "18:00:00",
  "traffic_mode": "AUTOMATIC",
  "city": {
    "id": "...",
    "name": "Santa Aurora",
    "dataset_version": "1.0.0"
  },
  "depot": {
    "id": "...",
    "name": "Centro de Distribuição FluxMed"
  },
  "summary": {
    "delivery_count": 40,
    "critical_count": 5,
    "refrigerated_count": 8,
    "hard_window_count": 12
  },
  "current_revision": {
    "id": "...",
    "revision_number": 3,
    "status": "OPTIMIZED"
  }
}
```

---

# 32. Revisões

Endpoints:

```text
GET /operations/{id}/revisions
GET /operations/{id}/revisions/{revision_id}
```

Criar revisão explícita por endpoint somente se necessário na implementação.

A maior parte pode ser controlada por casos de uso.

---

# 33. Entregas da operação

Endpoints:

```text
GET    /operations/{id}/deliveries
POST   /operations/{id}/deliveries
PATCH  /operations/{id}/deliveries/{delivery_id}
DELETE /operations/{id}/deliveries/{delivery_id}
```

---

# 34. POST delivery manual

Request:

```json
{
  "invoice_number": "45872",
  "invoice_series": "1",
  "issuer_document": "12.345.678/0001-90",
  "issuer_name": "Distribuidora Médica Aurora",
  "recipient_name": "Hospital Universitário de Santa Aurora",
  "destination_address_id": "...",
  "package_count": 8,
  "total_weight_kg": "84.50",
  "total_volume_m3": "0.72",
  "priority": "HIGH",
  "time_window_start": "2026-09-13T09:00:00-03:00",
  "time_window_end": "2026-09-13T11:00:00-03:00",
  "time_window_policy": "HARD",
  "temperature_class": "REFRIGERATED",
  "handling_requirement": "STANDARD",
  "service_time_minutes": 15,
  "notes": null
}
```

---

# 35. Listagem global de entregas

```text
GET /deliveries
```

Filtros:

```text
operation_id
priority
temperature_class
status
district_id
q
```

---

# 36. Importação de entregas

Endpoints:

```text
POST /operations/{id}/delivery-imports
GET  /delivery-imports/{import_id}
POST /delivery-imports/{import_id}/confirm
DELETE /delivery-imports/{import_id}
```

---

# 37. Upload de importação

`POST /operations/{id}/delivery-imports`

Tipo:

```text
multipart/form-data
```

Arquivo:

```text
file
```

Formatos:

```text
.xlsx
.csv
```

Response:

```text
202 Accepted
```

ou `201` se parsing for síncrono rápido.

---

# 38. Import preview

Response exemplo:

```json
{
  "id": "...",
  "status": "REVIEW",
  "summary": {
    "total_rows": 40,
    "valid_rows": 35,
    "warning_rows": 3,
    "error_rows": 2
  },
  "rows": [
    {
      "row_number": 2,
      "status": "VALID",
      "normalized": {}
    },
    {
      "row_number": 7,
      "status": "ERROR",
      "errors": [
        {
          "code": "ADDRESS_NOT_FOUND",
          "message": "Número 600 não existe nesta rua."
        }
      ],
      "suggestions": []
    }
  ]
}
```

---

# 39. Confirmação de importação

```text
POST /delivery-imports/{id}/confirm
```

Persistência deve ser atômica.

Se houver erros bloqueantes:

```text
409 ou 422
```

---

# 40. Template de importação

Endpoint opcional:

```text
GET /delivery-imports/template
```

Retorna XLSX.

---

# 41. Geração de cenário

Endpoint:

```text
POST /operations/{id}/generate-scenario
```

Request:

```json
{
  "profile": "NORMAL",
  "delivery_count": 40,
  "random_seed": 12345
}
```

`random_seed` opcional.

---

# 42. Scenario response

Exemplo:

```json
{
  "seed": 12345,
  "generated_count": 40,
  "summary": {
    "critical_count": 4,
    "refrigerated_count": 7,
    "hard_window_count": 9,
    "total_weight_kg": "4280.00",
    "total_volume_m3": "31.70"
  },
  "validation": {
    "status": "FEASIBLE"
  }
}
```

---

# 43. Frota

Endpoints:

```text
GET    /vehicles
POST   /vehicles
GET    /vehicles/{vehicle_id}
PATCH  /vehicles/{vehicle_id}
POST   /vehicles/{vehicle_id}/deactivate
```

Evitar DELETE físico.

---

# 44. Vehicle response

Exemplo:

```json
{
  "id": "...",
  "plate": "ABC1D23",
  "type": "CARGO_VAN",
  "ownership_type": "OWNED",
  "max_payload_kg": "1500.00",
  "max_volume_m3": "8.50",
  "max_range_km": "450.00",
  "refrigerated": true,
  "helper_policy": "OPTIONAL",
  "status": "AVAILABLE",
  "active": true
}
```

---

# 45. Vehicle cost profile

Endpoints opcionais/separados:

```text
GET  /vehicles/{id}/cost-profile
PUT  /vehicles/{id}/cost-profile
```

Pode ser embutido no create/update se simplificar V1.

---

# 46. Equipe

Endpoints:

```text
GET    /workers
POST   /workers
GET    /workers/{worker_id}
PATCH  /workers/{worker_id}
POST   /workers/{worker_id}/deactivate
```

---

# 47. Worker response

```json
{
  "id": "...",
  "name": "Carlos Almeida",
  "role": "DRIVER",
  "engagement_type": "EMPLOYEE",
  "compensation_model": "HOURLY",
  "compensation_value_brl": "28.50",
  "active": true
}
```

---

# 48. Disponibilidade

Pode ser controlada por:

```text
GET /workers/{id}/availability
PUT /workers/{id}/availability
```

ou via seleção da operação.

A implementação deve escolher a forma mais simples coerente.

---

# 49. Seleção de recursos da operação

Endpoints:

```text
GET /operations/{id}/resources
PUT /operations/{id}/resources
```

Request exemplo:

```json
{
  "vehicle_ids": ["...", "..."],
  "worker_ids": ["...", "...", "..."]
}
```

Backend valida elegibilidade básica.

---

# 50. Cidade — metadata

```text
GET /cities
GET /cities/{city_id}
```

Response:

```json
{
  "id": "...",
  "name": "Santa Aurora",
  "country_code": "BR",
  "timezone": "America/Sao_Paulo",
  "dataset_version": "1.0.0",
  "source_type": "SYNTHETIC"
}
```

---

# 51. Bairros

```text
GET /cities/{city_id}/districts
```

Pode retornar GeoJSON FeatureCollection ou DTO comum.

---

# 52. Facilities

```text
GET /cities/{city_id}/facilities
```

Filtros:

```text
type
district_id
q
```

---

# 53. Busca de endereço

Endpoint:

```text
GET /cities/{city_id}/addresses/search
```

Query:

```text
?q=Rua das Acacias 593
&limit=10
```

---

# 54. Address search response

```json
{
  "items": [
    {
      "id": "...",
      "street_name": "Rua das Acácias",
      "house_number": "593",
      "district_name": "Jardim das Flores",
      "label": "Rua das Acácias, 593 — Jardim das Flores",
      "match_type": "EXACT"
    }
  ]
}
```

---

# 55. Busca em duas etapas

Também pode existir:

```text
GET /cities/{city_id}/streets/search?q=Acassias
GET /streets/{street_id}/addresses?number=600
```

Se isso melhorar UX.

Não é obrigatório expor ambos se uma busca unificada resolver.

---

# 56. Address not found

Response de domínio:

```json
{
  "error": {
    "code": "ADDRESS_NOT_FOUND",
    "message": "Número não encontrado.",
    "details": {
      "street_id": "...",
      "requested_number": "600",
      "nearest_numbers": ["593", "611"]
    }
  }
}
```

---

# 57. Map layers

Endpoint recomendado:

```text
GET /cities/{city_id}/map
```

Pode aceitar:

```text
layers=water,districts,roads,facilities,depot
```

---

# 58. Map response

Formato:

```json
{
  "city": {...},
  "layers": {
    "water": {...GeoJSON...},
    "districts": {...GeoJSON...},
    "roads": {...GeoJSON...},
    "facilities": {...GeoJSON...},
    "depot": {...GeoJSON...}
  }
}
```

Se payload ficar grande, separar endpoints.

Medir antes de sofisticar.

---

# 59. GeoJSON

Usar formato padrão:

```text
Feature
FeatureCollection
```

Properties devem conter apenas campos úteis ao frontend.

Não expor ORM completo.

---

# 60. Road overrides

Endpoints:

```text
GET    /operations/{id}/road-overrides
POST   /operations/{id}/road-overrides
PATCH  /operations/{id}/road-overrides/{override_id}
DELETE /operations/{id}/road-overrides/{override_id}
```

---

# 61. Criar closure

Request:

```json
{
  "road_segment_id": "...",
  "override_type": "CLOSURE",
  "direction_scope": "SEGMENT_DIRECTION",
  "reason": "ROADWORK",
  "notes": "Obra simulada"
}
```

---

# 62. Criar traffic override

```json
{
  "road_segment_id": "...",
  "override_type": "TRAFFIC",
  "direction_scope": "SEGMENT_DIRECTION",
  "traffic_level": "HEAVY",
  "reason": "EVENT"
}
```

Backend converte `traffic_level` em fator.

---

# 63. Buscar segmento clicado

Endpoint útil:

```text
GET /cities/{city_id}/road-segments/nearest
```

Query:

```text
lat
lng
max_distance_m
```

Ou frontend usa properties já presentes na layer.

Preferir evitar roundtrip se `road_segment_id` já estiver no GeoJSON.

---

# 64. Preflight

Endpoint:

```text
POST /operations/{id}/validate
```

Response:

```json
{
  "status": "VALID",
  "blocking_errors": [],
  "warnings": [],
  "summary": {
    "delivery_count": 40,
    "vehicle_count": 8,
    "worker_count": 11
  }
}
```

---

# 65. Preflight inválido

```json
{
  "status": "INVALID",
  "blocking_errors": [
    {
      "code": "NO_FEASIBLE_VEHICLE",
      "message": "Nenhum veículo refrigerado foi selecionado.",
      "related_delivery_ids": ["..."]
    }
  ],
  "warnings": []
}
```

---

# 66. Iniciar otimização

Endpoint:

```text
POST /operations/{id}/optimize
```

Request opcional:

```json
{
  "random_seed": 582914
}
```

Parâmetros internos do GA não devem vir do PLANNER.

---

# 67. Optimize response

```text
202 Accepted
```

Response:

```json
{
  "optimization_run_id": "...",
  "status": "QUEUED",
  "stream_url": "/api/v1/optimization-runs/.../events"
}
```

Se execução já existir:

```text
409 OPTIMIZATION_ALREADY_RUNNING
```

ou retornar a ativa de forma idempotente.

---

# 68. Optimization run status

```text
GET /optimization-runs/{run_id}
```

Response:

```json
{
  "id": "...",
  "operation_revision_id": "...",
  "status": "RUNNING",
  "generation": 37,
  "elapsed_ms": 8400,
  "best_metrics": {
    "total_cost_brl": "1742.30",
    "makespan_minutes": 318,
    "distance_km": "126.40",
    "hard_violations": 0
  },
  "pruned_total": 1842,
  "stop_reason": null
}
```

---

# 69. SSE endpoint

```text
GET /optimization-runs/{run_id}/events
```

Content-Type:

```text
text/event-stream
```

---

# 70. SSE event format

Exemplo:

```text
event: generation_snapshot
data: {"generation":37,"elapsed_ms":8400,...}
```

---

# 71. optimization_started

Payload:

```json
{
  "run_id": "...",
  "started_at": "...",
  "algorithm_version": "1.0.0",
  "configuration_version": "production-v1"
}
```

---

# 72. generation_snapshot

```json
{
  "generation": 37,
  "elapsed_ms": 8400,
  "best_cost_brl": "1742.30",
  "best_makespan_minutes": 318,
  "best_distance_km": "126.40",
  "hard_violations": 0,
  "diversity": 0.61,
  "mutation_rate": 0.08,
  "pruned_total": 1842
}
```

---

# 73. best_solution_updated

Pode incluir resumo suficiente para atualizar mapa:

```json
{
  "generation": 37,
  "routes": [
    {
      "vehicle_id": "...",
      "delivery_ids": ["...", "..."]
    }
  ],
  "metrics": {
    "total_cost_brl": "1742.30",
    "makespan_minutes": 318
  }
}
```

Não incluir detalhes excessivos.

---

# 74. pruning_summary

```json
{
  "generation": 37,
  "total_pruned": 1842,
  "by_reason": {
    "CAPACITY_EXCEEDED": 812,
    "HARD_TIME_WINDOW_IMPOSSIBLE": 327,
    "DOMINATED_STATE": 529,
    "RANGE_IMPOSSIBLE": 83
  }
}
```

---

# 75. optimization_completed

```json
{
  "run_id": "...",
  "result_id": "...",
  "status": "COMPLETED",
  "stop_reason": "EARLY_STOPPING"
}
```

---

# 76. optimization_failed

```json
{
  "run_id": "...",
  "status": "FAILED",
  "error": {
    "code": "OPTIMIZER_INTERNAL_ERROR",
    "message": "..."
  }
}
```

---

# 77. Cancelar otimização

```text
POST /optimization-runs/{run_id}/cancel
```

Response:

```text
202 Accepted
```

ou status final se imediato.

---

# 78. Resultado da otimização

```text
GET /optimization-runs/{run_id}/result
```

Response principal deve conter:

- métricas;
- rotas;
- equipes;
- custos;
- validação;
- versão;
- stop reason.

---

# 79. Result response — resumo

```json
{
  "run_id": "...",
  "status": "COMPLETED",
  "validated": true,
  "metrics": {
    "delivery_count": 40,
    "vehicles_used": 6,
    "total_cost_brl": "1742.30",
    "distance_km": "126.40",
    "makespan_minutes": 318,
    "critical_delays": 0,
    "on_time_percentage": 97.5
  },
  "routes": []
}
```

---

# 80. Route response

```json
{
  "id": "...",
  "route_code": "R-01",
  "vehicle": {
    "id": "...",
    "plate": "ABC1D23",
    "type": "CARGO_VAN"
  },
  "team": {
    "driver": {...},
    "helper": {...}
  },
  "metrics": {
    "distance_km": "24.80",
    "duration_minutes": 142,
    "cost_brl": "318.20",
    "weight_utilization_pct": 82.0,
    "volume_utilization_pct": 54.0
  },
  "stops": [],
  "geometry": {...}
}
```

---

# 81. Stop response

```json
{
  "sequence": 1,
  "stop_type": "DELIVERY",
  "delivery": {
    "id": "...",
    "delivery_code": "DLV-NF45872-001",
    "recipient_name": "Hospital Universitário"
  },
  "address": {
    "label": "Avenida da Integração, 420"
  },
  "priority": "HIGH",
  "planned_arrival_at": "...",
  "planned_departure_at": "...",
  "time_window": {
    "start": "...",
    "end": "...",
    "policy": "HARD"
  }
}
```

---

# 82. Route detail endpoint

```text
GET /routes/{route_id}
```

Pode incluir detalhes maiores do que result summary.

---

# 83. Explicação estruturada

Endpoint:

```text
GET /routes/{route_id}/explanation
```

ou:

```text
GET /optimization-runs/{run_id}/decisions
```

Pode retornar:

```json
{
  "vehicle_selection": {
    "reason_codes": [
      "REFRIGERATION_REQUIRED",
      "LOWER_MARGINAL_COST"
    ],
    "facts": []
  }
}
```

---

# 84. Decision Trace

Endpoints:

```text
GET /optimization-runs/{run_id}/trace
GET /optimization-runs/{run_id}/trace/events
```

Pode suportar paginação/timeline.

---

# 85. Replay

Frontend usa:

```text
GET /optimization-runs/{run_id}/trace
```

Não precisa de endpoint específico “replay” se trace já for suficiente.

---

# 86. Aprovar plano

```text
POST /operations/{id}/approve
```

Request opcional:

```json
{
  "optimization_run_id": "..."
}
```

Backend valida se:

- run pertence à revisão;
- solução é válida;
- plano não está OUTDATED.

---

# 87. Dispatch

```text
POST /operations/{id}/dispatch
```

Request:

```json
{
  "revision_id": "...",
  "confirmation": true
}
```

Response:

```json
{
  "status": "DISPATCHED",
  "dispatch_snapshot_id": "..."
}
```

Operação passa a ser imutável.

---

# 88. Troca manual de equipe

Endpoint:

```text
POST /routes/{route_id}/team/simulate
POST /routes/{route_id}/team/apply
```

---

# 89. Simulate team change

Request:

```json
{
  "driver_worker_id": "...",
  "helper_worker_id": "..."
}
```

Response:

```json
{
  "valid": true,
  "current_cost_brl": "230.00",
  "new_cost_brl": "258.00",
  "cost_delta_brl": "28.00",
  "duration_delta_minutes": 0,
  "warnings": []
}
```

---

# 90. Reports

Endpoints:

```text
GET  /reports
POST /operations/{id}/reports
GET  /reports/{report_id}
GET  /reports/{report_id}/download
```

---

# 91. Criar relatório

Request:

```json
{
  "report_type": "DAILY_OPERATION",
  "format": "PDF"
}
```

Response:

```text
202 Accepted
```

com `report_id`.

---

# 92. Report status

```json
{
  "id": "...",
  "status": "COMPLETED",
  "format": "PDF",
  "report_type": "DAILY_OPERATION",
  "download_url": "/api/v1/reports/.../download"
}
```

---

# 93. CSV/XLSX

Download deve definir headers corretos:

```text
Content-Type
Content-Disposition
```

Nome sugerido:

```text
fluxmed_OP-20260913-001_report.pdf
```

---

# 94. Assistente IA

Endpoint principal:

```text
POST /assistant/messages
```

---

# 95. Assistant request

```json
{
  "message": "Por que a van ABC1D23 foi escolhida?",
  "context": {
    "operation_id": "...",
    "route_id": "...",
    "delivery_id": null
  }
}
```

---

# 96. Assistant response

```json
{
  "message": "A van ABC1D23 foi escolhida porque...",
  "provider": "gemini",
  "model": "...",
  "tool_calls": [
    {
      "name": "get_route_details",
      "status": "success"
    }
  ],
  "suggested_actions": []
}
```

---

# 97. Assistant simulation

Pode utilizar:

```text
POST /assistant/simulations
```

ou tool calling interno dentro do mesmo endpoint.

Se houver impacto operacional, resultado deve ser estruturado.

---

# 98. Suggested action

Exemplo:

```json
{
  "type": "SIMULATE_HELPER_REMOVAL",
  "label": "Simular remoção do ajudante",
  "payload": {
    "route_id": "..."
  }
}
```

Frontend nunca aplica automaticamente.

---

# 99. Configurações

Endpoints ADMIN:

```text
GET   /settings
PATCH /settings
```

Expor somente configurações apropriadas.

---

# 100. Settings response

Exemplo:

```json
{
  "fuel_prices": {
    "gasoline_brl_per_l": "6.19",
    "diesel_brl_per_l": "6.05"
  },
  "llm": {
    "provider": "gemini",
    "status": "healthy"
  },
  "optimizer": {
    "algorithm_version": "1.0.0",
    "configuration_version": "production-v1"
  },
  "city": {
    "dataset_version": "1.0.0"
  }
}
```

Não retornar API keys.

---

# 101. Audit log

Endpoint ADMIN opcional:

```text
GET /audit-logs
```

Filtros:

```text
operation_id
user_id
action
date_from
date_to
```

---

# 102. Rate limiting

Aplicar principalmente a:

- login;
- assistant;
- optimize;
- reports pesados.

Não precisa infraestrutura externa na V1.

Implementação simples é aceitável.

---

# 103. Limite de payload

Definir limites razoáveis para:

- XLSX;
- CSV;
- JSON.

Evitar uploads arbitrariamente grandes.

---

# 104. CORS

Produção:

- permitir apenas frontend conhecido;
- não usar wildcard com credenciais.

Desenvolvimento:

- localhost configurado.

---

# 105. Security headers

Backend/proxy deve usar boas práticas básicas.

Não precisa construir sistema customizado complexo.

---

# 106. OpenAPI

FastAPI deve expor documentação automática em ambiente apropriado.

Exemplos:

```text
/docs
/openapi.json
```

Produção pública pode manter ou restringir conforme decisão final.

---

# 107. TypeScript client

Pipeline prevista:

```text
openapi.json
 ↓
client generator
 ↓
apps/web/src/services/generated/
```

Não editar cliente gerado manualmente.

Criar wrappers quando necessário.

---

# 108. Contract tests

Garantir que:

- OpenAPI é válido;
- schemas principais permanecem compatíveis;
- SSE payloads seguem contratos esperados;
- frontend não quebra silenciosamente.

---

# 109. Backward compatibility interna

Durante desenvolvimento pré-v1, pequenas quebras são aceitáveis desde que:

- frontend seja atualizado junto;
- docs sejam atualizadas;
- testes passem.

Após marcar `v1.0.0`, mudanças incompatíveis exigem mais cuidado.

---

# 110. Idempotência

Ações críticas devem ser protegidas.

Exemplos:

```text
POST /operations/{id}/optimize
POST /operations/{id}/dispatch
POST /delivery-imports/{id}/confirm
POST /operations/{id}/reports
```

Pode usar:

```text
Idempotency-Key
```

quando útil.

---

# 111. Conflict response

Exemplo:

```json
{
  "error": {
    "code": "OPTIMIZATION_ALREADY_RUNNING",
    "message": "Já existe uma otimização ativa para esta revisão.",
    "details": {
      "optimization_run_id": "..."
    }
  }
}
```

HTTP:

```text
409 Conflict
```

---

# 112. Optimistic concurrency

Pode ser adotada para edição de operação se conflitos aparecerem.

Exemplo:

```text
revision_number
```

No início, não criar mecanismo sofisticado sem necessidade.

---

# 113. Cache headers

Dados estáticos da cidade podem usar:

```text
ETag
Cache-Control
```

quando útil.

Dados operacionais devem ser tratados com maior cautela.

---

# 114. Mapa e payload grande

Se `/map` ficar pesado:

separar em:

```text
/cities/{id}/map/base
/cities/{id}/map/roads
/cities/{id}/map/facilities
```

Não fragmentar antes de medir.

---

# 115. Compressão

Permitir gzip/brotli na plataforma quando disponível.

Útil para GeoJSON.

---

# 116. Download de relatório

Pode usar URL direta da API.

Não é necessário introduzir object storage na V1 se arquivos pequenos puderem ser gerados sob demanda ou temporariamente.

Se persistência de arquivo for necessária, documentar depois.

---

# 117. Erro do provider LLM

Response:

```text
503 Service Unavailable
```

com:

```text
LLM_PROVIDER_UNAVAILABLE
```

Core permanece funcional.

---

# 118. Erro do banco

Quando persistência não estiver disponível:

```text
503
DATABASE_UNAVAILABLE
```

Não responder sucesso falso.

---

# 119. Timeout do optimizer

Se houver solução válida:

run pode finalizar normalmente com:

```text
stop_reason = TIME_BUDGET
```

Se não houver solução válida:

```text
OPTIMIZATION_TIMEOUT_NO_SOLUTION
```

---

# 120. Erro de SolutionValidator

```text
500
OPTIMIZER_VALIDATION_MISMATCH
```

e run falha.

Nunca retornar resultado inválido.

---

# 121. Endpoint de benchmarks

Não criar endpoint público para benchmark na V1.

Benchmarks rodam via:

```text
scripts
CLI
notebooks
```

---

# 122. Endpoint de parâmetros do GA

Não expor edição de parâmetros do GA ao PLANNER.

Settings pode mostrar versão ativa, apenas leitura.

---

# 123. Endpoint de versão

Opcional:

```text
GET /version
```

Response:

```json
{
  "app_version": "0.1.0",
  "api_version": "v1",
  "optimizer_version": "1.0.0",
  "city_dataset_version": "1.0.0"
}
```

Útil para demo e debugging.

---

# 124. API de replay

Não criar endpoints redundantes.

Preferir reutilizar:

```text
trace
+
result
```

---

# 125. WebSocket

Não usar na V1.

SSE cobre progresso de otimização.

WebSocket fica para futura telemetria/GPS.

---

# 126. GraphQL

Não usar.

REST é suficiente e mais simples para o projeto.

---

# 127. gRPC

Não usar.

Não há microserviços que justifiquem.

---

# 128. Regras de naming

Paths:

```text
kebab-case ou plural nouns consistentes
```

JSON:

```text
snake_case
```

Recomendação principal:

```text
snake_case
```

para alinhar Python/Pydantic.

Frontend adapta tipos sem renomear arbitrariamente.

---

# 129. Status enums

Valores em uppercase snake case:

```text
HIGH_PRESSURE
HARD
REFRIGERATED
```

---

# 130. Nullable fields

Diferenciar:

- campo ausente;
- campo `null`;
- campo vazio.

Pydantic deve definir semântica clara.

---

# 131. Partial updates

`PATCH` deve aceitar apenas campos alteráveis.

Nunca permitir mudar via PATCH:

- id;
- created_at;
- algorithm_version;
- immutable snapshot.

---

# 132. DELETE

Usar DELETE apenas quando:

- recurso ainda não possui histórico;
- remoção é conceitualmente válida.

Para Vehicle/Worker histórico:

```text
deactivate
```

é preferível.

---

# 133. Bulk actions

Evitar endpoints bulk genéricos na V1.

Adicionar somente onde há necessidade clara:

- import;
- resource selection;
- scenario generation.

---

# 134. Segurança de dados

Mesmo usando dados sintéticos na demo:

- não logar senhas;
- não logar tokens;
- não logar secrets;
- limitar exposição de dados de usuário.

---

# 135. API tests prioritários

Cobrir:

- auth;
- operations CRUD/state;
- import;
- scenario generation;
- resources;
- address search;
- road overrides;
- preflight;
- optimize start;
- SSE;
- result;
- approve;
- dispatch;
- reports;
- assistant degraded state.

---

# 136. Smoke flow

Fluxo mínimo:

```text
login
 ↓
GET city
 ↓
create operation
 ↓
generate scenario 20
 ↓
select resources
 ↓
validate
 ↓
optimize
 ↓
get result
```

---

# 137. Critério de aceite da API

A API V1 está pronta quando:

- OpenAPI descreve os endpoints;
- frontend consegue consumir sem contratos manuais conflitantes;
- erros são tipados;
- auth funciona;
- operações funcionam;
- cidade funciona;
- optimization SSE funciona;
- reports funcionam;
- assistant funciona;
- testes passam.

---

# 138. Ordem recomendada de implementação

```text
1. health
2. auth
3. operations
4. city metadata/map
5. deliveries
6. vehicles
7. workers
8. resource selection
9. scenario generation
10. address search
11. road overrides
12. preflight
13. optimization run
14. SSE
15. result/routes
16. approval/dispatch
17. reports
18. assistant
19. settings
```

---

# 139. O que não fazer

Não:

- expor banco diretamente ao frontend;
- usar endpoints RPC genéricos como `/execute`;
- retornar ORM cru;
- criar GraphQL paralelo;
- criar WebSocket sem necessidade;
- expor API key de LLM;
- permitir frontend enviar fitness weights livremente;
- permitir alterar snapshot despachado;
- transformar API em gateway de microserviços inexistentes.

---

# 140. Regra final

> A API do FluxMed deve refletir o domínio e os fluxos reais do produto, mantendo contratos claros entre React e FastAPI sem transformar a camada HTTP em lugar de regras de negócio.

O backend é a autoridade operacional; o frontend é o consumidor tipado dessas decisões.
