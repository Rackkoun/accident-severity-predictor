# Accident Severity Predictor — Learning Guides

A phase-by-phase walkthrough of **how this repository was built**, written so you can
read it, understand the *what* and the *why*, and reproduce every part locally in VS Code.

These guides are learning material *about* the codebase. They live in `learning-guides/`
and do not affect how the project runs.

---

## What this project is (one paragraph)

An **MLOps** project that predicts the **severity of road accidents in France** from the
official government **BAAC** dataset (published on data.gouv.fr). It is deliberately built
like a small production system, not a single notebook: a **DVC-versioned data pipeline**
(download → build dataset → train), a **training service** that produces a model plus
metrics and reports, a **FastAPI backend** that serves predictions and can trigger training,
**Docker** packaging, and **GitHub Actions CI/CD**. A Streamlit frontend is scaffolded for later.

The guiding idea throughout: **reproducibility and separation of concerns**. Every artifact
(data, model, metrics) is versioned; every responsibility (data prep, training, serving)
lives in its own module or service.

---

## Run it and check the results

See **[HOW-TO-VERIFY.md](HOW-TO-VERIFY.md)** — a single tick-list to run each phase locally and
confirm the result (command → expected output), tiered by what you need (nothing / internet /
Docker / DagsHub), with the full step-by-step Docker walkthrough.

## How to use these guides

Each phase is a standalone Markdown file with four recurring sections:

1. **What & Why** — the concept and the design decision behind it.
2. **The files** — a guided read of the actual source, line group by line group.
3. **Reproduce it yourself** — exact commands to run locally, with expected output.
4. **Checkpoint** — how to know the phase "worked" before moving on.

Work through them in order. Each builds on the previous one.

---

## Phase roadmap

| Phase | Title | What you'll learn |
|------:|-------|-------------------|
| **0** | [Foundations & Tooling](phase-0-foundations-and-tooling.md) | Repo layout, `uv` + `pyproject.toml`, Makefile, pre-commit, Ruff/mypy, Git workflow |
| **1** | [Data Acquisition & DVC Pipeline](phase-1-data-and-dvc-pipeline.md) | Why DVC, `dvc.yaml` stages, remote storage on DagsHub, `dvc repro` |
| **2** | [Data Processing Modules](phase-2-data-processing-modules.md) | `download → clean → merge → make_dataset`, the `common/` package, unit tests |
| **3** | [Training Service](phase-3-training-service.md) | `train_model` + `evaluate_model`, config-driven training, artifacts |
| **4** | [Backend API](phase-4-backend-api.md) | FastAPI structure: routes, schemas, services, model lifecycle on startup |
| **5** | [Containerization](phase-5-containerization.md) | Dockerfiles, `docker-compose`, the "train inside a Docker container" pattern |
| **6** | [CI/CD](phase-6-cicd.md) | The four GitHub Actions workflows: code quality, tests, container build, orchestrator |
| **7** | [Frontend & Wrap-up](phase-7-frontend-and-wrapup.md) | Streamlit scaffold, and how the whole system fits together end to end |
| **8** | [Airflow Orchestration](phase-8-airflow-orchestration.md) | *(extension)* Apache Airflow DAG orchestrating the pipeline via DockerOperator |

Status: **Core series complete (Phases 0–7)** 🎉 plus **Phase 8 (Airflow)** as the first extension. Start with [Phase 0](phase-0-foundations-and-tooling.md) and work through in order; the [Phase 7 runbook](phase-7-frontend-and-wrapup.md#75-a-learners-roadmap--how-to-do-it-yourself) reproduces the whole system end to end, and [Phase 8](phase-8-airflow-orchestration.md) adds Airflow orchestration on top.

> **Extensions (beyond the original repo):** Phase 8 lives on the `feature/airflow-orchestration` branch and adds a self-contained `airflow/` folder — nothing in the original structure changes.

---

## Prerequisites for following along locally

- **Python 3.12** (the project pins this exact minor version).
- **uv** — the package manager this project uses ([install instructions in Phase 0](phase-0-foundations-and-tooling.md)).
- **Git**.
- **Docker Desktop** (only needed from Phase 5 onward).
- A terminal and **VS Code**.

You do **not** need cloud credentials to read and understand the code. You only need a
DagsHub/DVC remote if you want to pull the real versioned data (covered in Phase 1).
