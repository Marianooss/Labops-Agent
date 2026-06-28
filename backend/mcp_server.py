"""
mcp_server.py — Real MCP Server using Anthropic MCP Python SDK.
Exposes 4 lab tools: get_inventory, get_forecast, create_order, update_canvas.

Dual-mode:
  1. Direct Python functions (used by FastAPI REST endpoints in main.py)
  2. MCP Server via stdio transport (used by Claude Desktop / MCP clients)
"""
import asyncio
import json
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

import database as db
import prediction


# ---------------------------------------------------------------------------
# Core tool functions (REST / direct import compatible)
# ---------------------------------------------------------------------------
def get_inventory(reagent_name: Optional[str] = None) -> Dict[str, Any]:
    """Return current stock for one or all reagents."""
    rows = db.get_inventory(reagent_name)
    return {
        "tool": "get_inventory",
        "reagent_name": reagent_name or "all",
        "results": rows,
        "count": len(rows),
    }


def get_forecast(reagent_name: str, days: int = 30) -> Dict[str, Any]:
    """Return Prophet demand forecast for a reagent."""
    forecast = prediction.get_forecast(reagent_name, days=days)
    return {
        "tool": "get_forecast",
        "reagent_name": reagent_name,
        "forecast": forecast,
    }


def create_order(reagent_name: str, quantity: float, supplier: str) -> Dict[str, Any]:
    """Create a reagent order in Supabase."""
    order = db.create_order(reagent_name, quantity, supplier, status="pending")
    return {
        "tool": "create_order",
        "order": order,
        "success": bool(order),
    }


def update_canvas(channel_id: str, reagent_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update the Slack Canvas inventory document (payload prepared)."""
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


# ---------------------------------------------------------------------------
# MCP Server (Anthropic MCP SDK — stdio transport)
# ---------------------------------------------------------------------------
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent

    _server = Server("labops-agent")

    @_server.list_tools()
    async def _list_tools():
        return [
            Tool(
                name="get_inventory",
                description="Get current reagent stock levels from the lab inventory",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "reagent_name": {
                            "type": "string",
                            "description": "Name of the reagent (e.g. TSH, Hemograma)"
                        }
                    }
                }
            ),
            Tool(
                name="get_forecast",
                description="Get Prophet demand forecast for a reagent",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "reagent_name": {"type": "string"},
                        "days": {"type": "integer", "default": 30}
                    },
                    "required": ["reagent_name"]
                }
            ),
            Tool(
                name="create_order",
                description="Create a reagent order in the system",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "reagent_name": {"type": "string"},
                        "quantity": {"type": "number"},
                        "supplier": {"type": "string"}
                    },
                    "required": ["reagent_name", "quantity", "supplier"]
                }
            ),
            Tool(
                name="update_canvas",
                description="Update the Slack Canvas inventory document",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {"type": "string"},
                        "reagent_data": {"type": "object"}
                    },
                    "required": ["channel_id", "reagent_data"]
                }
            ),
        ]

    @_server.call_tool()
    async def _call_tool(name: str, arguments: dict):
        if name == "get_inventory":
            result = get_inventory(arguments.get("reagent_name"))
            return [TextContent(type="text", text=json.dumps(result))]

        elif name == "get_forecast":
            result = get_forecast(
                arguments["reagent_name"],
                days=arguments.get("days", 30)
            )
            return [TextContent(type="text", text=json.dumps(result))]

        elif name == "create_order":
            result = create_order(
                arguments["reagent_name"],
                arguments["quantity"],
                arguments["supplier"]
            )
            return [TextContent(type="text", text=json.dumps(result))]

        elif name == "update_canvas":
            result = update_canvas(
                arguments["channel_id"],
                arguments["reagent_data"]
            )
            return [TextContent(type="text", text=json.dumps(result))]

        raise ValueError(f"Unknown tool: {name}")

    async def run_mcp_server():
        async with stdio_server() as streams:
            await _server.run(
                streams[0], streams[1],
                _server.create_initialization_options()
            )

except ImportError:
    _server = None
    run_mcp_server = None


if __name__ == "__main__":
    if run_mcp_server:
        asyncio.run(run_mcp_server())
    else:
        print("[ERROR] MCP SDK not installed. Run: pip install mcp>=1.0.0")
