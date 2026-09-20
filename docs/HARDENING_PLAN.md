# FluxMed — Phase 18 Hardening Plan

**Branch:** `chore/v1-hardening`  
**Goal:** make the V1 stable, safe and presentation-ready without changing the academic optimizer evidence.

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

## Remaining Phase 18 work

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
- review error taxonomy and transaction boundaries;
- review idempotency and write retries;
- review audit events, log redaction and health endpoints;
- add bounded request/rate protections where appropriate;
- verify failures do not leak provider secrets or operational payloads.

### Resilience

Validate explicit failure behavior for:

- LLM unavailable;
- database unavailable — validated manually with stop/restart recovery;
- report generation failure;
- SSE disconnect/reconnect;
- optimizer failure/cancellation;
- persisted-result validation mismatch.

### Security

- frontend lockfile is versioned and PR CI uses `npm ci`;
- enable dependency/security scanning with an economical CI policy;
- review upload/import validation;
- review CORS/session/cookie production settings;
- run secret and static-analysis checks before release.

### Final E2E

Revalidate:

`login -> operation -> deliveries -> resources -> closure -> optimization -> result -> assistant -> report -> dispatch`.

## Acceptance

Phase 18 closes when there are no known blocking bugs, the presentation flows are stable, local
lint/type/test/build checks are green, and any unavailable GitHub Actions evidence is documented as
infrastructure/account limitation rather than silently ignored.
