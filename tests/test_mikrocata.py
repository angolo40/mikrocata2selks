"""Tests for the alert logic. Router and Telegram libraries are stubbed, so these run anywhere."""
import importlib.util
import os
import sys
import types
import unittest
from unittest import mock

for name in ("pyinotify", "ujson", "librouteros", "librouteros.query", "requests"):
    sys.modules.setdefault(name, mock.MagicMock())
sys.modules["pyinotify"].ProcessEvent = object

SPEC = importlib.util.spec_from_file_location("mikrocata", os.path.join(os.path.dirname(__file__), "..", "mikrocata.py"))
mk = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mk)
mk.WHITELIST_IPS = ("192.168.0.0/16", "172.16.0.0/12", "10.0.0.0/8", "fe80:")


def alert(src, sport, dst, dport):
    return {"src_ip": src, "src_port": sport, "dest_ip": dst, "dest_port": dport, "proto": "TCP"}


class PickTarget(unittest.TestCase):
    def test_inbound_blocks_the_remote_source(self):
        self.assertEqual(mk.pick_target(alert("203.0.113.9", 4444, "192.168.1.5", 22)), ("203.0.113.9", 22, False))

    def test_issue_53_outbound_keeps_the_service_port(self):
        e = alert("172.16.0.179", 56924, "172.235.15.5", 22)
        self.assertEqual(mk.pick_target(e), ("172.235.15.5", 22, True))

    def test_both_internal_is_skipped(self):
        self.assertIsNone(mk.pick_target(alert("192.168.1.5", 1000, "10.0.0.2", 445)))


class FormatAlert(unittest.TestCase):
    def test_issue_53_from_and_to_match_eve_json(self):
        e = alert("172.16.0.179", 56924, "172.235.15.5", 22)
        testo = mk.format_alert(e, "172.235.15.5", True, "rule")
        self.assertIn("From: 172.16.0.179:56924", testo)
        self.assertIn("To: 172.235.15.5:22", testo)
        self.assertIn("outbound", testo)


class Telegram(unittest.TestCase):
    def test_proxy_is_off_by_default_and_text_is_not_in_the_url(self):
        self.assertFalse(mk.TELEGRAM_PROXY_ENABLED)
        mk.enable_telegram = True
        with mock.patch.object(mk, "requests") as req:
            req.post.return_value = mock.Mock(status_code=200, json=lambda: {})
            self.assertTrue(mk.sendTelegram("a & b <c>"))
        url = req.post.call_args.args[0]
        self.assertNotIn("a & b", url)
        self.assertEqual(req.post.call_args.kwargs["proxies"], None)


if __name__ == "__main__":
    unittest.main()
