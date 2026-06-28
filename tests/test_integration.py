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
        body = {
            "actions": [{"value": "TSH"}],
            "channel": {"id": "C123"},
            "message": {"ts": "1234567890.123456"},
        }

        handle_view_forecast(ack, body, client)

        # Should post forecast table
        calls = client.chat_postMessage.call_args_list
        self.assertTrue(any("Pronóstico" in str(c) for c in calls))
        # Should post channel history summary (either with alerts or empty state)
        self.assertTrue(any("alerta" in str(c).lower() for c in calls))


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
    """App mention handler — onboarding and summarization"""

    @patch("slack_client.claude.summarize_messages")
    def test_summary_mode_calls_claude(self, mock_summarize):
        mock_summarize.return_value = "TSH has been stable."

        event = {
            "text": "@labops resumen TSH",
            "user": "U123",
            "channel": "C123",
        }
        say = MagicMock()
        client = MagicMock()
        client.conversations_history.return_value = {"messages": [{"text": "old alert"}]}

        handle_app_mention(event, say, client)

        mock_summarize.assert_called_once()
        say.assert_called_once()
        blocks = say.call_args[1]["blocks"]
        self.assertTrue(any("Resumen IA" in str(b) for b in blocks))

    def test_default_onboarding(self):
        event = {
            "text": "@labops hello",
            "user": "U123",
            "channel": "C123",
        }
        say = MagicMock()
        client = MagicMock()

        handle_app_mention(event, say, client)

        say.assert_called_once()
        text = str(say.call_args)
        self.assertIn("LabOps Agent", text)


if __name__ == "__main__":
    unittest.main()
