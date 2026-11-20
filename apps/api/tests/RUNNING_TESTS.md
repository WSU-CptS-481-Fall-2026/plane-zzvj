# Running the API Test Suite

This guide covers running the Django/pytest suite for `apps/api` inside Docker via `docker-compose-test.yml` at the repo root. The compose file boots an isolated stack — Postgres, Valkey (Redis), RabbitMQ, MinIO — with tmpfs-backed data dirs, so every run begins from a clean slate and a single teardown command removes everything.

For the test layout, markers, and fixtures, see the [testing guide](../plane/tests/TESTING_GUIDE.md) and [test suite overview](../plane/tests/README.md).

## Prerequisites

- Docker and Docker Compose v2 (`docker compose ...`)
- Env files generated via the setup script:

  ```bash
  ./setup.sh
  ```

  This copies `apps/api/.env.example` → `apps/api/.env` (along with the other app env files). The compose file reads `apps/api/.env`, so this step must run **before** the first `docker compose` invocation.

## Running the suite

All commands are run from the repo root.

### Full suite

```bash
docker compose -f docker-compose-test.yml up \
  --build \
  --abort-on-container-exit \
  --exit-code-from api-tests
```

- `--build` rebuilds the `api-tests` image when `Dockerfile.dev` or `requirements/*.txt` change.
- `--abort-on-container-exit` stops the dependency services as soon as `api-tests` exits.
- `--exit-code-from api-tests` propagates pytest's exit code so this works in CI.

### Filtered runs

Use `docker compose run` to override the default `pytest` command. Anything you pass after the service name is forwarded to pytest.

```bash
# Only unit tests (marker defined in pytest.ini)
docker compose -f docker-compose-test.yml run --rm --build api-tests pytest -m unit

# A single directory, filtered by name
docker compose -f docker-compose-test.yml run --rm api-tests \
  pytest plane/tests/unit -k "test_workspace"

# Single file with verbose output
docker compose -f docker-compose-test.yml run --rm api-tests \
  pytest plane/tests/unit/models/test_workspace.py -vv
```

The available markers (`unit`, `contract`, `smoke`, `slow`) are declared in `apps/api/pytest.ini`.

### State group filters (#5728)

Invalid state groups now return HTTP 400, including mixed input like `completed,hello`.
Valid groups with no matching issues still return HTTP 200 with empty results.

For GET requests, use `state_group=completed,started` or
`filters={"state_group__in":["completed","started"]}`.
JSON `state_group` and `state_group__exact` take one value and return HTTP 400 for arrays.

Run the tests:

```bash
docker compose -f docker-compose-test.yml run --rm api-tests \
  pytest plane/tests/unit/utils/test_issue_filters.py \
  plane/tests/unit/utils/test_issue_datetime_filters.py \
  plane/tests/contract/app/test_issue_state_group_filters.py
```

### Workspace invitation resend (#2372)

These tests check resend permissions, invitation status, cooldowns and retries. No real emails are sent.

```bash
docker compose -f docker-compose-test.yml run --rm api-tests \
  pytest plane/tests/contract/app/test_workspace_invitation_resend.py
```

### Deliverable 2 filtering regression suite

From the repository root, define the seven test files and the Docker command in Bash or Zsh.
The invitation and calendar-date tests are part of the original 115-case comparison.

```bash
filter_tests=(
  plane/tests/unit/utils/test_issue_filters.py
  plane/tests/unit/utils/test_filter_backend.py
  plane/tests/unit/utils/test_filter_converters.py
  plane/tests/unit/utils/test_issue_datetime_filters.py
  plane/tests/contract/app/test_issue_complex_filters.py
  plane/tests/contract/app/test_issue_state_group_filters.py
  plane/tests/contract/app/test_workspace_invitation_resend.py
)
filter_stack=(docker compose -p plane-filter-review -f docker-compose-test.yml)
filter_pytest=(python -m pytest -o 'addopts=--strict-markers --nomigrations' -p no:cacheprovider -q --tb=short)
```

Run the tests with the repository's test image.

```bash
"${filter_stack[@]}" run --rm --build -T api-tests "${filter_pytest[@]}" "${filter_tests[@]}"
```

To collect statement and branch coverage with the same tests, run this version. It writes the JSON coverage and JUnit results to a temporary host directory.

```bash
filter_results=$(mktemp -d)
"${filter_stack[@]}" run --rm --build -T -v "$filter_results:/results" -e COVERAGE_FILE=/tmp/.coverage api-tests \
  "${filter_pytest[@]}" "${filter_tests[@]}" \
  --cov=plane.utils.issue_filters --cov=plane.utils.filters.filter_backend --cov=plane.utils.filters.converters \
  --cov-branch --cov-report=term-missing --cov-report=json:/results/coverage.json --junitxml=/results/tests.xml
echo "$filter_results"
"${filter_stack[@]}" down --volumes
```

In `coverage.json`, use `covered_branches / num_branches` for branch coverage and `covered_lines / num_statements` for line coverage. The terminal combines both under `Cover`.

Check `tests.xml` for failures. This run skips migrations.

### Teardown

```bash
docker compose -f docker-compose-test.yml down -v
```

`-v` removes the ephemeral volumes and the `test_env` network. Because the data directories are tmpfs, no host state survives a teardown — every run starts clean. Run this between unrelated test sessions to free Docker resources.

## How it works

| Service      | Image                                                | Purpose                                       |
| ------------ | ---------------------------------------------------- | --------------------------------------------- |
| `test-db`    | `postgres:15.7-alpine`                               | Application database                          |
| `test-redis` | `valkey/valkey:7.2.11-alpine`                        | Cache / Celery broker                         |
| `test-mq`    | `rabbitmq:3.13.6-management-alpine`                  | Task queue                                    |
| `test-minio` | `docker.io/pgsty/minio:RELEASE.2026-08-04T00-00-00Z` | S3-compatible object storage                  |
| `api-tests`  | built from `apps/api/Dockerfile.dev`                 | Installs `requirements/test.txt`, runs pytest |

All four dependencies expose health checks; `api-tests` waits for `service_healthy` on each via `depends_on`, so pytest only starts once the stack is ready.

Test-time env overrides live in the compose file itself (`POSTGRES_HOST=test-db`, `REDIS_URL=redis://test-redis:6379/`, `AWS_S3_ENDPOINT_URL=http://test-minio:9000`, `DJANGO_SETTINGS_MODULE=plane.settings.test`). Everything else is inherited from `apps/api/.env`.

## Troubleshooting

- **`./apps/api/.env: no such file or directory`** — run `./setup.sh` from the repo root.
- **Port already in use** — none of the test services publish host ports; if you see this it's coming from a different compose stack. Stop the local stack (`docker compose -f docker-compose-local.yml down`).
- **Stale image after dependency changes** — rebuild explicitly: `docker compose -f docker-compose-test.yml build --no-cache api-tests`.
- **MinIO bucket missing** — the `test-minio` entrypoint creates the bucket named by `AWS_S3_BUCKET_NAME` (default `uploads`). Change the value in `apps/api/.env` and re-run.
- **Database state leaking between runs** — confirm you ran `down -v` (not just `down`). The tmpfs mounts are torn down with the container, but the network and any externally created volumes need `-v` to clear.
