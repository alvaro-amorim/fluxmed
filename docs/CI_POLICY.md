# CI policy

FluxMed uses staged CI to preserve GitHub Actions minutes without weakening the merge gate.

## Development loop

1. Develop and run the relevant checks locally.
2. Fix lint, formatting, type and test failures before pushing.
3. Prefer one coherent commit/push for a logical change instead of several microcommits.
4. Keep the pull request as Draft while the phase is under active development.
5. Mark the PR Ready for review only after the local suite is green.

## Draft pull requests

On PR opening, update or reopening, path-scoped fast checks run for both Draft and Ready PRs:

- `PR Backend Fast` runs when `apps/api/**` or its own workflow file changes.
- `PR Frontend Fast` runs when `apps/web/**` or its own workflow file changes.
- Backend fast checks skip tests marked `integration`.
- Frontend fast checks skip the production build and Playwright E2E.
- `concurrency.cancel-in-progress` cancels obsolete runs when a newer push arrives.

The fast workflows use path filters. Full CI follows the PR/main/manual triggers below, including documentation-only changes when those triggers apply.

## Full CI

`Full CI` runs the complete backend, frontend and demo-login E2E suites only when:

- a PR is Ready for review;
- a Ready PR receives new commits;
- a maintainer starts it manually with `workflow_dispatch`; or
- changes reach `main`.

For draft PR events the Full CI jobs are skipped before runner allocation.

All full jobs have explicit timeouts. Backend pytest also enables a faulthandler timeout so a stalled integration test produces a stack trace instead of consuming runner hours.

## Dependency caches

Python uses the native `setup-python` pip cache keyed by `apps/api/pyproject.toml`.

The frontend versions `apps/web/package-lock.json`. Full CI and the demo-login E2E job install with `npm ci --prefer-offline --no-audit --no-fund` and cache npm downloads keyed by that lockfile. Keep the lockfile synchronized with `package.json`; intentional dependency changes must update both.

## Merge rule

Do not merge a feature phase until:

- the relevant local suite is green;
- the PR is Ready for review;
- Full CI has executed successfully, unless GitHub Actions itself is unavailable because of an account/billing/quota condition that is documented on the PR.

A CI failure caused before any job step starts is infrastructure/account evidence, not a demonstrated code failure, but it must be documented explicitly.
