"""Integration tests for Bolt handlers.

Uses unittest.mock to verify handler flows without real Slack/DB/Prophet.
"""
import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from slack_client import (
    handle_view_forecast,
    handle_order_reagent,
    handle_order_submission,
    handle_assign_team,
    handle_assign_team_submission,
    handle_app_mention,
)


class FakeAck:
    def __call__(self):
        pass


class TestViewForecast(unittest.TestCase):
    """Button: 📊 Ver proyección"""

    @patch("slack_client.prediction.get_forecast")
    @patch("slack_client.db.get_lab_config")
    @patch.dict(os.environ, {"LABOPS_ALERTS_CHANNEL_ID": "C456"})
    def test_handler_posts_forecast_and_history(self, mock_get_lab_config, mock_get_forecast):
        mock_get_forecast.return_value = {
            "daily_demand": [
                {"date": "2026-06-27", "predicted_qty": 200, "lower_bound": 180, "upper_bound": 220},
            ]
        }
        mock_get_lab_config.return_value = None

        ack = FakeAck()
        client = MagicMock()
        client.conversations_history.return_value = {
            "messages": [
                {"text": "TSH alert", "ts": "123.456", "bot_id": "B1"},
            ]
        }
        client.search_messages.return_value = {
            "messages": {
                "matches": [
                    {"text": "TSH stock low", "ts": "123.456", "channel": {"name": "labops-alerts"}},
                ]
            }
        }
        body = {
            "actions": [{"value": "TSH"}],
            "channel": {"id": "C123"},
            "message": {"ts": "1234567890.123456"},
        }

        handle_view_forecast(ack, body, client)

        # Should post forecast with NATIVE Block Kit fields (no ASCII tables)
        calls = client.chat_postMessage.call_args_list
        self.assertTrue(any("Pronóstico" in str(c) for c in calls))
        forecast_call = [c for c in calls if "Pronóstico" in str(c)][0]
        blocks = forecast_call[1]["blocks"]
        # Native fields present
        self.assertTrue(any(b.get("type") == "section" and "fields" in b for b in blocks))
        # No raw ASCII code-block table in the forecast section text
        self.assertFalse(any("```" in str(b) for b in blocks))
        # With no public BACKEND_URL, the chart image is omitted (not broken)
        self.assertFalse(any(b.get("type") == "image" for b in blocks))
        # Should post channel history summary (either with alerts or empty state)
        self.assertTrue(any("alerta" in str(c).lower() for c in calls))
        # Should post workspace search results
        self.assertTrue(any("Búsqueda" in str(c) for c in calls))
        # Should call search.messages
        client.search_messages.assert_called_once()

    @patch("slack_client.prediction.get_forecast")
    @patch("slack_client.db.get_lab_config")
    @patch.dict(os.environ, {"BACKEND_URL": "https://labops.example.com"})
    def test_chart_image_included_with_public_https_backend(self, mock_get_lab_config, mock_get_forecast):
        mock_get_forecast.return_value = {
            "daily_demand": [
                {"date": "2026-06-27", "predicted_qty": 200, "lower_bound": 180, "upper_bound": 220},
            ]
        }
        mock_get_lab_config.return_value = None

        ack = FakeAck()
        client = MagicMock()
        client.conversations_history.return_value = {"messages": []}
        client.search_messages.return_value = {"messages": {"matches": []}}
        body = {
            "actions": [{"value": "TSH"}],
            "channel": {"id": "C123"},
            "message": {"ts": "1234567890.123456"},
        }

        handle_view_forecast(ack, body, client)

        calls = client.chat_postMessage.call_args_list
        forecast_call = [c for c in calls if "Pronóstico" in str(c)][0]
        blocks = forecast_call[1]["blocks"]
        image_blocks = [b for b in blocks if b.get("type") == "image"]
        self.assertEqual(len(image_blocks), 1)
        self.assertIn("https://labops.example.com/chart/forecast/TSH", image_blocks[0]["image_url"])


