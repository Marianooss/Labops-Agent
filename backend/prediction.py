"""
prediction.py — Prophet demand forecasting + stockout calculation.
Calibrated with patterns derived from anonymized demand analysis (Argentina).
"""
import os
import sys
import logging
import pickle
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# Ensure local backend imports resolve when this module runs from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

import numpy as np
import pandas as pd
from prophet import Prophet

import database as db

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
os.makedirs(MODELS_DIR, exist_ok=True)

# Synthetic demo calibration: TSH spikes in winter (Jun-Aug in AR)
# These are calibrated patterns, not real patient data.
_SEASONAL_PATTERNS = {
    "TSH": {"base": 120, "winter_mult": 1.8, "winter_months": [6, 7, 8]},
    "Hemograma": {"base": 200, "winter_mult": 1.0, "winter_months": []},
    "Ionograma": {"base": 180, "winter_mult": 1.0, "winter_months": []},
    "Glucosa": {"base": 150, "winter_mult": 1.05, "winter_months": [6, 7, 8]},
    "Urea": {"base": 90, "winter_mult": 1.0, "winter_months": []},
    "Creatinina": {"base": 95, "winter_mult": 1.0, "winter_months": []},
}


def _build_synthetic_history(reagent_name: str, days: int = 365) -> pd.DataFrame:
    """Build a synthetic DAILY demand history calibrated with real patterns.

    Deterministic: np.random.seed(42) is set before generation so the
    same data is produced every run. This ensures reproducible demos.
    """
    np.random.seed(42)
    pattern = _SEASONAL_PATTERNS.get(reagent_name, {"base": 100, "winter_mult": 1.0, "winter_months": []})
    base = pattern["base"]
    winter_mult = pattern["winter_mult"]
    winter_months = pattern["winter_months"]

    records = []
    today = datetime.now(timezone.utc).date()
    for i in range(days, 0, -1):
        d = today - timedelta(days=i)
        mult = winter_mult if d.month in winter_months else 1.0
        noise = np.random.normal(0, base * 0.08)
        weekend_mult = 0.6 if d.weekday() >= 5 else 1.0
        qty = max(0, int(base * mult * weekend_mult + noise))
        records.append({"ds": pd.Timestamp(d), "y": float(qty)})

    return pd.DataFrame(records)


def _get_or_build_model(reagent_name: str) -> Prophet:
    """Load serialized Prophet model or train + cache on first call."""
    model_path = os.path.join(MODELS_DIR, f"{reagent_name}_model_v2.pkl")
    if os.path.exists(model_path):
        # Re-train if model file is older than 1 day (data may have changed)
        mtime = os.path.getmtime(model_path)
        age_seconds = datetime.now().timestamp() - mtime
        if age_seconds < 86400:
            with open(model_path, "rb") as f:
                return pickle.load(f)
        else:
            logger.info("Model for %s is stale (%.1f h old); retraining.", reagent_name, age_seconds / 3600)

    # Try real seeded demand_history first; fall back to synthetic on low data or error.
    try:
        rows = db.get_demand_history(reagent_name, limit=500)
        if len(rows) >= 30:
            df = pd.DataFrame(rows)
            df = df.rename(columns={"date": "ds", "quantity": "y"})
            df["ds"] = pd.to_datetime(df["ds"])
            df = df.sort_values("ds").reset_index(drop=True)
            last_date = df["ds"].max()
            days_stale = (datetime.now(timezone.utc) - last_date.replace(tzinfo=timezone.utc)).days
            if days_stale > 7:
                logger.warning(
                    "DB demand_history for %s is stale (last %s, %d days ago); using synthetic history.",
                    reagent_name, last_date.strftime("%Y-%m-%d"), days_stale
                )
                df = _build_synthetic_history(reagent_name, days=365)
        else:
            logger.info("Only %d demand rows for %s; using synthetic history.", len(rows), reagent_name)
            df = _build_synthetic_history(reagent_name, days=365)
    except Exception as e:
        logger.warning("Failed to load demand_history for %s: %s; using synthetic.", reagent_name, e)
        df = _build_synthetic_history(reagent_name, days=365)

    # Pin randomness for reproducible demo (Prophet L-BFGS is deterministic for same data + seed)
    np.random.seed(42)

    m = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        interval_width=0.8,
    )
    m.fit(df)
    with open(model_path, "wb") as f:
        pickle.dump(m, f)
    return m


def get_forecast(reagent_name: str, days: int = 30) -> Dict[str, Any]:
    """
    Return demand forecast + projected stockout date.
    Uses Prophet trained on synthetic calibrated history.
    """
    model = _get_or_build_model(reagent_name)
    future = model.make_future_dataframe(periods=days)
    forecast = model.predict(future)

    # Get next N days of forecast
    future_slice = forecast[forecast["ds"] > pd.Timestamp(datetime.now(timezone.utc).date())].head(days)
    daily_demand = future_slice[["ds", "yhat", "yhat_lower", "yhat_upper"]].to_dict(orient="records")

    # Calculate cumulative demand for stockout projection
    # We need current stock from inventory (caller should pass it; here we default)
    return {
        "reagent_name": reagent_name,
        "forecast_days": days,
        "daily_demand": [
            {
                "date": row["ds"].strftime("%Y-%m-%d"),
                "predicted_qty": round(row["yhat"], 2),
                "lower_bound": round(row["yhat_lower"], 2),
                "upper_bound": round(row["yhat_upper"], 2),
            }
            for row in daily_demand
        ],
        "model": "Prophet",
        "calibrated": True,
        "note": "DEMO — synthetic data calibrated with real demand patterns",
    }


def calculate_stockout_projection(reagent_name: str, current_stock: float, reorder_lead_time: int = 7) -> Dict[str, Any]:
    """
    Project when stock will run out based on forecasted demand.
    Alert fires when projected_stockout_days < reorder_lead_time.
    """
    forecast = get_forecast(reagent_name, days=90)
    cumulative = 0.0
    stockout_date = None
    projected_stockout_days = None

    for day in forecast["daily_demand"]:
        cumulative += day["predicted_qty"]
        if cumulative >= current_stock and stockout_date is None:
            stockout_date = day["date"]
            ds = datetime.strptime(day["date"], "%Y-%m-%d")
            projected_stockout_days = (ds.date() - datetime.now(timezone.utc).date()).days
            break

    severity = "critical" if projected_stockout_days is not None and projected_stockout_days < reorder_lead_time else "warning"

    return {
        "reagent_name": reagent_name,
        "current_stock": current_stock,
        "projected_stockout_date": stockout_date,
        "projected_stockout_days": projected_stockout_days,
        "reorder_lead_time": reorder_lead_time,
        "severity": severity,
        "alert_trigger": projected_stockout_days is not None and projected_stockout_days < reorder_lead_time,
        "forecast": forecast,
        "note": "DEMO — synthetic data calibrated with real demand patterns",
    }
