from shared.constants.domain import SYMBOL_XAUUSD


def test_symbol_fixed() -> None:
    assert SYMBOL_XAUUSD == "XAUUSD"
