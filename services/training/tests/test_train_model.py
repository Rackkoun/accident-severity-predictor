
"""
Tests for train_model
"""

from pathlib import Path

import joblib
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier

from services.training.src.train_model import run_training, save_model_artifacts


@pytest.fixture
def training_data(tmp_path: Path) -> Path:
    d = tmp_path / "processed"
    d.mkdir()
    pd.DataFrame({"f1": [1.0, 2.0, 3.0, 4.0, 5.0], "f2": [0, 1, 0, 1, 0]}).to_csv(d / "X_train.csv", index=False)
    pd.Series([0, 1, 0, 1, 0]).to_csv(d / "y_train.csv", index=False)
    return d


@pytest.fixture
def trained_model() -> RandomForestClassifier:
    X = [[1, 2], [3, 4], [5, 6], [7, 8]]
    y = [0, 1, 0, 1]
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    model.fit(X, y)
    return model


def test_run_training_returns_model(training_data: Path, tmp_path: Path) -> None:
    model = run_training(
        processed_data_dir=training_data,
        model_out_dir=tmp_path / "models",
        reports_dir=tmp_path / "reports",
        model_name="test",
        model_parameters={"n_estimators": 10, "random_state": 42},
    )
    assert isinstance(model, RandomForestClassifier)


def test_run_training_saves_artifacts(training_data: Path, tmp_path: Path) -> None:
    run_training(
        processed_data_dir=training_data,
        model_out_dir=tmp_path / "models",
        reports_dir=tmp_path / "reports",
        model_name="test",
        model_parameters={"n_estimators": 10, "random_state": 42},
    )
    assert (tmp_path / "models" / "test.joblib").exists()
    assert (tmp_path / "models" / "test_features.json").exists()


def test_run_training_missing_data(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(FileNotFoundError):
        run_training(
            processed_data_dir=empty,
            model_out_dir=tmp_path / "models",
            reports_dir=tmp_path / "reports",
            model_name="test",
            model_parameters={"n_estimators": 10},
        )


def test_save_artifacts_saves_all(trained_model: RandomForestClassifier, tmp_path: Path) -> None:
    paths = save_model_artifacts(
        model=trained_model,
        features=["f1", "f2"],
        model_parameters={"n": 10},
        model_out_dir=tmp_path / "m",
        reports_dir=tmp_path / "r",
        model_name="test",
    )
    assert paths["model"].exists()
    assert paths["features"].exists()
    assert paths["parameters"].exists()
    assert paths["feature_importance"].exists()


def test_save_artifacts_loadable_model(trained_model: RandomForestClassifier, tmp_path: Path) -> None:
    paths = save_model_artifacts(
        model=trained_model,
        features=["f1", "f2"],
        model_parameters={"n": 10},
        model_out_dir=tmp_path / "m",
        reports_dir=tmp_path / "r",
        model_name="test",
    )
    loaded = joblib.load(paths["model"])
    assert isinstance(loaded, RandomForestClassifier)


def test_save_artifacts_exists_no_overwrite(trained_model: RandomForestClassifier, tmp_path: Path) -> None:
    (tmp_path / "m").mkdir()
    (tmp_path / "r").mkdir()
    (tmp_path / "m" / "test.joblib").write_text("dummy")
    with pytest.raises(FileExistsError):
        save_model_artifacts(
            model=trained_model,
            features=["f1", "f2"],
            model_parameters={"n": 10},
            model_out_dir=tmp_path / "m",
            reports_dir=tmp_path / "r",
            model_name="test",
            overwrite=False,
        )


def test_save_artifacts_overwrite_true(trained_model: RandomForestClassifier, tmp_path: Path) -> None:
    (tmp_path / "m").mkdir()
    (tmp_path / "r").mkdir()
    (tmp_path / "m" / "test.joblib").write_text("dummy")
    paths = save_model_artifacts(
        model=trained_model,
        features=["f1", "f2"],
        model_parameters={"n": 10},
        model_out_dir=tmp_path / "m",
        reports_dir=tmp_path / "r",
        model_name="test",
        overwrite=True,
    )
    loaded = joblib.load(paths["model"])
    assert isinstance(loaded, RandomForestClassifier)