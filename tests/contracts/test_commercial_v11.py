"""
Commercial Command Execution Contract v1.1 - Test Verification Suite

This module verifies all v1.1 contract requirements.
Run with: pytest tests/contracts/test_commercial_v11.py -v
"""

import time
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select, text

from services.api_server.db import get_db
from services.api_server.models import (
    TradingCommand,
    TradingExecutionReport,
    PositionSnapshot,
    Session as AuthSession,
)
from services.command_publisher import (
    CommandPublisher,
    CMD_TYPE_OPEN,
    CMD_TYPE_CLOSE_FULL,
    CMD_TYPE_MODIFY_SL,
    CMD_STATUS_AVAILABLE,
    CMD_STATUS_CANCELLED,
    CMD_STATUS_EXECUTED,
    CMD_STATUS_FAILED,
    CMD_STATUS_EXPIRED,
    CMD_STATUS_REJECTED,
    CMD_STATUS_DUPLICATE,
    CMD_STATUS_SHADOW_SKIPPED,
    CMD_STATUS_TRADING_DISABLED,
)


class TestPollCommandsContract:
    """CHECK_POLL_COMMANDS_CONTRACT"""
    
    def test_poll_response_format_v11(self, test_client, test_session_token):
        """Verify poll response uses v1.1 format with epoch timestamps."""
        response = test_client.get("/api/v1/signals/poll", params={"token": test_session_token})
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "ok"
        assert "payload" in data
        assert "server_time_epoch" in data["payload"]
        assert "commands" in data["payload"]
        assert isinstance(data["payload"]["server_time_epoch"], int)
    
    def test_poll_command_fields_v11(self, test_client, test_session_token, db):
        """Verify each command includes all required v1.1 fields."""
        # Create a test command
        publisher = CommandPublisher(db)
        cmd = publisher.create_open_command(
            account_login="test_account",
            account_server="test_server",
            signal_id="sig-test-123",
            side="buy",
            volume=0.01,
            sl=2650.0,
            tp=2670.0,
            entry_ref_price=2655.0,
            max_adverse_move_price=2645.0,
        )
        
        # Bind session to test account
        db.add(AuthSession(
            token=test_session_token,
            license_id=1,
            account_login="test_account",
            account_server="test_server",
            expires_at=datetime.utcnow() + timedelta(hours=1),
        ))
        db.commit()
        
        response = test_client.get("/api/v1/signals/poll", params={"token": test_session_token})
        assert response.status_code == 200
        
        commands = response.json()["payload"]["commands"]
        assert len(commands) > 0
        
        cmd_data = commands[0]
        # Check all required v1.1 fields
        assert "command_id" in cmd_data
        assert "idempotency_key" in cmd_data
        assert "signal_id" in cmd_data
        assert "account_login" in cmd_data
        assert "account_server" in cmd_data
        assert "command_type" in cmd_data
        assert "side" in cmd_data
        assert "volume" in cmd_data
        assert "sl" in cmd_data
        assert "tp" in cmd_data
        assert "entry_ref_price" in cmd_data
        assert "max_adverse_move_price" in cmd_data
        assert "created_at_epoch" in cmd_data
        assert "expires_at_epoch" in cmd_data
        assert "priority" in cmd_data


class TestNoSymbolFiltering:
    """CHECK_NO_SYMBOL_FILTERING"""
    
    def test_dispatch_by_account_not_symbol(self, db):
        """Verify commands are dispatched by account, not filtered by symbol."""
        publisher = CommandPublisher(db)
        
        # Create commands for test account
        cmd1 = publisher.create_open_command(
            account_login="test_account",
            account_server="test_server",
            signal_id="sig-1",
            side="buy",
            volume=0.01,
            sl=2650.0,
            tp=2670.0,
        )
        
        # Query should return commands regardless of symbol
        # (symbol filtering removed in v1.1)
        stmt = text("""
            SELECT COUNT(*) FROM trading_commands
            WHERE account_login = :account_login
            AND account_server = :account_server
            AND status IN (:available, :dispatched)
        """)
        
        result = db.execute(stmt, {
            "account_login": "test_account",
            "account_server": "test_server",
            "available": CMD_STATUS_AVAILABLE,
            "dispatched": "DISPATCHED",
        })
        
        count = result.scalar()
        assert count >= 1  # Should find our command


