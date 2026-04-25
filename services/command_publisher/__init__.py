"""
Trading Command Publisher Service (v1.1)

Provides utilities for signal_engine and position_supervisor to create
and publish trading commands to the command queue.
"""

import time
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from services.api_server.models import TradingCommand, TradingExecutionReport
from shared.constants.domain import SYMBOL_XAUUSD

# Command type constants
CMD_TYPE_OPEN = "OPEN"
CMD_TYPE_MODIFY_SL = "MODIFY_SL"
CMD_TYPE_MODIFY_TP = "MODIFY_TP"
CMD_TYPE_CLOSE_PARTIAL = "CLOSE_PARTIAL"
CMD_TYPE_CLOSE_FULL = "CLOSE_FULL"
CMD_TYPE_CANCEL_OPEN = "CANCEL_OPEN"

# Source module constants
SOURCE_SIGNAL_ENGINE = "signal_engine"
SOURCE_POSITION_SUPERVISOR = "position_supervisor"
SOURCE_MANUAL_ADMIN = "manual_admin"

# Priority levels (lower = higher priority)
PRIORITY_CLOSE_FULL = 10
PRIORITY_CLOSE_PARTIAL = 20
PRIORITY_MODIFY_SL = 50
PRIORITY_MODIFY_TP = 60
PRIORITY_OPEN = 100
PRIORITY_CANCEL_OPEN = 200

# Status constants (v1.1)
CMD_STATUS_AVAILABLE = "AVAILABLE"
CMD_STATUS_DISPATCHED = "DISPATCHED"
CMD_STATUS_EXECUTED = "EXECUTED"
CMD_STATUS_FAILED = "FAILED"
CMD_STATUS_EXPIRED = "EXPIRED"
CMD_STATUS_REJECTED = "REJECTED"
CMD_STATUS_DUPLICATE = "DUPLICATE"
CMD_STATUS_CANCELLED = "CANCELLED"
CMD_STATUS_SHADOW_SKIPPED = "SHADOW_SKIPPED"
CMD_STATUS_TRADING_DISABLED = "TRADING_DISABLED"


