# Airflow Orchestration (ASP)

A **self-contained** Apache Airflow setup that orchestrates the project's existing
DVC pipeline. It runs independently of the main app — it does **not** touch
`docker-compose.yaml`, `dvc.yaml`, or any service code. Lives under `infra/airflow/`.

There are **two DAGs**:

**1. `asp_pipeline` (minimal core)** — `dags/asp_pipeline_dag.py`. Three steps, each launching
one of the project's **existing** images as a short-lived container:

```
download_data  ->  make_dataset  ->  train_evaluate
 (asp-backend)     (asp-training)     (asp-training)
```

**2. `asp_retraining` (full pipeline)** — `dags/asp_retraining_dag.py`. The complete 8-step
retraining flow. In-scope steps are implemented; steps that depend on a teammate's component
are clearly-marked placeholders that succeed as no-ops until wired in:

| Step | Task | Status |
|------|------|--------|
| 1 | `check_and_ingest_data` (+ `build_dataset`) | ✅ implemented (Docker) |
| 3 | `validate_data` — quality + shape checks | ✅ implemented (runner image) |
| 2 | `version_dataset_dvc` — `dvc commit` + `dvc push` | ✅ implemented (needs DagsHub creds) |
| 4 | `train_and_log_mlflow` — train + evaluate | ✅ training; 🟡 MLflow = hook |
| 5 | `compare_against_champion` | 🟡 placeholder (needs MLflow) |
| 6 | `promote_to_production` | 🟡 placeholder (needs MLflow) |
| 7 | `reload_fastapi` | 🟡 placeholder (needs a backend reload endpoint) |
| 8 | success/failure alerts | ✅ implemented (DAG callbacks) |

> The retraining DAG runs `validate_data` **before** `version_dataset_dvc` on purpose (don't
> version data that failed QA). Swap those two lines in the DAG to match a strict 2-before-3 order.

Full explanation: see `learning-guides/phase-8-airflow-orchestration.md`.

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

# 5) Run a pipeline
#    In the UI: enable the "asp_pipeline" (or "asp_retraining") DAG, then click ▶ "Trigger DAG".
#    Watch the tasks go green. Click a task -> Logs to see its output.

# 6) Stop Airflow (keeps your data/artifacts on the host)
docker compose -f docker-compose.airflow.yml down
```

Trigger from the command line instead of the UI, if you prefer:

```bash
docker exec asp-airflow airflow dags trigger asp_pipeline
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
docker exec asp-airflow airflow tasks states-for-dag-run asp_pipeline <run_id>
```

If `list-import-errors` shows anything, a DAG file has a problem — read the message,
fix it under `dags/`, and Airflow reloads it automatically within ~30s.

---

## Troubleshooting

| Symptom | Cause / Fix |
|---------|-------------|
| Task fails: `image not found` | Build the images first (see Prerequisites). |
| Task fails: `Cannot connect to the Docker daemon` | The socket mount or permissions. On Docker Desktop it usually just works; on Linux set `DOCKER_GID` in `.env` to `getent group docker \| cut -d: -f3`. |
| Task fails: mount source path does not exist | `HOST_PROJECT_ROOT` in `.env` is wrong. Use the ABSOLUTE host path, forward slashes on Windows. |
| `check_and_ingest_data` fails on `import requests` | It must use `asp-backend:latest` (has requests). Don't point it at the training image. |
| `version_dataset_dvc` fails | Needs DagsHub creds — set `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` in `.env`. |
| Can't find the admin password | `docker exec asp-airflow cat /opt/airflow/standalone_admin_password.txt` |
| Port 8080 already in use | Change the left side of `"8080:8080"` in the compose file (e.g. `"8081:8080"`). |

---

## What this does NOT do (by design)

- No MLflow logging (that's a teammate's feature; a hook is marked in the retraining DAG's
  `train_and_log_mlflow` task, and steps 5–6 are placeholders for later).
- No FastAPI reload endpoint (step 7 is a placeholder until the backend exposes one).
- The `asp_pipeline` DAG needs no `dvc pull` — it regenerates everything from the public data
  source. To version the produced model, the retraining DAG's `version_dataset_dvc` runs
  `dvc push` (with creds), or run `uv run dvc push` from the repo root manually.
