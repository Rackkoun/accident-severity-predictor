# Phase 8 — Airflow Orchestration

> **Goal of this phase:** add **Apache Airflow** on top of the finished system to *orchestrate*
> the existing pipeline — turning the manual "run download, then make_dataset, then train"
> sequence into a single, visual, schedulable, retry-able workflow. You'll learn what an
> orchestrator is and why it matters, read every file in the new `infra/airflow/` folder, and run the
> whole thing locally.
>
> This is the first phase that **extends** the project rather than explaining it. It is purely
> additive: a new `infra/airflow/` folder and a feature branch, with **no change** to any existing
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

## 8.3 The files (a guided read of `infra/airflow/`)

```
infra/airflow/
├── Dockerfile.airflow            # Airflow image = official image + the Docker provider
├── docker-compose.airflow.yml   # one container running `airflow standalone`
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

### `docker-compose.airflow.yml` — the standalone stack

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
      ASP_RUNNER_IMAGE:   ${ASP_RUNNER_IMAGE:-asp-airflow-runner:latest}
      DAGSHUB_USER_TOKEN: ${DAGSHUB_USER_TOKEN:-}   # MLflow auth for the train task
      AWS_ACCESS_KEY_ID:  ${AWS_ACCESS_KEY_ID:-}    # DagsHub S3 creds for the DVC push task
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY:-}
      FASTAPI_RELOAD_URL: ${FASTAPI_RELOAD_URL:-}   # optional reload endpoint (step 7)
    volumes:
      - ./dags:/opt/airflow/dags                    # our DAG(s)
      - ./plugins:/opt/airflow/plugins              # Airflow plugins (empty for now)
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
- **The credential passthroughs** (`DAGSHUB_USER_TOKEN`, `AWS_ACCESS_KEY_ID`,
  `AWS_SECRET_ACCESS_KEY`, `FASTAPI_RELOAD_URL`) are read from `.env` and injected into the Airflow
  container, which then forwards the relevant ones into the sibling task containers. They default to
  **empty**, so the core `asp_pipeline` runs without any of them; they only matter for the retraining
  DAG's train (MLflow) and DVC-push tasks. See §8.7 and §8.9 for exactly which task uses which.
  **These are recreate-time values:** after you edit `.env`, you must re-run
  `docker compose ... up -d` so the container picks up the new values.

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
    dns=["8.8.8.8", "8.8.4.4"],  # force public DNS inside the sibling containers
)
```

Defined once and reused for all three tasks (DRY). `mount_tmp_dir=False` and `auto_remove="success"`
are the two settings people most often trip over with `DockerOperator`: the first avoids a temp-dir
mount that isn't needed here, the second cleans up finished containers so they don't pile up.

