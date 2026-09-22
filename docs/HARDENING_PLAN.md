# FluxMed — Phase 18 Hardening Plan

**Branch:** `chore/v1-hardening`  
**Goal:** make the V1 stable, safe and presentation-ready without changing the academic optimizer evidence.  
**Status:** **closed on 2026-09-22** after full local regression and manual end-to-end validation.

## Closure evidence

Phase 18 closed with the current hardening branch green locally and the complete V1 presentation flow validated against the real application.

### Final local regression

Backend:

- `ruff check src tests` — green;
- `ruff format --check src tests` — 173 files formatted;
- `mypy src` — green across 126 source files;
- `pytest -q` — **169 passed**, 5 non-blocking dependency/deprecation warnings.

Frontend:

- `npm run lint` — green;
- `npm run typecheck` — green;
- `npm test -- --run` — **10 test files / 26 tests passed**;
- `npm run build` — green; the remaining Vite chunk-size notice is a non-blocking optimization warning.

### Final manual E2E

Validated in order with operation `OP-20260922-001`:

`login -> operation -> deliveries -> resources -> closure/preflight -> optimization -> result -> assistant -> report -> approve -> dispatch`.

Observed final result for the validated scenario:

- 40 deliveries;
- 5 vehicles used;
- total cost `R$ 944,22`;
- total distance about `265,77 km`;
- makespan about `5h45`;
- 0 critical delays;
- 100% on time;
- reports generated and downloaded as PDF/XLSX/CSV;
- transition `OPTIMIZED -> APPROVED -> DISPATCHED` persisted successfully;
- post-dispatch editing, reoptimization and team mutation controls are blocked/frozen.

### Assistant hardening completed during final E2E

The final E2E exposed two real assistant issues and both were fixed before closure:

- aggregate questions now receive complete operation-summary grounding instead of a single specialized fragment;
- grounded final replies use a direct Gemini `generateContent` REST call with an explicit timeout instead of the SDK path that was observed retrying/hanging for multiple minutes.

The assistant was then manually revalidated against the real Gemini provider, including the aggregate operation summary and the follow-up question identifying `R-01` as the route with 14 deliveries.

## Execution rule

Phase 18 is split into small, locally validated increments. Avoid microcommits and avoid rerunning
the expensive Phase 17 benchmark unless optimizer behavior changes.

The hardening branch is stacked on `feat/academic-benchmarks` while the earlier phase branches
remain pending merge because GitHub Actions account quota/billing has prevented runners from
starting. Merge order remains Phase 16 -> Phase 17 -> Phase 18.

## Increment 1 — Assistant UX — validated

Manual validation with the real Gemini provider confirmed improved readability for long operational
answers, lists, emphasis and inline code. Keyboard behavior and the copy-history workflow remain
intact.

- render a safe Markdown subset without raw HTML;
- preserve structured-source provenance;
- auto-scroll to the newest response;
- Enter sends and Shift+Enter inserts a newline;
- improve thinking/loading feedback;
- keep the composer visible while reading long answers;
- honor reduced-motion preferences;
- preserve the existing copy-history Markdown export.

No new frontend dependency is introduced in this increment.

## Increment 2 — frontend shell and accessibility — validated

Local lint, typecheck, unit tests and production build are green. React Router future warnings are
no longer emitted by the test suite.

- opt into the React Router v7 transition flags already supported by the current v6 release;
- remove stale phase-specific copy from the assistant surface;
- extend keyboard focus styling and inherited typography to textareas/selects;
- keep behavior unchanged while reducing presentation/test warnings.

## Increment 3 — frontend toolchain hygiene — validated

Local lint, typecheck, 23 frontend tests and production build are green after the dependency
updates. Both `npm audit --omit=dev` and the full `npm audit` report zero known vulnerabilities.
The generated `package-lock.json` is versioned and CI now installs exactly that dependency graph
with `npm ci`.

- pin TypeScript to the newest line supported by the current @typescript-eslint parser;
- remove development-only footer copy from the presentation shell;
- address production dependency advisories with minimum patched MapLibre and React Router releases;
- production audit is clean after the runtime dependency updates;
- update Vite/Vitest to patched development-toolchain lines and revalidate lint, typecheck, tests, build and audit;
- validate the resulting lockfile and runtime before versioning it;
- version the lockfile and move frontend CI to reproducible `npm ci` installs.

