# Airflow Orchestration (ASP)

A **self-contained** Apache Airflow setup that orchestrates the project's existing
DVC pipeline. It runs independently of the main app — it does **not** touch
`docker-compose.yaml`, `dvc.yaml`, or any service code. Lives under `infra/airflow/`.

There is **one DAG**: **`asp_retraining`** (`dags/asp_retraining_dag.py`) — the complete
retraining flow, all steps implemented. Each step launches one of the project's images as a
short-lived container (the final reload step calls the backend's reload endpoint):

| Step | Task | Status |
|------|------|--------|
| 1 | `check_and_ingest_data` (+ `build_dataset`) | ✅ implemented (Docker) |
| 3 | `validate_data` — quality + shape checks | ✅ implemented (runner image) |
| 2 | `version_dataset_dvc` — `dvc commit` + `dvc push` | ✅ implemented (needs DagsHub creds) |
| 4 | `train_and_log_mlflow` — train + log + register candidate | ✅ implemented |
| 5 | `compare_against_champion` — `promote compare` (read-only verdict) | ✅ implemented |
| 6 | `promote_to_production` — `promote promote` (reuses `promote_if_better`) | ✅ implemented |
| 7 | `reload_fastapi` — POSTs `/api/v1/model/reload` | ✅ implemented (set `FASTAPI_RELOAD_URL`) |
| 8 | success/failure alerts — **Slack** (+ logging) | ✅ implemented (set `SLACK_WEBHOOK_URL`) |

> **Schedule:** the DAG runs **once a year (00:00 on 1 Jan)** to match the annual BAAC batch
> (`schedule="0 0 1 1 *"`). To trigger manually only, comment that line and uncomment `schedule=None`
> in the DAG. **Alerts** post to Slack when `SLACK_WEBHOOK_URL` is set (lenient — logs only if unset).

> **Promotion = "Option B":** training only trains + logs + **registers** a candidate; the DAG
> governs promotion via `services.training.promote` (compare → promote, reusing the tested
> `promote_if_better`). Set `ASP_PROMOTE_AFTER_TRAIN=1` to let training self-promote instead (off by
> default). Steps 4–6 need `DAGSHUB_USER_TOKEN` in `.env`.

> The retraining DAG runs `validate_data` **before** `version_dataset_dvc` on purpose (don't
> version data that failed QA). Swap those two lines in the DAG to match a strict 2-before-3 order.

Learning guides (what/why + guided read + do-it-yourself steps + Windows notes):
- `infra/airflow/docs/phase-8-airflow-orchestration.md` — the DAG, Option B promotion, and the
  validated local-run playbook (§8.9 lists the five issues a fresh Windows/Docker-Desktop run hits).
- `infra/airflow/docs/HOW-TO-VERIFY.md` — the run-it-yourself checklist.

---

## Prerequisites

- **Docker Desktop** running.
- The project's images built once (from the repo root):

  ```bash
  docker compose --profile build-only build     # builds asp-training:latest
  docker compose build backend                  # builds asp-backend:latest
  # helper image for the retraining DAG's DVC + validation tasks:
  docker build -f infra/airflow/Dockerfile.runner -t asp-airflow-runner:latest infra/airflow
  ```

  Check they exist: `docker images | grep asp-` → you should see `asp-backend`,
  `asp-training`, and (for the retraining DAG) `asp-airflow-runner`.

---

## Quickstart

From **inside this `infra/airflow/` folder**:

```bash
# 1) Configure the host path
cp .env.example .env
#    edit .env -> set HOST_PROJECT_ROOT to the ABSOLUTE path of the repo
#    Windows example (forward slashes!):
#    HOST_PROJECT_ROOT=C:/Users/you/Documents/GitHub/accident-severity-predictor

# 2) Build + start Airflow
docker compose -f docker-compose.airflow.yml up -d --build

# 3) Get the auto-generated admin password
docker compose -f docker-compose.airflow.yml logs airflow | grep -i "password"
#    (or: docker exec asp-airflow cat /opt/airflow/standalone_admin_password.txt)

# 4) Open the UI
#    http://localhost:8080     user: admin     password: (from step 3)

# 5) Run the pipeline
#    In the UI: enable the "asp_retraining" DAG, then click ▶ "Trigger DAG".
#    Watch the tasks go green. Click a task -> Logs to see its output.

# 6) Stop Airflow (keeps your data/artifacts on the host)
docker compose -f docker-compose.airflow.yml down
```

Trigger from the command line instead of the UI, if you prefer:

```bash
docker exec asp-airflow airflow dags trigger asp_retraining
```

---

## Verify it's healthy (no errors)

```bash
# a) The compose file is valid
docker compose -f docker-compose.airflow.yml config >/dev/null && echo "compose OK"

# b) The container is up
docker compose -f docker-compose.airflow.yml ps

# c) The DAGs parsed with NO import errors (should print nothing / empty list)
docker exec asp-airflow airflow dags list-import-errors

# d) The DAGs are registered
docker exec asp-airflow airflow dags list | grep asp

# e) After a run: every task should be "success"
docker exec asp-airflow airflow tasks states-for-dag-run asp_retraining <run_id>
```

If `list-import-errors` shows anything, a DAG file has a problem — read the message,
fix it under `dags/`, and Airflow reloads it automatically within ~30s.

---

## Troubleshooting

| Symptom | Cause / Fix |
|---------|-------------|
| **Build** fails: `groupadd: invalid group ID 'appuser'` (asp-training) | Windows: `UID`/`GID` unset and the training service has no default. Create a **root** `.env` with `UID=1000` / `GID=1000` before building (or `$env:UID="1000"; $env:GID="1000"`). |
| `download_data` / `check_and_ingest_data` fails: `Failed to resolve 'www.data.gouv.fr'` | Container DNS can't resolve (corp net / Docker Desktop). Fixed in-code via `dns=["8.8.8.8","8.8.4.4"]` on every task; if `8.8.8.8` is blocked, use your own resolver. |
| `make_dataset` fails: `Cannot save file into a non-existent directory: '/app/data/processed'` | Host bind-mount shadows the build-time dir. Fixed in-code: the task runs `mkdir -p /app/data/processed && …`. |
| `train_evaluate` / `train_and_log_mlflow` fails: DagsHub OAuth `JSONDecodeError` | Training calls `dagshub.init()`; headless container can't OAuth. Set `DAGSHUB_USER_TOKEN` in `.env` (the DAG passes it through). |
| Task fails: `image not found` | Build the images first (see Prerequisites) — incl. `asp-airflow-runner` for the retraining DAG. |
| Task fails: `Cannot connect to the Docker daemon` | The socket mount or permissions. On Docker Desktop it usually just works; on Linux set `DOCKER_GID` in `.env` to `getent group docker \| cut -d: -f3`. |
| Task fails: mount source path does not exist | `HOST_PROJECT_ROOT` in `.env` is wrong. Use the ABSOLUTE host path, forward slashes on Windows. |
| `check_and_ingest_data` fails on `import requests` | It must use `asp-backend:latest` (has requests). Don't point it at the training image. |
| `version_dataset_dvc` fails / `403 Forbidden` | Needs DagsHub creds — set `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` (both = your DagsHub token) in `.env`. Verify success with `N files pushed` in the log + `dvc status -c`. |
| `.env` change not taking effect | Env is injected at container start — re-run `docker compose -f docker-compose.airflow.yml up -d` to recreate the container. |
| Can't find the admin password | `docker exec asp-airflow cat /opt/airflow/simple_auth_manager_passwords.json.generated` (older builds: `/opt/airflow/standalone_admin_password.txt`). User is `admin`. |
| Port 8080 already in use | Change the left side of `"8080:8080"` in the compose file (e.g. `"8081:8080"`). |

---

## What this does NOT do (by design)

- No MLflow logging (that's a teammate's feature; a hook is marked in the retraining DAG's
  `train_and_log_mlflow` task, and steps 5–6 are placeholders for later).
- Step 7 posts to the backend's `POST /api/v1/model/reload`; it's **lenient** — if the backend
  isn't reachable it logs a warning and the DAG still succeeds (the model goes live on the
  backend's next start). Set `FASTAPI_RELOAD_URL` in `.env` and run the backend to enable it.
- The DAG needs no `dvc pull` — it regenerates everything from the public data
  source. To version the produced model, the retraining DAG's `version_dataset_dvc` runs
  `dvc push` (with creds), or run `uv run dvc push` from the repo root manually.
