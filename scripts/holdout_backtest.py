"""
holdout_backtest.py — Honest hold-out backtest on seeded demand_history.

Trains Prophet on 2024-2025 monthly points, predicts 2026 Jan-Jun,
and reports error against the held-out 2026 seeded values.

This replaces the circular "self-consistency on synthetic data" metric
with a genuine out-of-sample test.
"""
import sys
import os
import json
from datetime import datetime

import numpy as np
import pandas as pd
from prophet import Prophet

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


def _parse_seed_demand_history():
    """Parse demand_history INSERT values from seed_data.sql when DB is offline."""
    seed_path = os.path.join(os.path.dirname(__file__), "..", "data", "seed_data.sql")
    rows = []
    with open(seed_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    in_demand = False
    for line in lines:
        stripped = line.strip()
        if "INSERT INTO demand_history" in stripped:
            in_demand = True
            continue
        if in_demand and stripped.startswith("("):
            # Parse ('TSH', '2024-01-15', 124, 'TSH', true),
            # Handle trailing comma and semicolon
            stripped = stripped.rstrip(",;").strip()
            if not stripped.endswith(")"):
                stripped += ")"
            try:
                vals = stripped.strip("()").split(",")
                if len(vals) >= 5:
                    rows.append({
                        "reagent_name": vals[0].strip().strip("'\""),
                        "date": vals[1].strip().strip("'\""),
                        "quantity": int(vals[2].strip()),
                        "test_type": vals[3].strip().strip("'\""),
                        "is_demo": vals[4].strip() == "true",
                    })
            except Exception:
                pass
        if in_demand and "INSERT INTO" in stripped and "demand_history" not in stripped:
            break
    return rows


def run_backtest(reagent_name: str):
    try:
        import database as db
        rows = db.get_demand_history(reagent_name, limit=500)
    except Exception as exc:
        print(f"DB unavailable ({exc}), falling back to seed_data.sql parser")
        all_rows = _parse_seed_demand_history()
        rows = [r for r in all_rows if r["reagent_name"] == reagent_name]

    if not rows:
        print(f"No data for {reagent_name}")
        return None

    df = pd.DataFrame(rows)
    df = df.rename(columns={"date": "ds", "quantity": "y"})
    df["ds"] = pd.to_datetime(df["ds"])
    df = df.sort_values("ds").reset_index(drop=True)

    # Split: train = 2024-2025, test = 2026
    train = df[df["ds"].dt.year < 2026].copy()
    test = df[df["ds"].dt.year == 2026].copy()

    if len(train) < 6 or len(test) < 1:
        print(f"Insufficient data for {reagent_name}: train={len(train)}, test={len(test)}")
        return None

    # Prophet: monthly data is acceptable but sparse reagents need
    # conservative settings to prevent wild trend extrapolation.
    use_flat = len(train) < 15
    m = Prophet(
        growth="flat" if use_flat else "linear",
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        interval_width=0.8,
        changepoint_prior_scale=0.001 if use_flat else 0.05,
    )
    m.fit(train[["ds", "y"]])

    # Predict for test dates
    future = m.make_future_dataframe(periods=180, freq="D")  # enough to cover test dates
    forecast = m.predict(future)

    # Extract predictions for exact test dates
    results = []
    for _, row in test.iterrows():
        test_date = row["ds"]
        actual = row["y"]
        pred_row = forecast[forecast["ds"] == test_date]
        if pred_row.empty:
            # If exact date missing, find nearest
            idx = (forecast["ds"] - test_date).abs().idxmin()
            pred_row = forecast.loc[[idx]]
        yhat = pred_row["yhat"].values[0]
        results.append({
            "date": test_date.strftime("%Y-%m-%d"),
            "actual": float(actual),
            "predicted": round(float(yhat), 2),
            "error": round(float(actual - yhat), 2),
        })

    # Metrics
    actuals = np.array([r["actual"] for r in results])
    preds = np.array([r["predicted"] for r in results])
    mae = float(np.mean(np.abs(actuals - preds)))
    rmse = float(np.sqrt(np.mean((actuals - preds) ** 2)))
    mape = float(np.mean(np.abs((actuals - preds) / actuals)) * 100)

    metrics = {
        "reagent": reagent_name,
        "holdout_period": "2026-01 to 2026-06",
        "train_samples": len(train),
        "test_samples": len(test),
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "mape_percent": round(mape, 2),
        "method": "hold-out backtest on seeded monthly data",
        "note": "DEMO — synthetic monthly data calibrated with real AR demand patterns",
        "detail": results,
    }

    return metrics


def main():
    all_metrics = {}
    reagents = ["TSH", "Hemograma", "Ionograma"]
    for r in reagents:
        print(f"\n=== Backtest: {r} ===")
        m = run_backtest(r)
        if m:
            all_metrics[r] = m
            print(json.dumps(m, indent=2, ensure_ascii=False, default=str))

    # Write aggregated metrics
    out_path = os.path.join(os.path.dirname(__file__), "..", "notebooks", "holdout_metrics.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_metrics, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n✅ Hold-out metrics written to {out_path}")


if __name__ == "__main__":
    main()
