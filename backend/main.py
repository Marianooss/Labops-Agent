"""
main.py — FastAPI entry point for LabOps Agent.
Exposes health check, MCP tools, prediction, and Slack event adapter.
"""
import logging
import os
from typing import Dict, Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slack_bolt.adapter.fastapi import SlackRequestHandler

import database as db
import prediction
import claude_client as claude
import mcp_server as mcp
from slack_client import bolt_app, _post_stockout_alert

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="LabOps Agent", version="1.0.0")
slack_handler = SlackRequestHandler(bolt_app)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/")
def root() -> Dict[str, str]:
    return {"status": "ok", "agent": "LabOps Agent", "version": "1.0.0"}


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "healthy", "database": "supabase", "model": "prophet"}


# ---------------------------------------------------------------------------
# MCP Tools (REST exposure for agent consumption)
# ---------------------------------------------------------------------------
@app.get("/mcp/inventory")
def api_get_inventory(reagent_name: str | None = None) -> Dict[str, Any]:
    return mcp.get_inventory(reagent_name)


@app.get("/mcp/forecast")
def api_get_forecast(reagent_name: str, days: int = 30) -> Dict[str, Any]:
    return mcp.get_forecast(reagent_name, days)


@app.post("/mcp/order")
def api_create_order(payload: Dict[str, Any]) -> Dict[str, Any]:
    return mcp.create_order(
        payload["reagent_name"],
        payload["quantity"],
        payload["supplier"],
    )


@app.post("/mcp/canvas")
def api_update_canvas(payload: Dict[str, Any]) -> Dict[str, Any]:
    return mcp.update_canvas(payload["channel_id"], payload["reagent_data"])


@app.get("/mcp/info")
async def mcp_info():
    return {
        "name": "labops-agent",
        "version": "1.0.0",
        "tools": ["get_inventory", "get_forecast", "create_order", "update_canvas"],
        "transport": "stdio",
        "description": "MCP Server for clinical lab reagent management",
    }


# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------
@app.get("/predict/{reagent_name}")
def api_predict(reagent_name: str, current_stock: float, lead_time: int = 7) -> Dict[str, Any]:
    return prediction.calculate_stockout_projection(reagent_name, current_stock, lead_time)


# ---------------------------------------------------------------------------
# Alert trigger (for scheduler / demo)
# ---------------------------------------------------------------------------
@app.get("/alert/trigger")
def api_trigger_alert(
    reagent_name: str = "TSH",
    channel: str = os.environ.get("LABOPS_ALERTS_CHANNEL", "#labops-alerts"),
    current_stock: float = None,
):
    reagent = reagent_name
    stock = current_stock

    if stock is None:
        inv = db.get_inventory(reagent)
        stock = inv[0]["current_stock"] if inv else 0

    proj = prediction.calculate_stockout_projection(reagent, stock)
    if not proj["alert_trigger"]:
        return {"alert_triggered": False, "projection": proj}

    explanation = claude.explain_stockout(
        reagent,
        proj["projected_stockout_days"],
        stock,
        seasonality_hint="TSH demand spikes in winter (Jun-Aug) in Argentina",
    )

    db.log_alert(reagent, proj["projected_stockout_date"], proj["severity"], explanation)

    # Post to Slack
    result = _post_stockout_alert(
        channel=channel,
        reagent_name=reagent,
        projected_days=proj["projected_stockout_days"],
        severity=proj["severity"],
        explanation=explanation,
        current_stock=stock,
    )

    return {
        "alert_triggered": True,
        "projection": proj,
        "explanation": explanation,
        "slack_message_ts": result.get("ts") if hasattr(result, "get") else None,
    }


# ---------------------------------------------------------------------------
# Forecast chart (PNG) — embedded in Block Kit messages
# ---------------------------------------------------------------------------
from io import BytesIO
from fastapi.responses import StreamingResponse

try:
    import matplotlib
    matplotlib.use("Agg")  # headless backend
    import matplotlib.pyplot as plt
    _matplotlib_available = True
except ImportError:
    _matplotlib_available = False
    logger.warning("matplotlib not installed. Forecast charts disabled.")


@app.get("/chart/forecast/{reagent_name}")
def api_forecast_chart(reagent_name: str, days: int = 14):
    if not _matplotlib_available:
        return JSONResponse({"error": "matplotlib not installed"}, status_code=503)

    try:
        forecast = prediction.get_forecast(reagent_name, days=days)
        daily = forecast["daily_demand"]
        dates = [d["date"] for d in daily]
        yhat = [d["predicted_qty"] for d in daily]
        lower = [d["lower_bound"] for d in daily]
        upper = [d["upper_bound"] for d in daily]

        fig, ax = plt.subplots(figsize=(6, 3), dpi=100)
        ax.fill_between(dates, lower, upper, color="#0F6B45", alpha=0.15, label="80% CI")
        ax.plot(dates, yhat, color="#0F6B45", linewidth=2, marker="o", markersize=3, label="Predicted")
        ax.set_title(f"Demand Forecast — {reagent_name}", fontsize=11, fontweight="bold")
        ax.set_ylabel("Units / day")
        ax.set_xlabel("Date")
        ax.tick_params(axis="x", rotation=30, labelsize=7)
        ax.legend(loc="upper left", fontsize=8)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()

        buf = BytesIO()
        fig.savefig(buf, format="png")
        buf.seek(0)
        plt.close(fig)

        return StreamingResponse(buf, media_type="image/png")
    except Exception as e:
        logger.error("Chart generation failed: %s", e, exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


# ---------------------------------------------------------------------------
# Slack Events adapter
# ---------------------------------------------------------------------------
@app.post("/slack/events")
async def slack_events(req: Request):
    return await slack_handler.handle(req)


# ---------------------------------------------------------------------------
# Startup validation
# ---------------------------------------------------------------------------
@app.on_event("startup")
def startup():
    # Verify Supabase connection on startup
    try:
        db.get_supabase()
    except Exception as e:
        logger.warning("Supabase not connected: %s", e)

    # Pre-train Prophet models for all seeded reagents to eliminate demo lag
    seeded_reagents = ["TSH", "Hemograma", "Ionograma", "Glucosa", "Urea", "Creatinina"]
    for reagent in seeded_reagents:
        try:
            prediction.get_forecast(reagent, days=30)
            logger.info("Prophet model pre-trained for %s", reagent)
        except Exception as e:
            logger.warning("Failed to pre-train model for %s: %s", reagent, e)