## Phase 18 hardening record

### Frontend

- audit spacing, typography, tables, empty/loading/error states and responsive behavior;
- audit maps and route colors for presentation consistency;
- review keyboard navigation, focus treatment and accessible labels;
- remove stale demo/development copy where it harms the final presentation.

### Backend

Database outage handling has been manually validated end to end: liveness stays at HTTP 200 while
readiness returns HTTP 503 with a sanitized payload, and readiness recovers to HTTP 200 after
PostgreSQL comes back without restarting the API.

- database failures now return a sanitized 503 response instead of exposing driver exceptions;
- PostgreSQL connection attempts are bounded by a short configurable timeout so readiness checks fail fast instead of hanging;
- add liveness/readiness separation so a database outage does not make the API process itself unobservable;
- startup trace recovery no longer prevents process startup when PostgreSQL is temporarily unavailable;
- report generation/retry failures now preserve history while exposing only sanitized public errors;
- SSE recovery rehydrates persisted trace data after connection loss and de-duplicates events by sequence;
- optimizer runtime failures now expose stable public error codes/messages without persisting raw exception text;
- completed-but-unvalidated runs are rejected by the result read boundary;
- review error taxonomy and transaction boundaries;
- optimization start rejects duplicate active runs, cancellation is terminal-safe, and report retry is append-only and restricted to failed reports;
- report creation remains append-only by design; callers that require network-retry idempotency should add an explicit idempotency key in a future API version;
- production mode now forces Secure session cookies and restricts SameSite to lax/strict;
- V1 keeps browser sessions same-origin by design instead of enabling permissive credentialed CORS;
- delivery imports now use a bounded streaming read and normalized filenames before parsing;
- request logs now carry a server-generated correlation ID, log only method/path/status/duration, and omit query strings and bodies;
- authentication audit logs record success/failure/logout without email, password or session token values;
- unexpected errors return a generic 500 payload with a correlation ID instead of exception details;
- health endpoints remain intentionally payload-minimal;
- review audit events, log redaction and health endpoints — core request/auth/error paths covered;
- expensive assistant calls now have a database-backed per-user rolling-window rate guard, shared across application instances;
- verify failures do not leak provider secrets or operational payloads — provider/report/optimizer/generic error paths use sanitized public messages;
- dispatch is terminal-safe and freezes operation edits, reoptimization and route-team mutations;
- assistant aggregate grounding and real-provider latency behavior were corrected and revalidated in the final E2E.

### Resilience

Validated explicit failure behavior for:

- LLM unavailable;
- database unavailable — validated manually with stop/restart recovery;
- report generation failure — sanitized failure state and retry history covered by automated tests;
- SSE disconnect/reconnect — browser reconnect uses persisted event IDs, a one-second retry hint, and REST rehydration closes any event gap;
- optimizer failure/cancellation — failures are sanitized, cancellation restores the operation and cancelled runs cannot expose a result;
- persisted-result validation mismatch — only COMPLETED + validated runs are readable as persisted optimization results.

### Security

- frontend lockfile is versioned and PR CI uses `npm ci`;
- enable dependency/security scanning with an economical CI policy;
- upload/import validation — bounded upload size and filename normalization implemented;
- integration tests refuse to run against a non-test database, preventing destructive seed/cleanup operations from touching demo data;
- CORS/session/cookie production settings — Secure cookies are forced in production; cross-origin cookie auth is intentionally not enabled in V1;
- assistant provider spend is protected by a configurable database-backed per-user request limit;
- provider/report/optimizer/generic errors expose sanitized public messages rather than secrets or raw operational payloads.

### Final E2E — validated

`login -> operation -> deliveries -> resources -> closure -> optimization -> result -> assistant -> report -> approve -> dispatch`.

## Acceptance — satisfied

Phase 18 is closed: there are no known blocking bugs in the validated V1 flow, presentation-critical
flows are stable, local lint/type/test/build checks are green, and the complete manual E2E has been
executed successfully. Any unavailable GitHub Actions evidence remains an infrastructure/account
limitation and must be documented rather than silently treated as passing CI.
