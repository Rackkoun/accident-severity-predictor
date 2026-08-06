"""
ASP RETRAINING DAG — the full production retraining pipeline (8 steps).

This is the "target" pipeline (the simpler `asp_pipeline_dag.py` is the minimal core).
It lays out ALL eight retraining steps in order. Steps fully in the Airflow owner's
lane are IMPLEMENTED; steps that depend on a teammate's component (MLflow, the FastAPI
reload endpoint) are clearly-marked PLACEHOLDER tasks that succeed as no-ops until the
teammate plugs their logic in — so the DAG runs end-to-end today and shows the whole flow.

Step map (your 8-task spec):
  1. check_and_ingest_data     -> ingest new yearly data            [IMPLEMENTED, Docker]
     (+ build_dataset)         -> build processed X/y (needed prep) [IMPLEMENTED, Docker]
  3. validate_data             -> data quality + shape checks       [IMPLEMENTED, Docker+runner]
  2. version_dataset_dvc       -> version dataset with DVC          [IMPLEMENTED, needs creds]
  4. train_and_log_mlflow      -> train + evaluate + REGISTER cand. [IMPLEMENTED, Docker]
  5. compare_against_champion  -> compare candidate vs champion     [IMPLEMENTED, Docker (promote compare)]
  6. promote_to_production     -> promote in MLflow Registry        [IMPLEMENTED, Docker (promote promote)]
  7. reload_fastapi            -> tell the API to load new model    [PLACEHOLDER — needs reload endpoint]
  8. success/failure alerts    -> logging + alert hooks             [IMPLEMENTED as callbacks]

Promotion design (Option B): the training step only trains + logs + REGISTERS a
candidate model version. The DAG then GOVERNS promotion as two explicit steps that
run `services.training.promote` (compare, then promote) — reusing the tested
`promote_if_better` helper. Keeping promotion in the orchestrator (not the training
script) is the cleaner MLOps separation. Steps 5 & 6 therefore run as DockerOperator
tasks in the training image, exactly like train. Only STEP 7 (API reload) remains a
placeholder — it needs a reload endpoint the backend does not expose yet.

NOTE on ordering: your spec lists version(2) before validate(3). We intentionally run
`validate_data` BEFORE `version_dataset_dvc` so we never version a dataset that failed
QA. Swap the two lines at the bottom if you must match the exact spec order.

Prereqs (see infra/airflow/README.md):
  - Build images: asp-backend:latest, asp-training:latest, asp-airflow-runner:latest
  - Set HOST_PROJECT_ROOT (+ optional AWS_* DagsHub creds, FASTAPI_RELOAD_URL) in infra/airflow/.env
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.docker.operators.docker import DockerOperator
from docker.types import Mount

log = logging.getLogger("airflow.task")

# ---------------------------------------------------------------------------
# Configuration (from environment; see infra/airflow/.env)
# ---------------------------------------------------------------------------
HOST_PROJECT_ROOT = os.environ.get("HOST_PROJECT_ROOT", "/absolute/path/to/accident-severity-predictor")

BACKEND_IMAGE = os.environ.get("ASP_BACKEND_IMAGE", "asp-backend:latest")
TRAINING_IMAGE = os.environ.get("ASP_TRAINING_IMAGE", "asp-training:latest")
RUNNER_IMAGE = os.environ.get("ASP_RUNNER_IMAGE", "asp-airflow-runner:latest")

VENV_PYTHON = "/app/.venv/bin/python"  # interpreter inside the asp-backend / asp-training images

# DagsHub S3 credentials for the DVC task (empty by default -> that task will fail loudly,
# which is the correct signal that creds are missing).
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")

# Where the running FastAPI backend exposes a "reload the model" endpoint (does not exist yet).
FASTAPI_RELOAD_URL = os.environ.get("FASTAPI_RELOAD_URL", "")

# Mounts for tasks that run the project images (data/ + artifacts/, same as the app).
APP_MOUNTS = [
    Mount(source=f"{HOST_PROJECT_ROOT}/data", target="/app/data", type="bind"),
    Mount(source=f"{HOST_PROJECT_ROOT}/artifacts", target="/app/artifacts", type="bind"),
]

# Settings shared by every DockerOperator task.
DOCKER_COMMON = dict(
    api_version="auto",
    docker_url="unix://var/run/docker.sock",
    mount_tmp_dir=False,
    auto_remove="success",
    network_mode="bridge",
    dns=["8.8.8.8", "8.8.4.4"],  # <-- add: containers use public DNS
)

default_args = {
    "owner": "asp-team",
    "retries": 0,
}


# ---------------------------------------------------------------------------
# Placeholder callable (step 7) — teammate plugs real logic in here
# (Steps 5 & 6 are now REAL DockerOperator tasks running services.training.promote.)
# ---------------------------------------------------------------------------
def _reload_fastapi(**context) -> None:
    """STEP 7 — signal the running FastAPI backend to load the newly promoted model."""
    if not FASTAPI_RELOAD_URL:
        log.info("STEP 7 (placeholder): FASTAPI_RELOAD_URL not set.")
        log.info("  -> backend owner: add a reload endpoint, then set FASTAPI_RELOAD_URL in infra/airflow/.env.")
        return
    try:
        import requests  # available in the Airflow image

        resp = requests.post(FASTAPI_RELOAD_URL, timeout=10)
        log.info(f"STEP 7: reload signal -> {FASTAPI_RELOAD_URL} returned {resp.status_code}")
    except Exception as exc:  # noqa: BLE001 - placeholder should never fail the DAG
        log.warning(f"STEP 7: reload call failed (endpoint may not exist yet): {exc}")


# ---------------------------------------------------------------------------
# Alerting (step 8) — DAG-level success/failure callbacks
# ---------------------------------------------------------------------------
def _on_success(context) -> None:
    log.info(f"ALERT ok: DAG '{context['dag'].dag_id}' run '{context['run_id']}' SUCCEEDED.")
    log.info("  -> hook email/Slack/Teams notification here.")


def _on_failure(context) -> None:
    ti = context.get("task_instance")
    where = ti.task_id if ti else "unknown"
    log.error(f"ALERT fail: DAG '{context['dag'].dag_id}' run '{context['run_id']}' FAILED at task '{where}'.")
    log.error("  -> hook email/Slack/Teams alert here.")


# ---------------------------------------------------------------------------
# The DAG
# ---------------------------------------------------------------------------
with DAG(
    dag_id="asp_retraining",
    description="Full ASP retraining pipeline: ingest -> validate -> version -> train -> compare -> promote -> reload.",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule=None,  # manual trigger; set a cron (e.g. "0 2 * * 1") to retrain weekly
    catchup=False,
    on_success_callback=_on_success,  # STEP 8
    on_failure_callback=_on_failure,  # STEP 8
    tags=["asp", "mlops", "retraining"],
) as dag:
    # STEP 1 — check & ingest new yearly data (download raw CSVs from data.gouv.fr).
    check_and_ingest_data = DockerOperator(
        task_id="check_and_ingest_data",
        image=BACKEND_IMAGE,  # needs `requests` (backend group)
        entrypoint=[VENV_PYTHON],
        command=["-m", "common.data.download_data"],
        mounts=APP_MOUNTS,
        **DOCKER_COMMON,
    )

    # PREP — build the processed X/y dataset (clean + merge + split + scale).
    build_dataset = DockerOperator(
        task_id="build_dataset",
        image=TRAINING_IMAGE,
        # mkdir mirrors the dvc.yaml stage (`mkdir -p data/processed && ...`); the host
        # bind-mount shadows the dir the image created at build time, so create it here.
        entrypoint=["/bin/sh", "-c"],
        command=["mkdir -p /app/data/processed && /app/.venv/bin/python -m common.data.make_dataset"],
        mounts=APP_MOUNTS,
        **DOCKER_COMMON,
    )

    # STEP 3 — validate data quality & shapes (fails the pipeline if the data is bad).
    validate_data = DockerOperator(
        task_id="validate_data",
        image=RUNNER_IMAGE,
        entrypoint=["python"],
        command=["/scripts/validate_data.py"],
        mounts=[
            Mount(source=f"{HOST_PROJECT_ROOT}/data", target="/data", type="bind"),
            Mount(source=f"{HOST_PROJECT_ROOT}/infra/airflow/scripts", target="/scripts", type="bind"),
        ],
        **DOCKER_COMMON,
    )

    # STEP 2 — version the dataset (and artifacts) with DVC, then push to DagsHub.
    #          Runs `dvc commit` (record current pipeline outputs) + `dvc push` (upload).
    version_dataset_dvc = DockerOperator(
        task_id="version_dataset_dvc",
        image=RUNNER_IMAGE,
        entrypoint=["/bin/sh", "-c"],
        command=["cd /repo && dvc commit -f && dvc push"],
        working_dir="/repo",
        mounts=[Mount(source=HOST_PROJECT_ROOT, target="/repo", type="bind")],
        environment={
            "AWS_ACCESS_KEY_ID": AWS_ACCESS_KEY_ID,  # DagsHub S3 creds
            "AWS_SECRET_ACCESS_KEY": AWS_SECRET_ACCESS_KEY,
        },
        **DOCKER_COMMON,
    )

    # DagsHub token env, shared by the train/compare/promote tasks (they all talk to
    # MLflow via dagshub.init(), which needs the token in a headless container).
    MLFLOW_ENV = {"DAGSHUB_USER_TOKEN": os.environ.get("DAGSHUB_USER_TOKEN", "")}

    # STEP 4 — train + evaluate, then REGISTER the model as a new candidate version.
    #          (services.training.train no longer auto-promotes — the DAG governs that.)
    train_and_log_mlflow = DockerOperator(
        task_id="train_and_log_mlflow",
        image=TRAINING_IMAGE,
        entrypoint=[VENV_PYTHON],
        command=["-m", "services.training.train"],
        mounts=APP_MOUNTS,
        environment=MLFLOW_ENV,
        **DOCKER_COMMON,
    )

    # STEP 5 — compare the candidate against the current champion (read-only).
    #          Logs the verdict and writes artifacts/reports/promotion_decision.json.
    compare_against_champion = DockerOperator(
        task_id="compare_against_champion",
        image=TRAINING_IMAGE,
        entrypoint=[VENV_PYTHON],
        command=["-m", "services.training.promote", "compare"],
        mounts=APP_MOUNTS,
        environment=MLFLOW_ENV,
        **DOCKER_COMMON,
    )

    # STEP 6 — promote the candidate to the 'production' alias IF it beats the champion
    #          (moves the old model to 'fallback' for rollback). Reuses promote_if_better.
    promote_to_production = DockerOperator(
        task_id="promote_to_production",
        image=TRAINING_IMAGE,
        entrypoint=[VENV_PYTHON],
        command=["-m", "services.training.promote", "promote"],
        mounts=APP_MOUNTS,
        environment=MLFLOW_ENV,
        **DOCKER_COMMON,
    )

    # STEP 7 — signal FastAPI to reload the new model (placeholder; needs a reload endpoint).
    reload_fastapi = PythonOperator(
        task_id="reload_fastapi",
        python_callable=_reload_fastapi,
    )

    # --- Wire the pipeline ---------------------------------------------------
    # ingest -> build -> validate -> version -> train -> compare -> promote -> reload
    # (validate before version on purpose; see the note at the top of this file.)
    (
        check_and_ingest_data
        >> build_dataset
        >> validate_data
        >> version_dataset_dvc
        >> train_and_log_mlflow
        >> compare_against_champion
        >> promote_to_production
        >> reload_fastapi
    )
