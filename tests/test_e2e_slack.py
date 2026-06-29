"""
tests/e2e_slack.py — End-to-end Slack handler validation WITHOUT Socket Mode.

Simulates Slack events and asserts the full handler pipeline:
  - database lookup
  - Prophet forecast
  - Claude explanation (if key present)
  - Block Kit response structure
  - DEMO badge presence

Usage:
    python -m pytest tests/e2e_slack.py -v

Exit 0 = all assertions pass.
Exit 1 = any assertion fails.
"""
import os
import sys
import unittest
from unittest.mock import MagicMock

# Ensure backend imports resolve when running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import slack_client as sc
from slack_client import (
    handle_app_mention,
    handle_view_forecast,
    handle_order_reagent,
    _demo_badge,
)


class FakeAck:
    def __call__(self):
        pass


class E2ESlackHandlers(unittest.TestCase):
    """E2E tests that exercise real backend logic through Slack handlers."""

    def _fake_say(self):
        """Capture say() calls for assertion."""
        calls = []

        def capture(**kwargs):
            calls.append(kwargs)

        return capture, calls

    def test_demo_badge_present(self):
        """R06 — every message must carry a visible DEMO badge."""
        badge = _demo_badge()
        self.assertEqual(badge["type"], "context")
        text = badge["elements"][0]["text"]
        self.assertIn("DEMO", text)
        self.assertIn("sintéticos", text)

    def test_app_mention_forecast(self):
        """E2E: @mention TSH returns agent response with DEMO badge."""
        say, calls = self._fake_say()
        event = {
            "text": "<@U123> TSH",
            "user": "U456",
            "channel": "C789",
        }
        client = MagicMock()

        handle_app_mention(event=event, say=say, client=client)

        self.assertTrue(len(calls) >= 1, "say() was never called")
        blocks = calls[0].get("blocks", [])
        texts = [b.get("text", {}).get("text", "") for b in blocks if b.get("type") == "section"]
        full_text = " ".join(texts)
        self.assertIn("TSH", full_text)

        # R06 — DEMO badge must be present
        badge_types = [b.get("type") for b in blocks]
        self.assertIn("context", badge_types)

    def test_app_mention_summary(self):
        """E2E: @mention 'resumen TSH' triggers agent router (or graceful fallback)."""
        say, calls = self._fake_say()
        event = {
            "text": "<@U123> resumen TSH",
            "user": "U456",
            "channel": "C789",
        }
        client = MagicMock()
        client.conversations_history.return_value = {"messages": [{"text": "Test message"}]}

        handle_app_mention(event=event, say=say, client=client)

        self.assertTrue(len(calls) >= 1)
        full_text = str(calls[0])
        self.assertIn("LabOps Agent", full_text)

    def test_view_forecast_button(self):
        """E2E: 'Ver proyección' button returns forecast Block Kit with fields."""
        ack = FakeAck()
        body = {
            "actions": [{"value": "TSH"}],
            "channel": {"id": "C789"},
            "message": {"ts": "1234567890.123456"},
        }
        client = MagicMock()

        handle_view_forecast(ack=ack, body=body, client=client)

        # chat_postMessage is called for forecast + history + search results
        self.assertTrue(client.chat_postMessage.called, "chat_postMessage was never called")
        call_kwargs_list = [c[1] for c in client.chat_postMessage.call_args_list]

        # Find the forecast call (has header block)
        forecast_call = None
        for kwargs in call_kwargs_list:
            blocks = kwargs.get("blocks", [])
            if any(b.get("type") == "header" for b in blocks):
                forecast_call = kwargs
                break

        self.assertIsNotNone(forecast_call, "No chat_postMessage call contained a header block")
        blocks = forecast_call["blocks"]

        header_texts = [b.get("text", {}).get("text", "") for b in blocks if b.get("type") == "header"]
        self.assertTrue(any("TSH" in t for t in header_texts), "Header should contain reagent name")

        # Should contain fields section with 7 days
        fields_blocks = [b for b in blocks if b.get("type") == "section" and "fields" in b]
        self.assertTrue(len(fields_blocks) > 0, "Forecast should include fields block")

        # DEMO badge present
        badge_types = [b.get("type") for b in blocks]
        self.assertIn("context", badge_types)

    def test_order_reagent_button(self):
        """E2E: 'Ordenar reactivo' button opens a modal with supplier dropdown."""
        ack = FakeAck()
        body = {
            "actions": [{"value": "TSH"}],
            "trigger_id": "T123",
            "channel": {"id": "C789"},
            "message": {"ts": "1234567890.123456"},
        }
        client = MagicMock()

        handle_order_reagent(ack=ack, body=body, client=client)

        client.views_open.assert_called_once()
        call_args = client.views_open.call_args[1]
        view = call_args["view"]
        self.assertEqual(view["type"], "modal")
        self.assertIn("Ordenar", view["title"]["text"])
        # private_metadata should contain reagent, channel, thread_ts
        meta = view.get("private_metadata", "")
        self.assertIn("TSH", meta)
        self.assertIn("C789", meta)


if __name__ == "__main__":
    unittest.main(verbosity=2)