> **`dns=[...]` — added after a real local run.** On some machines (corporate networks, VPNs, certain
> Docker Desktop setups) the sibling containers inherit a DNS server they can't reach, so
> `download_data` dies with `Failed to resolve 'www.data.gouv.fr'` (a `socket.gaierror`). Pinning
> Google's public DNS (`8.8.8.8` / `8.8.4.4`) on every task container fixes it. If your network
> blocks `8.8.8.8`, swap in your own resolver. See §8.9 for the full story.

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
        # mkdir mirrors the dvc.yaml stage; the host bind-mount shadows the dir
        # the image created at build time, so we recreate it here before writing.
        entrypoint=["/bin/sh", "-c"],
        command=["mkdir -p /app/data/processed && /app/.venv/bin/python -m common.data.make_dataset"],
        **COMMON_DOCKER_ARGS,
    )
    train_evaluate = DockerOperator(
        task_id="train_evaluate", image=TRAINING_IMAGE,
        entrypoint=[VENV_PYTHON], command=["-m", "services.training.train"],
        # training calls dagshub.init() for MLflow -> pass the token so it
        # authenticates non-interactively (no browser/OAuth in a headless container).
        environment={"DAGSHUB_USER_TOKEN": os.environ.get("DAGSHUB_USER_TOKEN", "")},
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
- **`make_dataset` wraps the command in `sh -c "mkdir -p … && …"`.** The `dvc.yaml` stage does the
  same `mkdir` first. It's needed because the host bind-mount of `data/` *shadows* the
  `data/processed/` directory the image created at build time, so the folder can be missing at run
  time. Without the `mkdir`, `make_dataset` fails with `Cannot save file into a non-existent
  directory: '/app/data/processed'`. (Found during a real local run — see §8.9.)
- **`train_evaluate` passes `environment={"DAGSHUB_USER_TOKEN": …}`.** The training code now calls
  `dagshub.init()` to log the run to the team's MLflow on DagsHub. A headless container can't do the
  interactive browser/OAuth login, so we hand it the token from `.env` and it authenticates
  non-interactively. Leave the token blank and this task fails with a DagsHub OAuth
  `JSONDecodeError`. (Also found during the local run — §8.9.)
- **`download_data >> make_dataset >> train_evaluate`** — the single most important line. The `>>`
  operator sets dependencies: "run download_data, then make_dataset, then train_evaluate." This is
  the graph Airflow draws and enforces. Reverse an arrow and you'd change the order; branch it and
  you'd get parallel tasks.

**MLflow is now live in `train_evaluate`.** When the guide was first written, MLflow was a marked
comment/hook (out of scope for the Airflow branch). Since then a teammate wired `dagshub.init()` into
the training service, so the task genuinely logs each run (params, metrics, model) to the shared
DagsHub experiment registry — which is exactly why the `DAGSHUB_USER_TOKEN` passthrough above is
required. You'll see the run appear under the repo's **Experiments** tab (§8.7).

### `.env.example`, `.gitignore`, `README.md`

- **`.env.example`** documents the variables (`HOST_PROJECT_ROOT`, image tags, `DOCKER_GID`) with
  Windows and Linux examples. You copy it to `.env` (git-ignored) and fill in your path.
- **`.gitignore`** keeps local runtime state out of Git: the SQLite DB, logs, and the generated
  admin-password file. (Same "commit the recipe, not the runtime state" idea as the main repo.)
- **`README.md`** is the operational quickstart + a troubleshooting table.

---

## 8.4 Reproduce it yourself (run Airflow locally)

Yes — this is built to run on your machine with **Docker Desktop**. This walkthrough was **validated
end-to-end on Windows 11 + Docker Desktop + VS Code**, both DAGs fully green. Commands are given for
**PowerShell** (the default VS Code terminal on Windows); the bash equivalents are in the repo's
`infra/airflow/README.md`.

> **Windows note on `grep`.** PowerShell has no `grep`. Wherever a command below pipes to
> `Select-String`, that's the PowerShell stand-in for `grep`. If you're on macOS/Linux, use `grep`.

### Step 0 — build the project images (once)

The DAGs launch `asp-backend:latest`, `asp-training:latest`, and (retraining DAG only)
`asp-airflow-runner:latest`, so they must exist. From the **repo root**:

```powershell
# The training image's Dockerfile creates a user with your UID/GID. On Windows those
# variables aren't set by default, so the build fails with:
#   "groupadd: invalid group ID 'appuser'".
# Fix: create a root .env with UID/GID before building (Docker Compose auto-reads it).
"UID=1000`nGID=1000`nHOST_PROJECT_ROOT=C:/Users/you/Documents/GitHub/accident-severity-predictor" `
  | Out-File -Encoding ascii .env

docker compose --profile build-only build      # -> asp-training:latest
docker compose build backend                   # -> asp-backend:latest
docker build -f infra/airflow/Dockerfile.runner -t asp-airflow-runner:latest infra/airflow  # retraining DAG

docker images | Select-String asp-              # confirm all three are present
```

> **Why the root `.env`?** The backend service defaults its UID/GID (`${UID:-1000}`), but the
> **training** service does not (`USER_ID: ${UID}`), so an unset `UID` breaks *its* build on Windows.
> Setting `UID=1000`/`GID=1000` once fixes it. (A good follow-up PR: give the training service the
> same `:-1000` defaults the backend has, so no root `.env` is needed. See §8.9.)

### Step 1 — configure and start Airflow

From **inside `infra/airflow/`**:

```powershell
cp .env.example .env
#   edit infra/airflow/.env:
#   - HOST_PROJECT_ROOT = your absolute repo path (forward slashes!):
#       C:/Users/you/Documents/GitHub/accident-severity-predictor
#   - (retraining DAG) DAGSHUB_USER_TOKEN, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY = your DagsHub token
#     (the same token is used for all three — see §8.7)

docker compose -f docker-compose.airflow.yml up -d --build
```

> **Re-run `up -d` after any `.env` edit.** Environment values are injected when the container
> starts. If you add/rotate the DagsHub token later, run `docker compose -f
> docker-compose.airflow.yml up -d` again so the container picks up the new `.env` — a running
> container will not see the change on its own.

### Step 2 — log in

`airflow standalone` auto-creates user **`admin`** with a random password:

```powershell
docker exec asp-airflow cat /opt/airflow/simple_auth_manager_passwords.json.generated
# older builds instead: docker exec asp-airflow cat /opt/airflow/standalone_admin_password.txt
# or grep the logs:
docker compose -f docker-compose.airflow.yml logs airflow | Select-String -Pattern "password"
```

Open **http://localhost:8080**, log in as `admin` with that password. (It persists across restarts.)

### Step 3 — run the pipeline

In the UI: find **`asp_pipeline`**, toggle it **On**, then click **▶ Trigger DAG**. Watch the three
boxes go from white → bright green (running) → dark green (success). Click any task → **Logs** to see
the exact output of that pipeline step (the same logs you'd see running it by hand). Or from a
terminal:

```powershell
docker exec asp-airflow airflow dags trigger asp_pipeline
```

**Expected result:** three successful tasks, and — on the host — freshly written files in
`data/raw/`, `data/processed/`, and `artifacts/models|metrics|reports/`, exactly as if you'd run
the pipeline manually in Phase 2–3, but now orchestrated. If MLflow is wired (it is), a new run also
appears on the team's DagsHub **Experiments** tab (see §8.7).

### Step 4 — verify health (see §8.5) and tear down

```powershell
docker compose -f docker-compose.airflow.yml down
```

> **First run is slow.** `download_data` fetches ~130 MB and training builds a 200-tree forest, so
> the DAG can take several minutes. That's the real pipeline running — not Airflow being slow. A
> `train_evaluate` task sitting in **running** (bright green) for a few minutes is normal and means
> MLflow auth already succeeded.

---

## 8.5 How to check it runs correctly (no errors)

Work through these in order; each catches a different class of problem.

```bash
# 1) Is the compose file valid?
docker compose -f docker-compose.airflow.yml config >/dev/null && echo "compose OK"

# 2) Is the Airflow container up and running?
docker compose -f docker-compose.airflow.yml ps

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
  code itself. The `infra/airflow/README.md` troubleshooting table maps each symptom to a fix.
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
- How the **MLflow logging** in `train_evaluate` works now that a teammate wired `dagshub.init()`,
  and why it needs the `DAGSHUB_USER_TOKEN` passthrough (headless containers can't do OAuth).

---

## 8.7 The full retraining DAG (`asp_retraining`)

The 3-task `asp_pipeline` above is the *minimal core*. The real production goal is a **retraining
pipeline** with eight steps — ingest new data, version it, validate it, retrain, compare against the
current best model, promote the winner, tell the API to reload, and alert on success/failure. That
lives in `infra/airflow/dags/asp_retraining_dag.py` as the `asp_retraining` DAG.

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

**(a) The `asp-airflow-runner` helper image** (`infra/airflow/Dockerfile.runner`). Two steps can't reuse the
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
  `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` from the environment (set them in `infra/airflow/.env`). Leave
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

Same as the core DAG, plus build the runner image first and set your DagsHub token (needed by both
the train task's MLflow logging **and** the DVC-push task):

```powershell
docker build -f infra/airflow/Dockerfile.runner -t asp-airflow-runner:latest infra/airflow   # once
# in infra/airflow/.env set all three to your DagsHub token (one token does both jobs):
#   DAGSHUB_USER_TOKEN=<token>      # MLflow auth (train_and_log_mlflow)
#   AWS_ACCESS_KEY_ID=<token>       # DagsHub S3 for dvc push (version_dataset_dvc)
#   AWS_SECRET_ACCESS_KEY=<token>
docker compose -f docker-compose.airflow.yml up -d --build
docker exec asp-airflow airflow dags list-import-errors        # should be empty
# UI: enable + trigger "asp_retraining"; watch all 8 boxes go green.
# The placeholder steps (5-7) log their TODOs and pass as no-ops.
```

> **Get a DagsHub token:** dagshub.com → your avatar → **Settings → Tokens** → copy your default
> token (or generate one). The **same** token value goes into all three `.env` lines. Treat it as a
> secret: `infra/airflow/.env` is git-ignored so it never gets committed, and you should rotate the
> token if it's ever exposed.

### Verifying the two "real write" steps

Two tasks in this DAG do genuine writes to the shared DagsHub project — worth confirming they landed.

**`version_dataset_dvc` (the DVC push).** Open the task → **Logs** and look for three lines:

```
INFO - Starting docker container from image asp-airflow-runner:latest
INFO - Updating lock file 'dvc.lock'          <- dvc commit recorded the outputs
INFO - N files pushed                         <- dvc push uploaded them to DagsHub
```

`N files pushed` (or `Everything is up to date` on a repeat run) means success. Cross-check two ways:

```powershell
cd C:\Users\you\Documents\GitHub\accident-severity-predictor
dvc status -c        # expect: "Cache and remote 'origin' are in sync"
```

and on DagsHub, the repo's **Files** tab shows the DVC-tracked `data/`/`artifacts/` with versions,
and the onboarding **"Version your data with our client"** item flips to a green ✓. This is the
reproducibility payoff: `dvc.lock` (in git) now holds the md5 of the exact dataset this model saw, so
`git checkout <commit>` + `dvc pull` restores that precise data months later.

**`train_and_log_mlflow` (the MLflow run).** Go to the repo's **Experiments** tab
(`https://dagshub.com/<owner>/<repo>/experiments`). Your run appears at the top with its `accuracy`,
`f1_score`, `precision`, and params (`n_estimators=200`, `random_state=42` — the values from
`common/utils/paths.py`). Two real-world gotchas from our run:

- **It's a *shared* registry.** Everyone's runs land in the same table, so if a column **filter** is
  active you may see only one run and the tab may read "Experiments 1". Click **Reset filters** to
  see them all.
- **Tell runs apart by their params.** A run showing e.g. `n_estimators=50` is *not* yours — the
  committed config is `200`. Match your run by timestamp and the `200`/`42` params, or read the DAG's
  train log to get the exact run name:
  ```powershell
  docker exec asp-airflow sh -lc "find /opt/airflow/logs -path '*asp_retraining*train_and_log_mlflow*' -name '*.log' | sort | tail -1 | xargs grep -iE 'n_estimators|run|accuracy|f1'"
  ```

### Handing off the placeholders

- **Steps 4–6 (MLflow):** your teammate's integration point is the `train_and_log_mlflow` hook (log the
  run) and the `_compare_against_champion` / `_promote_to_production` callables (read the registry,
  decide, promote). A natural improvement is to make step 6 *conditional* on step 5 (only promote if
  better) using a `ShortCircuitOperator` or XCom — the stub already returns the decision.
- **Step 7 (reload):** once the backend exposes a reload endpoint, set `FASTAPI_RELOAD_URL` in
  `infra/airflow/.env` and `reload_fastapi` will POST to it automatically.

---

## 8.8 Where to take it next

1. **Schedule it.** Change `schedule=None` to a cron string (e.g. `"0 2 * * 1"`) to retrain weekly —
   the course's "retraining automation" deliverable.
2. **Make promotion conditional.** Gate `promote_to_production` on `compare_against_champion` so only
   a better model is promoted.
3. **Wire real alerts.** Turn the callback log lines into email/Slack notifications.
4. **Complete the hand-offs** — the MLflow steps (4–6) and the FastAPI reload (7) with your teammates.

---

## 8.9 Real local-run playbook — the 5 issues we hit (and the fixes)

Everything above runs green, but getting there on a fresh **Windows 11 + Docker Desktop** machine
surfaced five issues in sequence. Each one blocked exactly one task; fixing it moved the pipeline one
step further. **If you're a teammate running this locally, this section is the fast path — the fixes
are already in the committed code/`.env.example`, so mostly you just need to know what to set.**

### Quick reference

| # | Symptom (task that failed) | Root cause | Fix |
|---|---------------------------|------------|-----|
| 1 | `groupadd: invalid group ID 'appuser'` while **building `asp-training`** | On Windows, `UID`/`GID` are unset; the training service uses `${UID}` with **no default** | Create a **root** `.env` with `UID=1000` and `GID=1000` before building (see §8.4 Step 0) |
| 2 | `download_data` fails: `Failed to resolve 'www.data.gouv.fr'` (`socket.gaierror`) | Sibling containers inherit a DNS server they can't reach (corp network / Docker Desktop) | `dns=["8.8.8.8","8.8.4.4"]` in the DAG's `COMMON_DOCKER_ARGS` (already in the code) |
| 3 | `make_dataset` fails: `Cannot save file into a non-existent directory: '/app/data/processed'` | The host bind-mount **shadows** the `data/processed/` dir the image made at build | `entrypoint=["/bin/sh","-c"]` + `mkdir -p /app/data/processed && …` (already in the code) |
| 4 | `train_evaluate` fails: DagsHub OAuth `JSONDecodeError` | Training calls `dagshub.init()`; a headless container can't do interactive OAuth | Set `DAGSHUB_USER_TOKEN` in `infra/airflow/.env`; the DAG passes it into the task (already wired) |
| 5 | `version_dataset_dvc` fails / `403 Forbidden` on push | Missing DagsHub S3 creds for `dvc push` | Set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` (both = your DagsHub token) in `.env` |

### The details, in the order they bite

**1 — UID/GID on Windows (build time).** The training image builds a non-root user from `UID`/`GID`
build args. The backend service supplies defaults (`${UID:-1000}`), but the training service uses a
bare `${UID}`, so on Windows (where the shell doesn't export `UID`) the arg is empty and `groupadd`
rejects it. Two fixes: a root `.env` containing `UID=1000`/`GID=1000` (recommended, persistent), or a
one-shot `$env:UID="1000"; $env:GID="1000"` in the PowerShell session before building. *Do not* type
`UID=1000` bare in PowerShell — that's bash syntax and errors. **Suggested code fix:** give the
training service the same `:-1000` defaults as the backend, so no root `.env` is needed.

**2 — DNS inside the task containers (download step).** With the socket-launched sibling containers,
DNS resolution can silently fail on some networks. You can confirm it independently:
`docker run --rm asp-backend:latest /app/.venv/bin/python -c "import socket;print(socket.gethostbyname('www.data.gouv.fr'))"` fails, but adding `--dns 8.8.8.8` succeeds. The permanent
fix is the `dns=[...]` key on every `DockerOperator` (via `COMMON_DOCKER_ARGS` / `DOCKER_COMMON`).

**3 — The shadowed `processed/` directory (make_dataset).** The image creates `/app/data/processed`
at build time, but the DAG bind-mounts the **host** `data/` folder over `/app/data`, which hides that
build-time directory. If your host `data/processed/` doesn't exist yet, the write fails. Re-creating
the dir at run time (`mkdir -p … && …`) mirrors exactly what the `dvc.yaml` stage already does.

**4 — MLflow auth in a headless container (train step).** The training service now logs to DagsHub
MLflow via `dagshub.init(repo_owner="Rackkoun", repo_name="accident-severity-predictor")`
(`common/utils/mlflow.py`). Interactively that pops a browser to authenticate; inside Airflow's
container there's no browser, so it errors. Setting `DAGSHUB_USER_TOKEN` lets `dagshub.init()`
authenticate non-interactively. Flow of the token: `infra/airflow/.env` → `docker-compose.airflow.yml`
(`DAGSHUB_USER_TOKEN: ${DAGSHUB_USER_TOKEN:-}`) → the Airflow container → the DAG reads
`os.environ["DAGSHUB_USER_TOKEN"]` and passes it as `environment=` into the training sibling container
→ `dagshub.init()` reads it. **Note (design smell):** the training service currently *requires*
DagsHub auth even for a purely local run. A nice improvement is an offline/local-MLflow fallback so a
teammate without a token can still train locally.

**5 — DagsHub S3 creds for DVC (version step).** `dvc push` uploads to DagsHub's S3-compatible
remote, which authenticates with your DagsHub token used as **both** the access key id and the secret
access key. Set both `AWS_*` vars in `.env` (same token value as `DAGSHUB_USER_TOKEN`). Leave them
blank and the task fails loudly — the correct signal that creds are missing.

### One token, three lines

For the retraining DAG, your single DagsHub token goes into three `.env` variables — it does double
duty as the MLflow credential and the DVC/S3 credential:

```
DAGSHUB_USER_TOKEN=<your DagsHub token>
AWS_ACCESS_KEY_ID=<same token>
AWS_SECRET_ACCESS_KEY=<same token>
```

**Security:** `infra/airflow/.env` is git-ignored, so it is never committed — keep it that way. If a
token is ever pasted somewhere shared (chat, screenshot, logs), **rotate it**: DagsHub → avatar →
**Settings → Tokens → regenerate**, then update the three `.env` lines and re-run `docker compose -f
docker-compose.airflow.yml up -d`.

### The 4 code fixes, and where they live

Fixes **2, 3, 4** are baked into the DAG files (`dags/asp_pipeline_dag.py` and
`dags/asp_retraining_dag.py`) and the compose file, so teammates inherit them automatically. Fixes
**1** and **5** are environment/config you set locally. All four are good candidates for a small
**follow-up PR** so nobody rediscovers them — plus the two suggested source improvements above
(training-service UID defaults; offline MLflow fallback).

---

*This is an extension phase beyond the original build. The full learning series (Phases 0–7)
explains the system these DAGs orchestrate; start from the [README](README.md).*
