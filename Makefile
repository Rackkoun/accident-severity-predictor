.PHONY: init-project train-model dvc-push run-pipeline

# Detect the project root directory universally across Mac, Linux, and Windows
ROOT_DIR := $(shell git rev-parse --show-toplevel)

# 1. Run this once after cloning or pulling to install all dependencies locally
init-project:
	uv sync --all-groups

# 2. Fetch the current data and model versions from DagsHub
dvc-pull:
	uv run dvc pull


# 3. Start the model training inside the Docker container
train-model:
	docker run --rm \
		-v "$(ROOT_DIR)/data:/app/data" \
		-v "$(ROOT_DIR)/artifacts:/app/artifacts" \
		asp-training

# 4. Track new data/model states and push them to DagsHub
dvc-push:
	uv run dvc add data
	uv run dvc add artifacts/models
	uv run dvc add artifacts/metrics
	uv run dvc add artifacts/reports
	uv run dvc push -r origin

# 5. Execute the entire end-to-end ML pipeline
run-pipeline: train-model dvc-push