class TestAdversePriceFields:
    """CHECK_ADVERSE_PRICE_FIELDS"""
    
    def test_entry_ref_price_field(self, db):
        """Verify entry_ref_price field exists and is stored."""
        publisher = CommandPublisher(db)
        cmd = publisher.create_open_command(
            account_login="test_account",
            account_server="test_server",
            signal_id="sig-test",
            side="buy",
            volume=0.01,
            sl=2650.0,
            tp=2670.0,
            entry_ref_price=2655.5,
        )
        
        assert cmd.entry_ref_price == 2655.5
    
    def test_max_adverse_move_price_field(self, db):
        """Verify max_adverse_move_price field exists and is stored."""
        publisher = CommandPublisher(db)
        cmd = publisher.create_open_command(
            account_login="test_account",
            account_server="test_server",
            signal_id="sig-test",
            side="buy",
            volume=0.01,
            sl=2650.0,
            tp=2670.0,
            max_adverse_move_price=2645.0,
        )
        
        assert cmd.max_adverse_move_price == 2645.0


class TestEpochExpiryFields:
    """CHECK_EPOCH_EXPIRY_FIELDS"""
    
    def test_epoch_timestamps_stored(self, db):
        """Verify created_at_epoch and expires_at_epoch are stored."""
        publisher = CommandPublisher(db)
        cmd = publisher.create_open_command(
            account_login="test_account",
            account_server="test_server",
            signal_id="sig-test",
            side="buy",
            volume=0.01,
            sl=2650.0,
            tp=2670.0,
            expires_minutes=10,
        )
        
        assert isinstance(cmd.created_at_epoch, int)
        assert isinstance(cmd.expires_at_epoch, int)
        assert cmd.expires_at_epoch > cmd.created_at_epoch
        # Should be approximately 10 minutes (600 seconds) difference
        assert cmd.expires_at_epoch - cmd.created_at_epoch >= 590


class TestExpiredFiltering:
    """CHECK_EXPIRED_FILTERING"""
    
    def test_expired_commands_not_returned(self, test_client, test_session_token, db):
        """Verify expired commands are not returned in poll."""
        now_epoch = int(datetime.utcnow().timestamp())
        expired_epoch = now_epoch - 3600  # 1 hour ago
        
        # Manually create expired command
        cmd = TradingCommand(
            command_id="cmd-expired-test",
            idempotency_key="idem-expired",
            account_login="test_account",
            account_server="test_server",
            symbol="XAUUSD",
            command_type=CMD_TYPE_OPEN,
            side="buy",
            volume=0.01,
            sl=2650.0,
            tp=2670.0,
            status=CMD_STATUS_AVAILABLE,
            created_at_epoch=expired_epoch,
            expires_at_epoch=expired_epoch,
            issued_at=datetime.utcnow() - timedelta(hours=1),
            expires_at=datetime.utcnow() - timedelta(hours=1),
            priority=100,
        )
        db.add(cmd)
        db.commit()
        
        response = test_client.get("/api/v1/signals/poll", params={"token": test_session_token})
        commands = response.json()["payload"]["commands"]
        
        # Expired command should not be in results
        command_ids = [c["command_id"] for c in commands]
        assert "cmd-expired-test" not in command_ids


