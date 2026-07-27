.PHONY: init-project dvc-pull train-model dvc-push run-pipeline run-backend stop-backend


# 1. Run this once after cloning or pulling to install all dependencies locally
init-project:
	uv sync --all-groups

# 2. Fetch the current data and model versions from DagsHub
dvc-pull:
	uv run dvc pull

# 3. Start the model training inside the Docker container (via Docker Compose)
train-model:
	docker compose run --rm training

# 4. Push new pipeline states directly to DagsHub
dvc-push:
	uv run dvc push

# 5. Execute the entire end-to-end ML pipeline locally (using dvc.yaml)
run-pipeline:
	uv run dvc repro
	uv run dvc push

# 6. Start the FastAPI Predict-API in the background
run-backend:
	docker compose up -d --build backend

# 7. Stop the FastAPI Predict-API
stop-backend:
	docker compose down