class TestOrderReagent(unittest.TestCase):
    """Button: 🛒 Ordenar reactivo (opens modal)"""

    @patch("slack_client.db.get_inventory")
    def test_opens_modal_with_prefilled_values(self, mock_get_inventory):
        mock_get_inventory.return_value = [{"current_stock": 680}]

        ack = FakeAck()
        client = MagicMock()
        body = {
            "actions": [{"value": "TSH"}],
            "trigger_id": "T123",
            "channel": {"id": "C123"},
            "message": {"ts": "1234567890.123456"},
        }

        handle_order_reagent(ack, body, client)

        client.views_open.assert_called_once()
        view = client.views_open.call_args[1]["view"]
        self.assertEqual(view["callback_id"], "order_modal")
        # Only input blocks have block_id in this template
        input_blocks = [b for b in view["blocks"] if b.get("block_id")]
        blocks = {b["block_id"]: b for b in input_blocks}
        # Verify reagent is pre-filled
        self.assertEqual(blocks["reagent_block"]["element"]["initial_value"], "TSH")
        # Verify quantity is suggested
        self.assertIn("340", blocks["quantity_block"]["element"]["initial_value"])


class TestOrderSubmission(unittest.TestCase):
    """Modal: confirm order"""

    @patch("slack_client.mcp.create_order")
    @patch("slack_client.db.get_lab_config")
    def test_creates_order_and_updates_canvas(self, mock_get_lab_config, mock_create_order):
        mock_create_order.return_value = {"id": 1, "status": "pending"}
        mock_get_lab_config.return_value = None

        ack = FakeAck()
        client = MagicMock()
        body = {
            "view": {
                "private_metadata": json.dumps({"reagent": "TSH", "channel": "C123", "thread_ts": "1234567890.123456"}),
                "state": {
                    "values": {
                        "reagent_block": {"reagent_name": {"value": "TSH"}},
                        "quantity_block": {"quantity": {"value": "500"}},
                        "supplier_block": {"supplier": {"selected_option": {"value": "LabSupplier AR"}}},
                    }
                },
            }
        }

        handle_order_submission(ack, body, client)

        mock_create_order.assert_called_once_with("TSH", 500.0, "LabSupplier AR")
        # Should confirm in thread
        calls = client.chat_postMessage.call_args_list
        self.assertTrue(any("Orden creada" in str(c) for c in calls))


class TestAssignTeam(unittest.TestCase):
    """Button: 👤 Asignar al equipo (opens user selector modal)"""

    def test_opens_assign_modal(self):
        ack = FakeAck()
        client = MagicMock()
        body = {
            "actions": [{"value": "TSH"}],
            "trigger_id": "T456",
            "channel": {"id": "C123"},
            "message": {"ts": "1234567890.123456"},
        }

        handle_assign_team(ack, body, client)

        client.views_open.assert_called_once()
        view = client.views_open.call_args[1]["view"]
        self.assertEqual(view["callback_id"], "assign_team_modal")


class TestAssignTeamSubmission(unittest.TestCase):
    """Modal: assign team member"""

    def test_sends_dm_and_confirms_in_thread(self):
        ack = FakeAck()
        client = MagicMock()
        body = {
            "view": {
                "private_metadata": json.dumps({"reagent": "TSH", "channel": "C123", "thread_ts": "1234567890.123456"}),
                "state": {
                    "values": {
                        "user_block": {"selected_user": {"selected_user": "U999"}},
                    }
                },
            }
        }

        handle_assign_team_submission(ack, body, client)

        # DM to assigned user
        dm_calls = [c for c in client.chat_postMessage.call_args_list if c[1].get("channel") == "U999"]
        self.assertEqual(len(dm_calls), 1)
        # Thread confirmation
        thread_calls = [c for c in client.chat_postMessage.call_args_list if c[1].get("channel") == "C123"]
        self.assertEqual(len(thread_calls), 1)