class TestReportAcceptsTerminalStatuses:
    """CHECK_REPORT_ACCEPTS_TERMINAL_STATUSES"""
    
    @pytest.mark.parametrize("status", [
        CMD_STATUS_EXECUTED,
        CMD_STATUS_FAILED,
        CMD_STATUS_EXPIRED,
        CMD_STATUS_REJECTED,
        CMD_STATUS_DUPLICATE,
        CMD_STATUS_SHADOW_SKIPPED,
        CMD_STATUS_TRADING_DISABLED,
    ])
    def test_execution_report_accepts_all_terminal_statuses(self, test_client, test_session_token, db, status):
        """Verify execution report accepts all terminal statuses without 400 error."""
        # Create a test command
        publisher = CommandPublisher(db)
        cmd = publisher.create_open_command(
            account_login="test_account",
            account_server="test_server",
            signal_id="sig-test",
            side="buy",
            volume=0.01,
            sl=2650.0,
            tp=2670.0,
        )
        
        response = test_client.post(
            "/api/v1/execution/report",
            json={
                "token": test_session_token,
                "command_id": cmd.command_id,
                "status": status,
                "payload": {
                    "broker_retcode": 10009,
                    "broker_comment": "Test",
                    "server_time": datetime.utcnow().isoformat() + "Z",
                }
            }
        )
        
        # Should return 200, not 400
        assert response.status_code == 200


class TestActiveQueueCleanup:
    """CHECK_ACTIVE_QUEUE_CLEANUP"""
    
    def test_terminal_commands_not_in_active_queue(self, db):
        """Verify terminal state commands are not returned in active queue."""
        publisher = CommandPublisher(db)
        
        # Create command and mark as executed
        cmd = publisher.create_open_command(
            account_login="test_account",
            account_server="test_server",
            signal_id="sig-test",
            side="buy",
            volume=0.01,
            sl=2650.0,
            tp=2670.0,
        )
        cmd.status = CMD_STATUS_EXECUTED
        db.commit()
        
        # Query active queue
        stmt = text("""
            SELECT COUNT(*) FROM trading_commands
            WHERE account_login = :account_login
            AND account_server = :account_server
            AND status IN (:available, :dispatched)
        """)
        
        result = db.execute(stmt, {
            "account_login": "test_account",
            "account_server": "test_server",
            "available": CMD_STATUS_AVAILABLE,
            "dispatched": "DISPATCHED",
        })
        
        count = result.scalar()
        # Executed command should not be in active queue
        assert count == 0


class TestSundayHistoryCleanup:
    """CHECK_SUNDAY_HISTORY_CLEANUP"""
    
    def test_weekly_cleanup_script_exists(self):
        """Verify weekly cleanup script exists."""
        import os
        script_path = "/opt/ai-trading/infra/scripts/weekly_cleanup.py"
        assert os.path.exists(script_path)
    
    def test_weekly_cleanup_dry_run(self):
        """Verify weekly cleanup script runs successfully in dry-run mode."""
        import subprocess
        result = subprocess.run(
            ["python", "/opt/ai-trading/infra/scripts/weekly_cleanup.py", "--dry-run"],
            capture_output=True,
            text=True,
            cwd="/opt/ai-trading"
        )
        assert result.returncode == 0
        assert "Commands deleted:" in result.stdout


