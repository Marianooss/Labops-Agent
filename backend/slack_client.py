"""
slack_client.py — Bolt Python app + event handlers for LabOps Agent.
Socket Mode only. 4 handlers: scheduled alert, view_forecast, order_reagent, assign_team.
All messages carry a visible DEMO badge.
Uses Slack Channel History API + Claude API summarization.
"""
import json
import logging
import os
import re
import time
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))  # Load .env from project root

import database as db
import prediction
import claude_client as claude
import mcp_server as mcp
import blocks_loader as bl
import agent_router

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN", "")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET", "")
SLACK_USER_TOKEN = os.environ.get("SLACK_USER_TOKEN", "")
LABOPS_ALERTS_CHANNEL = os.environ.get("LABOPS_ALERTS_CHANNEL", "#labops-alerts")

ENV = os.environ.get("ENV", "production")
token_verification_enabled = ENV != "development"

bolt_app = App(
    token=SLACK_BOT_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET,
    token_verification_enabled=token_verification_enabled,
)


# ---------------------------------------------------------------------------
# UTILS
# ---------------------------------------------------------------------------
def _severity_badge(severity: str) -> str:
    return "🔴 *CRITICAL*" if severity == "critical" else "🟡 *WARNING*"


def _demo_badge() -> Dict[str, Any]:
    return {
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": ":warning: *DEMO* — datos sintéticos calibrados con patrones reales",
            }
        ],
    }


def _update_inventory_canvas(client, channel_id: str, thread_ts: str, updated_reagent: str):
    """
    Update the LabOps inventory display.
    First tries Slack Canvas API (canvases.edit if canvas_id exists,
    otherwise canvases.create), falls back to rich Block Kit message.
    Stores canvas_id in Supabase lab_config for persistence.
    """
    items = db.get_inventory()
    canvas_id = db.get_lab_config("canvas_id")

    # Build markdown content
    lines = ["# 📋 LabOps Inventario\n"]
    lines.append("| Reactivo | Stock | Crítico | Días restantes |")
    lines.append("|----------|-------|---------|----------------|")
    for item in items:
        r = item["reagent_name"]
        stock = item["current_stock"]
        crit = item.get("criticality", "medium")
        lead = item.get("reorder_lead_time_days", 7)
        try:
            proj = prediction.calculate_stockout_projection(r, stock, lead)
            days = proj.get("projected_stockout_days", "N/A")
        except Exception:
            days = "N/A"
        marker = " 🆕" if r == updated_reagent else ""
        lines.append(f"| {r}{marker} | {stock} | {crit} | {days} |")
    lines.append("\n_Last update: just now_")
    markdown_content = "\n".join(lines)

    # Try real Canvas API
    try:
        if canvas_id:
            result = client.api_call(
                "canvases.edit",
                json={
                    "canvas_id": canvas_id,
                    "document_content": {
                        "type": "markdown",
                        "markdown_value": markdown_content,
                    },
                },
            )
            if result.get("ok"):
                logger.info("Canvas %s edited successfully", canvas_id)
                client.chat_postMessage(
                    channel=channel_id,
                    thread_ts=thread_ts,
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": (
                                    f":page_facing_up: *Canvas de inventario actualizado*\n"
                                    f"Reactivo `{updated_reagent}` incluido.\n"
                                    f"Canvas ID: `{canvas_id}`"
                                ),
                            },
                        },
                        _demo_badge(),
                    ],
                    text="Canvas de inventario actualizado",
                )
                return
            else:
                logger.warning("canvases.edit failed: %s — falling back to create", result.get("error"))
                canvas_id = None

        if not canvas_id:
            result = client.api_call(
                "canvases.create",
                json={
                    "title": "LabOps Inventario",
                    "document_content": {
                        "type": "markdown",
                        "markdown_value": markdown_content,
                    },
                },
            )
            if result.get("ok"):
                new_canvas_id = result.get("canvas", {}).get("id", "")
                canvas_url = result.get("canvas", {}).get("url", "")
                if new_canvas_id:
                    db.set_lab_config("canvas_id", new_canvas_id)
                    logger.info("Canvas created and stored: %s", new_canvas_id)
                client.chat_postMessage(
                    channel=channel_id,
                    thread_ts=thread_ts,
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": (
                                    f":page_facing_up: *Canvas de inventario creado*\n"
                                    f"Reactivo `{updated_reagent}` incluido.\n"
                                    f"<{canvas_url}|Ver Canvas completo>"
                                ),
                            },
                        },
                        _demo_badge(),
                    ],
                    text="Canvas de inventario creado",
                )
                return
    except Exception as exc:
        logger.error("Canvas API failed: %s", exc, exc_info=True)

    # Fallback: rich Block Kit inventory update
    block_rows = []
    for item in items:
        r = item["reagent_name"]
        stock = item["current_stock"]
        crit = item.get("criticality", "medium")
        lead = item.get("reorder_lead_time_days", 7)
        try:
            proj = prediction.calculate_stockout_projection(r, stock, lead)
            days = proj.get("projected_stockout_days", "N/A")
            sev = proj.get("severity", "unknown")
            emoji = "🔴" if sev == "critical" else "🟡" if sev == "warning" else "🟢"
        except Exception:
            days = "N/A"
            emoji = "⚪"
        block_rows.append(f"{emoji} *{r}* — {stock} u. | {days} días | {crit}")

    try:
        client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            blocks=[
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "📋 LabOps Inventario"},
                },
                {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(block_rows)}},
                _demo_badge(),
            ],
            text="Inventario actualizado",
        )
    except Exception as exc:
        logger.error("Block Kit fallback failed: %s", exc, exc_info=True)