class CommandPublisher:
    """Publishes trading commands to the command queue (v1.1)."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def _cancel_pending_open(self, account_login: str, account_server: str, reason: str = "replaced") -> int:
        """
        Cancel pending OPEN commands for an account (OPEN replacement logic).
        
        If new OPEN arrives and old OPEN still unexecuted: old OPEN -> cancelled.
        If old OPEN already executed to position: keep it (position supervisor handles close).
        
        Returns count of cancelled commands.
        """
        from sqlalchemy import text
        
        now = datetime.utcnow()
        now_epoch = int(now.timestamp())
        
        result = self.db.execute(
            text("""
                UPDATE trading_commands 
                SET status = :status, reason = :reason, executed_at = :now
                WHERE account_login = :account_login
                  AND account_server = :account_server
                  AND command_type = :command_type
                  AND status IN (:available, :dispatched)
                  AND expires_at_epoch > :now_epoch
            """),
            {
                "status": CMD_STATUS_CANCELLED,
                "reason": reason,
                "account_login": account_login,
                "account_server": account_server,
                "command_type": CMD_TYPE_OPEN,
                "available": CMD_STATUS_AVAILABLE,
                "dispatched": CMD_STATUS_DISPATCHED,
                "now": now,
                "now_epoch": now_epoch,
            }
        )
        
        self.db.commit()
        return result.rowcount
    
    def create_open_command(
        self,
        account_login: str,
        account_server: str,
        signal_id: str,
        side: str,
        volume: float,
        sl: float,
        tp: float,
        entry_ref_price: Optional[float] = None,
        max_adverse_move_price: Optional[float] = None,
        strategy_version: str = "stage3-v11",
        config_version: str = "2026.04",
        expires_minutes: int = 10,
        priority: int = PRIORITY_OPEN,
        extra_payload: dict = None,
    ) -> TradingCommand:
        """
        Create an OPEN command for new position entry (v1.1).
        
        Args:
            account_login: MT5 account login
            account_server: MT5 server name
            signal_id: Source signal ID
            side: 'buy' or 'sell'
            volume: Trade volume in lots
            sl: Stop loss price
            tp: Take profit price
            entry_ref_price: Reference entry price for adverse move calculation
            max_adverse_move_price: Maximum adverse price allowed
            strategy_version: Strategy version identifier
            config_version: Config version identifier
            expires_minutes: Command expiry time in minutes
            priority: Command priority (lower = higher)
            extra_payload: Additional payload data
        
        Returns:
            Created TradingCommand object
        """
        now = datetime.utcnow()
        now_epoch = int(now.timestamp())
        command_id = f"cmd-{uuid.uuid4().hex[:12]}"
        idempotency_key = f"idem-{uuid.uuid4().hex}"
        
        payload = extra_payload.copy() if extra_payload else {}
        payload.update({
            "initial_sl": sl,
            "initial_tp": tp,
            "entry_reason": "ai_signal_approved",
        })
        
        # Handle OPEN replacement logic: cancel old unexecuted OPEN for same account
        self._cancel_pending_open(account_login, account_server, reason="replaced_by_new_open")
        
        command = TradingCommand(
            command_id=command_id,
            account_login=account_login,
            account_server=account_server,
            symbol=SYMBOL_XAUUSD,
            command_type=CMD_TYPE_OPEN,
            side=side,
            volume=volume,
            sl=sl,
            tp=tp,
            entry_ref_price=entry_ref_price,
            max_adverse_move_price=max_adverse_move_price,
            source_module=SOURCE_SIGNAL_ENGINE,
            signal_id=signal_id,
            strategy_version=strategy_version,
            config_version=config_version,
            issued_at=now,
            expires_at=now + timedelta(minutes=expires_minutes),
            created_at_epoch=now_epoch,
            expires_at_epoch=now_epoch + (expires_minutes * 60),
            priority=priority,
            idempotency_key=idempotency_key,
            status=CMD_STATUS_AVAILABLE,
            payload=payload,
        )
        
        self.db.add(command)
        self.db.commit()
        self.db.refresh(command)
        
        return command
    
    def create_modify_sl_command(
        self,
        account_login: str,
        account_server: str,
        position_ref: str,
        new_sl: float,
        signal_id: Optional[str] = None,
        reason: str = "trailing_stop",
        priority: int = PRIORITY_MODIFY_SL,
        expires_minutes: int = 5,
    ) -> TradingCommand:
        """
        Create a MODIFY_SL command for stop loss update (v1.1).
        
        Args:
            account_login: MT5 account login
            account_server: MT5 server name
            position_ref: Position ticket or reference
            new_sl: New stop loss price
            signal_id: Optional source signal ID
            reason: Reason for SL modification (e.g., "trailing_stop", "protect_profit", "breakeven")
            priority: Command priority
            expires_minutes: Command expiry time
        
        Returns:
            Created TradingCommand object
        """
        now = datetime.utcnow()
        now_epoch = int(now.timestamp())
        command_id = f"cmd-{uuid.uuid4().hex[:12]}"
        idempotency_key = f"idem-{uuid.uuid4().hex}"
        
        command = TradingCommand(
            command_id=command_id,
            account_login=account_login,
            account_server=account_server,
            symbol=SYMBOL_XAUUSD,
            command_type=CMD_TYPE_MODIFY_SL,
            side=None,
            volume=None,
            sl=new_sl,
            tp=None,
            position_ref=position_ref,
            source_module=SOURCE_POSITION_SUPERVISOR,
            signal_id=signal_id,
            issued_at=now,
            expires_at=now + timedelta(minutes=expires_minutes),
            created_at_epoch=now_epoch,
            expires_at_epoch=now_epoch + (expires_minutes * 60),
            priority=priority,
            idempotency_key=idempotency_key,
            status=CMD_STATUS_AVAILABLE,
            reason=reason,
            payload={
                "modification_reason": reason,
                "new_sl": new_sl,
            },
        )
        
        self.db.add(command)
        self.db.commit()
        self.db.refresh(command)
        
        return command
    
    def create_close_full_command(
        self,
        account_login: str,
        account_server: str,
        position_ref: str,
        signal_id: Optional[str] = None,
        reason: str = "ai_reversal",
        priority: int = PRIORITY_CLOSE_FULL,
        expires_minutes: int = 2,
    ) -> TradingCommand:
        """
        Create a CLOSE_FULL command for complete position close (v1.1).
        
        Args:
            account_login: MT5 account login
            account_server: MT5 server name
            position_ref: Position ticket or reference
            signal_id: Optional source signal ID
            reason: Reason for closing (e.g., "ai_reverse_signal", "protect_profit", "risk_management")
            priority: Command priority (default high for risk management)
            expires_minutes: Command expiry time
        
        Returns:
            Created TradingCommand object
        """
        now = datetime.utcnow()
        now_epoch = int(now.timestamp())
        command_id = f"cmd-{uuid.uuid4().hex[:12]}"
        idempotency_key = f"idem-{uuid.uuid4().hex}"
        
        command = TradingCommand(
            command_id=command_id,
            account_login=account_login,
            account_server=account_server,
            symbol=SYMBOL_XAUUSD,
            command_type=CMD_TYPE_CLOSE_FULL,
            side=None,
            volume=None,
            sl=None,
            tp=None,
            position_ref=position_ref,
            source_module=SOURCE_POSITION_SUPERVISOR,
            signal_id=signal_id,
            issued_at=now,
            expires_at=now + timedelta(minutes=expires_minutes),
            created_at_epoch=now_epoch,
            expires_at_epoch=now_epoch + (expires_minutes * 60),
            priority=priority,
            idempotency_key=idempotency_key,
            status=CMD_STATUS_AVAILABLE,
            reason=reason,
            payload={
                "close_reason": reason,
                "close_type": "full",
            },
        )
        
        self.db.add(command)
        self.db.commit()
        self.db.refresh(command)
        
        return command
    
    def create_close_partial_command(
        self,
        account_login: str,
        account_server: str,
        position_ref: str,
        close_ratio: float,
        signal_id: Optional[str] = None,
        reason: str = "partial_profit",
        priority: int = PRIORITY_CLOSE_PARTIAL,
        expires_minutes: int = 3,
    ) -> TradingCommand:
        """
        Create a CLOSE_PARTIAL command for partial position close.
        
        Args:
            account_login: MT5 account login
            account_server: MT5 server name
            position_ref: Position ticket or reference
            close_ratio: Ratio to close (0.0 to 1.0)
            signal_id: Optional source signal ID
            reason: Reason for partial close
            priority: Command priority
            expires_minutes: Command expiry time
        
        Returns:
            Created TradingCommand object
        """
        if not 0.0 < close_ratio <= 1.0:
            raise ValueError(f"close_ratio must be between 0 and 1, got {close_ratio}")
        
        now = datetime.utcnow()
        command_id = f"cmd-{uuid.uuid4().hex[:12]}"
        idempotency_key = f"idem-{uuid.uuid4().hex}"
        
        command = TradingCommand(
            command_id=command_id,
            account_login=account_login,
            account_server=account_server,
            symbol=SYMBOL_XAUUSD,
            command_type=CMD_TYPE_CLOSE_PARTIAL,
            side=None,
            volume=None,
            sl=None,
            tp=None,
            close_ratio=close_ratio,
            position_ref=position_ref,
            source_module=SOURCE_POSITION_SUPERVISOR,
            signal_id=signal_id,
            issued_at=now,
            expires_at=now + timedelta(minutes=expires_minutes),
            priority=priority,
            idempotency_key=idempotency_key,
            status="PENDING",
            reason=reason,
            payload={
                "close_reason": reason,
                "close_type": "partial",
                "close_ratio": close_ratio,
            },
        )
        
        self.db.add(command)
        self.db.commit()
        self.db.refresh(command)
        
        return command
    
    def get_command_by_id(self, command_id: str) -> Optional[TradingCommand]:
        """Get a command by its ID."""
        from sqlalchemy import select
        return self.db.scalar(
            select(TradingCommand).where(TradingCommand.command_id == command_id)
        )
    
    def get_pending_commands(
        self,
        account_login: str,
        account_server: str,
        limit: int = 20,
    ) -> list:
        """Get pending commands for an account."""
        from sqlalchemy import select, and_
        from datetime import datetime
        
        now = datetime.utcnow()
        
        stmt = (
            select(TradingCommand)
            .where(
                and_(
                    TradingCommand.account_login == account_login,
                    TradingCommand.account_server == account_server,
                    TradingCommand.status.in_(["PENDING", "SENT"]),
                    TradingCommand.expires_at > now,
                )
            )
            .order_by(TradingCommand.priority, TradingCommand.issued_at)
            .limit(limit)
        )
        
        return self.db.execute(stmt).scalars().all()
    
    def expire_old_commands(self) -> int:
        """Expire commands past their expires_at. Returns count of expired commands."""
        from sqlalchemy import text
        from datetime import datetime
        
        now = datetime.utcnow()
        
        result = self.db.execute(
            text("""
                UPDATE trading_commands 
                SET status = :status, reason = :reason, executed_at = :now
                WHERE status IN (:pending, :sent) 
                AND expires_at < :now
            """),
            {
                "status": "EXPIRED",
                "reason": "Command expired",
                "pending": "PENDING",
                "sent": "SENT",
                "now": now,
            }
        )
        
        self.db.commit()
        return result.rowcount
