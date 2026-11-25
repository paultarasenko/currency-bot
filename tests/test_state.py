import unittest
from decimal import Decimal

from bot import state

D = Decimal


class PairTests(unittest.TestCase):
    def test_defaults(self):
        self.assertEqual(state.get_pair({}), state.DEFAULT_PAIR)
        self.assertEqual(state.get_amount({}), state.DEFAULT_AMOUNT)

    def test_corrupted_data_falls_back_to_defaults(self):
        ud = {"pair": ("USD", "USD"), "amount": "100", "favorites": "x", "history": [1, 2], "base": 5}
        self.assertEqual(state.get_pair(ud), state.DEFAULT_PAIR)
        self.assertEqual(state.get_amount(ud), state.DEFAULT_AMOUNT)
        self.assertEqual(state.get_favorites(ud), [])
        self.assertEqual(state.get_history(ud), [])
        self.assertEqual(state.get_base(ud), state.DEFAULT_PAIR[0])

    def test_selecting_the_other_side_swaps(self):
        ud = {}
        state.set_pair(ud, "USD", "EUR")
        state.set_from(ud, "EUR")
        self.assertEqual(state.get_pair(ud), ("EUR", "USD"))
        state.set_to(ud, "EUR")
        self.assertEqual(state.get_pair(ud), ("USD", "EUR"))

    def test_regular_selection(self):
        ud = {}
        state.set_pair(ud, "USD", "EUR")
        state.set_from(ud, "PLN")
        state.set_to(ud, "RUB")
        self.assertEqual(state.get_pair(ud), ("PLN", "RUB"))

    def test_same_currency_rejected(self):
        with self.assertRaises(ValueError):
            state.set_pair({}, "USD", "USD")

    def test_swap(self):
        ud = {}
        state.set_pair(ud, "USD", "EUR")
        state.swap(ud)
        self.assertEqual(state.get_pair(ud), ("EUR", "USD"))


class FavoritesTests(unittest.TestCase):
    def test_toggle(self):
        ud = {}
        self.assertEqual(state.toggle_favorite(ud, ("USD", "EUR")), "added")
        self.assertTrue(state.is_favorite(ud, ("USD", "EUR")))
        self.assertEqual(state.toggle_favorite(ud, ("USD", "EUR")), "removed")
        self.assertFalse(state.is_favorite(ud, ("USD", "EUR")))

    def test_limit(self):
        ud = {}
        codes = ["EUR", "BYN", "RUB", "PLN", "GBP", "CNY", "JPY", "CHF", "UAH"]
        for code in codes[: state.MAX_FAVORITES]:
            self.assertEqual(state.toggle_favorite(ud, ("USD", code)), "added")
        self.assertEqual(state.toggle_favorite(ud, ("USD", codes[state.MAX_FAVORITES])), "full")
        self.assertEqual(len(state.get_favorites(ud)), state.MAX_FAVORITES)

    def test_remove_missing_is_noop(self):
        ud = {}
        state.remove_favorite(ud, ("USD", "EUR"))
        self.assertEqual(state.get_favorites(ud), [])


class HistoryTests(unittest.TestCase):
    def test_newest_first_without_duplicates(self):
        ud = {}
        state.add_history(ud, "USD", "EUR", D(100))
        state.add_history(ud, "EUR", "BYN", D(5))
        state.add_history(ud, "USD", "EUR", D(100))
        self.assertEqual(state.get_history(ud), [("USD", "EUR", D(100)), ("EUR", "BYN", D(5))])

    def test_capped(self):
        ud = {}
        for i in range(1, state.MAX_HISTORY + 5):
            state.add_history(ud, "USD", "EUR", D(i))
        history = state.get_history(ud)
        self.assertEqual(len(history), state.MAX_HISTORY)
        self.assertEqual(history[0][2], D(state.MAX_HISTORY + 4))

    def test_clear(self):
        ud = {}
        state.add_history(ud, "USD", "EUR", D(1))
        state.clear_history(ud)
        self.assertEqual(state.get_history(ud), [])


if __name__ == "__main__":
    unittest.main()