# ---------------------------------------------------------------------------
# HANDLER 1 — Scheduled alert (called every hour or via /alert/trigger)
# ---------------------------------------------------------------------------
def check_and_send_stockout_alerts(channel: Optional[str] = None):
    """
    Check all inventory items. For each with alert_trigger=True,
    post a Block Kit alert message to the alerts channel.
    """
    target = channel or LABOPS_ALERTS_CHANNEL
    logger.info("Checking stockout alerts for channel %s", target)
    try:
        items = db.get_inventory()
    except Exception as exc:
        logger.error("Failed to load inventory: %s", exc, exc_info=True)
        return

    for item in items:
        reagent = item["reagent_name"]
        stock = item["current_stock"]
        lead = item.get("reorder_lead_time_days", 7)
        try:
            proj = prediction.calculate_stockout_projection(reagent, stock, lead)
            if not proj["alert_trigger"]:
                continue
            explanation = claude.explain_stockout(
                reagent,
                proj["projected_stockout_days"],
                stock,
                seasonality_hint="TSH demand spikes in winter (Jun-Aug) in Argentina",
            )
            db.log_alert(reagent, proj["projected_stockout_date"], proj["severity"], explanation)
            _post_stockout_alert(target, reagent, proj["projected_stockout_days"], proj["severity"], explanation, current_stock=stock)
            logger.info("Alert sent for %s: %s days remaining", reagent, proj["projected_stockout_days"])
        except Exception as exc:
            logger.error("Alert failed for %s: %s", reagent, exc, exc_info=True)


def _post_stockout_alert(channel: str, reagent_name: str, projected_days: int, severity: str, explanation: str, current_stock: float = 0):
    """Post the canonical Block Kit alert to #labops-alerts using blocks/alert.json template."""
    try:
        template = bl.load_template(
            "alert",
            reagent_name=reagent_name,
            current_stock=current_stock,
            projected_days=projected_days,
            explanation=explanation,
        )
        blocks = template["blocks"]
        # Inject dynamic severity badge into the explanation section
        for block in blocks:
            if block.get("type") == "section" and block.get("text", {}).get("text", "").startswith("*¿Por qué?*"):
                block["text"]["text"] = f"{_severity_badge(severity)}\n{explanation}"
        return bolt_app.client.chat_postMessage(
            channel=channel,
            blocks=blocks,
            text=f"Alerta: {reagent_name} stockout in {projected_days} days",
        )
    except Exception:
        # Graceful fallback when Slack token is dummy/invalid or template missing
        logger.warning("[DEMO] Would post Slack alert to %s: %s stockout in %s days", channel, reagent_name, projected_days)
        return {"ok": True, "ts": "DEMO_TS"}


