"""Exercise the real database module with fake settings and temporary SQLite."""
from contextlib import closing, contextmanager
import importlib.util
from pathlib import Path
import sqlite3
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="flightbizubot-test-")
        self.addCleanup(temporary.cleanup)
        self.settings = SimpleNamespace(
            DB_PATH=str(Path(temporary.name) / "test.sqlite3"),
            TELEGRAM_CHAT_ID="",
            DISCOUNT_THRESHOLD_PERCENT=20,
        )
        config = ModuleType("config")
        config.settings = self.settings
        spec = importlib.util.spec_from_file_location("flightbizubot_test_database", ROOT / "database.py")
        self.db = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"config": config}):
            spec.loader.exec_module(self.db)

        # Production's SQLite context manager commits but does not close.
        # Close every real connection used in these tests explicitly.
        @contextmanager
        def connection():
            with closing(sqlite3.connect(self.settings.DB_PATH)) as conn:
                conn.row_factory = sqlite3.Row
                with conn:
                    yield conn

        self.db.get_connection = connection
        self.db.init_db()

    def test_initialization_is_repeatable_and_empty(self):
        self.db.init_db()
        self.assertEqual(self.db.count_active_subscribers(), 0)
        self.assertEqual(self.db.get_recent_promotions(), [])
        self.assertIsNone(self.db.get_lowest_price("CWB", "GIG"))

    def test_subscriber_can_pause_and_resubscribe_without_duplicates(self):
        self.db.register_or_update_subscriber("test-user", "fixture", "Test")
        self.assertTrue(self.db.is_subscriber_active("test-user"))
        self.db.set_subscriber_status("test-user", False)
        self.assertEqual(self.db.get_active_subscribers(), [])
        self.db.register_or_update_subscriber("test-user")
        self.assertEqual(self.db.get_active_subscribers(), ["test-user"])
        self.assertEqual(self.db.count_active_subscribers(), 1)

    def test_promotion_link_is_deduplicated(self):
        self.assertTrue(self.db.save_promotion("fixture", "Offer", "https://example.invalid/promo"))
        self.assertFalse(self.db.save_promotion("fixture", "Duplicate", "https://example.invalid/promo"))
        self.assertEqual(len(self.db.get_recent_promotions()), 1)

    def test_flight_history_keeps_route_and_round_trip_details(self):
        for price in (900, 600):
            self.db.save_flight_price("CWB", "GIG", "2030-01-10", price, "Fixture", 0,
                                      return_date="2030-01-15", is_round_trip=True)
        self.assertIsNone(self.db.get_historical_average("CWB", "GIG"))
        self.db.save_flight_price("CWB", "GIG", "2030-01-10", 750, "Fixture", 0)
        self.db.save_flight_price("CWB", "POA", "2030-01-10", 1, "Fixture", 0)
        self.assertEqual(self.db.get_historical_average("CWB", "GIG"), 750)
        lowest = self.db.get_lowest_price("CWB", "GIG")
        self.assertEqual(lowest["price"], 600)
        self.assertEqual(lowest["return_date"], "2030-01-15")
        self.assertEqual(lowest["is_round_trip"], 1)

    def test_alert_suppresses_same_price_but_allows_larger_drop(self):
        args = ("CWB", "GIG", "2030-01-10")
        self.assertTrue(self.db.should_send_flight_alert(*args, 500, 600))
        self.db.mark_alert_sent("flight", "flight:CWB:GIG:2030-01-10", 500)
        self.assertFalse(self.db.should_send_flight_alert(*args, 500, 600))
        self.assertTrue(self.db.should_send_flight_alert(*args, 470, 600))
        self.assertFalse(self.db.should_send_flight_alert(*args, 700, 600))


if __name__ == "__main__":
    unittest.main()
