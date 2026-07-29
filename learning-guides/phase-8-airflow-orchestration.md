# Phase 8 — Airflow Orchestration

> **Goal of this phase:** add **Apache Airflow** on top of the finished system to *orchestrate*
> the existing pipeline — turning the manual "run download, then make_dataset, then train"
> sequence into a single, visual, schedulable, retry-able workflow. You'll learn what an
> orchestrator is and why it matters, read every file in the new `airflow/` folder, and run the
> whole thing locally.
>
> This is the first phase that **extends** the project rather than explaining it. It is purely
> additive: a new `airflow/` folder and a feature branch, with **no change** to any existing
> code, `dvc.yaml`, or `docker-compose.yaml`. It maps to the course's **Phase 3 — Orchestration &
> Deployment**.

---

## 8.1 What & Why — what an orchestrator adds

By Phase 7 you could run the pipeline by hand: `download_data`, then `make_dataset`, then `train`.
That works, but in a real system you want more:

- **A schedule** — "retrain every Monday at 2am" without a human running commands.
- **Dependencies enforced** — never start training before the dataset is built.
- **Retries** — if a step fails on a network blip, retry it automatically.
- **Visibility** — a UI showing what ran, when, how long, and *why* it failed, with per-step logs.
- **Backfills & history** — a record of every run you can inspect and re-run.

That is exactly what an **orchestrator** provides, and **Apache Airflow** is the most widely used
one. Airflow's core concept is the **DAG** (Directed Acyclic Graph): you describe your workflow as
a set of **tasks** with **dependencies** (arrows), and Airflow schedules them, runs them in the
right order, retries failures, and shows it all in a web UI.

```
   Before (manual)                     After (Airflow DAG)
   you type 3 commands                 one DAG, triggered/scheduled, with a UI:
   in the right order,                     download_data ─▶ make_dataset ─▶ train_evaluate
   hope none fail                          (retries, logs, schedule, history — all free)
```

The visuals for this project put Airflow in **Phase 3 (Deployment)**: the *Airflow DAG* sits at the
top and drives the pipeline that feeds serving. Our DAG orchestrates the three `dvc.yaml` stages
you already know.

**A key design principle for this phase:** the orchestrator *calls* the existing pipeline — it does
**not** reimplement it. Every task runs the exact same command a `dvc.yaml` stage runs. Airflow is a
conductor, not a new orchestra.

---

## 8.2 The approach — reuse the existing images (docker-out-of-docker, again)

Recall Phase 4/5: the backend launches training by asking the host's Docker daemon (via the mounted
socket) to run the `asp-training` image as a **sibling container**. This Airflow feature uses the
*same* pattern. Each DAG task is a **`DockerOperator`** that launches one of the project's existing
images as a short-lived sibling container, running one pipeline command:

```
   asp-airflow container (standalone)
   ├─ mounts /var/run/docker.sock  ──────────────▶  HOST Docker daemon
   └─ DAG tasks call DockerOperator, which asks the daemon to run:
         download_data   → docker run asp-backend  python -m common.data.download_data
         make_dataset    → docker run asp-training python -m common.data.make_dataset
         train_evaluate  → docker run asp-training python -m services.training.train
      each mounts the host's  data/  and  artifacts/  so results land in the real folders
```

Two consequences worth understanding, because they explain the whole design:

- **Why two different images.** `download_data.py` imports `requests`, which is in the **backend**
  dependency group — *not* training. So the download task reuses `asp-backend:latest` (it installs
  both backend + training groups). The two modeling tasks need only training-group libraries, so
  they reuse `asp-training:latest`. This way we reuse the images **exactly as they are**, with zero
  edits to their Dockerfiles (which belong to teammates).
- **Why no DVC step is needed.** Because `download_data` re-fetches the raw CSVs from data.gouv.fr,
  the DAG rebuilds *everything* from scratch — raw → processed → model. There's no need for
  `dvc pull` to seed data. (Versioning the *output* with `dvc push` is an optional manual follow-up.)

