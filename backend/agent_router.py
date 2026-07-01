"""
agent_router.py — Claude tool-use agent router for LabOps Agent.

When a user @mentions the bot, this module sends the message to Claude
with MCP tool definitions. The LLM decides which tool(s) to call,
we execute them, and Claude generates the natural-language response.

Tools exposed to Claude (mirroring mcp_server.py):
  - get_inventory(reagent_name?)
  - get_forecast(reagent_name, days?)
  - create_order(reagent_name, quantity, supplier)
  - update_canvas(channel_id, reagent_data)

Temperature=0 (immutable per CLAUDE.md).
"""
import json
import logging
import os
import sys
from typing import Dict, Any, Optional

# Ensure local backend imports resolve when this module runs from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

import claude_client as claude
import mcp_server as mcp
import prediction

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool schema definitions for Anthropic API
# ---------------------------------------------------------------------------
TOOLS = [
    {
        "name": "get_inventory",
        "description": "Get current stock levels for one or all reagents in the lab inventory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reagent_name": {
                    "type": "string",
                    "description": "Name of the reagent (e.g. TSH, Hemograma). Omit to get all.",
                }
            },
        },
    },
    {
        "name": "get_forecast",
        "description": "Get Prophet demand forecast for a reagent over N days.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reagent_name": {
                    "type": "string",
                    "description": "Name of the reagent (e.g. TSH, Hemograma).",
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days to forecast (default 14).",
                    "default": 14,
                },
            },
            "required": ["reagent_name"],
        },
    },
    {
        "name": "create_order",
        "description": "Create a reagent order in the system. Only use when the user explicitly requests to place an order.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reagent_name": {
                    "type": "string",
                    "description": "Name of the reagent to order.",
                },
                "quantity": {
                    "type": "number",
                    "description": "Quantity to order.",
                },
                "supplier": {
                    "type": "string",
                    "description": "Supplier name (e.g. LabSupplier AR).",
                },
            },
            "required": ["reagent_name", "quantity", "supplier"],
        },
    },
    {
        "name": "update_canvas",
        "description": "Update the Slack Canvas inventory document with latest reagent data.",
        "input_schema": {
            "type": "object",
            "properties": {
                "channel_id": {
                    "type": "string",
                    "description": "Slack channel ID where the canvas lives.",
                },
                "reagent_data": {
                    "type": "object",
                    "description": "Dict with reagent_name, current_stock, last_order_status.",
                },
            },
            "required": ["channel_id", "reagent_data"],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool execution dispatcher
# ---------------------------------------------------------------------------
def _execute_tool(name: str, arguments: dict) -> str:
    """Execute an MCP tool by name and return a JSON string result."""
    logger.info("Agent executing tool: %s args=%s", name, arguments)
    try:
        if name == "get_inventory":
            result = mcp.get_inventory(arguments.get("reagent_name"))
            # Inject authoritative stockout projection so Claude doesn't compute its own
            if result.get("reagent_name") and result.get("current_stock") is not None:
                try:
                    proj = prediction.calculate_stockout_projection(
                        result["reagent_name"],
                        float(result["current_stock"]),
                        reorder_lead_time=7,
                    )
                    result["projected_stockout_days"] = proj["projected_stockout_days"]
                    result["severity"] = proj["severity"]
                    result["alert_trigger"] = proj["alert_trigger"]
                    result["reorder_lead_time"] = proj["reorder_lead_time"]
                except Exception:
                    pass  # leave result unchanged if projection fails
            return json.dumps(result, ensure_ascii=False, default=str)

        elif name == "get_forecast":
            result = mcp.get_forecast(
                arguments["reagent_name"],
                days=arguments.get("days", 14),
            )
            return json.dumps(result, ensure_ascii=False, default=str)

        elif name == "create_order":
            result = mcp.create_order(
                arguments["reagent_name"],
                arguments["quantity"],
                arguments["supplier"],
            )
            return json.dumps(result, ensure_ascii=False, default=str)

        elif name == "update_canvas":
            result = mcp.update_canvas(
                arguments["channel_id"],
                arguments["reagent_data"],
            )
            return json.dumps(result, ensure_ascii=False, default=str)

        else:
            return json.dumps({"error": f"Unknown tool: {name}"})
    except Exception as exc:
        logger.error("Tool execution failed: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------
def run_agent(
    user_message: str,
    channel_id: Optional[str] = None,
    max_tool_rounds: int = 3,
) -> str:
    """
    Send user message to Claude with tools enabled, execute any tool_use
    requests, and return the final natural-language response.

    Falls back to a static Spanish response if the Claude API is unavailable.
    """
    system_prompt = (
        "You are LabOps Agent, an AI assistant for clinical laboratory operations. "
        "You have access to tools that query lab inventory, run demand forecasts, "
        "create reagent orders, and update inventory canvases. "
        "Respond in the same language the user writes in (usually Spanish). "
        "Be concise, specific, and action-oriented. "
        "When creating orders, always confirm the details in your response. "
        "When inventory data includes projected_stockout_days, always report that exact number. "
        "Do not calculate your own estimate from stock and forecast data."
    )

    messages: list = [{"role": "user", "content": user_message}]

    try:
        client = claude.get_client()
    except Exception as exc:
        logger.warning("Claude client unavailable, using fallback: %s", exc)
        return _fallback_response(user_message)

    for _ in range(max_tool_rounds):
        try:
            response = client.messages.create(
                model=claude.CLAUDE_MODEL,
                max_tokens=1024,
                temperature=0,
                system=system_prompt,
                tools=TOOLS,
                messages=messages,
            )
        except Exception as exc:
            logger.error("Claude API call failed: %s", exc, exc_info=True)
            return _fallback_response(user_message)

        # Collect text and tool_use blocks
        text_parts = []
        tool_uses = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_uses.append(block)

        # If no tools requested, return the text
        if not tool_uses:
            return " ".join(text_parts)

        # Append assistant message (text + tool_use blocks)
        assistant_content = []
        for block in response.content:
            assistant_content.append(block)
        messages.append({"role": "assistant", "content": assistant_content})

        # Execute each tool and append tool_result
        tool_results = []
        for tu in tool_uses:
            result_text = _execute_tool(tu.name, tu.input)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": result_text,
                }
            )
        messages.append({"role": "user", "content": tool_results})

    # If we hit the round limit, return whatever we have
    return " ".join(text_parts) if text_parts else _fallback_response(user_message)


def _fallback_response(user_message: str) -> str:
    """Graceful fallback when Claude API is unavailable."""
    msg_lower = user_message.lower()
    reagent = "TSH"
    for candidate in ["tsh", "hemograma", "ionograma", "glucosa", "urea", "creatinina"]:
        if candidate in msg_lower:
            reagent = candidate.upper()
            break

    return (
        f"🤖 *LabOps Agent* — modo fallback activado (Claude API no disponible).\n"
        f"Podés usar los botones en las alertas de `{reagent}` para ver proyecciones, "
        f"ordenar reactivos o asignar tareas al equipo."
    )
