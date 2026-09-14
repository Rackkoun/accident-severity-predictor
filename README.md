# Accident Severity Predictor

An MLOps project focused on predicting the severity of road accidents in France using Machine Learning.

---

## Getting Started

### Prerequisites

This project uses [uv](https://docs.astral.sh/uv/) as the Python package manager. Python 3.12 is required.

You can install Python 3.12 with:

```bash
uv python install 3.12
```

#### Windows

Install `uv` with Scoop:

```powershell
scoop install uv
```

or with Winget:

```powershell
winget install Astral-sh.uv
```

#### macOS

```bash
brew install uv
```

#### Linux

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## Clone the Repository

```bash
git clone git@github.com:Rackkoun/accident-severity-predictor.git

cd accident-severity-predictor
```

---

## Create the Project Environment

Synchronize the project environment. This automatically creates a `.venv` virtual environment if it does not already exist and installs the project dependencies.

First, pin the project to Python 3.12:

```bash
uv python pin 3.12
```

This creates a `.python-version` file.

Then install all dependencies:

```bash
uv sync --all-groups
```

---

## Activate the Virtual Environment

Activation is optional when using `uv`, but recommended for local development.

### Windows - PowerShell

```powershell
.venv\Scripts\Activate.ps1
```

### Windows — Command Prompt

```cmd
.venv\Scripts\activate.bat
```

### macOS / Linux

```bash
source .venv/bin/activate
```

Once activated, your terminal should display something similar to:

```text
(.venv)
```

---

## Verify the Installation

Check the installed Python and `uv` versions:

```bash
python --version
uv --version
```

Python should report version `3.12.x`.


***
If everything is correctly installed, the development environment is ready.

---

## Documentation

The project documentation is organized by component and responsibility.

| Document                               | Description                                                                          |
| -------------------------------------- | ------------------------------------------------------------------------------------ |
| [Backend](docs/backend.md)             | Backend architecture, configuration, authentication, API usage, training and testing |
| [Reverse Proxy](docs/reverse_proxy.md) | Nginx setup, local HTTPS, TLS certificates, routing, rate limiting and verification  |
| [DVC / DagsHub](docs/dvc_setup.md)     | Dataset and model versioning setup                                                   |
| [MLflow](infra/tracking/mlflow/README.md) | Experiment tracking setup and configuration via DagsHub                           |
| [Airflow Orchestration](infra/airflow/README.md) | Retraining DAG, DAG-governed promotion (Option B), drift gate, yearly schedule + Slack alerts |
| [Drift Detection](services/monitoring/README.md) | Evidently data/target drift detection with an F1 quality gate; see infra/airflow/docs/phase-9 |
| [Prometheus / Grafana](infra/monitoring/README.md) | Prometheus and Grafana monitoring setup and configuration                |
| [Monitoring dashboards & alerts](docs/monitoring.md) | Grafana dashboards, provisioning, and Slack alerting                   |

Additional documentation will be added to `docs/` as the corresponding project components mature.
