"""
Tests for evaluate_model
"""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier

from services.training.src.evaluate_model import run_evaluation


@pytest.fixture
def eval_setup(tmp_path: Path) -> tuple[Path, Path, Path, Path, str]:
    # Model
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    X = [[1, 2], [3, 4], [5, 6], [7, 8]]
    y = [0, 1, 0, 1]
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    model.fit(X, y)
    joblib.dump(model, model_dir / "test_model.joblib")

    # Test data
    proc = tmp_path / "processed"
    proc.mkdir()
    pd.DataFrame({"f1": [1.0, 3.0, 5.0], "f2": [2.0, 4.0, 6.0]}).to_csv(proc / "X_test.csv", index=False)
    pd.Series([0, 1, 0]).to_csv(proc / "y_test.csv", index=False)

    # Output dirs
    metrics_dir = tmp_path / "metrics"
    reports_dir = tmp_path / "reports"
    metrics_dir.mkdir()
    reports_dir.mkdir()

    return proc, model_dir, metrics_dir, reports_dir, "test_model"


def test_eval_returns_metrics(eval_setup: tuple) -> None:
    proc, m_dir, met_dir, rep_dir, name = eval_setup
    metrics = run_evaluation(name, proc, m_dir, met_dir, rep_dir)
    assert isinstance(metrics, dict)
    assert "Accuracy" in metrics


def test_eval_saves_metrics_json(eval_setup: tuple) -> None:
    proc, m_dir, met_dir, rep_dir, name = eval_setup
    run_evaluation(name, proc, m_dir, met_dir, rep_dir)
    assert (met_dir / f"{name}_metrics.json").exists()


def test_eval_saves_confusion_matrix(eval_setup: tuple) -> None:
    proc, m_dir, met_dir, rep_dir, name = eval_setup
    run_evaluation(name, proc, m_dir, met_dir, rep_dir)
    assert (rep_dir / f"{name}_confusion_matrix.png").exists()


def test_eval_metrics_are_floats_0_to_1(eval_setup: tuple) -> None:
    proc, m_dir, met_dir, rep_dir, name = eval_setup
    metrics = run_evaluation(name, proc, m_dir, met_dir, rep_dir)
    for k, v in metrics.items():
        if k != "Model":
            assert isinstance(v, float)
            assert 0 <= v <= 1


def test_eval_missing_model(eval_setup: tuple, tmp_path: Path) -> None:
    proc, _, met_dir, rep_dir, _ = eval_setup
    with pytest.raises(FileNotFoundError):
        run_evaluation("missing", proc, tmp_path / "empty", met_dir, rep_dir)


def test_eval_missing_test_data(eval_setup: tuple, tmp_path: Path) -> None:
    _, m_dir, met_dir, rep_dir, name = eval_setup
    with pytest.raises(FileNotFoundError):
        run_evaluation(name, tmp_path / "empty", m_dir, met_dir, rep_dir)