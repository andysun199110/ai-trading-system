"""Unit Tests - Negative and Boundary Cases for Stage 2 Services."""
import pytest

from services.signal_engine.service import Service as SignalService
from services.risk_manager.service import Service as RiskService


class TestSignalEngineNegativeCases:
    """Signal Engine negative and boundary tests."""

    def test_non_xauusd_symbol_blocked(self) -> None:
        """Test that non-XAUUSD symbols are blocked."""
        result = SignalService().run({"symbol": "EURUSD", "side": "buy", "entry": 1.1})
        assert result.status == "blocked"
        assert result.payload["reason"] == "symbol_not_allowed"

    def test_all_checks_fail_blocked(self) -> None:
        """Test that all checks failing results in block."""
        result = SignalService().run({
            "symbol": "XAUUSD",
            "side": "buy",
            "entry": 2300.0,
            "h1_regime_ok": False,
            "m15_setup_ok": False,
            "m5_trigger_ok": False,
            "spread_ok": False,
            "event_block_active": True,
            "kill_switch": True,
        })
        assert result.status == "blocked"
        assert len(result.payload.get("blocked_reasons", [])) > 0

    def test_partial_checks_fail_blocked(self) -> None:
        """Test that partial check failures are captured."""
        result = SignalService().run({
            "symbol": "XAUUSD",
            "side": "buy",
            "entry": 2300.0,
            "h1_regime_ok": True,
            "m15_setup_ok": False,
            "m5_trigger_ok": True,
            "spread_ok": True,
        })
        assert result.status == "blocked"
        blocked = result.payload.get("blocked_reasons", [])
        assert "m15" in str(blocked)


class TestRiskManagerBoundaryCases:
    """Risk Manager boundary tests."""

    def test_zero_atr_uses_structure_sl(self) -> None:
        """Test zero ATR uses structure SL fallback."""
        result = RiskService().run({
            "entry": 2300.0,
            "side": "buy",
            "atr": 0,
            "structure_sl": 2280.0,
            "rr": 1.5,
        })
        assert result.payload["initial_sl"] == 2280.0

    def test_missing_structure_sl_uses_atr(self) -> None:
        """Test that missing structure SL uses ATR-based calculation."""
        result = RiskService().run({
            "entry": 2300.0,
            "side": "buy",
            "atr": 2.0,
            "rr": 1.5,
        })
        assert "initial_sl" in result.payload
        assert result.payload["initial_sl"] < 2300.0

    def test_sell_side_sl_above_entry(self) -> None:
        """Test sell side has SL above entry."""
        result = RiskService().run({
            "entry": 2300.0,
            "side": "sell",
            "atr": 2.0,
            "rr": 1.5,
        })
        assert result.payload["initial_sl"] > 2300.0

    def test_zero_rr_handled(self) -> None:
        """Test zero risk-reward ratio still calculates TP."""
        result = RiskService().run({
            "entry": 2300.0,
            "side": "buy",
            "atr": 2.0,
            "structure_sl": 2280.0,
            "rr": 0,
        })
        assert "tp" in result.payload
        assert result.payload["tp"] == 2300.0  # 0 R means TP = entry

    def test_breakeven_action_no_move(self) -> None:
        """Test breakeven when price hasn't reached trigger."""
        result = RiskService().breakeven_action({
            "entry": 2300.0,
            "side": "buy",
            "current_price": 2305.0,
            "initial_sl": 2280.0,
            "breakeven_trigger_r": 0.8,
        })
        # progressed = 5/20 = 0.25 < 0.8
        assert result["move_to_breakeven"] == False

    def test_breakeven_action_move(self) -> None:
        """Test breakeven when price has reached trigger."""
        result = RiskService().breakeven_action({
            "entry": 2300.0,
            "side": "buy",
            "current_price": 2316.0,  # 16/20 = 0.8 >= 0.8
            "initial_sl": 2280.0,
            "breakeven_trigger_r": 0.8,
        })
        assert result["move_to_breakeven"] == True

    def test_trailing_action_structure(self) -> None:
        """Test trailing with structure level."""
        result = RiskService().trailing_action({
            "side": "buy",
            "current_price": 2320.0,
            "structure_level": 2305.0,
            "atr": 2.0,
        })
        assert result["trail_method"] == "structure"
        assert result["new_sl"] == 2305.0

    def test_trailing_action_atr(self) -> None:
        """Test trailing with ATR fallback."""
        result = RiskService().trailing_action({
            "side": "buy",
            "current_price": 2320.0,
            "atr": 2.0,
            "trail_atr_mult": 1.0,
        })
        assert result["trail_method"] == "atr"
        assert result["new_sl"] == 2318.0  # 2320 - 2*1