# ---------------------------------------------------------------------------
# HANDLER 2 — Button: "📊 Ver proyección" (responds in thread)
# ---------------------------------------------------------------------------
@bolt_app.action("view_forecast")
def handle_view_forecast(ack, body, client):
    ack()
    reagent = ""
    channel = ""
    thread_ts = ""
    try:
        reagent = body["actions"][0].get("value", "TSH")
        channel = body["channel"]["id"]
        thread_ts = body["message"]["ts"]
        logger.info("view_forecast triggered for %s", reagent)

        forecast = prediction.get_forecast(reagent, days=14)
        next_7 = forecast["daily_demand"][:7]

        rows = ""
        for day in next_7:
            rows += f"| {day['date']} | {day['predicted_qty']} | {day['lower_bound']} – {day['upper_bound']} |\n"

        table = (
            f"*Pronóstico de demanda — {reagent} (próximos 7 días)*\n"
            f"```\n| Fecha       | Predicción | Rango (80% CI) |\n"
            f"|-------------|------------|----------------|\n"
            f"{rows}```"
        )

        # -------------------------------------------------------------------
        # Rich Block Kit: forecast table + embedded chart image
        # -------------------------------------------------------------------
        backend_url = os.environ.get("BACKEND_URL", "http://localhost:8000")
        chart_url = f"{backend_url}/chart/forecast/{reagent}?days=14"

        client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            blocks=[
                {"type": "section", "text": {"type": "mrkdwn", "text": table}},
                {
                    "type": "image",
                    "image_url": chart_url,
                    "alt_text": f"Pronóstico de demanda — {reagent}",
                },
                _demo_badge(),
            ],
            text=f"Pronóstico {reagent}",
        )

        # -------------------------------------------------------------------
        # TASK 1 — Slack Channel History API (conversations.history)
        # -------------------------------------------------------------------
        LABOPS_ALERTS_CHANNEL_ID = os.environ.get("LABOPS_ALERTS_CHANNEL_ID", "")
        history_text = ""
        try:
            if LABOPS_ALERTS_CHANNEL_ID:
                history_result = client.conversations_history(
                    channel=LABOPS_ALERTS_CHANNEL_ID,
                    limit=20,
                )
                messages = history_result.get("messages", [])
                reagent_mentions = [
                    m for m in messages
                    if reagent.upper() in m.get("text", "").upper()
                    and m.get("bot_id")
                ][:3]
                if reagent_mentions:
                    alert_lines = []
                    for msg in reagent_mentions:
                        ts = msg.get("ts", "")
                        date = ts.split(".")[0] if ts else "N/A"
                        text_snippet = msg.get("text", "")[:80]
                        alert_lines.append(f"• `{date}` — {text_snippet}...")
                    history_text = (
                        f"*📋 {len(reagent_mentions)} alerta(s) reciente(s) de `{reagent}`:*\n"
                        + "\n".join(alert_lines)
                    )
                else:
                    history_text = f"*📋 Sin alertas previas de `{reagent}` en el historial reciente.*"
            else:
                history_text = "*📋 `LABOPS_ALERTS_CHANNEL_ID` no configurado. Agregalo a .env.*"
        except Exception as e:
            logger.error("Channel history fetch failed: %s", e, exc_info=True)
            history_text = f"*📋 No se pudo obtener historial: {str(e)} (verificá scope `channels:history`).*"

        client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            blocks=[
                {"type": "section", "text": {"type": "mrkdwn", "text": history_text}},
                _demo_badge(),
            ],
            text=f"Historial {reagent}",
        )

        # -------------------------------------------------------------------
        # TASK 2 — Slack Real-Time Search API (search.messages)
        # -------------------------------------------------------------------
        # search.messages requires a USER token (xoxp-).
        # If SLACK_USER_TOKEN is set, we use it; otherwise the bot token
        # returns empty results gracefully.
        search_text = ""
        try:
            if SLACK_USER_TOKEN:
                from slack_sdk import WebClient
                user_client = WebClient(token=SLACK_USER_TOKEN)
                search_result = user_client.search_messages(
                    query=f"{reagent} in:labops-alerts",
                    count=5,
                    sort="timestamp",
                    sort_dir="desc",
                )
            else:
                search_result = client.search_messages(
                    query=f"{reagent} in:labops-alerts",
                    count=5,
                    sort="timestamp",
                    sort_dir="desc",
                )
            matches = search_result.get("messages", {}).get("matches", [])
            if matches:
                search_lines = []
                for msg in matches[:3]:
                    channel_name = msg.get("channel", {}).get("name", "unknown")
                    ts = msg.get("ts", "")
                    date = ts.split(".")[0] if ts else "N/A"
                    snippet = msg.get("text", "")[:80]
                    search_lines.append(f"• `{date}` — #{channel_name}: {snippet}...")
                search_text = (
                    f"*🔍 {len(matches)} resultado(s) de búsqueda en el workspace para `{reagent}`:*\n"
                    + "\n".join(search_lines)
                )
            else:
                search_text = f"*🔍 Sin resultados de búsqueda para `{reagent}` en el workspace.*"
        except Exception as e:
            logger.error("Search messages failed: %s", e, exc_info=True)
            search_text = f"*🔍 No se pudo ejecutar búsqueda: {str(e)} (verificá scope `search:read` y token de usuario).*"

        client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            blocks=[
                {"type": "section", "text": {"type": "mrkdwn", "text": search_text}},
                _demo_badge(),
            ],
            text=f"Búsqueda {reagent}",
        )
    except Exception as exc:
        logger.error("handle_view_forecast failed: %s", exc, exc_info=True)
        if channel:
            client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts if thread_ts else None,
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"❌ Error al generar proyección para `{reagent or '?'}`: `{str(exc)}`",
                        },
                    },
                    _demo_badge(),
                ],
                text="Error en proyección",
            )


