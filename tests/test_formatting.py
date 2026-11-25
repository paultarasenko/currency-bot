import unittest
from datetime import datetime, timezone
from decimal import Decimal

from bot.formatting import NBSP, fmt_money, fmt_plain, fmt_rate, fmt_time

D = Decimal


class FormattingTests(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(fmt_plain(D(100)), "100")
        self.assertEqual(fmt_plain(D(1500)), f"1{NBSP}500")
        self.assertEqual(fmt_plain(D("2.5")), "2,5")
        self.assertEqual(fmt_plain(D("1000000")), f"1{NBSP}000{NBSP}000")
        self.assertEqual(fmt_plain(D("0.000001")), "0,000001")

    def test_money(self):
        self.assertEqual(fmt_money(D("1234.567"), "USD"), f"1{NBSP}234,57")
        self.assertEqual(fmt_money(D("15000.4"), "JPY"), f"15{NBSP}000")
        self.assertEqual(fmt_money(D("0.00512"), "USD"), "0,0051")
        self.assertEqual(fmt_money(D(0), "USD"), "0,00")

    def test_rate(self):
        self.assertEqual(fmt_rate(D("150.1234")), "150,12")
        self.assertEqual(fmt_rate(D("2.91344")), "2,9134")
        self.assertEqual(fmt_rate(D("0.0066667")), "0,006667")

    def test_time(self):
        moment = datetime(2026, 11, 10, 2, 0, tzinfo=timezone.utc)
        self.assertEqual(fmt_time(moment), "10.11.2026, 02:00 UTC")


if __name__ == "__main__":
    unittest.main()