---

## 8.3 The files (a guided read of `airflow/`)

```
airflow/
├── Dockerfile.airflow            # Airflow image = official image + the Docker provider
├── docker-compose.airflow.yaml   # one container running `airflow standalone`
├── dags/
│   └── asp_pipeline_dag.py       # the DAG (3 DockerOperator tasks)
├── .env.example                  # HOST_PROJECT_ROOT + image tags
├── .gitignore                    # ignore local runtime state (logs, db, password)
└── README.md                     # quickstart + troubleshooting
```

### `Dockerfile.airflow` — a minimal Airflow image

```dockerfile
FROM apache/airflow:2.10.5-python3.12
RUN pip install --no-cache-dir "apache-airflow-providers-docker==3.14.1"
```

That's the whole file. We start from the **official Airflow image** (which already contains Airflow,
its scheduler, and its web UI) and add just **one** thing: the *Docker provider*, which ships the
`DockerOperator` and the Python Docker SDK. The version is pinned — same reproducibility habit as
`uv.lock`/`dvc.lock`. We match the project's **Python 3.12** by using the `-python3.12` image tag.

### `docker-compose.airflow.yaml` — the standalone stack

```yaml
services:
  airflow:
    build: { context: ., dockerfile: Dockerfile.airflow }
    image: asp-airflow:latest
    container_name: asp-airflow
    command: standalone                       # single-process Airflow (webserver+scheduler+SQLite)
    ports: ["8080:8080"]                      # UI at http://localhost:8080
    environment:
      AIRFLOW__CORE__LOAD_EXAMPLES: "False"   # hide the built-in demo DAGs
      AIRFLOW__CORE__EXECUTOR: SequentialExecutor
      HOST_PROJECT_ROOT: ${HOST_PROJECT_ROOT} # absolute host path -> passed to sibling containers
      ASP_BACKEND_IMAGE:  ${ASP_BACKEND_IMAGE:-asp-backend:latest}
      ASP_TRAINING_IMAGE: ${ASP_TRAINING_IMAGE:-asp-training:latest}
    volumes:
      - ./dags:/opt/airflow/dags                    # our DAG(s)
      - /var/run/docker.sock:/var/run/docker.sock   # the docker-out-of-docker socket
    group_add: [ "${DOCKER_GID:-999}" ]             # Linux: socket access (harmless on Desktop)
    restart: unless-stopped
```

Read it against what you learned in Phase 5 and it's all familiar:

- **`command: standalone`** — `airflow standalone` is the simplest way to run Airflow: it starts the
  web server, the scheduler, and a SQLite metadata DB in one process, and auto-creates an `admin`
  user. Perfect for learning (production uses Postgres + a separate scheduler/executor, which you
  can graduate to later).
- **The socket mount** `/var/run/docker.sock` — identical to the backend in Phase 5. It's what lets
  `DockerOperator` launch sibling containers on the host daemon.
- **`HOST_PROJECT_ROOT`** — the same absolute-host-path lesson as Phase 5's `HOST_DATA_DIR`. The DAG
  reads it to build the sibling containers' bind mounts. It must be a *host* path because the host
  daemon (not the Airflow container) resolves those mounts.
- **`LOAD_EXAMPLES: "False"`** — keeps the UI clean, showing only your DAG.
- **`${VAR:-default}`** — compose's "use `VAR` from `.env`, else this default" syntax. So the image
  tags and `DOCKER_GID` have sensible fallbacks.

Notice what is **not** here: no Postgres, no Redis, no separate scheduler service. That's the
"minimal" choice — one container, easy to read.

### `dags/asp_pipeline_dag.py` — the DAG itself

This is the heart of the phase. Read it in three parts.

**(a) Configuration from the environment**

