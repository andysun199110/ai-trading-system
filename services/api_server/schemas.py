from datetime import datetime

from pydantic import BaseModel, Field


class ActivateRequest(BaseModel):
    license_key: str
    account_login: str
    account_server: str


class ActivateResponse(BaseModel):
    token: str
    expires_at: datetime
    mode: str


class HeartbeatRequest(BaseModel):
    token: str


class LogoutRequest(BaseModel):
    token: str


class CustomerCreateRequest(BaseModel):
    name: str
    email: str
    plan_type: str
    seat_limit: int = 1


class LicenseCreateRequest(BaseModel):
    customer_id: int
    license_key: str
    expires_at: datetime


class ExtendLicenseRequest(BaseModel):
    license_key: str
    expires_at: datetime


class RevokeLicenseRequest(BaseModel):
    license_key: str


class BindAccountRequest(BaseModel):
    license_key: str
    account_login: str
    account_server: str


class AccountControlRequest(BindAccountRequest):
    pass


class DeploymentPromoteRequest(BaseModel):
    environment: str = Field(pattern="^(develop|research|shadow|staging|live)$")
    version: str


class ExecutionReportRequest(BaseModel):
    token: str
    signal_id: str
    status: str
    payload: dict = Field(default_factory=dict)


class EAHealthRequest(BaseModel):
    token: str
    terminal: str
    payload: dict = Field(default_factory=dict)


# ============== Trading Command Protocol Schemas ==============

class CommandPayload(BaseModel):
    """Payload structure for trading commands."""
    command_type: str  # OPEN, MODIFY_SL, MODIFY_TP, CLOSE_PARTIAL, CLOSE_FULL, CANCEL_OPEN
    symbol: str = "XAUUSD"
    side: str | None = None  # buy, sell
    volume: float | None = None
    sl: float | None = None  # Stop loss price
    tp: float | None = None  # Take profit price
    sl_points: int | None = None  # Stop loss in points (alternative to sl)
    tp_points: int | None = None  # Take profit in points (alternative to tp)
    close_ratio: float | None = None  # 0~1 for partial close
    position_ref: str | None = None  # Position ticket or signal_id
    signal_id: str | None = None
    strategy_version: str | None = None
    config_version: str | None = None


class TradingCommandResponse(BaseModel):
    """Response structure for a single trading command in poll response (v1.1)."""
    command_id: str
    idempotency_key: str
    signal_id: str | None = None
    account_login: str
    account_server: str
    command_type: str
    side: str | None = None
    volume: float | None = None
    sl: float | None = None
    tp: float | None = None
    entry_ref_price: float | None = None
    max_adverse_move_price: float | None = None
    created_at_epoch: int
    expires_at_epoch: int
    priority: int = 100
    payload: dict = Field(default_factory=dict)


class PollCommandsResponse(BaseModel):
    """Response structure for GET /api/v1/signals/poll."""
    message: str = "ok"
    payload: dict
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "ok",
                "payload": {
                    "commands": [
                        {
                            "command_id": "cmd-uuid-123",
                            "command_type": "OPEN",
                            "symbol": "XAUUSD",
                            "side": "buy",
                            "volume": 0.01,
                            "sl": 2650.00,
                            "tp": 2670.00,
                            "signal_id": "sig-uuid-456",
                            "issued_at": "2026-04-24T10:00:00Z",
                            "expires_at": "2026-04-24T10:10:00Z",
                            "priority": 100,
                            "payload": {}
                        }
                    ],
                    "server_time": "2026-04-24T10:00:00Z",
                    "entries_enabled": True,
                    "protective_mode_only": False
                }
            }
        }


class ExecutionReportRequest(BaseModel):
    """Request structure for POST /api/v1/execution/report (v1.1)."""
    token: str
    command_id: str
    status: str  # executed, failed, expired, rejected, duplicate, shadow_skipped, trading_disabled
    payload: dict = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "token": "session-token-xxx",
                "command_id": "cmd-uuid-123",
                "status": "executed",
                "payload": {
                    "broker_retcode": 10009,
                    "broker_comment": "Request executed",
                    "executed_price": 2655.50,
                    "executed_volume": 0.01,
                    "executed_symbol": "XAUUSD",
                    "sl": 2650.00,
                    "tp": 2670.00,
                    "server_time": "2026-04-24T10:00:05Z"
                }
            }
        }


class AdminCommandsQuery(BaseModel):
    """Query parameters for GET /admin/commands."""
    account_login: str | None = None
    status: str | None = None
    command_type: str | None = None
    signal_id: str | None = None
    limit: int = Field(default=100, ge=1, le=500)


class AdminExecutionReportsQuery(BaseModel):
    """Query parameters for GET /admin/execution-reports."""
    command_id: str | None = None
    status: str | None = None
    limit: int = Field(default=100, ge=1, le=500)


class PositionSnapshotRequest(BaseModel):
    """Request structure for POST /api/v1/positions/snapshot (v1.1)."""
    token: str
    account_login: str
    account_server: str
    positions: list[dict] = Field(default_factory=list)
    
    class Config:
        json_schema_extra = {
            "example": {
                "token": "session-token-xxx",
                "account_login": "12345678",
                "account_server": "MetaQuotes-Demo",
                "positions": [
                    {
                        "ticket": 123456,
                        "symbol": "XAUUSD",
                        "side": "buy",
                        "volume": 0.01,
                        "entry_price": 2650.00,
                        "current_price": 2655.50,
                        "sl": 2645.00,
                        "tp": 2670.00,
                        "swap": -0.50,
                        "profit": 5.50,
                    }
                ]
            }
        }
