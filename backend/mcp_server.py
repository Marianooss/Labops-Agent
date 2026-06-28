"""
mcp_server.py — MCP Server exposing lab tools for the Slack agent.
Tools: get_inventory, get_forecast, create_order, update_canvas
"""
from typing import Dict, Any, Optional
import database as db
import prediction


# ---------------------------------------------------------------------------
# Tool: get_inventory
# ---------------------------------------------------------------------------
def get_inventory(reagent_name: Optional[str] = None) -> Dict[str, Any]:
    """
    MCP tool: Return current stock for one or all reagents.
    """
    rows = db.get_inventory(reagent_name)
    return {
        "tool": "get_inventory",
        "reagent_name": reagent_name or "all",
        "results": rows,
        "count": len(rows),
    }


# ---------------------------------------------------------------------------
# Tool: get_forecast
# ---------------------------------------------------------------------------
def get_forecast(reagent_name: str, days: int = 30) -> Dict[str, Any]:
    """
    MCP tool: Return Prophet demand forecast for a reagent.
    """
    forecast = prediction.get_forecast(reagent_name, days=days)
    return {
        "tool": "get_forecast",
        "reagent_name": reagent_name,
        "forecast": forecast,
    }


# ---------------------------------------------------------------------------
# Tool: create_order
# ---------------------------------------------------------------------------
def create_order(reagent_name: str, quantity: float, supplier: str) -> Dict[str, Any]:
    """
    MCP tool: Create a reagent order in Supabase.
    """
    order = db.create_order(reagent_name, quantity, supplier, status="pending")
    return {
        "tool": "create_order",
        "order": order,
        "success": bool(order),
    }


# ---------------------------------------------------------------------------
# Tool: update_canvas
# ---------------------------------------------------------------------------
def update_canvas(channel_id: str, reagent_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    MCP tool: Update the Slack Canvas inventory document.
    TODO: Connect to Slack Canvas API via bolt client.
    For hackathon demo, returns the prepared payload.
    """
    # Canvas update is a Slack API call; this tool returns the prepared payload.
    # See: https://api.slack.com/reference/canvas-api
    payload = {
        "channel_id": channel_id,
        "canvas_title": "LabOps Inventario — DEMO",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"Inventario actualizado — {reagent_data.get('reagent_name', 'N/A')}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*Reactivo:* `{reagent_data.get('reagent_name')}`\n"
                        f"*Stock actual:* {reagent_data.get('current_stock')} unidades\n"
                        f"*Última orden:* {reagent_data.get('last_order_status', 'N/A')}"
                    ),
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": ":warning: *DEMO* — datos sintéticos calibrados",
                    }
                ],
            },
        ],
    }
    return {
        "tool": "update_canvas",
        "channel_id": channel_id,
        "payload": payload,
        "success": True,
        "note": "Canvas payload prepared. Send via Slack Canvas API in production.",
    }