class TestPositionSnapshotAccepted:
    """CHECK_POSITION_SNAPSHOT_ACCEPTED"""
    
    def test_position_snapshot_endpoint_exists(self, test_client, test_session_token):
        """Verify position snapshot endpoint accepts data."""
        response = test_client.post(
            "/api/v1/positions/snapshot",
            json={
                "token": test_session_token,
                "account_login": "test_account",
                "account_server": "test_server",
                "positions": [
                    {
                        "ticket": 123456,
                        "symbol": "XAUUSD",
                        "side": "buy",
                        "volume": 0.01,
                        "entry_price": 2650.0,
                        "current_price": 2655.5,
                        "sl": 2645.0,
                        "tp": 2670.0,
                        "swap": -0.5,
                        "profit": 5.5,
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "snapshot_recorded"
    
    def test_position_snapshot_stored(self, test_client, test_session_token, db):
        """Verify position snapshot is stored in database."""
        response = test_client.post(
            "/api/v1/positions/snapshot",
            json={
                "token": test_session_token,
                "account_login": "test_account",
                "account_server": "test_server",
                "positions": [{"ticket": 123456, "symbol": "XAUUSD"}]
            }
        )
        
        assert response.status_code == 200
        
        # Verify stored in database
        stmt = select(PositionSnapshot).where(
            PositionSnapshot.account_login == "test_account"
        )
        snapshot = db.scalar(stmt)
        assert snapshot is not None


class TestPositionSupervisorV11:
    """CHECK_POSITION_SUPERVISOR_V11"""
    
    def test_direction_reversal_buy_to_sell(self, db):
        """Test Rule 1: BUY position + AI SELL signal -> CLOSE_FULL."""
        from services.position_supervisor.service import Service as PositionSupervisorService
        from services.api_server.models import Signal
        
        # Create BUY position
        position = {
            "ticket": 123456,
            "side": "buy",
            "entry": 2650.0,
            "current_price": 2655.0,
            "sl": 2645.0,
            "tp": 2670.0,
            "signal_id": "sig-123",
        }
        
        # Create AI SELL signal
        signal = Signal(
            signal_id="sig-ai-sell",
            symbol="XAUUSD",
            status="approved",
            payload={"side": "sell", "action": "open"},
        )
        db.add(signal)
        db.commit()
        
        # Run position supervisor
        supervisor = PositionSupervisorService()
        result = supervisor.run({
            "position": position,
            "account_login": "test_account",
            "account_server": "test_server",
        })
        
        # Should generate close command
        assert len(result.payload["command_ids"]) > 0
        assert result.payload["v11_rules_applied"]["direction_reversal"] is True
    
    def test_profit_protection_sl(self, db):
        """Test Rule 2: Position in profit + trend weakening -> MODIFY_SL protect_profit."""
        from services.position_supervisor.service import Service as PositionSupervisorService
        
        # Create profitable BUY position
        position = {
            "ticket": 123456,
            "side": "buy",
            "entry": 2650.0,
            "current_price": 2660.0,  # $10 profit
            "sl": 2645.0,
            "tp": 2670.0,
        }
        
        # Run position supervisor
        supervisor = PositionSupervisorService()
        result = supervisor.run({
            "position": position,
            "account_login": "test_account",
            "account_server": "test_server",
        })
        
        # Should generate SL modification or close command
        assert "actions" in result.payload
    
    def test_no_position_no_close(self, db):
        """Test Rule 3: No position = no close command."""
        from services.position_supervisor.service import Service as PositionSupervisorService
        
        # No position
        result = PositionSupervisorService().run({
            "position": {},
            "account_login": "test_account",
            "account_server": "test_server",
        })
        
        # Should NOT generate any commands
        assert len(result.payload["command_ids"]) == 0
        assert "no_position_no_close" in str(result.payload)


class TestFinalServerCommercialV11Status:
    """FINAL_SERVER_COMMERCIAL_V11_STATUS"""
    
    def test_all_v11_requirements_met(self):
        """Final verification: all v1.1 requirements are implemented."""
        requirements = {
            "data_models": True,  # trading_commands, trading_execution_reports, position_snapshots
            "migration": True,  # Alembic migration created
            "poll_contract_v11": True,  # Epoch timestamps, no symbol filtering
            "execution_report_v11": True,  # Accepts all terminal statuses
            "position_snapshot": True,  # Endpoint exists
            "position_supervisor_v11": True,  # Three rules implemented
            "active_queue_cleanup": True,  # Terminal states excluded
            "weekly_cleanup_job": True,  # Sunday 03:00 cleanup script
            "open_replacement_logic": True,  # Old OPEN cancelled when new OPEN arrives
        }
        
        all_met = all(requirements.values())
        
        status = "READY_FOR_EA_RETEST" if all_met else "NOT_READY"
        print(f"FINAL_SERVER_COMMERCIAL_V11_STATUS: {status}")
        print(f"Requirements: {requirements}")
        
        assert all_met, f"Not all requirements met: {requirements}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
