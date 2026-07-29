# Phase 4 — Backend API

> **Goal of this phase:** read the `services/backend/` FastAPI application end to end — how it's
> structured into routes/schemas/services, how it loads the latest model once on startup and
> caches it, how `/predict` validates a request and returns a severity prediction, and how
> `/train` launches a training container in the background. This phase also **resolves the
> serving/scaling question** we've tracked since Phase 2 — and the answer is a real, teachable
> finding, not a tidy one.

This is the service that a user or another system actually *talks to*. Everything before it
existed to produce a model; this turns that model into a live prediction endpoint.

---

## 4.1 What & Why — the anatomy of a prediction API

The backend follows a clean three-layer split that mirrors how well-built web services are
organized:

```
services/backend/src/
├── main.py                       ← the app: creates FastAPI, wires routers, manages startup
├── routes/                       ← HTTP layer: URL + method → call a service function
│   ├── health.py                 #   GET  /api/v1/health
│   ├── predict.py                #   POST /api/v1/predict
│   └── train.py                  #   POST /api/v1/train
├── schemas/                      ← the CONTRACT: request/response shapes (Pydantic), validated
│   ├── prediction.py             #   PredictionRequest, PredictionResponse, HealthResponse
│   └── training.py               #   TrainRequest, TrainResponse
└── services/                     ← the LOGIC: what actually happens (no HTTP knowledge)
    ├── prediction_service.py     #   load model, align features, predict
    └── training_service.py       #   launch the training Docker container
```

The guiding principle is **separation of concerns by layer**:

- **Routes** know about HTTP (paths, status codes) but contain almost no logic — they just call a
  service.
- **Schemas** define and *validate* the data crossing the boundary. Nothing untyped gets in or out.
- **Services** hold the real behavior and know nothing about HTTP — which makes them easy to unit
  test directly.

This is the same "thin edge, logic in the middle" shape as the training service's composition
root, applied to a web app. It's why the routes are each ~10 lines.

---

## 4.2 `main.py` — the application and its lifespan

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """load latest model on startup if available."""
    try:
        load_latest_model()          # <- runs ONCE when the server boots
    except Exception as e:
        logger.exception(f"Unable to load model at startup: {e}")
    yield                            # <- server runs here
    logger.info("Shutting down backend...")

app = FastAPI(title="Accident Severity Predictor API", version="1.0.0", lifespan=lifespan)

app.include_router(health.router)
app.include_router(train.router)
app.include_router(predict.router)
```

Two ideas to take away:

- **The `lifespan` context manager** is FastAPI's modern startup/shutdown hook. Everything before
  `yield` runs once when the app starts; everything after runs at shutdown. Here it **loads the
  model into memory a single time at boot**, so requests don't each pay the cost of reading a
  multi-hundred-MB model file off disk. Crucially, it's wrapped in `try/except` — if *no* model
  exists yet, the server still starts (it just can't predict until one is trained). A server that
  refuses to boot because an artifact is missing is a fragile server; this one degrades gracefully.
- **`include_router`** composes the app from the three route modules. Each router is defined in its
  own file and plugged in here — the same modular assembly as everything else in this repo.

There's also a friendly `GET /` root that returns a little map of the endpoints and a link to
`/docs` (FastAPI auto-generates interactive Swagger docs — free, and great for exploring the API).

---

## 4.3 The routes — thin HTTP handlers

All three routers share a `prefix="/api/v1"` (API versioning — so a future `/api/v2` can coexist)
and a `tags=[...]` label (which groups them in the auto-docs).

**Health** — a liveness/readiness probe:

```python
@router.get("/health", response_model=HealthResponse)
def health():
    status = get_model_status()
    return HealthResponse(status="healthy", model_loaded=status["loaded"], model_name=status["name"])
```

It reports not just "am I up?" but "**do I have a model loaded?**" — exactly what a load balancer
or Docker `healthcheck` (Phase 5) needs to decide whether this instance can serve predictions.

**Predict** — the core endpoint, and note how little it does:

```python
@router.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest) -> PredictionResponse:
    return predict_accident(request)
