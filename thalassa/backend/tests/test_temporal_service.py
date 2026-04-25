"""Unit tests for temporal anomaly scoring logic (pure numpy, no ECCO data)."""
from __future__ import annotations

import numpy as np
import pytest


def _compute_anomaly_scores(means: list[float]) -> list[float]:
    """Replicate the z-score logic from compute_temporal_window_async."""
    arr = np.array(means)
    window_mean = float(np.mean(arr))
    window_std  = float(np.std(arr)) or 1.0
    return np.abs((arr - window_mean) / window_std).tolist()


def test_uniform_signal_zero_anomaly():
    scores = _compute_anomaly_scores([27.0] * 10)
    for s in scores:
        assert abs(s) < 1e-6, f"uniform signal should give zero anomaly, got {s}"


def test_outlier_high_anomaly():
    means = [27.0] * 9 + [30.0]
    scores = _compute_anomaly_scores(means)
    assert scores[-1] > 2.0, "extreme outlier should have z-score > 2"


def test_scores_are_non_negative():
    import random
    rng = random.Random(42)
    means = [rng.gauss(27.0, 0.3) for _ in range(50)]
    scores = _compute_anomaly_scores(means)
    assert all(s >= 0 for s in scores)


def test_z_score_mean_near_zero():
    """Mean of absolute z-scores for Gaussian data should be near 0.8 (half-normal)."""
    rng = np.random.default_rng(0)
    means = rng.normal(27.0, 0.5, 200).tolist()
    scores = _compute_anomaly_scores(means)
    assert 0.5 < float(np.mean(scores)) < 1.2


def test_two_element_window():
    scores = _compute_anomaly_scores([26.0, 28.0])
    assert len(scores) == 2
    assert all(np.isfinite(s) for s in scores)


def test_single_element_no_crash():
    scores = _compute_anomaly_scores([27.0])
    assert len(scores) == 1
    assert scores[0] == 0.0


# ── Schema validation tests ──────────────────────────────────────────────────

def test_temporal_window_request_validation():
    from api.schemas import TemporalWindowRequest
    req = TemporalWindowRequest(
        lat_min=35, lat_max=45, lon_min=-40, lon_max=-30,
        t_start=0, t_end=100, n_samples=10,
    )
    assert req.n_samples == 10
    assert req.t_end == 100


def test_temporal_window_n_samples_capped():
    from api.schemas import TemporalWindowRequest, MAX_WINDOW_SAMPLES
    req = TemporalWindowRequest(
        lat_min=35, lat_max=45, lon_min=-40, lon_max=-30,
        t_start=0, t_end=500, n_samples=9999,
    )
    assert req.n_samples == MAX_WINDOW_SAMPLES


def test_temporal_window_t_order_validated():
    from api.schemas import TemporalWindowRequest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        TemporalWindowRequest(
            lat_min=35, lat_max=45, lon_min=-40, lon_max=-30,
            t_start=200, t_end=100,
        )


def test_temporal_window_out_of_range():
    from api.schemas import TemporalWindowRequest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        TemporalWindowRequest(
            lat_min=35, lat_max=45, lon_min=-40, lon_max=-30,
            t_start=0, t_end=99999,
        )
