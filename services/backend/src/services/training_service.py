"""
Backend training service.
Launches the training Docker container via subprocess.
"""

import os
import subprocess
import time

from common.utils.asp_logging import get_logger

logger = get_logger(__name__)

# try to solve: FileNotFoundError: [Errno 2] No such file or directory: '/app/data/processed/X_train.csv'
# default paths
DEFAULT_HOST_DATA_DIR = os.getenv("HOST_DATA_DIR", "/app/data")
DEFAULT_HOST_ARTIFACTS_DIR = os.getenv("HOST_ARTIFACTS_DIR", "/app/artifacts")
# docker image name for training
TRAINING_IMAGE = "asp-training:latest"


def _build_command(
    model_name: str,
    host_data_dir: str,
    host_artifacts_dir: str,
) -> list[str]:
    """build the docker run command for the training container.

    Args:
        model_name: Base name for the model.
        host_data_dir: Absolute path on the DOCKER HOST for data volume.
        host_artifacts_dir: Absolute path on the DOCKER HOST for artifacts volume.

    Returns:
        List of command arguments for subprocess.
    """
    return [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{host_data_dir}:/app/data",
        "-v",
        f"{host_artifacts_dir}:/app/artifacts",
        "-e",
        f"MODEL_NAME={model_name}",
        TRAINING_IMAGE,
    ]


def run_training_container(
    model_name: str = "model",
    host_data_dir: str | None = None,
    host_artifacts_dir: str | None = None,
    timeout_seconds: int | None = None,
) -> dict:
    """launch the training container and wait for completion.

    uses host paths for volume mounts because the Docker daemon runs on the host.
    If host paths are not provided, falls back to environment variables
    HOST_DATA_DIR and HOST_ARTIFACTS_DIR.

    Args:
        model_name: Base name for the model (default: "model").
        host_data_dir: Absolute path on the Docker host for data.
            If None, uses HOST_DATA_DIR env var or defaults to /app/data.
        host_artifacts_dir: Absolute path on the Docker host for artifacts.
            If None, uses HOST_ARTIFACTS_DIR env var or defaults to /app/artifacts.
        timeout_seconds: Max time to wait for training (None = no timeout).

    Returns:
        Dict with status, duration, and container output.

    Raises:
        RuntimeError: If the training container fails.
        FileNotFoundError: If docker is not installed in the container.
    """
    # Resolve host paths
    data_dir = host_data_dir or DEFAULT_HOST_DATA_DIR
    artifacts_dir = host_artifacts_dir or DEFAULT_HOST_ARTIFACTS_DIR

    logger.info(
        f"Starting training container (image={TRAINING_IMAGE}, model_name={model_name}, host_data={data_dir}, host_artifacts={artifacts_dir})"
    )

    command = _build_command(model_name, data_dir, artifacts_dir)
    start = time.time()

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout_seconds,
        )
        duration = time.time() - start

        logger.info(f"Training container finished in {duration:.2f}s")
        logger.debug(f"Container stdout:\n{result.stdout}")

        return {
            "status": "success",
            "duration_seconds": round(duration, 2),
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    except subprocess.CalledProcessError as exc:
        duration = time.time() - start
        logger.error(f"Training container failed after {duration:.2f}s")
        logger.error(f"stdout: {exc.stdout}")
        logger.error(f"stderr: {exc.stderr}")
        raise RuntimeError(f"Training container failed (exit code {exc.returncode}). stderr: {exc.stderr[:500]}") from exc

    except subprocess.TimeoutExpired as exc:
        logger.error(f"Training container timed out after {timeout_seconds}s")
        raise RuntimeError(f"Training container exceeded timeout of {timeout_seconds}s") from exc

    except FileNotFoundError as exc:
        logger.error("Docker CLI not found. Is docker-ce-cli installed?")
        raise RuntimeError(
            "Docker CLI not found in backend container. Ensure docker-ce-cli is installed and /var/run/docker.sock is mounted."
        ) from exc
