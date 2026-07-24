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
1. Set `YEAR` variable in the script `./common/data/download_data.py`
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

## 🛠️ Pipeline Automation & Docker

We use a plattform-independent `Makefile` to automate the local environment setup, container execution, and data/model tracking. 

To run the ML training pipeline inside the Docker container, you no longer need long manual commands. Simply make sure your Docker Daemon is running, build the image once, and use `make`:

```shell
# Build the training image once (run in root directory):
docker build -f services/training/Dockerfile.training -t asp-training:latest .

# Run the training and evaluation inside the container:
make train-model
```

---

## 📦 Data & Model Versioning (DVC)

We use **DVC (Data Version Control)** combined with **DagsHub** to version control our large datasets and heavy `.joblib` models. 

### 1. Setup & Credentials (Once per Machine)

If you have just cloned or pulled this branch, synchronize your environment once to ensure DVC is installed locally:
```bash
make init-project
```

Next, configure your personal DagsHub credentials to unlock the shared remote storage (do **not** commit these, they stay private on your machine):
```bash
uv run dvc remote modify origin --local access_key_id <YOUR_DAGSHUB_USERNAME>
uv run dvc remote modify origin --local secret_access_key <YOUR_DAGSHUB_TOKEN>
```
### 2. Configure Personal DagsHub Credentials (Mandatory)

> ⚠️ **IMPORTANT:** To allow DVC to pull or push data, you must configure your personal DagsHub credentials **once per machine**. Never commit these credentials to Git!

1. Go to **DagsHub.com** to the repo ➡️ click on **data** (green button, top right) ➡️ go to **Setup S3 credentials** ➡️ **Copy commands** (make sure to click on the eye to see the keys before copying).
2. Run the copied commands in your terminal. It should look like this:

```bash
v run dvc remote modify origin --local access_key_id <YOUR_ACCESS_KEY_ID>
uv run dvc remote modify origin --local secret_access_key <YOUR_SECRET_ACCESS_KEY>
```

*Note: The `--local` flag ensures that your credentials are saved in `.dvc/config.local`, which is strictly ignored by Git and stays safely on your machine.*

### 3. Fetching Existing Data & Models from the Cloud

If you freshly cloned the repository or switched to this branch, the datasets and models will be missing locally. To pull the exact versions belonging to the current code state from DagsHub, simply run:

```bash
make dvc-pull
```

### 4. Run the End-to-End Automated Pipeline (DVC Pipeline)

We use a `dvc.yaml` pipeline to orchestrate the data and training steps. DVC automatically tracks your scripts, data splits, and model artifacts. It will intelligently skip steps if no code or data has changed.

To execute the entire training pipeline, track the new artifacts, and push them to DagsHub, run:

```bash
# Run the pipeline locally (DVC tracks dependencies and outputs automatically)
uv run dvc repro

# Push the newly generated data and models to DagsHub S3 storage
uv run dvc push
```

*Note: DVC automatically protects the heavy binaries (`data/` and `artifacts/models/`), ensuring they are never accidentally committed to Git, while code and lightweight configurations are managed via Git.*


### 🔄 Automated CI/CD Execution (No Manual Action Required)

Thanks to our integrated **GitHub Actions CI/CD Pipeline**, you rarely need to run the training or deployment manually:

* **Automatic Model Verification:** Every time you open a Pull Request, GitHub automatically spins up a runner, installs the environment via `uv`, pulls the latest model from DagsHub via S3, and verifies that the prediction service (`backend`) passes all integration and health checks.
* **Continuous Training (CD):** Merging code into the main branches triggers the automated orchestration, ensuring that containers are rebuilt and validated without any local hardware dependency.

***

---

## Good Practices

* Keep pull requests small and focused.
* Write clear commit messages.
* Run the tests and linting before opening a Pull Request.
* Ask questions whenever you're unsure - collaboration is part of the project!

Good luck, and have fun building! 🚀