```

The route is three lines. FastAPI has *already* validated the incoming JSON against
`PredictionRequest` before this function runs (invalid input → automatic `422` with a helpful
error). All real work is delegated to the service. This is the "thin route" principle in its
purest form.

**Train** — kicks off training without blocking:

```python
@router.post("/train", response_model=TrainResponse)
def train(request: TrainRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(_train_and_reload, model_name=request.model_name)
    return TrainResponse(status="started", model_name=request.model_name or "auto-resolved",
                         message="Training container launched in background. Check logs for progress.")
```

Training takes minutes; an HTTP request that waited for it would time out. So the route schedules
the work with **`BackgroundTasks`** and returns *immediately* with `"started"`. The background
helper then runs training and reloads the model:

```python
def _train_and_reload(model_name):
    try:
        result = run_training_container(model_name=model_name)
        logger.info(f"Training succeeded: {result['model_name']}")
        load_latest_model(force_reload=True)      # hot-swap the new model into the live cache
    except RuntimeError:
        pass   # already logged in training_service
```

That `load_latest_model(force_reload=True)` at the end is elegant: after a new model is trained,
the running API **swaps to it without a restart**. This is a mini "continuous deployment of the
model" loop, all inside one service.

---

## 4.4 The schemas — the validated contract

Pydantic models are where FastAPI gets its superpower: **declarative validation.** Read a few
fields of `PredictionRequest`:

```python
class PredictionRequest(BaseModel):
    place:      int   = Field(..., ge=1, le=10, description="place of the user in the vehicle")
    catu:       int   = Field(..., ge=1, le=3,  description="user cat: 1 driver, 2 passenger, 3 pedestrian")
    sexe:       int   = Field(..., ge=1, le=2,  description="1 male, 2 female")
    year_acc:   int   = Field(..., ge=2021, le=2024)
    victim_age: float = Field(..., ge=1)
    catv:       int   = Field(..., ge=0, le=6,  description="vehicle cat (remapped 0-6)")
    atm:        int   = Field(..., ge=0, le=1,  description="weather (binary)")
    lat:        float = Field(..., ge=41.0, le=51.0)
    long:       float = Field(..., ge=-5.0, le=10.0)
    int_:       int   = Field(..., ge=1, le=9, alias="int")   # 'int' is a Python keyword!
    ...
```

Things worth noticing:

- **`...` (Ellipsis)** as the first arg means the field is **required**. No default — omit it and
  validation fails.
- **`ge`/`le`** are min/max bounds. So `sexe` must be 1 or 2, `catu` 1–3, `lat` within France's
  latitude band, etc. This is **domain validation at the edge** — nonsense inputs are rejected
  with a clear `422` before they ever reach the model. The bounds also encode the *remapping* from
  Phase 2 (e.g. `catv` 0–6, `atm` 0–1), so the API only accepts already-remapped category codes.
- **`alias="int"`** on `int_` solves a real Python problem: the BAAC feature is literally named
  `int` (intersection type), which is a reserved word in Python. The field is called `int_` in
  code but accepts/returns JSON key `"int"`. (This is why the service later does
  `request.model_dump(by_alias=True)` — to get the real column name back.)

`PredictionResponse` defines what comes back — a human `severity` string, a `severity_code`
(0/1), a `probability`, and which `model_used`. `HealthResponse` reports status + model name.
Defining the *response* shape too means the API's output is validated and self-documented, not
just its input.

---

## 4.5 `prediction_service.py` — load, align, predict (the payoff)

This is the heart of serving, and where our long-running scaling question gets answered.

### The in-memory model cache

```python
_model_cache = {"model": None, "features": None, "name": None}

def load_latest_model(force_reload=False):
    if _model_cache["model"] is not None and not force_reload:
        return                                              # already loaded → no-op
    model_path   = _latest_model_path(MODEL_DIR, "model")   # newest model_*.joblib by mtime
    feature_path = _latest_feature_path(MODEL_DIR, "model") # matching *_features.json
    _model_cache["model"]    = joblib.load(model_path)
    _model_cache["features"] = json.load(open(feature_path))
    _model_cache["name"]     = model_path.stem
```

The model and its **feature list** live in a module-level dict — loaded once (at startup, or
lazily on first predict), reused for every request. `force_reload=True` is the hook the `/train`
flow uses to hot-swap. If no model file exists, it raises an **`HTTPException(503)`** ("no trained
model available, run training first") — the correct HTTP semantics for "service temporarily can't
do this."

Notice it loads the same two artifacts the training service saved in Phase 3: the `.joblib` model
and the `_features.json` feature order. That feature list is about to matter.

### Turning a request into a prediction

```python
def predict_accident(request):
    if _model_cache["model"] is None:
        load_latest_model()                       # lazy-load safety net

    model, features, model_name = _model_cache["model"], _model_cache["features"], _model_cache["name"]

    input_data = request.model_dump(by_alias=True)          # {"int": ..., "place": ..., ...}
    if "id_usager" in features and "id_usager" not in input_data:
        input_data["id_usager"] = 0                          # model expects this internal id; fill a placeholder

    df = pd.DataFrame([input_data])                          # 1-row frame

    try:
        df = df[features]                                    # ← ALIGN to training feature order
    except KeyError as exc:
        missing = set(features) - set(input_data.keys())
        extra   = set(input_data.keys()) - set(features)
        raise HTTPException(422, detail=f"Feature mismatch... Missing: {missing}, Extra: {extra}") from exc

    prediction = int(model.predict(df)[0])
    probability = None
    if hasattr(model, "predict_proba"):
        probability = float(model.predict_proba(df)[0][prediction])

    severity_map = {0: "Unharmed / Lightly injured", 1: "Injured (hospitalized) / Killed"}
    return PredictionResponse(severity=severity_map.get(prediction, "Unknown"),
                              severity_code=prediction, probability=probability,
                              model_used=model_name or "unknown")
```

Read `df = df[features]` carefully — this is the **feature-alignment** step and it's why Phase 3
bothered to save `_features.json`. A Random Forest identifies features by *column position*; the
incoming JSON has no guaranteed order, so the service reorders the one-row DataFrame to exactly
match the columns the model was trained on. If a column is missing or extra, it fails loudly with
a `422` that *names* the mismatch — a genuinely helpful error. The `id_usager` placeholder handles
a quirk where the saved feature list includes an internal id the caller shouldn't have to provide.

The prediction itself is standard: `model.predict` gives the class (0/1), and because a Random
Forest supports `predict_proba`, it also returns the model's confidence in the predicted class.
The 0/1 code is mapped back to a readable label for the response.

### The resolution of the scaling question — an honest finding

Here is the thread we've carried since Phase 2, now resolvable by reading this code directly.

**At training time (Phases 2–3):** features were imputed and **StandardScaler-transformed** (mean
0, std ~1), and the model learned on those *scaled* values.

**At serving time (this file):** the request is turned into a DataFrame and passed **straight to
`model.predict` with no scaling or imputation applied.** And the `PredictionRequest` schema
validates *raw, human-scale* ranges — `victim_age >= 1`, `lat` 41–51, `year_acc` 2021–2024,
`vma >= 1`. Those are real-world units, not standardized z-scores (which would sit roughly in
−3…+3).

So the serving path does **not** reproduce the training-time feature scaling. The fitted
`StandardScaler`/imputers were never persisted (we flagged this in Phase 2 and Phase 3), and
nothing in `predict_accident` re-applies them. The schema's docstring hints at the intent
("*other features are normed/scaled*"), as if expecting the caller to pass already-scaled numbers
— but the field bounds accept raw values, so in practice the model receives unscaled input that
doesn't match the distribution it was trained on.

**Why this matters, stated plainly:** feeding raw-scale features to a model trained on
standardized features is a **train/serve skew** bug. The API will still return a 0/1 answer and a
probability — nothing crashes — but the numbers aren't trustworthy, because the inputs live on a
different scale than the model expects. This is one of the most common and most *invisible* issues
in real ML systems: the pipeline runs green end to end, yet the served predictions are quietly
wrong.

**How a production system fixes it** (worth understanding, and a great exercise on your own build):

1. **Persist the preprocessor.** In Phase 2, instead of discarding the fitted imputers + scaler,
   `joblib.dump` them next to the model (e.g. `model_<ts>_preprocessor.joblib`).
2. **Apply it at serve time.** In `predict_accident`, load that preprocessor and call
   `preprocessor.transform(df)` before `model.predict`, so live input is scaled identically to
   training.
3. **Better still, use a single `sklearn.Pipeline`** that bundles impute → scale → RandomForest
   into one object. Then there's *only one thing to save and load*, and train/serve skew is
   impossible by construction — the exact same transformations always run. This is the standard
   professional pattern and it's what I'd recommend adding.

Finding this is exactly the kind of review an experienced MLOps engineer performs: the code is
clean, well-tested, and *structurally* correct — the routes, caching, feature alignment, and error
handling are all solid — but the *statistical contract* between training and serving is broken.
Both things are true at once, and noticing the second is what separates "it runs" from "it's
right."

---

## 4.6 `training_service.py` — the backend launches a training container

`/train` doesn't train in-process. It shells out to Docker and runs the **training image** (Phase
5) as a one-off container:

```python
TRAINING_IMAGE = "asp-training:latest"

def _build_command(model_name, host_data_dir, host_artifacts_dir):
    return ["docker", "run", "--rm", "--network", "asp-network",
            "-v", f"{host_data_dir}:/app/data",
            "-v", f"{host_artifacts_dir}:/app/artifacts",
            "-e", f"MODEL_NAME={model_name}",
            TRAINING_IMAGE]

def run_training_container(model_name=None, ...):
    ...
    result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=timeout_seconds)
    return {"status": "success", "duration_seconds": ..., "model_name": resolved_name, "stdout": ..., "stderr": ...}
