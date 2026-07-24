# Accident Severity Predictor

An MLOps project focused on predicting the severity of road accidents in France using Machine Learning.

---


## Getting Started


### Prerequisites

This project uses **uv** as the Python package manager. Python 3.12 is required.

You can install it using

```Bash
uv python install 3.12
```


#### Windows

Install **uv** with Scoop:

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

## Clone the repository

```bash
git clone git@github.com:Rackkoun/accident-severity-predictor.git

cd accident-severity-predictor
```

---


## Create the project environment

Synchronize the project environment. This will automatically:

- create a `.venv` virtual environment (if it doesn't already exist),
- install all project dependencies,

First, pin the project to Python 3.12.

```Bash
uv python pin 3.12 # this will create a .python-version file

```
Then install all the depencies

```Bash
uv sync --all-groups
```

## Activate the virtual environment (optional but recommended)

__Windows (PowerShell)__

```Powershell
.venv\Scripts\Activate.ps1
```

__Windows (Command Prompt)__

```Promt
.venv\Scripts\activate.bat
```

__macOS / Linux__

```Shell
source .venv/bin/activate
```

Once activated, your terminal should display something similar to: `(.venv)`


## Verify the installation

```Shell
python --version # or uv python --version -> out Python 3.12.x
uv --version
```

If everything is correctly installed, you're ready to go! 🎉

---

## Git Workflow

Please **never work directly on the `main` branch**.

1. Pull the latest changes.
2. Switch to the `develop` branch.
3. Create your own feature branch from `develop`.

Example:

```bash
git checkout develop
git pull
git checkout -b feature/containerization-fastapi
```

### Branch naming convention

```text
<category>/<functionality>-<task-description>
```

Examples:

```text
feature/api-add-prediction-endpoint
feature/ml-train-baseline-model
feature/mlflow-add-experiment-tracking
feature/frontend-add-dashboard
bug/backend-fix-validation
docs/update-readme
```

Categories:

* `feature`
* `bug`
* `docs`
* `release`

---

## Basic pipeline

**Download raw data for a specific year**:
1. Set `YEAR` variable in the script `./common/data/download_raw_data.py`
2. Run
    ```
    python -m common.data.download_data
    ```

**Create data splits**:
1. Set `YEARS` list in the script `./common/data/make_dataset.py` to specify which years from raw data to include.
2. Optionally set `EXCLUSIVE_TEST_YEAR` to specify if the test set should represent a specific year.
3. Run
    ```
    python -m common.data.make_dataset
    ```

**Run training and evaluation**:
1. Set `MODEL_PARAMETERS` dict in the script `./services/training/train.py` to specify model parameters.
2. Run
    ```
    python -m services.training.train
    ```

**Docker**

```Shell
# Build (in root dir):
docker build -f services/training/Dockerfile.training -t asp-training:latest .
# test docker container (this will mount the path to processed file from your disk drive)
# Linux / Mac
docker run --rm -v $(pwd)/data:/app/data -v $(pwd)/artifacts:/app/artifacts asp-training
# Windows PowerShell
docker run --rm -v ${PWD}/data:/app/data -v ${PWD}/artifacts:/app/artifacts asp-training
```


---

## Good Practices

* Keep pull requests small and focused.
* Write clear commit messages.
* Run the tests and linting before opening a Pull Request.
* Ask questions whenever you're unsure - collaboration is part of the project!

Good luck, and have fun building! 🚀