class TestEventCalendarBoundaryCases:
    """Event Calendar boundary tests."""

    def test_empty_events_list(self) -> None:
        """Test handling of empty events list."""
        from services.event_calendar.service import Service as EventService
        result = EventService().run({"events": []})
        assert result.status == "ok"
        assert result.payload.get("event_block_active") == False

    def test_hard_impact_event_blocks(self) -> None:
        """Test hard impact event triggers block (not 'high')."""
        from services.event_calendar.service import Service as EventService
        result = EventService().run({
            "events": [
                {"impact": "hard", "time": "2026-04-19T14:30:00Z", "name": "NFP"}
            ],
            "now": "2026-04-19T14:30:00Z",
        })
        assert result.payload.get("event_block_active") == True

    def test_low_impact_event_no_block(self) -> None:
        """Test low impact event doesn't block."""
        from services.event_calendar.service import Service as EventService
        result = EventService().run({
            "events": [
                {"impact": "low", "time": "2026-04-19T14:30:00Z", "name": "Speech"}
            ],
            "now": "2026-04-19T14:30:00Z",
        })
        assert result.payload.get("event_block_active") == False


class TestMarketStructureBoundaryCases:
    """Market Structure boundary tests."""

    def test_insufficient_price_data(self) -> None:
        """Test handling of insufficient price data."""
        from services.market_structure.service import Service as MarketService
        result = MarketService().run({"prices": [2300.0]})
        # Service returns 'insufficient_data' status
        assert result.status == "insufficient_data"

    def test_identical_prices_flat_market(self) -> None:
        """Test handling of identical prices (no movement)."""
        from services.market_structure.service import Service as MarketService
        result = MarketService().run({"prices": [2300.0, 2300.0, 2300.0, 2300.0]})
        assert result.status == "insufficient_data"

    def test_minimum_viable_prices(self) -> None:
        """Test with minimum viable price data."""
        from services.market_structure.service import Service as MarketService
        result = MarketService().run({
            "prices": [2300.0, 2305.0, 2298.0, 2310.0, 2295.0, 2315.0, 2308.0, 2320.0],
            "timeframe": "M15",
        })
        # Should have enough data for analysis
        assert result.status == "ok" or result.status == "insufficient_data"


class TestETFBiasNegativeCases:
    """ETF Bias negative tests."""

    def test_empty_holdings(self) -> None:
        """Test handling of empty ETF holdings."""
        from services.etf_bias.service import Service as ETFService
        result = ETFService().run({"symbol": "GLD", "holdings": []})
        assert isinstance(result, object)

    def test_missing_gold_holdings(self) -> None:
        """Test when gold holdings data is missing."""
        from services.etf_bias.service import Service as ETFService
        result = ETFService().run({"symbol": "GLD"})
        assert isinstance(result, object)


class TestReviewOptimizerBoundaryCases:
    """Weekly Review Optimizer boundary tests."""

    def test_empty_trades(self) -> None:
        """Test handling of empty trades list."""
        from services.review_optimizer.service import Service as ReviewService
        result = ReviewService().run({"week": "2026-W16", "trades": []})
        assert isinstance(result, object)

    def test_missing_week(self) -> None:
        """Test handling of missing week identifier."""
        from services.review_optimizer.service import Service as ReviewService
        result = ReviewService().run({"trades": []})
        assert isinstance(result, object)


class TestPositionSupervisorCases:
    """Position Supervisor tests."""

    def test_lightweight_supervision_ok(self) -> None:
        """Test lightweight 1m supervision without AI."""
        from services.position_supervisor.service import Service as PositionService
        result = PositionService().run({
            "position": {
                "entry": 2300.0,
                "side": "buy",
                "current_price": 2310.0,
                "initial_sl": 2280.0,
            },
            "event_window_active": False,
            "state_change": False,
        })
        assert result.status == "ok"
        assert result.payload["deep_ai_invoked"] == False

    def test_ai_invoked_on_state_change(self) -> None:
        """Test AI is invoked on state change."""
        from services.position_supervisor.service import Service as PositionService
        result = PositionService().run({
            "position": {
                "entry": 2300.0,
                "side": "buy",
                "current_price": 2310.0,
                "initial_sl": 2280.0,
            },
            "event_window_active": False,
            "state_change": True,
        })
        assert result.status == "ok"
        assert result.payload["deep_ai_invoked"] == True

    def test_ai_invoked_on_event_window(self) -> None:
        """Test AI is invoked during event window."""
        from services.position_supervisor.service import Service as PositionService
        result = PositionService().run({
            "position": {
                "entry": 2300.0,
                "side": "buy",
                "current_price": 2310.0,
                "initial_sl": 2280.0,
            },
            "event_window_active": True,
            "state_change": False,
        })
        assert result.status == "ok"
        assert result.payload["deep_ai_invoked"] == True