```

This is the **"docker-out-of-docker" / sibling-container** pattern, and it's clever:

- The backend container has the **Docker CLI** installed (see `Dockerfile.backend`) and the host's
  **Docker socket mounted** (`/var/run/docker.sock`, from `docker-compose.yaml` in Phase 5). So
  code *inside* the backend can ask the *host's* Docker daemon to start a *sibling* container.
- It **bind-mounts the host's `data/` and `artifacts/` folders** into the training container, so
  the freshly trained model lands back in the same `artifacts/` the backend reads from. That's why
  `HOST_DATA_DIR`/`HOST_ARTIFACTS_DIR` must be **absolute host paths** (the *host's* Docker daemon
  resolves them, not the backend container's filesystem).
- `--rm` cleans the container up when done; `--network asp-network` puts it on the shared compose
  network.

The error handling is textbook — three distinct failure modes, each turned into a clear
`RuntimeError`:

```python
except subprocess.CalledProcessError as exc:   # training script exited non-zero
    raise RuntimeError(f"Training container failed (exit code {exc.returncode})...")
except subprocess.TimeoutExpired:              # took too long
    raise RuntimeError(f"Training container exceeded timeout of {timeout_seconds}s")
except FileNotFoundError:                       # docker CLI not present in the backend image
    raise RuntimeError("Docker CLI not found... Ensure docker-ce-cli is installed and the socket is mounted.")
