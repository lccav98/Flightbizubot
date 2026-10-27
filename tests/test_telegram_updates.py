"""Regression tests using only fake transports: no Telegram or feed requests."""
import importlib.util
import asyncio
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, patch

ROOT = Path(__file__).resolve().parents[1]


class TelegramUpdatesTests(unittest.TestCase):
    def setUp(self):
        dependencies = {}
        for name in ("config", "curl_cffi", "database", "flight_engine", "car_engine",
                     "promo_engine", "feedparser", "rich", "rich.console"):
            dependencies[name] = ModuleType(name)
        dependencies["config"].settings = SimpleNamespace(
            TELEGRAM_BOT_TOKEN="fixture", TELEGRAM_CHAT_ID="")
        dependencies["flight_engine"].FlightOffer = object
        dependencies["car_engine"].CarRentalDeal = object
        dependencies["promo_engine"].PromoItem = object
        dependencies["rich.console"].Console = Mock()
        dependencies["database"].set_subscriber_status = Mock()
        dependencies["database"].save_promotion = Mock(return_value=True)
        dependencies["database"].register_or_update_subscriber = Mock()
        dependencies["curl_cffi"].requests = SimpleNamespace(Session=MagicMock(), AsyncSession=MagicMock())
        dependencies["feedparser"].parse = Mock(return_value=SimpleNamespace(entries=[]))
        self.dependencies = dependencies
        patcher = patch.dict(sys.modules, dependencies)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.notifier_module = self.load("telegram_notifier")
        self.notifier = self.notifier_module.TelegramNotifier()
        self.client = dependencies["curl_cffi"].requests.Session.return_value.__enter__.return_value

    def load(self, filename):
        name = "test_isolated_" + filename
        spec = importlib.util.spec_from_file_location(name, ROOT / (filename + ".py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        self.addCleanup(sys.modules.pop, name, None)
        spec.loader.exec_module(module)
        return module

    @staticmethod
    def response(status, description=""):
        return SimpleNamespace(status_code=status, json=lambda: {"description": description})

    def test_malformed_html_retries_plain_text_without_unsubscribing(self):
        self.client.post.side_effect = [
            self.response(400, "Bad Request: can't parse entities"), self.response(200)]
        self.assertTrue(self.notifier.send_to_chat("fixture-chat", "<b>Offer & test</b>"))
        payload = self.client.post.call_args.kwargs["json"]
        self.assertNotIn("parse_mode", payload)
        self.assertEqual(payload["text"], "Offer & test")
        self.dependencies["database"].set_subscriber_status.assert_not_called()

    def test_other_bad_request_does_not_disable_subscriber(self):
        self.client.post.return_value = self.response(400, "Bad Request: message text is empty")
        self.assertFalse(self.notifier.send_to_chat("fixture-chat", ""))
        self.dependencies["database"].set_subscriber_status.assert_not_called()

    def test_blocked_chat_is_disabled(self):
        self.client.post.return_value = self.response(403)
        self.assertFalse(self.notifier.send_to_chat("fixture-chat", "test"))
        self.dependencies["database"].set_subscriber_status.assert_called_once_with("fixture-chat", False)

    def test_invalid_chat_is_disabled(self):
        self.client.post.return_value = self.response(400, "Bad Request: chat not found")
        self.assertFalse(self.notifier.send_to_chat("fixture-chat", "test"))
        self.dependencies["database"].set_subscriber_status.assert_called_once_with("fixture-chat", False)

    def test_long_report_is_split_without_losing_text(self):
        self.client.post.return_value = self.response(200)
        content = "x" * 9000
        self.assertTrue(self.notifier.send_to_chat("fixture-chat", "<b>" + content + "</b>"))
        payloads = [call.kwargs["json"] for call in self.client.post.call_args_list]
        self.assertEqual("".join(p["text"] for p in payloads), content)
        self.assertTrue(all(len(p["text"]) <= 4000 for p in payloads))

    def test_news_escapes_external_html(self):
        self.notifier.broadcast = Mock(return_value=1)
        promo = SimpleNamespace(source="A&B", title="<offer>", snippet="x < y",
                                link="https://example.invalid/?a=1&b=2")
        self.assertTrue(self.notifier.notify_promo_news(promo))
        message = self.notifier.broadcast.call_args.args[0]
        self.assertIn("&lt;offer&gt;", message)
        self.assertIn("A&amp;B", message)

    def test_network_error_does_not_log_token_or_disable_chat(self):
        self.client.post.side_effect = RuntimeError("https://api.telegram.org/botSECRET/sendMessage")
        self.assertFalse(self.notifier.send_to_chat("fixture-chat", "test"))
        logs = str(self.notifier_module.console.log.call_args_list)
        self.assertNotIn("SECRET", logs)
        self.dependencies["database"].set_subscriber_status.assert_not_called()

    def test_async_polling_dispatches_command_and_keeps_tls_verification(self):
        async def run():
            session = self.dependencies["curl_cffi"].requests.AsyncSession
            client = session.return_value.__aenter__.return_value
            response = SimpleNamespace(status_code=200, json=lambda: {"result": [{
                "update_id": 3, "message": {"chat": {"id": "fixture-chat"},
                                             "text": "/status", "from": {}}
            }]})
            client.get = AsyncMock(return_value=response)
            callback = AsyncMock(side_effect=asyncio.CancelledError())
            with self.assertRaises(asyncio.CancelledError):
                await asyncio.wait_for(self.notifier.poll_telegram_commands(callback), timeout=2)
            session.assert_called_once_with(timeout=30.0, verify=True)
            callback.assert_awaited_once_with(self.notifier, "/status", "fixture-chat", {})
            self.assertEqual(self.notifier.last_update_id, 3)
        asyncio.run(run())

    def test_feed_download_has_timeout_and_parser_receives_bytes(self):
        promo = self.load("promo_engine")
        promo.FEEDS = [("fixture", "https://example.invalid/feed")]
        response = Mock(content=b"<rss/>")
        self.client.get.return_value = response
        self.assertEqual(promo.scan_promotions(), [])
        self.dependencies["curl_cffi"].requests.Session.assert_called_with(
            timeout=15.0, allow_redirects=True, verify=True)
        self.dependencies["feedparser"].parse.assert_called_once_with(b"<rss/>")

    def test_feed_timeout_continues_to_next_feed(self):
        promo = self.load("promo_engine")
        promo.FEEDS = [("first", "https://example.invalid/1"), ("second", "https://example.invalid/2")]
        self.client.get.side_effect = [TimeoutError(), Mock(content=b"<rss/>")]
        with self.assertLogs(promo.__name__, level="WARNING"):
            self.assertEqual(promo.scan_promotions(), [])
        self.assertEqual(self.client.get.call_count, 2)


if __name__ == "__main__":
    unittest.main()
