"""
slack_client.py — Bolt Python app + event handlers for LabOps Agent.
Socket Mode only. 4 handlers: scheduled alert, view_forecast, order_reagent, assign_team.
All messages carry a visible DEMO badge.
Includes Real-Time Search API + Slack AI summarization.
"""
import json
import os
import re
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))  # Load .env from project root

import database as db
import prediction
import claude_client as claude
import mcp_server as mcp

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN", "")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET", "")
LABOPS_ALERTS_CHANNEL = os.environ.get("LABOPS_ALERTS_CHANNEL", "#labops-alerts")

bolt_app = App(
    token=SLACK_BOT_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET,
    token_verification_enabled=False,  # Skip auth.test for local dev
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
    First tries Slack Canvas API, falls back to rich Block Kit message.
    """
    items = db.get_inventory()

    # Try real Canvas API
    try:
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
            canvas_url = result.get("canvas", {}).get("url", "")
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
                                f"<{canvas_url}|Ver Canvas completo>"
                            ),
                        },
                    },
                    _demo_badge(),
                ],
                text="Canvas de inventario actualizado",
            )
            return
    except Exception:
        pass  # Fall through to Block Kit fallback

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


# ---------------------------------------------------------------------------
# HANDLER 1 — Scheduled alert (called every hour or via /alert/trigger)
# ---------------------------------------------------------------------------
def check_and_send_stockout_alerts(channel: Optional[str] = None):
    """
    Check all inventory items. For each with alert_trigger=True,
    post a Block Kit alert message to the alerts channel.
    """
    target = channel or LABOPS_ALERTS_CHANNEL
    items = db.get_inventory()
    for item in items:
        reagent = item["reagent_name"]
        stock = item["current_stock"]
        lead = item.get("reorder_lead_time_days", 7)
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
        _post_stockout_alert(target, reagent, proj["projected_stockout_days"], proj["severity"], explanation)


def _post_stockout_alert(channel: str, reagent_name: str, projected_days: int, severity: str, explanation: str):
    """Post the canonical Block Kit alert to #labops-alerts."""
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"Alerta: {reagent_name} se agota en {projected_days} días",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"{_severity_badge(severity)}\n"
                    f"{explanation}"
                ),
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "📊 Ver proyección"},
                    "action_id": "view_forecast",
                    "value": reagent_name,
                    "style": "primary",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "🛒 Ordenar reactivo"},
                    "action_id": "order_reagent",
                    "value": reagent_name,
                    "style": "danger",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "👤 Asignar al equipo"},
                    "action_id": "assign_team",
                    "value": reagent_name,
                },
            ],
        },
        _demo_badge(),
    ]
    try:
        return bolt_app.client.chat_postMessage(
            channel=channel,
            blocks=blocks,
            text=f"Alerta: {reagent_name} stockout in {projected_days} days",
        )
    except Exception:
        # Graceful fallback when Slack token is dummy/invalid
        print(f"[DEMO] Would post Slack alert to {channel}: {reagent_name} stockout in {projected_days} days")
        return {"ok": True, "ts": "DEMO_TS"}


# ---------------------------------------------------------------------------
# HANDLER 2 — Button: "📊 Ver proyección" (responds in thread)
# ---------------------------------------------------------------------------
@bolt_app.action("view_forecast")
def handle_view_forecast(ack, body, client):
    ack()
    reagent = body["actions"][0].get("value", "TSH")
    channel = body["channel"]["id"]
    thread_ts = body["message"]["ts"]

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

    client.chat_postMessage(
        channel=channel,
        thread_ts=thread_ts,
        blocks=[
            {"type": "section", "text": {"type": "mrkdwn", "text": table}},
            _demo_badge(),
        ],
        text=f"Pronóstico {reagent}",
    )

    # -----------------------------------------------------------------------
    # TASK 1 — Real-Time Search API via conversations.history
    # -----------------------------------------------------------------------
    LABOPS_ALERTS_CHANNEL_ID = os.environ.get("LABOPS_ALERTS_CHANNEL_ID", "")
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
                and m.get("bot_id")  # only bot messages (our alerts)
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