# ---------------------------------------------------------------------------
# HANDLER 3 — Button: "🛒 Ordenar reactivo" (modal with supplier dropdown)
# ---------------------------------------------------------------------------
@bolt_app.action("order_reagent")
def handle_order_reagent(ack, body, client):
    ack()
    try:
        reagent = body["actions"][0].get("value", "TSH")
        logger.info("order_reagent triggered for %s", reagent)
        inv = db.get_inventory(reagent)
        stock = inv[0]["current_stock"] if inv else 0
        suggested_qty = max(50, int(stock * 0.5))

        view = bl.load_template(
            "modal_order",
            reagent_name=reagent,
            suggested_quantity=str(suggested_qty),
        )
        view["private_metadata"] = json.dumps({"reagent": reagent, "channel": body["channel"]["id"], "thread_ts": body["message"]["ts"]})
        client.views_open(
            trigger_id=body["trigger_id"],
            view=view,
        )
    except Exception as exc:
        logger.error("handle_order_reagent failed: %s", exc, exc_info=True)
        # ack() already sent; we can't show error in UI here easily
        raise


@bolt_app.view("order_modal")
def handle_order_submission(ack, body, client):
    ack()
    meta = {}
    try:
        meta = json.loads(body["view"]["private_metadata"])
        values = body["view"]["state"]["values"]
        reagent = values["reagent_block"]["reagent_name"]["value"]
        quantity = float(values["quantity_block"]["quantity"]["value"])
        supplier = values["supplier_block"]["supplier"]["selected_option"]["value"]
        logger.info("order_submission: %s x%s from %s", reagent, quantity, supplier)

        order = mcp.create_order(reagent, quantity, supplier)
        logger.debug("Order created: %s", order)

        # Confirm in thread
        client.chat_postMessage(
            channel=meta["channel"],
            thread_ts=meta["thread_ts"],
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f":white_check_mark: *Orden creada*\n"
                            f"*Reactivo:* `{reagent}`\n"
                            f"*Cantidad:* {quantity}\n"
                            f"*Proveedor:* {supplier}\n"
                            f"*Estado:* pending"
                        ),
                    },
                },
                _demo_badge(),
            ],
            text=f"Orden creada: {reagent} x{quantity}",
        )

        # Update Canvas (real API + Block Kit fallback)
        _update_inventory_canvas(client, meta["channel"], meta["thread_ts"], reagent)
    except Exception as exc:
        logger.error("handle_order_submission failed: %s", exc, exc_info=True)
        if meta.get("channel"):
            client.chat_postMessage(
                channel=meta["channel"],
                thread_ts=meta.get("thread_ts"),
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"❌ Error al procesar la orden: `{str(exc)}`",
                        },
                    },
                    _demo_badge(),
                ],
                text="Error en orden",
            )


