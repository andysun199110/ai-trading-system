from dataclasses import dataclass
from typing import Any, Optional

from services.ai_orchestrator.service import Service as AIService
from services.risk_manager.service import Service as RiskService
from services.command_publisher import CommandPublisher, CMD_TYPE_CLOSE_FULL, CMD_TYPE_MODIFY_SL
from services.api_server.db import get_db
from services.api_server.models import Signal
from sqlalchemy import select, desc


@dataclass
class ServiceResult:
    status: str
    payload: dict[str, Any]


class Service:
    """
    Position Supervisor v1.1 - Commercial Command Execution Contract.
    
    Implements three rules only:
    
    1) Direction reversal close:
       - BUY position + latest AI SELL signal -> CLOSE_FULL reason=ai_reverse_signal
       - SELL position + latest AI BUY signal -> CLOSE_FULL reason=ai_reverse_signal
    
    2) Profit protection SL:
       - Position in profit + trend weakening -> MODIFY_SL reason=protect_profit
       - Server provides protective SL price
    
    3) No position = no close command:
       - If no position exists, do NOT generate close commands
    """

    def run(self, payload: dict[str, Any] | None = None) -> ServiceResult:
        data = payload or {}
        pos = data.get("position", {})
        account_login = data.get("account_login")
        account_server = data.get("account_server")
        
        # Rule 3: No position = no close command
        if not pos or not pos.get("ticket"):
            return ServiceResult(
                status="ok",
                payload={
                    "cadence": "1m_lightweight",
                    "actions": [],
                    "command_ids": [],
                    "note": "No position - no commands generated (v1.1 rule 3)",
                },
            )
        
        risk = RiskService()
        actions: list[dict[str, Any]] = []
        command_ids: list[str] = []
        
        # Get latest AI signal for direction reversal check
        latest_ai_signal = self._get_latest_ai_signal()
        position_side = pos.get("side", "").lower()
        
        # Rule 1: Direction reversal close
        close_command_id = self._check_direction_reversal(
            position_side=position_side,
            latest_signal=latest_ai_signal,
            account_login=account_login,
            account_server=account_server,
            position_ref=str(pos.get("ticket")),
            signal_id=pos.get("signal_id"),
        )
        if close_command_id:
            command_ids.append(close_command_id)
            actions.append({
                "type": "close_full",
                "reason": "ai_reverse_signal",
                "command_id": close_command_id,
            })
        
        # Rule 2: Profit protection SL (only if not already closing)
        if not close_command_id:
            sl_command_id = self._check_profit_protection(
                pos=pos,
                risk=risk,
                account_login=account_login,
                account_server=account_server,
                position_ref=str(pos.get("ticket")),
                signal_id=pos.get("signal_id"),
            )
            if sl_command_id:
                command_ids.append(sl_command_id)
                actions.append({
                    "type": "modify_sl",
                    "reason": "protect_profit",
                    "command_id": sl_command_id,
                })
        
        return ServiceResult(
            status="ok",
            payload={
                "cadence": "1m_lightweight",
                "actions": actions,
                "command_ids": command_ids,
                "v11_rules_applied": {
                    "direction_reversal": bool(close_command_id),
                    "profit_protection": bool(sl_command_id),
                    "no_position_no_close": False,  # We have a position
                },
            },
        )
    
    def _get_latest_ai_signal(self) -> Optional[dict]:
        """Get the latest AI signal for direction reversal check."""
        try:
            db = next(get_db())
            stmt = (
                select(Signal)
                .where(Signal.status.in_(["new", "approved", "dispatched"]))
                .order_by(desc(Signal.id))
                .limit(1)
            )
            signal = db.scalar(stmt)
            db.close()
            
            if signal:
                return {
                    "signal_id": signal.signal_id,
                    "symbol": signal.symbol,
                    "payload": signal.payload,
                    "side": signal.payload.get("side"),
                }
        except Exception:
            pass
        
        return None
    
    def _check_direction_reversal(
        self,
        position_side: str,
        latest_signal: Optional[dict],
        account_login: str,
        account_server: str,
        position_ref: str,
        signal_id: Optional[str],
    ) -> Optional[str]:
        """
        Rule 1: Direction reversal close.
        
        - BUY position + latest AI SELL -> CLOSE_FULL reason=ai_reverse_signal
        - SELL position + latest AI BUY -> CLOSE_FULL reason=ai_reverse_signal
        
        Returns command_id if reversal detected, None otherwise.
        """
        if not latest_signal or not latest_signal.get("side"):
            return None
        
        ai_side = latest_signal["side"].lower()
        
        # Check for reversal
        is_reversal = (
            (position_side == "buy" and ai_side == "sell") or
            (position_side == "sell" and ai_side == "buy")
        )
        
        if not is_reversal:
            return None
        
        # Generate CLOSE_FULL command
        try:
            db = next(get_db())
            publisher = CommandPublisher(db)
            
            cmd = publisher.create_close_full_command(
                account_login=account_login,
                account_server=account_server,
                position_ref=position_ref,
                signal_id=signal_id or latest_signal.get("signal_id"),
                reason="ai_reverse_signal",
            )
            
            db.close()
            return cmd.command_id
        except Exception:
            pass
        
        return None
    
    def _check_profit_protection(
        self,
        pos: dict,
        risk: RiskService,
        account_login: str,
        account_server: str,
        position_ref: str,
        signal_id: Optional[str],
    ) -> Optional[str]:
        """
        Rule 2: Profit protection SL.
        
        - Position in profit + trend weakening -> MODIFY_SL reason=protect_profit
        - Server provides protective SL price
        
        Returns command_id if protection needed, None otherwise.
        """
        entry_price = pos.get("entry") or pos.get("entry_price")
        current_price = pos.get("current_price")
        initial_sl = pos.get("initial_sl") or pos.get("sl")
        side = pos.get("side", "").lower()
        
        if not entry_price or not current_price:
            return None
        
        # Check if position is in profit
        is_profit = (
            (side == "buy" and current_price > entry_price) or
            (side == "sell" and current_price < entry_price)
        )
        
        if not is_profit:
            return None
        
        # Check for trend weakening (simplified - use risk manager breakeven logic)
        be = risk.breakeven_action(
            {
                "entry": entry_price,
                "side": side,
                "current_price": current_price,
                "initial_sl": initial_sl,
                "breakeven_trigger_r": 0.8,  # 0.8R profit trigger
                "fee_buffer": 0.5,  # Small buffer for fees
            }
        )
        
        if not be.get("move_to_breakeven") or not be.get("new_sl"):
            return None
        
        # Generate MODIFY_SL command with protect_profit reason
        try:
            db = next(get_db())
            publisher = CommandPublisher(db)
            
            cmd = publisher.create_modify_sl_command(
                account_login=account_login,
                account_server=account_server,
                position_ref=position_ref,
                new_sl=be["new_sl"],
                signal_id=signal_id,
                reason="protect_profit",
            )
            
            db.close()
            return cmd.command_id
        except Exception:
            pass
        
        return None
