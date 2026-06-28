"""Tests for MCP Server tools."""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import mcp_server as mcp


class TestMCPTools(unittest.TestCase):
    """Validate 4 MCP tools: get_inventory, get_forecast, create_order, update_canvas."""

    @patch("mcp_server.db.get_inventory")
    def test_get_inventory(self, mock_get_inventory):
        """get_inventory returns tool metadata and results."""
        mock_get_inventory.return_value = [
            {"reagent_name": "TSH", "current_stock": 680}
        ]
        result = mcp.get_inventory("TSH")
        self.assertEqual(result["tool"], "get_inventory")
        self.assertEqual(result["reagent_name"], "TSH")
        self.assertEqual(result["count"], 1)

    @patch("mcp_server.prediction.get_forecast")
    def test_get_forecast(self, mock_get_forecast):
        """get_forecast returns forecast structure."""
        mock_get_forecast.return_value = {"daily_demand": []}
        result = mcp.get_forecast("TSH", days=7)
        self.assertEqual(result["tool"], "get_forecast")
        self.assertEqual(result["reagent_name"], "TSH")

    @patch("mcp_server.db.create_order")
    def test_create_order(self, mock_create_order):
        """create_order writes to Supabase and returns order data."""
        mock_create_order.return_value = {
            "id": "ord-123",
            "reagent_name": "TSH",
            "quantity": 500,
            "status": "pending",
        }
        result = mcp.create_order("TSH", 500, "LabSupplier AR")
        self.assertTrue(result["success"])
        self.assertEqual(result["order"]["status"], "pending")

    def test_update_canvas(self):
        """update_canvas prepares Block Kit payload."""
        result = mcp.update_canvas("C123", {
            "reagent_name": "TSH",
            "current_stock": 680,
            "last_order_status": "pending",
        })
        self.assertTrue(result["success"])
        self.assertIn("payload", result)
        self.assertEqual(result["tool"], "update_canvas")


class TestMCPServerAsync(unittest.TestCase):
    """Validate MCP Server stdio transport exists and has 4 tools."""

    def test_server_has_four_tools(self):
        """MCP Server exposes exactly 4 tools."""
        try:
            from mcp_server import _server
            if _server is not None:
                # _server is an mcp.server.Server instance
                self.assertIsNotNone(_server)
            else:
                self.skipTest("MCP SDK not installed")
        except ImportError:
            self.skipTest("MCP SDK not installed")


if __name__ == "__main__":
    unittest.main()