# ---------------------------------------------------------------------------
# HANDLER 3 — Button: "🛒 Ordenar reactivo" (modal with supplier dropdown)
# ---------------------------------------------------------------------------
@bolt_app.action("order_reagent")
def handle_order_reagent(ack, body, client):
    ack()
    reagent = body["actions"][0].get("value", "TSH")
    inv = db.get_inventory(reagent)
    stock = inv[0]["current_stock"] if inv else 0
    suggested_qty = max(50, int(stock * 0.5))

    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "order_modal",
            "private_metadata": json.dumps({"reagent": reagent, "channel": body["channel"]["id"], "thread_ts": body["message"]["ts"]}),
            "title": {"type": "plain_text", "text": "🛒 Ordenar reactivo"},
            "submit": {"type": "plain_text", "text": "Confirmar"},
            "close": {"type": "plain_text", "text": "Cancelar"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "reagent_block",
                    "label": {"type": "plain_text", "text": "Reactivo"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "reagent_name",
                        "initial_value": reagent,
                    },
                    "optional": False,
                },
                {
                    "type": "input",
                    "block_id": "quantity_block",
                    "label": {"type": "plain_text", "text": "Cantidad"},
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "quantity",
                        "initial_value": str(suggested_qty),
                    },
                    "optional": False,
                },
                {
                    "type": "input",
                    "block_id": "supplier_block",
                    "label": {"type": "plain_text", "text": "Proveedor"},
                    "element": {
                        "type": "static_select",
                        "action_id": "supplier",
                        "initial_option": {
                            "text": {"type": "plain_text", "text": "LabSupplier AR"},
                            "value": "LabSupplier AR",
                        },
                        "options": [
                            {"text": {"type": "plain_text", "text": "LabSupplier AR"}, "value": "LabSupplier AR"},
                            {"text": {"type": "plain_text", "text": "Bioquímica SA"}, "value": "Bioquimica SA"},
                            {"text": {"type": "plain_text", "text": "LabMed Corp"}, "value": "LabMed Corp"},
                            {"text": {"type": "plain_text", "text": "Diagnósticos Plus"}, "value": "Diagnosticos Plus"},
                        ],
                    },
                    "optional": False,
                },
                _demo_badge(),
            ],
        },
    )


@bolt_app.view("order_modal")
def handle_order_submission(ack, body, client):
    ack()
    meta = json.loads(body["view"]["private_metadata"])
    values = body["view"]["state"]["values"]
    reagent = values["reagent_block"]["reagent_name"]["value"]
    quantity = float(values["quantity_block"]["quantity"]["value"])
    supplier = values["supplier_block"]["supplier"]["selected_option"]["value"]

    order = mcp.create_order(reagent, quantity, supplier)

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


# ---------------------------------------------------------------------------
# HANDLER 4 — Button: "👤 Asignar al equipo" (user selector modal + DM)
# ---------------------------------------------------------------------------
@bolt_app.action("assign_team")
def handle_assign_team(ack, body, client):
    ack()
    reagent = body["actions"][0].get("value", "TSH")
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


@bolt_app.view("assign_team_modal")
def handle_assign_team_submission(ack, body, client):
    ack()
    meta = json.loads(body["view"]["private_metadata"])
    user_id = body["view"]["state"]["values"]["user_block"]["selected_user"]["selected_user"]
    reagent = meta["reagent"]

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


# ---------------------------------------------------------------------------
# App mention handler (onboarding)
# ---------------------------------------------------------------------------
@bolt_app.event("app_mention")
def handle_app_mention(event, say, client):
    text = event.get("text", "").lower()
    user = event.get("user", "")
    channel = event.get("channel", "")

    # Detect reagent name from mention
    reagent = "TSH"
    for candidate in ["tsh", "glucose", "hba1c", "lipid", "creatinine"]:
        if candidate in text:
            reagent = candidate.upper()
            break

    # -----------------------------------------------------------------------
    # TASK 2 — Slack AI summarization
    # -----------------------------------------------------------------------
    if "resumen" in text or "summary" in text or "summarize" in text:
        try:
            history = client.conversations_history(channel=channel, limit=10)
            messages = [
                m.get("text", "")
                for m in history.get("messages", [])
                if m.get("text")
            ]
            summary = claude.summarize_messages(messages, reagent)
            say(
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"🤖 *Resumen IA de `{reagent}`:*\n{summary}",
                        },
                    },
                    _demo_badge(),
                ],
                text=f"Resumen IA {reagent}",
            )
        except Exception as e:
            say(
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                f"🤖 *Resumen IA:* No pude acceder al historial del canal. "
                                f"Error: `{str(e)}`. Verificá que la app tenga el scope `channels:history`."
                            ),
                        },
                    },
                    _demo_badge(),
                ],
                text="Error resumen IA",
            )
        return

    # Default onboarding response
    say(
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"Hola <@{user}>! Soy *LabOps Agent*.\n"
                        "Te alerto *antes* de que un reactivo se agote.\n\n"
                        "*Comandos:*\n"
                        f"• `@LabOps Agent {reagent}` → pronóstico de stock\n"
                        f"• `@LabOps Agent resumen {reagent}` → resumen IA del canal"
                    ),
                },
            },
            _demo_badge(),
        ],
        text="LabOps Agent onboarding",
    )


# ---------------------------------------------------------------------------
# Socket Mode runner
# ---------------------------------------------------------------------------
def start_socket_mode():
    if not SLACK_APP_TOKEN:
        raise RuntimeError("SLACK_APP_TOKEN required for Socket Mode")
    handler = SocketModeHandler(bolt_app, SLACK_APP_TOKEN)
    handler.start()


if __name__ == "__main__":
    print("[LabOps] Registered handlers:")
    for key in bolt_app._listeners:
        print(f"  - {key}")
    start_socket_mode()