```

Each `except` explains *what* went wrong and *how to fix it* — the difference between a stack trace
and an actionable error. (We'll see the compose wiring that makes all this possible in Phase 5.)

---

## 4.7 The tests (19 tests)

| Test file | Tests | What it protects |
|-----------|------:|------------------|
| `routes/test_health.py` | 1 | `/health` returns status + model-loaded flag |
| `routes/test_predict.py` | 2 | `/predict` happy path + behavior with no model |
| `routes/test_train.py` | 1 | `/train` schedules a background task and returns "started" |
| `services/test_prediction_service.py` | 9 | load/cache, latest-model selection, feature alignment, predict + proba, 503/422 errors |
| `services/test_train_service.py` | 6 | docker command building, subprocess success, and each failure mode |

The `conftest.py` fixtures are a model of good API testing — study them:

- **`TestClient(app)`** — FastAPI's in-process test client. It exercises the *real* app (routing,
  validation, serialization) without opening a network port. Fast and faithful.
- **`reset_cache` (autouse=True)** — runs before *every* test and clears the global `_model_cache`.
  This is essential: the model cache is module-level global state, and without resetting it, one
  test's loaded model would leak into the next. `autouse=True` means you never forget to call it.
- **`mock_model`** — a `MagicMock` whose `.predict` returns `[1]` and `.predict_proba` returns
  `[[0.3, 0.7]]`. The prediction tests **never load a real model**; they inject this mock into the
  cache (`loaded_model_cache` fixture) and verify the *service logic* (alignment, mapping,
  response shape) in isolation from any actual ML. Same "mock the heavy/external dependency"
  discipline you saw for the network in Phase 2.
- **Realistic payloads** — `valid_payload`, `severe_payload` (night, highway, bad weather),
  `light_payload` (day, city, bike). Beyond passing tests, these double as **worked examples** of
  what a real request looks like — handy when you try the API yourself.

---

## 4.8 Reproduce it yourself

### Run the API locally (no Docker needed for the API itself)

```bash
uv run uvicorn services.backend.src.main:app --reload --port 8000
```

Then open **http://localhost:8000/docs** — FastAPI's interactive Swagger UI. You can fire requests
right from the browser. Or from another terminal:

```bash
# health (works even with no model — reports model_loaded: false)
curl http://localhost:8000/api/v1/health