class TestAppMention(unittest.TestCase):
    """App mention handler — agent router with Claude tool-use"""

    @patch("slack_client.agent_router.run_agent")
    def test_agent_router_called_on_mention(self, mock_run_agent):
        mock_run_agent.return_value = "TSH stock: 680 units. Projected stockout in 4 days."

        event = {
            "text": "@labops cuánto stock hay de TSH?",
            "user": "U123",
            "channel": "C123",
        }
        say = MagicMock()
        client = MagicMock()

        handle_app_mention(event, say, client)

        mock_run_agent.assert_called_once()
        say.assert_called_once()
        text = str(say.call_args)
        self.assertIn("LabOps Agent", text)
        self.assertIn("680 units", text)

    @patch("slack_client.agent_router.run_agent")
    def test_agent_router_handles_resumen(self, mock_run_agent):
        mock_run_agent.return_value = "TSH ha estado estable las últimas semanas."

        event = {
            "text": "@labops resumen TSH",
            "user": "U123",
            "channel": "C123",
        }
        say = MagicMock()
        client = MagicMock()

        handle_app_mention(event, say, client)

        mock_run_agent.assert_called_once()
        say.assert_called_once()
        text = str(say.call_args)
        self.assertIn("LabOps Agent", text)


class TestSearchMessages(unittest.TestCase):
    """search.messages uses SLACK_USER_TOKEN when available"""

    @patch("slack_sdk.WebClient")
    @patch("slack_client.SLACK_USER_TOKEN", "xoxp-test-user-token")
    @patch.dict(os.environ, {"LABOPS_ALERTS_CHANNEL_ID": "C456"})
    def test_user_token_used_for_search(self, mock_webclient_cls):
        mock_user_client = MagicMock()
        mock_user_client.search_messages.return_value = {
            "messages": {
                "matches": [
                    {"text": "TSH low", "ts": "123.456", "channel": {"name": "labops-alerts"}},
                ]
            }
        }
        mock_webclient_cls.return_value = mock_user_client

        mock_get_forecast = MagicMock()
        mock_get_forecast.return_value = {
            "daily_demand": [
                {"date": "2026-06-27", "predicted_qty": 200, "lower_bound": 180, "upper_bound": 220},
            ]
        }

        with patch("slack_client.prediction.get_forecast", mock_get_forecast):
            with patch("slack_client.db.get_lab_config", return_value=None):
                ack = FakeAck()
                client = MagicMock()
                client.conversations_history.return_value = {"messages": []}
                body = {
                    "actions": [{"value": "TSH"}],
                    "channel": {"id": "C123"},
                    "message": {"ts": "1234567890.123456"},
                }
                handle_view_forecast(ack, body, client)

        # User client should have been created with the user token
        mock_webclient_cls.assert_called_once_with(token="xoxp-test-user-token")
        mock_user_client.search_messages.assert_called_once()


class TestDynamicSeverity(unittest.TestCase):
    """Severity must be derived, never the hardcoded 'CRÍTICO' header."""

    def test_severity_label_mapping(self):
        from slack_client import _severity_label
        self.assertEqual(_severity_label("critical"), "🔴 CRÍTICO")
        self.assertEqual(_severity_label("warning"), "🟡 ADVERTENCIA")
        self.assertEqual(_severity_label("anything_else"), "🟢 OK")

    def test_alert_template_renders_warning_not_critico(self):
        import blocks_loader as bl
        from slack_client import _severity_label

        blocks = bl.load_template(
            "alert",
            reagent_name="Hemograma",
            current_stock=500,
            projected_days=20,
            explanation="Demanda estable.",
            severity_label=_severity_label("warning"),
        )["blocks"]

        header = next(b for b in blocks if b.get("type") == "header")
        self.assertIn("ADVERTENCIA", header["text"]["text"])
        self.assertNotIn("CRÍTICO", header["text"]["text"])
        # No literal placeholder left unrendered anywhere
        self.assertNotIn("severity_label", str(blocks))
        self.assertNotIn("{{", str(blocks))


if __name__ == "__main__":
    unittest.main()