# ---------------------------------------------------------------------------
# HANDLER 4 — Button: "👤 Asignar al equipo" (user selector modal + DM)
# ---------------------------------------------------------------------------
@bolt_app.action("assign_team")
def handle_assign_team(ack, body, client):
    ack()
    try:
        reagent = body["actions"][0].get("value", "TSH")
        logger.info("assign_team triggered for %s", reagent)
        client.views_open(
            trigger_id=body["trigger_id"],
            view={
                "type": "modal",
                "callback_id": "assign_team_modal",
                "private_metadata": json.dumps({
                    "reagent": reagent,
                    "channel": body["channel"]["id"],
                    "thread_ts": body["message"]["ts"],
                }),
                "title": {"type": "plain_text", "text": "👤 Asignar al equipo"},
                "submit": {"type": "plain_text", "text": "Asignar"},
                "close": {"type": "plain_text", "text": "Cancelar"},
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "user_block",
                        "label": {"type": "plain_text", "text": "Seleccionar miembro del equipo"},
                        "element": {
                            "type": "users_select",
                            "action_id": "selected_user",
                            "placeholder": {"type": "plain_text", "text": "Elegir usuario…"},
                        },
                        "optional": False,
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Reactivo:* `{reagent}`\nSe asignará la revisión de stock a la persona seleccionada.",
                        },
                    },
                    _demo_badge(),
                ],
            },
        )
    except Exception as exc:
        logger.error("handle_assign_team failed: %s", exc, exc_info=True)
        raise


@bolt_app.view("assign_team_modal")
def handle_assign_team_submission(ack, body, client):
    ack()
    meta = {}
    try:
        meta = json.loads(body["view"]["private_metadata"])
        user_id = body["view"]["state"]["values"]["user_block"]["selected_user"]["selected_user"]
        reagent = meta["reagent"]
        logger.info("assign_team_submission: %s assigned to %s", reagent, user_id)

        # Send DM to selected user
        client.chat_postMessage(
            channel=user_id,
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f":bust_in_silhouette: *Asignación de LabOps Agent*\n"
                            f"Se te asignó la revisión del reactivo `{reagent}`.\n"
                            f"Por favor verificá el stock y confirmá si es necesario ordenar."
                        ),
                    },
                },
                _demo_badge(),
            ],
            text=f"Asignación: revisar stock de {reagent}",
        )

        # Confirm in thread
        client.chat_postMessage(
            channel=meta["channel"],
            thread_ts=meta["thread_ts"],
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f":white_check_mark: *Asignado* a <@{user_id}> — "
                            f"revisar stock de `{reagent}`."
                        ),
                    },
                },
                _demo_badge(),
            ],
            text=f"Asignado a {user_id}",
        )
    except Exception as exc:
        logger.error("handle_assign_team_submission failed: %s", exc, exc_info=True)
        if meta.get("channel"):
            client.chat_postMessage(
                channel=meta["channel"],
                thread_ts=meta.get("thread_ts"),
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"❌ Error al asignar tarea: `{str(exc)}`",
                        },
                    },
                    _demo_badge(),
                ],
                text="Error en asignación",
            )


