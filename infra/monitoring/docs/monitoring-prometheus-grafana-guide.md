# Monitoring & Visualization — Prometheus + Grafana (learning guide)

> A beginner-friendly walkthrough of the ASP monitoring stack: **Prometheus** (metrics collection +
> alerts) and **Grafana** (dashboards). Prometheus + the backend `/metrics` instrumentation were
> built by the team; the **Grafana dashboards + provisioning** documented here are the piece added
> on top. Includes do-it-yourself run steps for a Windows laptop with Docker Desktop.

---

## 1. The big picture

Once the model serves predictions, we watch three things continuously:

1. **Is the service healthy?** API up? requests failing? slow?
2. **Is the model behaving?** how many predictions, which class, how confident, how fast?
3. **Is the data still like training?** has it drifted? is F1 still above the gate?

Two tools answer these:

- **Prometheus** — pulls ("scrapes") numeric metrics from each service every 15s, stores them as
  time series, and evaluates **alert rules**. *(Team's part — `infra/monitoring/prometheus/`.)*
- **Grafana** — queries Prometheus and draws the dashboards. *(This task — `infra/monitoring/grafana/`.)*

```
backend /metrics ─┐
node-exporter    ─┼─► Prometheus (store + alert) ─► Grafana (dashboards)
                  ┘
```

Everything runs as containers on the `asp-network`, behind the **Nginx** reverse proxy (Phase 5).
Grafana is served at **`https://asp.local:8081/grafana/`** (not a public port).

---

## 2. What Prometheus collects (the team's part — worth understanding)

**Config: `infra/monitoring/prometheus/prometheus.yml`.** It defines a 15s scrape interval and the
targets to pull from:

- `prometheus` itself (is Prometheus healthy?)
- `asp-backend:8000/metrics` — the API + model metrics (labelled `service: backend`)
- `node-exporter:9100` — host CPU/RAM/disk

**The metrics** (defined in `services/backend/src/core/metrics.py`, exposed at `/metrics`):

| Group | Metric | Meaning |
|-------|--------|---------|
| API | `http_requests_total` | request count by method/path/status |
| API | `http_request_duration_seconds` | latency histogram |
| Model | `predictions_total` | predictions by class |
| Model | `prediction_confidence` | predicted-probability histogram |
| Model | `prediction_duration_seconds` | inference time histogram |
| Model | `model_loaded`, `model_reload_total` | is a model live; reload attempts |
| Drift | `model_f1_score` | F1 of the promoted model (from the drift contract) |
| Drift | `model_drift_share` | share of features that drifted |
| Drift | `model_dataset_drift_detected` | 1 if dataset drift was flagged |

The three drift metrics come from the Phase 9 drift step: the backend reads `latest_metrics.json`
(the drift contract) on each scrape and publishes them — so the dashboards visualize the drift work.

**Alerts: `infra/monitoring/prometheus/alert_rules.yml`.** Rules that fire inside Prometheus
(visible under *Prometheus → Alerts*): backend down, high 5xx error rate, high p95 latency. Routing
them to Slack/email would need Alertmanager (out of scope for now).

---

## 3. What this task adds — the Grafana dashboards

Grafana starts empty. This task **provisions** it automatically on boot (no click-through setup):

```
infra/monitoring/grafana/
├── provisioning/
│   ├── datasources/prometheus.yml   # auto-connect the Prometheus datasource
│   └── dashboards/dashboards.yml     # auto-load the JSONs below
└── dashboards/
    ├── asp-api-health.json           # request rate, 5xx %, latency, requests by path
    ├── asp-model.json                # predictions/s by class, confidence, inference time, reloads
    ├── asp-drift.json                # F1 gauge vs the 0.65 gate, drift share, dataset-drift flag
    └── asp-infra.json                # host CPU / memory / load / disk / network (node-exporter)
```

For Grafana to see these, the `grafana` service in `docker-compose.yaml` mounts the two folders
read-only:

```yaml
    volumes:
      - grafana-data:/var/lib/grafana
      - ./infra/monitoring/grafana/provisioning:/etc/grafana/provisioning:ro
      - ./infra/monitoring/grafana/dashboards:/var/lib/grafana/dashboards:ro
```

The dashboards reference the datasource by **uid `prometheus`** (set in the provisioning file), so
they work regardless of Grafana's internal datasource id.

---

## 4. Do it yourself (run the whole stack)

**Prerequisite:** Docker Desktop running, and the one-time Nginx + Grafana setup below.

1. **One-time setup.**
   - Add to your hosts file (`C:\Windows\System32\drivers\etc\hosts`): `127.0.0.1 asp.local`
   - Generate the dev TLS cert (Phase 5): `bash infra/nginx/generate-dev-cert.sh`
   - Create **`.env.grafana`** at the repo root:
     ```
     GF_SECURITY_ADMIN_USER=admin
     GF_SECURITY_ADMIN_PASSWORD=<choose-a-password>
     GF_SERVER_ROOT_URL=https://asp.local:8081/grafana/
     GF_SERVER_SERVE_FROM_SUB_PATH=true
     ```

2. **Start everything** (from the repo root):
   ```bash
   docker compose up -d --build
   ```
   This starts the backend, Nginx, Prometheus, node-exporter, and Grafana.

3. **Check Prometheus is scraping.** Prometheus is internal, but you can confirm via Grafana (next
   step) — every target should feed data. (Targets: `asp-backend`, `node-exporter`, `prometheus`.)

4. **Open Grafana:** **https://asp.local:8081/grafana/login** → log in with the `admin` /
   `<password>` from `.env.grafana`. (Accept the self-signed-cert warning — expected in dev.)
   Under **Dashboards** you'll see four boards tagged `asp`:
   - **ASP · API Health**, **ASP · Model**, **ASP · Drift & Quality Gate**, **ASP · Infrastructure**.
   Set the time range (top-right) to *Last 30 minutes* and refresh to *10s*.

5. **Generate some data** so the API panels move: log in and hit `/predict` a few times
   (Phase 4 §4.3a shows the login → token → predict flow through `https://asp.local:8081`).

6. **Stop** (keeps data): `docker compose down`.

---

## 5. Do it yourself (read a query)

Every panel is a **PromQL** query. Two you'll see a lot:

- **Rate of a counter** — `sum(rate(http_requests_total[5m]))` = requests per second over the last
  5 minutes. `rate()` turns an ever-increasing counter into a per-second speed.
- **A percentile from a histogram** —
  `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))` = p95
  latency.

To experiment, click a panel title → **Edit**, and change the query; or use Grafana's **Explore** tab.

---

## 6. Windows / Docker Desktop notes

- **`.env.grafana` and the hosts entry are required** — without the hosts line, `asp.local` won't
  resolve; without `.env.grafana`, Grafana won't know its admin login or sub-path.
- **Grafana is behind Nginx at `/grafana/`** — always open `https://asp.local:8081/grafana/`, not
  `localhost:3000` (port 3000 is not published).
- **Dashboards not showing?** They're auto-loaded from the mounted `dashboards/` folder. Confirm the
  two volume mounts are present on the `grafana` service and the JSON is valid.
- **"No data" in a panel?** The datasource or a scrape target is the usual cause, not the dashboard.
  Check the Prometheus datasource (Connections → Data sources → Prometheus → *Test*) and that the
  backend has served some traffic.

---

## 7. Troubleshooting

| Symptom | Fix |
|---------|-----|
| Can't reach `https://asp.local:8081/grafana/` | Missing hosts entry (`127.0.0.1 asp.local`) or the stack isn't up. `docker compose ps` should show `asp-grafana` + `asp-nginx` healthy. |
| Grafana login rejected | Wrong `.env.grafana` password, or you changed it and the `grafana-data` volume persisted it. Reset with `docker compose down -v` (wipes stored Grafana data). |
| Dashboards missing | The two provisioning mounts aren't on the `grafana` service, or `dashboards.yml` path doesn't match `/var/lib/grafana/dashboards`. |
| Panels empty / "No data" | Prometheus datasource unreachable (should be `http://prometheus:9090`) or no traffic yet — hit `/predict` a few times and wait ~1–2 min for `rate()` to fill. |
| Drift panels empty | `model_f1_score` etc. only appear after a drift run has written `latest_metrics.json` and the backend has scraped it. |

---

## 8. Who owns what

- **Prometheus + backend `/metrics`** — the team (merged via PR #15). `infra/monitoring/prometheus/`,
  `services/backend/src/core/metrics.py`, `routes/metrics.py`.
- **Grafana dashboards + provisioning** — this task. `infra/monitoring/grafana/` + the two compose
  mounts. The dashboards are the visualization layer the stack was missing.