```python
HOST_PROJECT_ROOT = os.environ.get("HOST_PROJECT_ROOT", "/absolute/path/to/accident-severity-predictor")
BACKEND_IMAGE  = os.environ.get("ASP_BACKEND_IMAGE",  "asp-backend:latest")
TRAINING_IMAGE = os.environ.get("ASP_TRAINING_IMAGE", "asp-training:latest")
VENV_PYTHON = "/app/.venv/bin/python"      # the interpreter inside both images

COMMON_MOUNTS = [
    Mount(source=f"{HOST_PROJECT_ROOT}/data",      target="/app/data",      type="bind"),
    Mount(source=f"{HOST_PROJECT_ROOT}/artifacts", target="/app/artifacts", type="bind"),
]
```

The DAG is fully **config-driven** (same principle as `paths.py`/`MODEL_CONFIG` in the main
project): image tags and the host path come from environment variables, nothing is hard-coded. The
`Mount` objects tell each sibling container to bind-mount the real `data/` and `artifacts/` folders,
so a model trained by the DAG lands in the same `artifacts/` everything else reads from. `/app/...`
is where those folders live *inside* the images (from the Dockerfiles' `WORKDIR /app`).

**(b) Settings shared by every task**

```python
COMMON_DOCKER_ARGS = dict(
    api_version="auto",
    docker_url="unix://var/run/docker.sock",  # the mounted host socket
    mounts=COMMON_MOUNTS,
    mount_tmp_dir=False,      # don't mount Airflow's temp dir (avoids docker-in-docker snags)
    auto_remove="success",    # delete the sibling container once it succeeds
    network_mode="bridge",    # gives download_data internet access to data.gouv.fr
)
```

Defined once and reused for all three tasks (DRY). `mount_tmp_dir=False` and `auto_remove="success"`
are the two settings people most often trip over with `DockerOperator`: the first avoids a temp-dir
mount that isn't needed here, the second cleans up finished containers so they don't pile up.

**(c) The DAG and its three tasks**

```python
with DAG(
    dag_id="asp_pipeline",
    start_date=datetime(2024, 1, 1),
    schedule=None,        # manual trigger (put a cron string here to run on a schedule)
    catchup=False,
    tags=["asp", "mlops", "pipeline"],
) as dag:

    download_data = DockerOperator(
        task_id="download_data", image=BACKEND_IMAGE,
        entrypoint=[VENV_PYTHON], command=["-m", "common.data.download_data"],
        **COMMON_DOCKER_ARGS,
    )
    make_dataset = DockerOperator(
        task_id="make_dataset", image=TRAINING_IMAGE,
        entrypoint=[VENV_PYTHON], command=["-m", "common.data.make_dataset"],
        **COMMON_DOCKER_ARGS,
    )
    train_evaluate = DockerOperator(
        task_id="train_evaluate", image=TRAINING_IMAGE,
        entrypoint=[VENV_PYTHON], command=["-m", "services.training.train"],
        **COMMON_DOCKER_ARGS,
    )

    download_data >> make_dataset >> train_evaluate
```

Everything you need to understand a DAG is on this screen:

- **`with DAG(...) as dag:`** — the DAG is a *context*; any task created inside it belongs to it.
- **`dag_id="asp_pipeline"`** — the name you'll see and trigger in the UI.
- **`schedule=None`** — the DAG runs only when you trigger it (great for learning). Change it to a
  cron string like `"0 2 * * 1"` to retrain every Monday at 02:00 — that one edit turns this into an
  automated retraining pipeline.
- **`catchup=False`** — don't retroactively run for every date since `start_date`. Almost always
  what you want.
- **Each `DockerOperator`** = one pipeline step. `image` picks which image; `entrypoint` +
  `command` override what runs inside it (here: `python -m <the module>`). We override `entrypoint`
  explicitly so it's crystal clear what each task executes, regardless of the image's own default.
- **`download_data >> make_dataset >> train_evaluate`** — the single most important line. The `>>`
  operator sets dependencies: "run download_data, then make_dataset, then train_evaluate." This is
  the graph Airflow draws and enforces. Reverse an arrow and you'd change the order; branch it and
  you'd get parallel tasks.

The **MLflow hook** is a marked comment inside `train_evaluate` — the exact spot a teammate will add
run logging later. It's designed-in, not implemented (MLflow is out of scope for this branch).

### `.env.example`, `.gitignore`, `README.md`

- **`.env.example`** documents the variables (`HOST_PROJECT_ROOT`, image tags, `DOCKER_GID`) with
  Windows and Linux examples. You copy it to `.env` (git-ignored) and fill in your path.
- **`.gitignore`** keeps local runtime state out of Git: the SQLite DB, logs, and the generated
  admin-password file. (Same "commit the recipe, not the runtime state" idea as the main repo.)
- **`README.md`** is the operational quickstart + a troubleshooting table.

---

## 8.4 Reproduce it yourself (run Airflow locally)

Yes — this is built to run on your machine with **Docker Desktop**. Full walkthrough:

### Step 0 — build the project images (once)

The DAG launches `asp-backend:latest` and `asp-training:latest`, so they must exist. From the
**repo root**:

```bash
docker compose --profile build-only build     # -> asp-training:latest
docker compose build backend                   # -> asp-backend:latest
docker images | grep asp-                       # confirm both are present
```

### Step 1 — configure and start Airflow

From **inside `airflow/`**:

```bash
cp .env.example .env
#   edit .env: set HOST_PROJECT_ROOT to your absolute repo path
#   Windows (forward slashes!): C:/Users/you/Documents/GitHub/accident-severity-predictor

docker compose -f docker-compose.airflow.yaml up -d --build
```

### Step 2 — log in

```bash
docker compose -f docker-compose.airflow.yaml logs airflow | grep -i password
# or: docker exec asp-airflow cat /opt/airflow/standalone_admin_password.txt
```

Open **http://localhost:8080**, log in as `admin` with that password.

### Step 3 — run the pipeline

In the UI: find **`asp_pipeline`**, toggle it **On**, then click **▶ Trigger DAG**. Watch the three
boxes go from white → light green (running) → dark green (success). Click any task → **Logs** to see
the exact output of that pipeline step (the same logs you'd see running it by hand). Or from a
terminal:

```bash
docker exec asp-airflow airflow dags trigger asp_pipeline
```

**Expected result:** three successful tasks, and — on the host — freshly written files in
`data/raw/`, `data/processed/`, and `artifacts/models|metrics|reports/`, exactly as if you'd run
the pipeline manually in Phase 2–3, but now orchestrated.

### Step 4 — verify health (see §8.5) and tear down

```bash
docker compose -f docker-compose.airflow.yaml down
```

> **First run is slow.** `download_data` fetches ~130 MB and training builds a 200-tree forest, so
> the DAG can take a while. That's the real pipeline running — not Airflow being slow. To iterate
> faster you can temporarily point the DAG at a smaller `MODEL_CONFIG` in your own build.

---

## 8.5 How to check it runs correctly (no errors)

Work through these in order; each catches a different class of problem.

```bash
# 1) Is the compose file valid?
docker compose -f docker-compose.airflow.yaml config >/dev/null && echo "compose OK"

# 2) Is the Airflow container up and running?
docker compose -f docker-compose.airflow.yaml ps

# 3) Did the DAG parse with NO Python/import errors?  (should print an empty list)
docker exec asp-airflow airflow dags list-import-errors

# 4) Is the DAG registered and visible?
docker exec asp-airflow airflow dags list | grep asp_pipeline

# 5) After a run, are all three tasks "success"?
#    (get <run_id> from the UI, or: airflow dags list-runs -d asp_pipeline)
docker exec asp-airflow airflow tasks states-for-dag-run asp_pipeline <run_id>
```

Interpreting the results:

- **Import errors (step 3)** are the most common beginner issue — a typo or bad import in the DAG
  file. The command prints the traceback and the file; fix `dags/asp_pipeline_dag.py` and Airflow
  reloads it automatically within ~30 seconds (no restart needed).
- **A task fails** — open it in the UI → **Logs**. The message tells you which class of problem:
  `image not found` (build the images), `Cannot connect to the Docker daemon` (socket/permissions),
  `mount source path does not exist` (`HOST_PROJECT_ROOT` wrong), or a real error from the pipeline
  code itself. The `airflow/README.md` troubleshooting table maps each symptom to a fix.
- **Green across the board** — the DAG works. Confirm by checking the host `artifacts/` folder has a
  new timestamped model.

---

## 8.6 Phase 8 checkpoint

You understand Phase 8 when you can explain:

- What an **orchestrator** adds over running commands by hand (schedule, dependencies, retries,
  visibility, history) and what a **DAG** is.
- Why the DAG **calls** the existing pipeline instead of reimplementing it, and how each task maps
  1:1 to a `dvc.yaml` stage.
- How **`DockerOperator`** + the mounted socket reuse the **docker-out-of-docker** pattern from
  Phase 5, and **why two different images** are used (`requests` lives in the backend group).
- The role of `HOST_PROJECT_ROOT` and the bind mounts (the host-path lesson again), and why **no
  `dvc pull`** is needed.
- What `command: standalone`, `schedule=None`, `catchup=False`, and `a >> b >> c` each mean.
- How to start Airflow locally, trigger the DAG, and **verify** it with `list-import-errors`,
  `dags list`, and `states-for-dag-run`.
- Where the **MLflow hook** is, and why it's left unimplemented on this branch.

---

## 8.7 The full retraining DAG (`asp_retraining`)

The 3-task `asp_pipeline` above is the *minimal core*. The real production goal is a **retraining
pipeline** with eight steps — ingest new data, version it, validate it, retrain, compare against the
current best model, promote the winner, tell the API to reload, and alert on success/failure. That
lives in `airflow/dags/asp_retraining_dag.py` as the `asp_retraining` DAG.

The honest reality of a **group project**: some of those steps belong to *other people's*
components (MLflow is a teammate's; the API reload needs an endpoint in the backend service). So the
DAG is built as a **complete skeleton** — the steps in the Airflow owner's lane are fully
implemented, and the cross-team steps are **clearly-marked placeholder tasks that succeed as no-ops**
until a teammate plugs their logic in. This way the DAG runs end-to-end *today*, shows the whole
intended flow, and doesn't block on anyone.

### The eight steps and their status

| Step | Task (`task_id`) | How it's built | Status |
|------|------------------|----------------|--------|
| 1 | `check_and_ingest_data` (+ `build_dataset`) | `DockerOperator` runs `download_data` then `make_dataset` | ✅ implemented |
| 3 | `validate_data` | `DockerOperator` runs `scripts/validate_data.py` in the runner image | ✅ implemented |
| 2 | `version_dataset_dvc` | `DockerOperator` runs `dvc commit -f && dvc push` in the runner image | ✅ implemented* |
| 4 | `train_and_log_mlflow` | `DockerOperator` runs `services.training.train` | ✅ training; 🟡 MLflow = hook |
| 5 | `compare_against_champion` | `PythonOperator` stub | 🟡 placeholder (MLflow) |
| 6 | `promote_to_production` | `PythonOperator` stub | 🟡 placeholder (MLflow) |
| 7 | `reload_fastapi` | `PythonOperator` stub (optional HTTP POST) | 🟡 placeholder (needs endpoint) |
| 8 | success/failure alerts | DAG `on_success_callback` / `on_failure_callback` | ✅ implemented |

\* needs DagsHub credentials (see below).

### Two new ideas beyond the core DAG

**(a) The `asp-airflow-runner` helper image** (`airflow/Dockerfile.runner`). Two steps can't reuse the
app images: `dvc` isn't installed in them, and `validate_data` needs `pandas`. Rather than edit a
teammate's Dockerfile, we add a tiny standalone image:

```dockerfile
FROM python:3.12-slim
RUN pip install --no-cache-dir "dvc[s3]>=3.67.1" "pandas"
```

It bakes in *no* project code — the DAG bind-mounts the repo/data into it at run time. Same
"reuse-and-mount, don't-duplicate" instinct as the rest of the feature.

**(b) `PythonOperator` — logic that runs *inside* Airflow.** Steps 5–7 don't launch a container; they
run a Python function in the Airflow process itself. That's the other core Airflow operator besides
`DockerOperator`. Each placeholder is a small function with a `TODO(owner)` and a `log.info` of what
it *will* do, returning cleanly so the DAG stays green:

```python
def _compare_against_champion(**context) -> bool:
    log.info("STEP 5 (placeholder): would compare new model vs champion via MLflow.")
    return True   # assume improved so the demo flows; real logic pending MLflow
```

### How each in-scope step works

- **`validate_data`** runs `scripts/validate_data.py` in the runner image with `data/` mounted at
  `/data`. It checks the four files exist, are non-empty, have matching X/y row counts, share the same
  columns, have no all-null feature, and a binary `{0,1}` target — and **exits non-zero on the first
  failure**, which turns the task red and *stops the pipeline before training on bad data*. That
  gate-before-you-proceed pattern is the whole point of a validation step.
- **`version_dataset_dvc`** mounts the *whole repo* at `/repo`, then runs `dvc commit -f && dvc push`
  to record the current pipeline outputs in `dvc.lock` and upload them to DagsHub. It reads
  `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` from the environment (set them in `airflow/.env`). Leave
  them blank and this task fails loudly — the correct signal that creds are missing.
- **Alerts (step 8)** are DAG-level callbacks: `_on_success` / `_on_failure` log a clear message and
  mark exactly where an email/Slack/Teams notification would hook. Airflow calls them automatically —
  no extra task needed.

### A deliberate ordering choice

Your spec numbers versioning (2) before validation (3). The DAG runs **`validate_data` before
`version_dataset_dvc`** on purpose: you should never version a dataset that failed QA. The wiring is
one readable chain and the comment tells you to swap the two lines if a strict 2-before-3 order is
required:

```
check_and_ingest_data >> build_dataset >> validate_data >> version_dataset_dvc
    >> train_and_log_mlflow >> compare_against_champion >> promote_to_production >> reload_fastapi
```

### Running it

Same as the core DAG, plus build the runner image first and (optionally) set creds:

```bash
docker build -f airflow/Dockerfile.runner -t asp-airflow-runner:latest airflow   # once
# in airflow/.env: set HOST_PROJECT_ROOT, and (for step 2) AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY
docker compose -f docker-compose.airflow.yaml up -d --build
docker exec asp-airflow airflow dags list-import-errors        # should be empty
# UI: enable + trigger "asp_retraining"; the placeholder steps log their TODOs and pass.
```

### Handing off the placeholders

- **Steps 4–6 (MLflow):** your teammate's integration point is the `train_and_log_mlflow` hook (log the
  run) and the `_compare_against_champion` / `_promote_to_production` callables (read the registry,
  decide, promote). A natural improvement is to make step 6 *conditional* on step 5 (only promote if
  better) using a `ShortCircuitOperator` or XCom — the stub already returns the decision.
- **Step 7 (reload):** once the backend exposes a reload endpoint, set `FASTAPI_RELOAD_URL` in
  `airflow/.env` and `reload_fastapi` will POST to it automatically.

---

## 8.8 Where to take it next

1. **Schedule it.** Change `schedule=None` to a cron string (e.g. `"0 2 * * 1"`) to retrain weekly —
   the course's "retraining automation" deliverable.
2. **Make promotion conditional.** Gate `promote_to_production` on `compare_against_champion` so only
   a better model is promoted.
3. **Wire real alerts.** Turn the callback log lines into email/Slack notifications.
4. **Complete the hand-offs** — the MLflow steps (4–6) and the FastAPI reload (7) with your teammates.

---

*This is an extension phase beyond the original build. The full learning series (Phases 0–7)
explains the system these DAGs orchestrate; start from the [README](README.md).*
