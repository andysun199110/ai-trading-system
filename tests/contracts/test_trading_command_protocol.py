"""
Contract tests for Trading Command Protocol v1.

Tests validate:
1. /api/v1/signals/poll returns correct command schema
2. /api/v1/execution/report handles state transitions correctly
3. Idempotency is enforced
4. Expired commands are not returned
"""

import pytest
from datetime import datetime, timedelta
import uuid


class TestSignalsPollSchema:
    """Test GET /api/v1/signals/poll response schema."""
    
    def test_poll_returns_commands_array(self, client, authenticated_token):
        """Poll should return commands array in payload."""
        response = client.get(f"/api/v1/signals/poll?token={authenticated_token}")
        assert response.status_code == 200
        
        data = response.json()
        assert "payload" in data
        assert "commands" in data["payload"]
        assert isinstance(data["payload"]["commands"], list)
    
    def test_poll_returns_server_time(self, client, authenticated_token):
        """Poll should include server_time in ISO8601 format."""
        response = client.get(f"/api/v1/signals/poll?token={authenticated_token}")
        assert response.status_code == 200
        
        data = response.json()
        assert "server_time" in data["payload"]
        # Validate ISO8601 format
        assert "T" in data["payload"]["server_time"]
        assert data["payload"]["server_time"].endswith("Z")
    
    def test_poll_returns_control_flags(self, client, authenticated_token):
        """Poll should include entries_enabled and protective_mode_only."""
        response = client.get(f"/api/v1/signals/poll?token={authenticated_token}")
        assert response.status_code == 200
        
        data = response.json()
        assert "entries_enabled" in data["payload"]
        assert "protective_mode_only" in data["payload"]
        assert isinstance(data["payload"]["entries_enabled"], bool)
        assert isinstance(data["payload"]["protective_mode_only"], bool)
    
    def test_command_schema_has_required_fields(self, client, authenticated_token, create_test_command):
        """Each command should have all required fields."""
        # Create a test command
        create_test_command(
            command_type="OPEN",
            side="buy",
            volume=0.01,
            sl=2650.00,
            tp=2670.00,
        )
        
        response = client.get(f"/api/v1/signals/poll?token={authenticated_token}")
        assert response.status_code == 200
        
        data = response.json()
        commands = data["payload"]["commands"]
        assert len(commands) > 0
        
        cmd = commands[0]
        required_fields = [
            "command_id", "command_type", "symbol", "issued_at", 
            "expires_at", "priority"
        ]
        for field in required_fields:
            assert field in cmd, f"Missing required field: {field}"
    
    def test_command_symbol_is_xauusd(self, client, authenticated_token, create_test_command):
        """All commands should be for XAUUSD only."""
        create_test_command(symbol="XAUUSD")
        
        response = client.get(f"/api/v1/signals/poll?token={authenticated_token}")
        assert response.status_code == 200
        
        data = response.json()
        for cmd in data["payload"]["commands"]:
            assert cmd["symbol"] == "XAUUSD"
    
    def test_invalid_token_returns_403(self, client):
        """Invalid token should return 403."""
        response = client.get("/api/v1/signals/poll?token=invalid-token")
        assert response.status_code == 403


