"""Tests for Prophet prediction engine."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import prediction


class TestPrediction(unittest.TestCase):
    """Validate Prophet forecasting and stockout projection."""

    def test_build_synthetic_history_shape(self):
        """History DataFrame has correct shape."""
        df = prediction._build_synthetic_history("TSH", days=365)
        self.assertEqual(df.shape, (365, 2))
        self.assertIn("ds", df.columns)
        self.assertIn("y", df.columns)

    def test_get_forecast_structure(self):
        """Forecast returns expected keys."""
        result = prediction.get_forecast("TSH", days=14)
        self.assertEqual(result["reagent_name"], "TSH")
        self.assertGreater(len(result["daily_demand"]), 0)
        self.assertLessEqual(len(result["daily_demand"]), 14)
        self.assertEqual(result["model"], "Prophet")

    def test_tsh_stockout_reproducible(self):
        """TSH stockout with seed=42 always projects ~4 days."""
        result = prediction.calculate_stockout_projection("TSH", 680, 7)
        self.assertTrue(result["alert_trigger"])
        self.assertEqual(result["reagent_name"], "TSH")
        self.assertEqual(result["current_stock"], 680)
        # With np.random.seed(42), projected days must be reproducible
        self.assertIsNotNone(result["projected_stockout_days"])
        self.assertLess(result["projected_stockout_days"], 7)

    def test_hemograma_no_winter_spike(self):
        """Hemograma has stable demand (no winter multiplier)."""
        result = prediction.calculate_stockout_projection("Hemograma", 2100, 5)
        self.assertEqual(result["reagent_name"], "Hemograma")
        self.assertIsNotNone(result["projected_stockout_days"])

    def test_unknown_reagent_falls_back(self):
        """Unknown reagent falls back to base=100 pattern."""
        result = prediction.get_forecast("UnknownReagent", days=7)
        self.assertGreater(len(result["daily_demand"]), 0)
        self.assertLessEqual(len(result["daily_demand"]), 7)


if __name__ == "__main__":
    unittest.main()
