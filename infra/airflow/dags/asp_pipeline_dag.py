"""
ASP pipeline DAG — orchestrates the existing DVC pipeline with Apache Airflow.

Flow (mirrors dvc.yaml exactly):

    download_data  ->  make_dataset  ->  train_evaluate

Each task launches ONE of the project's EXISTING Docker images as a short-lived
"sibling" container (via DockerOperator + the mounted host Docker socket), running
exactly the same command the matching dvc.yaml stage runs. Nothing in the main
project (code, structure, Dockerfiles) is modified — this DAG only *calls* what
already exists.

Why two different images?
  - `download_data` imports the `requests` library, which lives in the BACKEND
    dependency group -> so that task uses asp-backend:latest (it has both the
    backend and training deps).
  - `make_dataset` and `train` use only training-group libraries -> they use
    asp-training:latest.
This lets us reuse the images AS-IS, with zero edits to their Dockerfiles.

Prerequisites (see infra/airflow/README.md):
  1. Build asp-backend:latest and asp-training:latest first (main project, Phase 5).
  2. Set HOST_PROJECT_ROOT in infra/airflow/.env to the ABSOLUTE host path of the repo.

Because `download_data` re-fetches the raw CSVs from data.gouv.fr, this DAG can
rebuild the whole pipeline from scratch — no `dvc pull` required.
"""

from __future__ import annotations

import os
from datetime import datetime

from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from docker.types import Mount

# ---------------------------------------------------------------------------
# Configuration (read from environment; see infra/airflow/.env)
# ---------------------------------------------------------------------------

# Absolute path to the project ON THE HOST (NOT inside this Airflow container).
# The host Docker daemon resolves bind-mount sources, so these MUST be host paths.
# Windows example: C:/Users/you/Documents/GitHub/accident-severity-predictor
HOST_PROJECT_ROOT = os.environ.get("HOST_PROJECT_ROOT", "/absolute/path/to/accident-severity-predictor")

BACKEND_IMAGE = os.environ.get("ASP_BACKEND_IMAGE", "asp-backend:latest")
TRAINING_IMAGE = os.environ.get("ASP_TRAINING_IMAGE", "asp-training:latest")

# The Python interpreter inside BOTH images (installed by uv at /app/.venv).
VENV_PYTHON = "/app/.venv/bin/python"

# Bind-mount the REAL data/ and artifacts/ folders into each task container so the
# stages read/write the same files the rest of the project uses (same lesson as
# Phase 5: the source paths are HOST paths).
COMMON_MOUNTS = [
    Mount(source=f"{HOST_PROJECT_ROOT}/data", target="/app/data", type="bind"),
    Mount(source=f"{HOST_PROJECT_ROOT}/artifacts", target="/app/artifacts", type="bind"),
]

# Settings shared by every DockerOperator task.
COMMON_DOCKER_ARGS = dict(
    api_version="auto",
    docker_url="unix://var/run/docker.sock",  # the mounted host socket
    mounts=COMMON_MOUNTS,
    mount_tmp_dir=False,  # don't mount Airflow's temp dir (not needed here)
    auto_remove="success",  # remove the sibling container when it finishes OK
    network_mode="bridge",  # gives download_data internet access to data.gouv.fr
    dns=["8.8.8.8", "8.8.4.4"],  # <-- add: containers use public DNS
)

default_args = {
    "owner": "asp-team",
    "retries": 0,  # keep it simple for learning; bump later if you like
}

# ---------------------------------------------------------------------------
# The DAG
# ---------------------------------------------------------------------------
with DAG(
    dag_id="asp_pipeline",
    description="Run the ASP DVC pipeline (download -> make_dataset -> train+evaluate) via Docker.",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule=None,  # manual trigger only (set a cron string to run on a schedule)
    catchup=False,
    tags=["asp", "mlops", "pipeline"],
) as dag:
    # 1) Download the raw BAAC CSVs from data.gouv.fr into data/raw/.
    download_data = DockerOperator(
        task_id="download_data",
        image=BACKEND_IMAGE,  # needs `requests` (backend group)
        entrypoint=[VENV_PYTHON],
        command=["-m", "common.data.download_data"],
        **COMMON_DOCKER_ARGS,
    )

    # 2) Clean + merge the raw tables into data/processed/ (X/y train + test).
    make_dataset = DockerOperator(
        task_id="make_dataset",
        image=TRAINING_IMAGE,
        # mkdir mirrors the dvc.yaml stage (`mkdir -p data/processed && ...`); the host
        # bind-mount shadows the dir the image created at build time, so create it here.
        entrypoint=["/bin/sh", "-c"],
        command=["mkdir -p /app/data/processed && /app/.venv/bin/python -m common.data.make_dataset"],
        **COMMON_DOCKER_ARGS,
    )

    # 3) Train the model AND evaluate it -> artifacts/{models,metrics,reports}/.
    #    (services.training.train runs training then evaluation — see Phase 3.)
    train_evaluate = DockerOperator(
        task_id="train_evaluate",
        image=TRAINING_IMAGE,
        entrypoint=[VENV_PYTHON],
        command=["-m", "services.training.train"],
        # training now calls dagshub.init() for MLflow -> pass the DagsHub token so it
        # authenticates non-interactively (no browser/OAuth in a headless container).
        environment={"DAGSHUB_USER_TOKEN": os.environ.get("DAGSHUB_USER_TOKEN", "")},
        **COMMON_DOCKER_ARGS,
    )

    # Wire the pipeline: each task runs only after the previous one succeeds.
    download_data >> make_dataset >> train_evaluate