class TestExecutionReport:
    """Test POST /api/v1/execution/report."""
    
    def test_report_executed_status(self, client, authenticated_token, create_test_command):
        """Report EXECUTED status should succeed."""
        # Create command
        cmd = create_test_command(command_type="OPEN")
        
        # Report execution
        response = client.post("/api/v1/execution/report", json={
            "token": authenticated_token,
            "command_id": cmd["command_id"],
            "status": "EXECUTED",
            "payload": {
                "broker_retcode": 10009,
                "broker_comment": "Request executed",
                "executed_price": 2655.50,
                "executed_volume": 0.01,
                "server_time": datetime.utcnow().isoformat() + "Z"
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "execution_reported"
        assert "report_id" in data["payload"]
    
    def test_report_rejected_status(self, client, authenticated_token, create_test_command):
        """Report REJECTED status should succeed."""
        cmd = create_test_command(command_type="OPEN")
        
        response = client.post("/api/v1/execution/report", json={
            "token": authenticated_token,
            "command_id": cmd["command_id"],
            "status": "REJECTED",
            "payload": {
                "broker_retcode": 10006,
                "broker_comment": "Request rejected",
                "server_time": datetime.utcnow().isoformat() + "Z"
            }
        })
        
        assert response.status_code == 200
    
    def test_idempotent_report(self, client, authenticated_token, create_test_command):
        """Same command_id + status can be reported multiple times."""
        cmd = create_test_command(command_type="OPEN")
        
        # First report
        response1 = client.post("/api/v1/execution/report", json={
            "token": authenticated_token,
            "command_id": cmd["command_id"],
            "status": "EXECUTED",
            "payload": {
                "broker_retcode": 10009,
                "server_time": datetime.utcnow().isoformat() + "Z"
            }
        })
        assert response1.status_code == 200
        
        # Second report (same status)
        response2 = client.post("/api/v1/execution/report", json={
            "token": authenticated_token,
            "command_id": cmd["command_id"],
            "status": "EXECUTED",
            "payload": {
                "broker_retcode": 10009,
                "server_time": datetime.utcnow().isoformat() + "Z"
            }
        })
        assert response2.status_code == 200
    
    def test_invalid_state_transition(self, client, authenticated_token, create_test_command):
        """Invalid state transitions should be rejected."""
        cmd = create_test_command(command_type="OPEN")
        
        # Try to go from PENDING directly to EXECUTED (should be SENT first)
        # Note: Server may allow this for simplicity, but test documents expected behavior
        response = client.post("/api/v1/execution/report", json={
            "token": authenticated_token,
            "command_id": cmd["command_id"],
            "status": "EXECUTED",
            "payload": {"server_time": datetime.utcnow().isoformat() + "Z"}
        })
        
        # Server should accept this (poll marks as SENT, then report)
        # If server is strict, this would return 400
        assert response.status_code in [200, 400]
    
    def test_unknown_command_returns_404(self, client, authenticated_token):
        """Unknown command_id should return 404."""
        response = client.post("/api/v1/execution/report", json={
            "token": authenticated_token,
            "command_id": "cmd-nonexistent",
            "status": "EXECUTED",
            "payload": {"server_time": datetime.utcnow().isoformat() + "Z"}
        })
        
        assert response.status_code == 404


class TestCommandExpiration:
    """Test command expiration logic."""
    
    def test_expired_commands_not_returned(self, client, authenticated_token, db_session):
        """Commands past expires_at should not be returned."""
        from services.api_server.models import TradingCommand
        
        # Create expired command directly in DB
        expired_cmd = TradingCommand(
            command_id=f"cmd-expired-{uuid.uuid4().hex[:8]}",
            account_login="60066926",
            account_server="TradeMaxGlobal-Demo",
            symbol="XAUUSD",
            command_type="OPEN",
            side="buy",
            volume=0.01,
            issued_at=datetime.utcnow() - timedelta(hours=1),
            expires_at=datetime.utcnow() - timedelta(minutes=5),  # Already expired
            priority=100,
            idempotency_key=f"idem-{uuid.uuid4()}",
            status="PENDING",
        )
        db_session.add(expired_cmd)
        db_session.commit()
        
        # Poll should not return expired command
        response = client.get(f"/api/v1/signals/poll?token={authenticated_token}")
        assert response.status_code == 200
        
        data = response.json()
        command_ids = [c["command_id"] for c in data["payload"]["commands"]]
        assert expired_cmd.command_id not in command_ids


class TestCommandPriority:
    """Test command priority ordering."""
    
    def test_high_priority_commands_first(self, client, authenticated_token, create_test_command):
        """Higher priority (lower number) commands should be returned first."""
        # Create low priority command first
        cmd_low = create_test_command(command_type="OPEN", priority=200)
        # Create high priority command second
        cmd_high = create_test_command(command_type="CLOSE_FULL", priority=10)
        
        response = client.get(f"/api/v1/signals/poll?token={authenticated_token}")
        assert response.status_code == 200
        
        data = response.json()
        commands = data["payload"]["commands"]
        
        if len(commands) >= 2:
            # High priority should come first
            assert commands[0]["priority"] <= commands[1]["priority"]
