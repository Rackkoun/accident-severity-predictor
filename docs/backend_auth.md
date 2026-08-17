# Backend Authentication (JWT)

This project secures the `predict` and `train` endpoints using **JWT Bearer Authentication**.

## 1. Setup the development environment

Activate your virtual environment and install all project dependencies:

```bash
uv sync --all-groups
```

---

## 2. Configure authentication

Create a `.env.backend` file.

### Generate password hashes

Each developer should generate their own password hashes.

Passwords are hashed using **bcrypt** and then **Base64-encoded**.

The Base64 encoding avoids issues caused by the `$` character in bcrypt hashes, which Docker interprets as environment variable substitutions.

Generate a password hash:

```bash
python -c "import bcrypt, base64; h = bcrypt.hashpw(b'password123', bcrypt.gensalt()); print(base64.b64encode(h).decode())"
```

Generate a JWT secret:

```bash
openssl rand -hex 32
```

Example:

```env
# Admin
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH_B64=<base64 bcrypt hash>

# Standard user
USER_USERNAME=datascientest
USER_PASSWORD_HASH_B64=<base64 bcrypt hash>

# JWT
JWT_SECRET_KEY=<generated JWT secret>
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=180
```

> **Important:** Never commit your `.env.backend` file or real credentials.

---

## 3. Start the backend

```bash
docker compose --profile build-only build training
docker compose up -d --build backend
```

Verify that the backend is running:

```bash
curl http://localhost:8000/api/v1/health
```

---

# Testing secured endpoints

## 1. Login (User)

Request a JWT access token:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/login \
-H "Content-Type: application/x-www-form-urlencoded" \
-d "username=datascientest&password=user123" \
| python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

---

## 2. Predict

Use the JWT token as a Bearer token:

```bash
curl -X POST http://localhost:8000/api/v1/predict \
-H "Authorization: Bearer $TOKEN" \
-H "Content-Type: application/json" \
-d '{
  "place":1,
  "catu":1,
  "sexe":1,
  "secu1":1,
  "year_acc":2023,
  "victim_age":30,
  "nb_victim":1,
  "catv":2,
  "obsm":0,
  "motor":1,
  "nb_vehicles":1,
  "catr":1,
  "circ":1,
  "surf":1,
  "situ":1,
  "vma":50,
  "jour":1,
  "mois":1,
  "lum":1,
  "dep":75,
  "com":101,
  "agg":1,
  "int":1,
  "atm":0,
  "col":1,
  "lat":48.85,
  "long":2.35,
  "hour":14
}'
```

---

## 3. Login (Admin)

The training endpoint requires an **admin** account.

```bash
TOKEN_ADMIN=$(curl -s -X POST http://localhost:8000/api/v1/login \
-H "Content-Type: application/x-www-form-urlencoded" \
-d "username=admin&password=admin123" \
| python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

---

## 4. Train

```bash
curl -X POST http://localhost:8000/api/v1/train \
-H "Authorization: Bearer $TOKEN_ADMIN" \
-H "Content-Type: application/json" \
-d '{"model_name":"test-model"}'
```

---

## Authorization Summary

| Endpoint        | Authentication      | Required Role  |
| --------------- | ------------------- | -------------- |
| `POST /login`   | Username + Password | Any valid user |
| `POST /predict` | JWT Bearer Token    | User or Admin  |
| `POST /train`   | JWT Bearer Token    | Admin only     |
| `GET /health`   | None                | Public         |
