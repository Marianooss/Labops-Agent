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
