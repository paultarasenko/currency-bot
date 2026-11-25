import unittest
from decimal import Decimal

from bot.parsing import MAX_AMOUNT, Query, parse, parse_callback_amount, validate_amount

D = Decimal


class ParseTests(unittest.TestCase):
    def test_valid_queries(self):
        cases = {
            "100 usd byn": Query(D(100), "USD", "BYN"),
            "100 USD to RUB": Query(D(100), "USD", "RUB"),
            "250 eur в rub": Query(D(250), "EUR", "RUB"),
            "100 usd -> byn": Query(D(100), "USD", "BYN"),
            "100usd byn": Query(D(100), "USD", "BYN"),
            "1 500 pln": Query(D(1500), "PLN", None),
            "1 500,50 pln": Query(D("1500.5"), "PLN", None),
            "3,5 eur": Query(D("3.5"), "EUR", None),
            "5k eur в rub": Query(D(5000), "EUR", "RUB"),
            "5к евро в рубли": Query(D(5000), "EUR", "RUB"),
            "$50": Query(D(50), "USD", None),
            "50€ в $": Query(D(50), "EUR", "USD"),
            "100 долларов в рубли": Query(D(100), "USD", "RUB"),
            "100 белорусских рублей в евро": Query(D(100), "BYN", "EUR"),
            "100 бел. руб. в доллары": Query(D(100), "BYN", "USD"),
            "250": Query(D(250), None, None),
            "usd byn": Query(None, "USD", "BYN"),
            "  100  USD  ": Query(D(100), "USD", None),
            "5kzt eur": Query(D(5), "KZT", "EUR"),
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(parse(text), expected)

    def test_not_a_query(self):
        for text in [
            "", "привет", "hello world", "usd", "100 usd byn eur", "100 usd 50", "1.5.3 usd",
            "100 привет", "1e999", "x" * 101, "/start", "100 ab", "100 abcd",
        ]:
            with self.subTest(text=text):
                self.assertIsNone(parse(text))

    def test_amount_precision_is_bounded_for_callback_data(self):
        query = parse("0." + "1" * 50 + " usd byn")
        self.assertEqual(query.amount, D("0.111111"))

    def test_huge_amount_does_not_crash(self):
        query = parse("9" * 60 + " usd")
        self.assertGreater(query.amount, MAX_AMOUNT)
        self.assertIsNotNone(validate_amount(query.amount))


class ValidateTests(unittest.TestCase):
    def test_validate_amount(self):
        self.assertIsNone(validate_amount(D(1)))
        self.assertIsNone(validate_amount(MAX_AMOUNT))
        self.assertIsNotNone(validate_amount(D(0)))
        self.assertIsNotNone(validate_amount(D(-5)))
        self.assertIsNotNone(validate_amount(MAX_AMOUNT + 1))

    def test_zero_after_rounding_is_rejected(self):
        self.assertIsNotNone(validate_amount(parse("0.0000001 usd").amount))

    def test_callback_amount(self):
        self.assertEqual(parse_callback_amount("100"), D(100))
        for bad in ["abc", "", "NaN", "Infinity", "-1", "0", "1e999999999999"]:
            with self.subTest(value=bad):
                self.assertIsNone(parse_callback_amount(bad))


if __name__ == "__main__":
    unittest.main()
