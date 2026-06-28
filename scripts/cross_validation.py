"""
cross_validation.py — Real rolling-origin cross-validation for the daily Prophet
model that actually serves forecasts in production (backend/prediction.py).

This is the credible, out-of-sample accuracy metric. It uses
`prophet.diagnostics.cross_validation`, which:
  - trains on an initial window,
  - rolls the cutoff forward by `period`,
  - forecasts `horizon` ahead at each cutoff (multiple folds),
  - compares every forecast against the held-out actuals.

It also reports **coverage** — the fraction of actuals that fell inside the 80%
prediction interval. Coverage near 80% means the model's uncertainty bands are
well calibrated (not over/under-confident). This replaces the misleading
"self-consistency on synthetic training data" figure and the statistically
meaningless 1-test-point monthly MAPE numbers.

Run:
    python scripts/cross_validation.py
Writes:
    notebooks/cv_metrics.json
"""
import os
import sys
import json
import logging
import warnings

warnings.filterwarnings("ignore")
logging.getLogger("prophet").setLevel(logging.ERROR)
logging.getLogger("cmdstanpy").setLevel(logging.ERROR)

import numpy as np
import pandas as pd
from prophet import Prophet
from prophet.diagnostics import cross_validation, performance_metrics

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

# Use the SAME synthetic history + patterns the production model trains on,
# so these metrics describe the model that actually runs in the demo.
from prediction import _build_synthetic_history, _SEASONAL_PATTERNS  # noqa: E402

# Rolling-origin CV parameters (documented so judges can reproduce).
CV_PARAMS = {
    "initial": "240 days",
    "period": "30 days",
    "horizon": "14 days",
    "interval_width": 0.8,
}


def _fit(df: pd.DataFrame) -> Prophet:
    """Mirror backend/prediction.py model configuration exactly."""
    np.random.seed(42)
    m = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        interval_width=CV_PARAMS["interval_width"],
    )
    m.fit(df)
    return m


def run_cv(reagent_name: str) -> dict:
    df = _build_synthetic_history(reagent_name, days=365)
    model = _fit(df)

    cv = cross_validation(
        model,
        initial=CV_PARAMS["initial"],
        period=CV_PARAMS["period"],
        horizon=CV_PARAMS["horizon"],
        parallel=None,
        disable_tqdm=True,
    )
    pm = performance_metrics(cv, rolling_window=1)

    n_folds = int(cv["cutoff"].nunique())
    coverage = float(pm["coverage"].iloc[-1]) if "coverage" in pm else None

    return {
        "reagent": reagent_name,
        "method": "rolling-origin cross-validation (prophet.diagnostics)",
        "model": "Prophet (daily, yearly+weekly seasonality)",
        "history_days": 365,
        "params": CV_PARAMS,
        "folds": n_folds,
        "n_predictions": int(len(cv)),
        "mae": round(float(pm["mae"].iloc[-1]), 2),
        "rmse": round(float(pm["rmse"].iloc[-1]), 2),
        "mape_percent": round(float(pm["mape"].iloc[-1]) * 100, 2),
        "coverage_80ci_percent": round(coverage * 100, 1) if coverage is not None else None,
        "note": "DEMO — synthetic daily data calibrated with real AR demand patterns",
    }


def main():
    reagents = list(_SEASONAL_PATTERNS.keys())
    results = {}
    for r in reagents:
        print(f"\n=== Rolling-origin CV: {r} ===")
        try:
            m = run_cv(r)
            results[r] = m
            print(
                f"  folds={m['folds']}  horizon={CV_PARAMS['horizon']}  "
                f"MAPE={m['mape_percent']}%  MAE={m['mae']}  RMSE={m['rmse']}  "
                f"coverage(80% CI)={m['coverage_80ci_percent']}%"
            )
        except Exception as exc:
            print(f"  CV failed for {r}: {exc}")

    out_path = os.path.join(os.path.dirname(__file__), "..", "notebooks", "cv_metrics.json")
    payload = {
        "generated_by": "scripts/cross_validation.py",
        "method": "rolling-origin cross-validation (prophet.diagnostics.cross_validation)",
        "params": CV_PARAMS,
        "interpretation": {
            "mape_percent": "mean absolute percentage error across all folds/horizons",
            "coverage_80ci_percent": "fraction of actuals inside the 80% interval; ~80% = well-calibrated",
        },
        "results": results,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"\nOK — cross-validation metrics written to {out_path}")


if __name__ == "__main__":
    main()
