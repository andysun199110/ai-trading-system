from services.risk_manager.service import RiskManagerService
from shared.schemas.trading import Side


def test_breakeven_trigger() -> None:
    svc = RiskManagerService()
    assert svc.should_breakeven(entry=2300, sl=2298, current=2301.8, side=Side.BUY)


def test_trailing_structure_preferred() -> None:
    svc = RiskManagerService()
    assert svc.trailing_stop(Side.BUY, structure_level=2301.2, atr_value=1.0, last_price=2302) == 2301.2
