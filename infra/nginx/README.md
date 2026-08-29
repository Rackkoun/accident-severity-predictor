# ASP Nginx

TLS-terminating reverse proxy in front of the ASP FastAPI backend.

## Architecture

```
Client
  |
  | HTTPS  https://asp.local:8081
  v
asp-nginx:443
  |
  | HTTP
  v
asp-backend:8000
```

- Host port: `8081:443`
- Internal network: `asp-network`
- Backend port `8000` is **not** exposed to the host.

## Files

| File                      | Purpose                                            |
|---------------------------|----------------------------------------------------|
| `nginx.conf`              | Single-file Nginx configuration                    |
| `Dockerfile.nginx`        | Container build (nginx:1.27-alpine)                |
| `generate-dev-cert.sh`    | Creates a dev self-signed cert for `asp.local`     |
| `certs/nginx.{crt,key}`   | Generated at build-test time; **never committed**   |

## Development setup

1. Add the hostname to `/etc/hosts`:

   ```
   127.0.0.1 asp.local
   ```

2. Generate the development certificate:

   ```
   bash infra/nginx/generate-dev-cert.sh
   ```

3. Start the stack:

   ```
   docker compose up -d --build
   ```

4. Verify:

   ```
    curl -k https://asp.local:8081/api/v1/health
    ```

## Testing the API

All requests go through the Nginx proxy (`https://asp.local:8081`, self-signed
cert → use `-k` or `-H 'Host: asp.local'`). Token parsing uses `python3` stdlib
(no `jq` required).

**1. Health check (no auth needed):**

```bash
curl -k https://asp.local:8081/api/v1/health
```

**2. Login → get access token (data scientist role):**

```bash
TOKEN=$(curl -sk -X POST https://asp.local:8081/api/v1/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=datascientest&password=user123" \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

**3. Predict (authenticated, Bearer token):**

```bash
curl -sk -X POST https://asp.local:8081/api/v1/predict \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "place": 1, "catu": 1, "sexe": 1, "secu1": 1,
    "year_acc": 2023, "victim_age": 30, "nb_victim": 1,
    "catv": 2, "obsm": 0, "motor": 1, "nb_vehicles": 1,
    "catr": 1, "circ": 1, "surf": 1, "situ": 1, "vma": 50,
    "jour": 1, "mois": 1, "lum": 1,
    "dep": 75, "com": 101, "agg": 1, "int": 1, "atm": 0, "col": 1,
    "lat": 48.85, "long": 2.35, "hour": 14
  }'
```

Expected response:

```json
{
  "severity": "Injured (hospitalized) / Killed",
  "severity_code": 1,
  "probability": 0.55,
  "model_used": "accident-severity-predictor@production (v3)"
}
```

**4. Train (admin role only):**

```bash
TOKEN_ADMIN=$(curl -sk -X POST https://asp.local:8081/api/v1/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123" \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

curl -sk -X POST https://asp.local:8081/api/v1/train \
  -H "Authorization: Bearer $TOKEN_ADMIN" \
  -H "Content-Type: application/json" \
  -d '{"model_name": null}'
```

**5. Verify rate limiting (login zone = 6 r/m, burst 1):**

```bash
for i in 1 2 3 4 5; do
  curl -sk -o /dev/null -w "attempt $i -> %{http_code}\n" \
    -X POST https://asp.local:8081/api/v1/login \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=ratecheck&password=wrong"
done
# Expected: first attempt -> 4xx (auth), then 429 for the rest
```

## Security

- TLS 1.2 + 1.3 only.
- HTTP (port 80) redirects to HTTPS with `301`.
- Security headers: HSTS, X-Frame-Options (`DENY`), `nosniff`,
  Referrer-Policy, Permissions-Policy.
- Request size capped at 10 MB (`client_max_body_size`).
- Rate limiting per client IP (see table below).

> Nginx rate limiting is an **additional** protection layer only.
> FastAPI remains the source of truth for authentication (JWT) and
> authorization (roles).

## Rate limiting

| Endpoint        | Zone             | Rate        | Burst |
|-----------------|------------------|-------------|-------|
| `/api/v1/login` | `asp_login_limit`   | 6 r/m    | 1     |
| `/api/v1/train` | `asp_train_limit`   | 1 r/m       | 1     |
| `/api/v1/predict` | `asp_predict_limit` | 10 r/s     | 20    |
| `/api/v1/health` | `asp_health_limit`  | 20 r/s     | 50    |

Excess requests receive `429 Too Many Requests`.

## Not in scope

- `auth_basic` / `.htpasswd`
- Load balancing / multiple backend replicas
- Prometheus / Grafana / exporters
- Kubernetes