# predict (needs a trained model in artifacts/models/ from Phase 3; use the valid payload)
curl -X POST http://localhost:8000/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{"place":1,"catu":1,"sexe":1,"secu1":1,"year_acc":2023,"victim_age":30.0,"nb_victim":1,
       "catv":2,"obsm":0,"motor":1,"nb_vehicles":1,"catr":1,"circ":1,"surf":1,"situ":1,"vma":50,
       "jour":1,"mois":1,"lum":1,"dep":75,"com":101,"agg":1,"int":1,"atm":0,"col":1,
       "lat":48.85,"long":2.35,"hour":14}'
```

**Expected output:** `/health` → `{"status":"healthy","model_loaded":true|false,"model_name":...}`.
`/predict` (with a model present) → a `PredictionResponse` like
`{"severity":"Unharmed / Lightly injured","severity_code":0,"probability":0.87,"model_used":"model_..."}`.
Try an out-of-range value (e.g. `"sexe":5`) and watch FastAPI reject it with a `422` before the
model is ever called — that's the schema doing its job.

> The `/train` endpoint needs Docker + the training image + the mounted socket, so it only fully
> works under the compose setup we cover in Phase 5. Locally it will schedule the task and then
> log a "Docker CLI not found"-style error if Docker isn't available — which is itself a good demo
> of the error handling.

### Always available — run the backend tests (no model, no Docker, no network)

```bash
uv run pytest services/backend/tests -v
```

**Expected output:** 19 tests `PASSED` in seconds, all using the `TestClient` + mock-model
fixtures.

---

## 4.9 Phase 4 checkpoint

You understand Phase 4 when you can explain:

- The routes / schemas / services split and why routes stay "thin."
- What the `lifespan` hook does and why loading the model once at startup (with a `try/except`
  fallback) matters.
- How Pydantic `Field(..., ge=, le=, alias=)` gives you required fields, domain-range validation,
  and the `int`→`int_` keyword workaround — and why bad input returns `422` automatically.
- The in-memory `_model_cache`, lazy loading, and the `force_reload` hot-swap after training.
- Why `df = df[features]` (feature alignment via `_features.json`) is essential, and what the `503`
  vs `422` errors mean.
- **The train/serve scaling gap:** training scaled its features, serving doesn't — why that's a
  train/serve-skew bug, and how persisting the preprocessor (ideally as a single `sklearn.Pipeline`)
  fixes it.
- The docker-out-of-docker training pattern: `/train` → `BackgroundTasks` → `subprocess docker run`
  the training image with host bind-mounts, then hot-reload the new model.
- Why `reset_cache(autouse=True)` and mock models make the API tests fast and isolated.

---

### Next up — Phase 5: Containerization

We open the two Dockerfiles and `docker-compose.yaml` and see how the whole system runs as
containers: how the backend image installs the Docker CLI and mounts the host socket, how the
training image is built, how compose wires the network, volumes, environment, and healthcheck —
and how the `HOST_*` paths from this phase's `training_service.py` get supplied. Say **"Phase 5"**
when you're ready.