# ---------------------------------------------------------------------------
# App mention handler — agent router with Claude tool-use
# ---------------------------------------------------------------------------
@bolt_app.event("app_mention")
def handle_app_mention(event, say, client):
    text = event.get("text", "")
    user = event.get("user", "")
    channel = event.get("channel", "")
    logger.info("app_mention from %s in %s: %s", user, channel, text[:80])

    try:
        # Strip the bot mention from text so Claude doesn't get confused
        clean_text = re.sub(r"<@\w+>", "", text).strip()
        if not clean_text:
            clean_text = "¿Cómo estás?"

        # Run the agent loop — Claude decides which MCP tool to call
        agent_response = agent_router.run_agent(
            user_message=clean_text,
            channel_id=channel,
        )

        say(
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"🤖 *LabOps Agent:*\n{agent_response}",
                    },
                },
                _demo_badge(),
            ],
            text="LabOps Agent response",
        )
    except Exception as exc:
        logger.error("handle_app_mention failed: %s", exc, exc_info=True)
        say(
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"❌ Error del agente: `{str(exc)}`",
                    },
                },
                _demo_badge(),
            ],
            text="Error del agente",
        )


# ---------------------------------------------------------------------------
# App Home dashboard
# ---------------------------------------------------------------------------
@bolt_app.event("app_home_opened")
def handle_app_home_opened(event, client):
    user_id = event.get("user", "")
    try:
        # Fetch live data
        inventory = db.get_inventory()
        alerts = db.get_alerts(limit=5)
        orders = db.get_orders(status="pending")

        # Build inventory rows
        inv_rows = []
        for item in inventory[:6]:
            r = item["reagent_name"]
            stock = item["current_stock"]
            crit = item.get("criticality", "medium")
            emoji = "🔴" if crit == "critical" else "🟡" if crit == "high" else "🟢"
            inv_rows.append(f"{emoji} *{r}* — {stock} u.")

        # Build alert rows
        alert_rows = []
        for alert in alerts[:3]:
            r = alert["reagent_name"]
            sev = alert.get("severity", "warning")
            emoji = "🔴" if sev == "critical" else "🟡"
            alert_rows.append(f"{emoji} `{r}` — stockout {alert.get('predicted_stockout_date', 'N/A')}")
        if not alert_rows:
            alert_rows.append("✅ Sin alertas activas")

        # Build order rows
        order_rows = []
        for order in orders[:3]:
            r = order["reagent_name"]
            qty = order["quantity"]
            order_rows.append(f"🛒 `{r}` x{qty} — {order.get('status', 'pending')}")
        if not order_rows:
            order_rows.append("📭 Sin órdenes pendientes")

        client.views_publish(
            user_id=user_id,
            view={
                "type": "home",
                "blocks": [
                    {
                        "type": "header",
                        "text": {"type": "plain_text", "text": "🏠 LabOps Agent — Dashboard"},
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                "*Estado del agente:* 🟢 Activo\n"
                                "*Último modelo:* Prophet (temperature=0)\n"
                                "*Canal de alertas:* " + LABOPS_ALERTS_CHANNEL
                            ),
                        },
                    },
                    {"type": "divider"},
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*📋 Inventario*\n" + "\n".join(inv_rows),
                        },
                    },
                    {"type": "divider"},
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*🔔 Alertas recientes*\n" + "\n".join(alert_rows),
                        },
                    },
                    {"type": "divider"},
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*🛒 Órdenes pendientes*\n" + "\n".join(order_rows),
                        },
                    },
                    _demo_badge(),
                ],
            },
        )
    except Exception as exc:
        logger.error("handle_app_home_opened failed: %s", exc, exc_info=True)
        client.views_publish(
            user_id=user_id,
            view={
                "type": "home",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"⚠️ No se pudo cargar el dashboard: `{str(exc)}`",
                        },
                    },
                    _demo_badge(),
                ],
            },
        )


# ---------------------------------------------------------------------------
# Socket Mode runner
# ---------------------------------------------------------------------------
def start_socket_mode():
    if not SLACK_APP_TOKEN:
        logger.warning("SLACK_APP_TOKEN not set. Slack Socket Mode disabled.")
        logger.warning("To enable Slack integration, add SLACK_APP_TOKEN to your .env file.")
        # Keep container alive so docker-compose doesn't restart-loop
        while True:
            time.sleep(3600)
    handler = SocketModeHandler(bolt_app, SLACK_APP_TOKEN)
    handler.start()


if __name__ == "__main__":
    logger.info("[LabOps] Registered handlers:")
    for key in bolt_app._listeners:
        logger.info("  - %s", key)
    start_socket_mode()
